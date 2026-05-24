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


def init_db() -> None:
    Base.metadata.create_all(bind=DBConfig.engine)
    ensure_sqlite_columns()



def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
