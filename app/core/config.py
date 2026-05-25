import os

from sqlalchemy import create_engine


class ProjectConfig:
    """Global filesystem configuration shared across the API services."""

    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    DB_PATH = os.path.join(BASE_DIR, "db")

    DIRECTORIES = [DB_PATH]

    for directory in DIRECTORIES:
        os.makedirs(directory, exist_ok=True)

    TABLE_ESPACO_ESPORTES = "espaco_esportes"
    TABLE_ENDERECOS = "enderecos"
    TABLE_USUARIOS = "usuarios"
    TABLE_PROPRIETARIOS = "proprietarios"
    TABLE_ESPORTES = "esportes"
    TABLE_ESPACOS = "espacos"
    TABLE_RESERVAS = "reservas"
    TABLE_AVALIACOES = "avaliacoes"
    TABLE_HORARIOS_FUNCIONAMENTO = "horarios_funcionamento"
    TABLE_BLOQUEIOS_HORARIO = "bloqueios_horario"
    TABLE_PAGAMENTOS = "pagamentos"
    TABLE_FOTOS_ESPACO = "fotos_espaco"
    TABLE_FAVORITOS = "favoritos"


def _build_database_url() -> tuple[str, dict]:
    """Return (database_url, engine_kwargs) based on DATABASE_URL env var.

    When DATABASE_URL is set (e.g. on Render) it takes precedence and the
    engine is created without SQLite-specific options.  Otherwise fall back
    to a local SQLite file.
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Render provides postgres:// but SQLAlchemy 1.4+ requires postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url, {}

    db_file = os.path.join(ProjectConfig.DB_PATH, "jogayjoga.db")
    return f"sqlite:///{db_file}", {"check_same_thread": False}


class DBConfig:
    """Centralized database engine settings shared across repositories."""

    SQLALCHEMY_DATABASE_URL, _connect_args = _build_database_url()
    IS_SQLITE = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,
        connect_args=_connect_args,
    )
