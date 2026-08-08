from collections.abc import Generator
import time

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(
    settings.sqlalchemy_database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)


# Columns added after initial create_all — applied on boot for existing DBs.
_COLUMN_MIGRATIONS = (
    ("listings", "team_channel_url", "ALTER TABLE listings ADD COLUMN team_channel_url VARCHAR"),
    (
        "user_profiles",
        "looking_for_team",
        "ALTER TABLE user_profiles ADD COLUMN looking_for_team BOOLEAN DEFAULT FALSE",
    ),
    (
        "user_profiles",
        "team_needs",
        "ALTER TABLE user_profiles ADD COLUMN team_needs JSON",
    ),
)


def ensure_schema() -> None:
    """create_all for new tables + additive column patches for existing DBs."""
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in _COLUMN_MIGRATIONS:
            if table not in inspector.get_table_names():
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            if column in existing:
                continue
            conn.execute(text(ddl))
            print(f"[db] added column {table}.{column}")


def init_db() -> None:
    ensure_schema()


def init_db_with_retry(*, attempts: int = 10, delay_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            init_db()
            print(f"[db] connected and schema ready (attempt {attempt})")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[db] init failed attempt {attempt}/{attempts}: {exc}")
            time.sleep(delay_seconds)
    raise RuntimeError(f"Database init failed after {attempts} attempts: {last_error}")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
