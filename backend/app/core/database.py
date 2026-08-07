from collections.abc import Generator
import time

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


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


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