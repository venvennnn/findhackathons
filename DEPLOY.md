# Deploy FindHackathons

Production stack:

```
Next.js (Vercel)  →  FastAPI (Railway)  →  Supabase Postgres
                                              ↑
                                   Modal.com worker (optional)
```

You can launch with steps **1–3** only. Modal is optional until you want live scraping.

---

## 1. Database (Supabase)

1. Create a free project at [supabase.com](https://supabase.com).
2. Open **Project Settings → Database**.
3. Copy the **URI** connection string, e.g.
   `postgresql://postgres:PASSWORD@db.<project>.supabase.co:5432/postgres`
4. Keep this as `DATABASE_URL` for Railway.

Tables are created automatically when the API boots (`SQLModel.create_all`). Demo listings seed if the DB is empty.

---

## 2. Backend API (Railway)

Config in this repo: `backend/railway.toml` + `backend/Procfile`.

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**.
2. Select this repository.
3. Set **Root Directory** to `backend` (or rely on `backend/railway.toml` if Railway detects it).
4. Add a **public HTTP** domain for the service.
5. Set environment variables:

| Variable | Example | Required |
| --- | --- | --- |
| `DATABASE_URL` | Supabase URI from step 1 | Yes |
| `CORS_ORIGINS` | `https://findhackathons.com,https://your-app.vercel.app` | Yes |
| `INGEST_TOKEN` | long random string | Yes (for worker) |
| `OPENAI_API_KEY` | `sk-...` | No (heuristic ranking works without it) |
| `OPENAI_MODEL` | `gpt-4o-mini` | No |
| `ENVIRONMENT` | `production` | No |

6. Redeploy, then open:
   - `https://<your-railway-domain>/api/health`
   - Expect `"status":"ok"` and a non-zero `listings_count` after first boot.

Start command used in production:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 3. Frontend (Vercel)

Config in this repo: `frontend/vercel.json`.

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → import this GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Next.js** (auto-detected).
4. Environment variable:

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Railway public URL, **no trailing slash** (e.g. `https://findhackathons-api.up.railway.app`) |

5. Deploy.
6. Optional custom domain:
   - Vercel → Project → **Domains** → add `findhackathons.com`
   - Point DNS as Vercel instructs (usually A/`@` + CNAME `www`)
7. Update Railway `CORS_ORIGINS` to include your final Vercel / custom domain, then redeploy the API.

---

## 4. Ingestion worker (Modal) — optional

Without Modal, the site still works on seeded demo listings.

```bash
cd worker
pip install modal
modal setup

modal secret create findhackathons-secrets \
  OPENAI_API_KEY=sk-... \
  BACKEND_API_URL=https://<your-railway-domain> \
  INGEST_TOKEN=<same-as-railway>

modal deploy modal_app.py   # schedule: every 6 hours
modal run modal_app.py      # one-shot test
```

Secrets expected by `worker/modal_app.py`:

- `OPENAI_API_KEY` — required for LLM enrichment
- `BACKEND_API_URL` — Railway API base URL
- `INGEST_TOKEN` — must match Railway
- `KAGGLE_USERNAME` / `KAGGLE_KEY` — optional

The worker posts enriched listings to `POST /api/internal/ingest`.

---

## Smoke checklist

After deploy:

1. `GET /api/health` → `ok`
2. Open the Vercel URL → listings appear
3. Use **Match me** → shortlist returns
4. Subscribe with a test email → `/api/alerts/subscribe` succeeds
5. (Optional) `modal run modal_app.py` → health `listings_count` may increase

---

## Local vs production

| Concern | Local | Production |
| --- | --- | --- |
| DB | SQLite file | Supabase Postgres |
| API | `localhost:8000` | Railway |
| Web | `localhost:3000` | Vercel |
| Scrapers | off / manual | Modal cron |

---

## Cost (typical v1)

All four free tiers are enough for early traffic:

- Supabase free Postgres
- Railway hobby / trial for API
- Vercel hobby for frontend
- Modal free tier for the cron worker

---

## Troubleshooting

**Frontend shows API errors**
- `NEXT_PUBLIC_API_URL` wrong or includes a trailing slash
- Railway service sleeping / not public
- `CORS_ORIGINS` missing the Vercel domain

**Empty listings**
- Hit `/api/health` — if `listings_count` is 0, restart the API once so seed runs
- Or run Modal once to ingest live sources

**Ingest rejected**
- `INGEST_TOKEN` mismatch between Railway and Modal
- Worker `BACKEND_API_URL` missing `https://`