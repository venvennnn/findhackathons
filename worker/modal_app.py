"""Modal.com cron worker: scrape → hash → enrich → upsert.

Deploy:
  modal deploy worker/modal_app.py

Schedule: every 6 hours.
"""

from __future__ import annotations

import asyncio
import os
from typing import Dict, List

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "playwright==1.48.0",
        "instructor>=1.6.0",
        "openai>=1.54.0",
        "pydantic>=2.9.0",
        "httpx>=0.27.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.10",
        "python-dotenv>=1.0.1",
    )
    .run_commands("playwright install chromium --with-deps")
)

app = modal.App("findhackathons-ingestion", image=image)

secrets = modal.Secret.from_name("findhackathons-secrets")


def _run_pipeline(limit_per_source: int = 20) -> Dict[str, int]:
    # Local imports so Modal serializes cleanly
    import sys
    from pathlib import Path

    worker_dir = Path(__file__).resolve().parent
    if str(worker_dir) not in sys.path:
        sys.path.insert(0, str(worker_dir))

    from enrichment import content_hash, enrich_or_none
    from db_writer import deactivate_stale, upsert_listing
    from scrapers.devfolio import fetch_devfolio
    from scrapers.devpost import fetch_devpost
    from scrapers.kaggle import fetch_kaggle
    from scrapers.unstop import fetch_unstop

    raw_batches = [
        ("kaggle", fetch_kaggle(limit=limit_per_source)),
        ("devpost", fetch_devpost(limit=limit_per_source)),
        ("devfolio", fetch_devfolio(limit=limit_per_source)),
        ("unstop", fetch_unstop(limit=limit_per_source)),
    ]

    # Prefer Playwright for Unstop when available
    try:
        from scrapers.unstop import fetch_unstop_playwright

        unstop_pw = asyncio.get_event_loop().run_until_complete(
            fetch_unstop_playwright(limit=limit_per_source)
        )
        if unstop_pw:
            raw_batches = [b for b in raw_batches if b[0] != "unstop"] + [("unstop", unstop_pw)]
    except Exception as exc:  # noqa: BLE001
        print(f"[pipeline] playwright unstop skipped: {exc}")

    stats = {"fetched": 0, "enriched": 0, "created": 0, "updated": 0, "unchanged": 0, "failed": 0}

    for source, rows in raw_batches:
        for row in rows:
            stats["fetched"] += 1
            digest = content_hash(row.raw_text)
            enriched = enrich_or_none(
                row.raw_text,
                source_url=row.url,
                organizer_hint=row.organizer,
            )
            if not enriched:
                stats["failed"] += 1
                continue
            # Preserve source URL when model invents one
            if not enriched.url:
                enriched.url = row.url
            stats["enriched"] += 1
            status = upsert_listing(
                enriched=enriched,
                source=source,
                content_hash=digest,
                raw_snippet=row.raw_text,
            )
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


@app.local_entrypoint()
def main():
    """Run once locally/remotely: modal run worker/modal_app.py"""
    print(_run_pipeline(limit_per_source=5))