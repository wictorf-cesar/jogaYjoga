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


class DBConfig:
    """Centralized database engine settings shared across repositories."""

    DB_PATH = ProjectConfig.DB_PATH
    DB_FILE_PATH = os.path.join(ProjectConfig.DB_PATH, "jogayjoga.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
    )
