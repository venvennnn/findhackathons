from functools import lru_cache
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Normalize Postgres URLs for Supabase / Railway."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    if not url.startswith("postgresql"):
        return url

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    # Supabase requires TLS; without this, connections often fail in hosted envs.
    query.setdefault("sslmode", "require")
    return urlunparse(parsed._replace(query=urlencode(query)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./findhackathons.db"
    openai_api_key: str = ""
    # Env name kept for compatibility; value should be an Anthropic/Claude model id.
    openai_model: str = "claude-haiku-4-5-20251001"
    cors_origins: str = "http://localhost:3000,https://findhackathons.com"
    environment: str = "development"
    app_name: str = "FindHackathons API"
    app_version: str = "0.1.0"
    ingest_token: str = ""
    # Ambient teammate count appears on cards once this many people signal interest.
    teammate_interest_threshold: int = 1
    # Shared Discord channel where people introduce themselves / find teammates.
    discord_team_url: str = (
        "https://discord.com/channels/1535536397463724062/1535536398093000708"
    )
    # Weekly digest email (Resend). Leave resend_api_key empty to disable sends.
    resend_api_key: str = ""
    email_from: str = "FindHackathons <onboarding@resend.dev>"
    # Public site URL used in unsubscribe links (Vercel / custom domain).
    app_base_url: str = "https://findhackathons-six.vercel.app"
    # Max listings per Friday digest email.
    alerts_digest_limit: int = 8

    @property
    def sqlalchemy_database_url(self) -> str:
        return normalize_database_url(self.database_url)

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()