"""Modal.com cron worker: scrape → hash → enrich → upsert + Friday digests.

Deploy:
  modal deploy worker/modal_app.py

Schedules:
  - ingest every 6 hours
  - weekly alerts Friday 02:30 UTC (≈ 08:00 IST)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import modal

# Run from the worker/ directory so these modules resolve for add_local_python_source.
_WORKER_DIR = Path(__file__).resolve().parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "playwright==1.48.0",
        "instructor>=1.6.0",
        "anthropic>=0.40.0",
        "openai>=1.54.0",
        "pydantic>=2.9.0",
        "httpx>=0.27.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.10",
        "python-dotenv>=1.0.1",
        "kaggle>=1.6.17",
    )
    .run_commands("playwright install chromium --with-deps")
    # Ship scraper/enrichment modules into the container (modal_app.py alone is not enough).
    .add_local_python_source("enrichment", "db_writer", "schemas", "scrapers")
)

app = modal.App("findhackathons-ingestion", image=image)

secrets = modal.Secret.from_name("findhackathons-secrets")


def _run_pipeline(limit_per_source: int = 20, kaggle_limit: int = 500) -> Dict[str, int]:
    # Local imports so Modal serializes cleanly
    import sys

    worker_dir = Path(__file__).resolve().parent
    if str(worker_dir) not in sys.path:
        sys.path.insert(0, str(worker_dir))
    # Also ensure /root (Modal default mount) is on path when modules are added there.
    if "/root" not in sys.path:
        sys.path.insert(0, "/root")

    api_url = (os.getenv("BACKEND_API_URL") or "").rstrip("/")
    has_token = bool((os.getenv("INGEST_TOKEN") or "").strip())
    print(f"[pipeline] BACKEND_API_URL={api_url or '(missing)'} INGEST_TOKEN_set={has_token}")
    if not api_url:
        raise RuntimeError(
            "BACKEND_API_URL is not set in Modal secret findhackathons-secrets. "
            "Set it to https://findhackathons-production.up.railway.app"
        )
    if not has_token:
        raise RuntimeError(
            "INGEST_TOKEN is not set in Modal secret findhackathons-secrets. "
            "It must match Railway Variables → INGEST_TOKEN exactly."
        )

    from enrichment import content_hash, enrich_or_none
    from db_writer import deactivate_stale, upsert_listing
    from scrapers.devfolio import fetch_devfolio
    from scrapers.devpost import fetch_devpost
    from scrapers.kaggle import fetch_kaggle, iter_prize_stats
    from scrapers.unstop import fetch_unstop

    kaggle_rows = fetch_kaggle(limit=kaggle_limit)
    print(f"[pipeline] kaggle stats: {iter_prize_stats(kaggle_rows)}")

    raw_batches = [
        ("kaggle", kaggle_rows),
        ("devpost", fetch_devpost(limit=max(limit_per_source, 60))),
        ("devfolio", fetch_devfolio(limit=max(limit_per_source, 60))),
        ("unstop", fetch_unstop(limit=20)),  # product: only nearest ~20
    ]

    stats = {
        "fetched": 0,
        "enriched": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "failed": 0,
        "kaggle_structured": 0,
    }

    for source, rows in raw_batches:
        for row in rows:
            stats["fetched"] += 1
            digest = content_hash(row.raw_text)
            structured = getattr(row, "structured", None)
            if structured:
                stats["kaggle_structured"] += 1
            try:
                enriched = enrich_or_none(
                    row.raw_text,
                    source_url=row.url,
                    organizer_hint=row.organizer,
                    structured=structured,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[pipeline] enrich failed for {row.url}: {exc}")
                stats["failed"] += 1
                continue
            if not enriched:
                stats["failed"] += 1
                continue
            # Preserve source URL when model invents one
            if not enriched.url:
                enriched.url = row.url
            stats["enriched"] += 1
            try:
                status = upsert_listing(
                    enriched=enriched,
                    source=source,
                    content_hash=digest,
                    raw_snippet=row.raw_text,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[pipeline] ingest failed for {row.url}: {exc}")
                stats["failed"] += 1
                continue
            stats[status] = stats.get(status, 0) + 1

    stale = deactivate_stale(days=2)
    stats["deactivated"] = stale
    print(f"[pipeline] done: {stats}")
    return stats


@app.function(
    schedule=modal.Cron("0 */6 * * *"),
    secrets=[secrets],
    timeout=60 * 30,
    memory=2048,
)
def ingest_cron():
    return _run_pipeline()


@app.function(secrets=[secrets], timeout=60 * 30, memory=2048)
def ingest_kaggle_only():
    """One-shot Kaggle sync for manual runs: modal run worker/modal_app.py::ingest_kaggle_only"""
    import sys

    worker_dir = Path(__file__).resolve().parent
    if str(worker_dir) not in sys.path:
        sys.path.insert(0, str(worker_dir))
    if "/root" not in sys.path:
        sys.path.insert(0, "/root")

    from enrichment import content_hash, enrich_or_none
    from db_writer import upsert_listing
    from scrapers.kaggle import fetch_kaggle, iter_prize_stats

    rows = fetch_kaggle(limit=500)
    print(f"[kaggle-only] stats: {iter_prize_stats(rows)}")
    stats = {"fetched": 0, "enriched": 0, "created": 0, "updated": 0, "unchanged": 0, "failed": 0}
    for row in rows:
        stats["fetched"] += 1
        enriched = enrich_or_none(
            row.raw_text,
            source_url=row.url,
            organizer_hint=row.organizer,
            structured=row.structured,
        )
        if not enriched:
            stats["failed"] += 1
            continue
        stats["enriched"] += 1
        status = upsert_listing(
            enriched=enriched,
            source="kaggle",
            content_hash=content_hash(row.raw_text),
            raw_snippet=row.raw_text,
        )
        stats[status] = stats.get(status, 0) + 1
    print(f"[kaggle-only] done: {stats}")
    return stats


@app.function(
    schedule=modal.Cron("30 2 * * 5"),  # Friday 02:30 UTC ≈ 08:00 IST
    secrets=[secrets],
    timeout=60 * 15,
    memory=512,
)
def weekly_alerts_cron():
    """Trigger Railway to email Friday digests to active subscribers."""
    import httpx

    api_url = (os.getenv("BACKEND_API_URL") or "").rstrip("/")
    token = (os.getenv("INGEST_TOKEN") or "").strip()
    if not api_url:
        raise RuntimeError("BACKEND_API_URL missing from findhackathons-secrets")
    if not token:
        raise RuntimeError("INGEST_TOKEN missing from findhackathons-secrets")

    url = f"{api_url}/api/internal/alerts/send-weekly"
    print(f"[weekly-alerts] POST {url}")
    response = httpx.post(
        url,
        headers={"X-Ingest-Token": token},
        timeout=60 * 14,
    )
    print(f"[weekly-alerts] status={response.status_code} body={response.text[:800]}")
    response.raise_for_status()
    return response.json()


@app.function(secrets=[secrets], timeout=60 * 15, memory=512)
def weekly_alerts_once(dry_run: bool = False, force: bool = False):
    """Manual digests: modal run worker/modal_app.py::weekly_alerts_once"""
    import httpx

    api_url = (os.getenv("BACKEND_API_URL") or "").rstrip("/")
    token = (os.getenv("INGEST_TOKEN") or "").strip()
    params = []
    if dry_run:
        params.append("dry_run=true")
    if force:
        params.append("force=true")
    qs = ("?" + "&".join(params)) if params else ""
    url = f"{api_url}/api/internal/alerts/send-weekly{qs}"
    response = httpx.post(
        url,
        headers={"X-Ingest-Token": token},
        timeout=60 * 14,
    )
    print(f"[weekly-alerts-once] {response.status_code} {response.text[:800]}")
    response.raise_for_status()
    return response.json()


@app.local_entrypoint()
def main():
    """Run once on Modal (not locally) so secrets + Railway ingest apply.

    Usage (from worker/):
      py -m modal run modal_app.py
    """
    # IMPORTANT: call .remote() so findhackathons-secrets are injected and
    # upserts go to BACKEND_API_URL (Railway). A bare _run_pipeline() call
    # runs on the laptop and falls back to local sqlite.
    print(ingest_cron.remote())
