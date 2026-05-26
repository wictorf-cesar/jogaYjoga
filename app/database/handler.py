from app.core.config import DBConfig
from app.models.entities import Base


class DBHandler(DBConfig):
    """Initializes the shared database schema."""

    def __init__(self):
        Base.metadata.create_all(self.engine)
