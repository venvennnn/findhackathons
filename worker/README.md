# FindHackathons ingestion worker

Modal.com cron that runs every 6 hours:

1. Fetch listings from Kaggle, Devpost, Devfolio, Unstop
2. SHA-256 hash raw content (skip unchanged)
3. Enrich with OpenAI via `instructor` into the `HackathonListing` schema
4. Upsert through `POST /api/internal/ingest`

## Secrets (Modal secret name: `findhackathons-secrets`)

- `OPENAI_API_KEY` (required for enrichment)
- `BACKEND_API_URL` (e.g. `https://api.findhackathons.com`)
- `INGEST_TOKEN` (shared with backend)
- `DATABASE_URL` (optional direct DB fallback)
- `KAGGLE_USERNAME` / `KAGGLE_KEY` (optional)

## Commands

```bash
modal secret create findhackathons-secrets \
  OPENAI_API_KEY=... \
  BACKEND_API_URL=https://... \
  INGEST_TOKEN=...

modal deploy modal_app.py
modal run modal_app.py
```