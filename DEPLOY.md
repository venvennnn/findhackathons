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

This monorepo includes a **root `Dockerfile` + `railway.toml`**, so Railway can build the API even if Root Directory is `/`.

### Recommended setup

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub** → this repo.
2. Open the service → **Settings**:
   - **Root Directory:** leave empty **or** set to `backend` (both work after this fix)
   - **Builder:** should pick up `Dockerfile` / `railway.toml` automatically  
     If you previously set a custom build command, **clear it**.
3. Generate a **public domain** (Settings → Networking → Generate Domain).
4. Set environment variables:

| Variable | Example | Required |
| --- | --- | --- |
| `DATABASE_URL` | Supabase URI from step 1 (**append `?sslmode=require` if missing**) | Yes |
| `CORS_ORIGINS` | `https://findhackathons.com,https://your-app.vercel.app` | Yes |
| `INGEST_TOKEN` | long random string | Yes (for worker) |
| `OPENAI_API_KEY` | `sk-...` | No (heuristic ranking works without it) |
| `OPENAI_MODEL` | `gpt-4o-mini` | No |
| `ENVIRONMENT` | `production` | No |

5. **Redeploy** (Deployments → Redeploy), then open:
   - `https://<your-railway-domain>/api/health`
   - Expect `"status":"ok"` and a non-zero `listings_count` after first boot.

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### If you still see “Railpack could not determine how to build”

Railway is analyzing the monorepo root without a Dockerfile config. Do one of:

1. Merge/pull latest main (must include root `Dockerfile` + `railway.toml`), then redeploy  
2. Or set **Root Directory** = `backend` and clear custom build/start overrides  
3. Or in Variables set `RAILWAY_DOCKERFILE_PATH=Dockerfile`
---

## 3. Frontend (Vercel)

Config in this repo: `frontend/vercel.json`.

The Next.js app proxies `/api/*` to Railway, so the browser never needs a public API URL.

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → import this GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Next.js** (auto-detected).
4. Environment variable:

| Variable | Value |
| --- | --- |
| `BACKEND_URL` | Railway public URL, **no trailing slash** (e.g. `https://findhackathons-api.up.railway.app`) |

> If you previously set `NEXT_PUBLIC_API_URL` to your **Vercel** URL, that causes the HTML 404 dump on the homepage. Remove it or replace with the Railway URL, and prefer `BACKEND_URL`.

5. Deploy / Redeploy.
6. Optional custom domain:
   - Vercel → Project → **Domains** → add `findhackathons.com`
   - Point DNS as Vercel instructs (usually A/`@` + CNAME `www`)
7. Update Railway `CORS_ORIGINS` to include your final Vercel / custom domain (still useful for direct API access), then redeploy the API.

Quick checks:
- Railway: `https://YOUR-RAILWAY-URL/api/health` → JSON `"status":"ok"`
- Vercel site should list competitions, not show raw HTML
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
- `KAGGLE_USERNAME` / `KAGGLE_KEY` — **required for Kaggle** (featured + community).
  Without these, Kaggle’s site is reCAPTCHA-gated from most cloud IPs.
  Create a token at https://www.kaggle.com/settings → API.

The worker posts enriched listings to `POST /api/internal/ingest`.
The public feed defaults to cash-prize competitions; Knowledge / no-prize comps
are ingested but only shown when the user selects “Include no-prize”.

### Teammate finding (Phase 0)

Optional env on Railway:

- `TEAMMATE_INTEREST_THRESHOLD=8` — ambient “N people looking for teammates”
  only appears on a listing once interest hits this count.

Internal demand dashboard (same token as ingest):

```bash
curl -H "X-Ingest-Token: $INGEST_TOKEN" https://YOUR-RAILWAY-URL/api/internal/demand
```

`gate_passed` is true when ≥15% of email profiles are looking for a team **and**
at least one listing has ≥ threshold interests. Do not build Phase 1 public
teammate profiles until that gate passes.

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

**Railway healthcheck fails / service unavailable**
- Open Railway → Deployments → **View Logs** (not just build logs) for the Python traceback
- Confirm `DATABASE_URL` is set and password is URL-encoded
- Use a URI like:
  `postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres?sslmode=require`
- Prefer Supabase **Direct** connection (port `5432`), not the serverless pooler, for this API
- After deploy, `/api/health` should return JSON even if DB is degraded

**Railway: `pip: command not found` / Railpack “could not determine how to build”**
- Pull latest main (root `Dockerfile` + `railway.toml`), clear custom Build Command, redeploy
- Or set Root Directory = `backend`
- Or set variable `RAILWAY_DOCKERFILE_PATH=Dockerfile`