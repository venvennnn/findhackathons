# FindHackathons

AI-enriched discovery layer and alert system for developer hackathons and data science competitions.

**Goal:** A beginner goes from landing page to a shortlist of 3–5 finishable hackathons in under 90 seconds.

## Architecture

```
Next.js (Vercel)  →  FastAPI (Railway)  →  Supabase Postgres
                                              ↑
                                   Modal.com ingestion worker
                                   (Playwright + Instructor + OpenAI)
```

| Layer | Stack | Host |
| --- | --- | --- |
| Frontend | Next.js App Router, Tailwind | Vercel |
| Backend | FastAPI, SQLModel | Railway |
| Worker | Playwright, Instructor, OpenAI | Modal.com |
| Database | PostgreSQL (SQLite locally) | Supabase |

## Monorepo layout

```
backend/     FastAPI API, SQLModel models, matching engine, Alembic
frontend/    Next.js UI (landing, onboarding, ranked feed, alerts)
worker/      Modal cron scrapers + LLM enrichment pipeline
```

## Quick start (local)

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

On boot the API seeds 10 demo listings (Devfolio / Unstop / Kaggle / Devpost) if the DB is empty.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

App: [http://localhost:3000](http://localhost:3000)

### 3. Ingestion worker (optional)

```bash
cd worker
pip install -r requirements.txt
# Set OPENAI_API_KEY + BACKEND_API_URL + INGEST_TOKEN
modal deploy modal_app.py   # every 6 hours
modal run modal_app.py      # one-shot
```

## Core API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health + listing count |
| `GET` | `/api/listings` | Deterministic filtered inventory |
| `POST` | `/api/listings/{id}/interest` | Phase 0: private teammate interest signal |
| `POST` | `/api/profiles` | Create preference profile |
| `POST` | `/api/match` | Hybrid SQL filter + LLM/heuristic rank (top 5) |
| `POST` | `/api/alerts/subscribe` | Email alert capture (+ optional looking-for-team) |
| `POST` | `/api/internal/ingest` | Worker upsert (token-gated) |
| `GET` | `/api/internal/demand` | Phase 0 teammate demand dashboard (token-gated) |

### Teammate finding (Phase 0)

No public teammate marketplace yet (auth + empty-state risk). Phase 0 only:

- capture `looking_for_team` / `team_needs` on alerts + per-listing interest
- show ambient counts only after a listing hits the threshold (default 8)
- link out to the event’s own team channel when known
- measure demand via `GET /api/internal/demand`

Phase 1 (public profiles + relayed contact) ships only if the Phase 0 gate passes.

## Matching flow

1. **Deterministic filters (SQL):** drop expired deadlines, ineligible countries, travel mismatches, over-skill listings.
2. **Probabilistic rank:** shortlist ≤40 candidates; OpenAI ranks top 5 with a one-sentence fit reason when `OPENAI_API_KEY` is set; otherwise a heuristic ranker is used.
3. **Empty / sparse state:** if &lt;3 exact matches, broaden domains, label expanded results, and prompt for weekly alerts.

## Deploy (production)

Step-by-step hosting guide: **[DEPLOY.md](./DEPLOY.md)**

Quick path:

1. **Supabase** — create Postgres; copy `DATABASE_URL`.
2. **Railway** — deploy API via root `Dockerfile` (or set Root Directory to `backend`); set `DATABASE_URL`, `CORS_ORIGINS`, `INGEST_TOKEN`.
3. **Vercel** — deploy `frontend/`; set `BACKEND_URL` to the Railway URL (not the Vercel URL).
4. **Modal** (optional) — `modal deploy worker/modal_app.py` for live scraping every 6 hours.
5. Attach custom DNS for `findhackathons.com` in Vercel.

## Tests

```bash
cd backend && source .venv/bin/activate && pytest -q
```

## V1 scope

**In:** Tier-1 ingestion sources, AI enrichment schema, onboarding + ranked feed, email alert capture.

**Out:** Native hosting/submissions, team matchmaking, monetization, native mobile apps.
