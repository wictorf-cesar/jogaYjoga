from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DBConfig
from app.models.entities import Base

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=DBConfig.engine,
)


def ensure_sqlite_columns() -> None:
    """Add missing columns to an existing SQLite database.

    This is a no-op when running against PostgreSQL because migrations
    are expected to handle schema changes there.
    """
    if not DBConfig.IS_SQLITE:
        return

    inspector = inspect(DBConfig.engine)
    if "usuarios" not in inspector.get_table_names():
        return

    user_columns = {column["name"] for column in inspector.get_columns("usuarios")}
    if "is_dono_quadra" not in user_columns:
        with DBConfig.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE usuarios "
                    "ADD COLUMN is_dono_quadra BOOLEAN NOT NULL DEFAULT 0"
                )
            )


def init_db(*, retries: int = 5, delay: float = 2.0) -> None:
    """Create all tables, retrying on transient DB connection errors.

    Render free-tier PostgreSQL may be asleep when the app starts —
    retry a few times before giving up.
    """
    import time
    import logging

    logger = logging.getLogger(__name__)

    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=DBConfig.engine)
            ensure_sqlite_columns()
            return
        except Exception as exc:
            if attempt == retries:
                raise
            logger.warning(
                "init_db attempt %d/%d failed: %s — retrying in %.1fs",
                attempt,
                retries,
                exc,
                delay,
            )
            time.sleep(delay)
            delay *= 2  # exponential backoff


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
