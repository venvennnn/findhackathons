# FindHackathons ingestion worker

Modal.com cron that runs every 6 hours:

1. Fetch listings from Kaggle, Devpost, Devfolio, Unstop
2. SHA-256 hash raw content (skip unchanged)
3. Enrich (structured scraper fields first; otherwise Claude via `OPENAI_API_KEY`)
4. Upsert through `POST /api/internal/ingest`

## Kaggle

Kaggle is the priority source. The scraper:

- Uses the **official Competitions API** with `KAGGLE_USERNAME` + `KAGGLE_KEY`
  (or `KAGGLE_API_TOKEN`)
- Sweeps featured / research / recruitment / gettingStarted / playground /
  masters **and** `group=community`
- Parses cash prizes (`$25,000`) vs Knowledge/Swag (stored as no prize)
- Falls back to Playwright against Kaggle’s internal ListCompetitions API when
  credentials are missing (often reCAPTCHA-blocked from datacenter IPs)

The site feed defaults to **cash-prize competitions only**. Knowledge / no-prize
comps are ingested but only shown when the user selects “Include no-prize”.

## Secrets (Modal secret name: `findhackathons-secrets`)

- `KAGGLE_USERNAME` / `KAGGLE_KEY` (required for reliable Kaggle ingest)
- `OPENAI_API_KEY` — **Anthropic/Claude key** (`sk-ant-…`); env name unchanged on purpose
- `OPENAI_MODEL` (optional Claude model id, default `claude-haiku-4-5-20251001`)
- `BACKEND_API_URL` (e.g. `https://api.findhackathons.com`)
- `INGEST_TOKEN` (shared with backend)
- `DATABASE_URL` (optional direct DB fallback)

## Commands

```bash
modal secret create findhackathons-secrets \
  KAGGLE_USERNAME=... \
  KAGGLE_KEY=... \
  OPENAI_API_KEY=sk-ant-... \
  BACKEND_API_URL=https://... \
  INGEST_TOKEN=...

modal deploy modal_app.py
modal run modal_app.py
# Kaggle-only sync:
modal run worker/modal_app.py::ingest_kaggle_only
```

Local unit tests (no network):

```bash
cd worker && python -m pytest tests/test_kaggle_prize.py -q
```