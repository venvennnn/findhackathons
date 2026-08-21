from collections.abc import Generator
import time
from uuid import uuid4

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
        "listings",
        "community_submitted",
        "ALTER TABLE listings ADD COLUMN community_submitted BOOLEAN DEFAULT FALSE",
    ),
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
    (
        "alert_subscriptions",
        "unsubscribe_token",
        "ALTER TABLE alert_subscriptions ADD COLUMN unsubscribe_token VARCHAR",
    ),
)


def _migrate_postgres_source_column(conn) -> None:
    """Convert listings.source from native ENUM to VARCHAR so new values (manual) work."""
    row = conn.execute(
        text(
            """
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'listings'
              AND column_name = 'source'
            """
        )
    ).first()
    if not row:
        return
    data_type, udt_name = row[0], row[1]
    if data_type == "USER-DEFINED" or (udt_name and udt_name.lower() == "sourceplatform"):
        conn.execute(
            text(
                "ALTER TABLE listings ALTER COLUMN source TYPE VARCHAR(32) "
                "USING source::text"
            )
        )
        print("[db] migrated listings.source from enum to VARCHAR(32)")
        # Best-effort cleanup of the old enum type if nothing else uses it.
        conn.execute(text("DROP TYPE IF EXISTS sourceplatform"))
        print("[db] dropped unused sourceplatform enum type")


def _ensure_postgres_enum_value(conn, type_name: str, value: str) -> None:
    """Fallback if source is still a native enum: add the missing label."""
    exists = conn.execute(
        text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": type_name},
    ).first()
    if not exists:
        return
    conn.execute(
        text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{value}'")
    )
    print(f"[db] ensured enum {type_name} has value '{value}'")


def ensure_schema() -> None:
    """create_all for new tables + additive patches for existing DBs."""
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    dialect = engine.dialect.name

    with engine.begin() as conn:
        for table, column, ddl in _COLUMN_MIGRATIONS:
            if table not in inspector.get_table_names():
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            if column in existing:
                continue
            conn.execute(text(ddl))
            print(f"[db] added column {table}.{column}")

        # Backfill unsubscribe tokens for rows created before the column existed.
        try:
            if "alert_subscriptions" in inspector.get_table_names():
                # Re-inspect so a column added above is visible.
                fresh = inspect(engine)
                cols = {col["name"] for col in fresh.get_columns("alert_subscriptions")}
                if "unsubscribe_token" in cols:
                    rows = conn.execute(
                        text(
                            "SELECT id FROM alert_subscriptions "
                            "WHERE unsubscribe_token IS NULL OR unsubscribe_token = ''"
                        )
                    ).fetchall()
                    for (row_id,) in rows:
                        conn.execute(
                            text(
                                "UPDATE alert_subscriptions "
                                "SET unsubscribe_token = :token WHERE id = :id"
                            ),
                            {"token": str(uuid4()), "id": row_id},
                        )
                    if rows:
                        print(
                            f"[db] backfilled unsubscribe_token for {len(rows)} subscriptions"
                        )
        except Exception as exc:  # noqa: BLE001
            print(f"[db] unsubscribe_token backfill skipped/failed: {exc}")

        if dialect == "postgresql":
            try:
                _migrate_postgres_source_column(conn)
            except Exception as exc:  # noqa: BLE001
                print(f"[db] source column migrate skipped/failed: {exc}")
                try:
                    _ensure_postgres_enum_value(conn, "sourceplatform", "manual")
                except Exception as enum_exc:  # noqa: BLE001
                    print(f"[db] enum add-value failed: {enum_exc}")


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
