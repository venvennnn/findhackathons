from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import engine, init_db_with_retry
from app.services.cleanup import deactivate_broken_demo_listings
from app.services.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Keep the server boot resilient: retry DB so Railway healthchecks can pass
    # even if Supabase is briefly unreachable at cold start.
    try:
        init_db_with_retry()
        with Session(engine) as session:
            created = seed_if_empty(session)
            if created:
                print(f"[db] seeded {created} demo listings")
            cleaned = deactivate_broken_demo_listings(session)
            if cleaned:
                print(f"[db] deactivated {len(cleaned)} broken demo listings")
    except Exception as exc:  # noqa: BLE001
        # Still start the HTTP server so /api/health can report the error.
        print(f"[db] startup warning: {exc}")
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
    }