from __future__ import annotations

from sqlalchemy.orm import Session

from app.backend.repositories.venues import list_owner_venues, list_public_venues
from app.models.entities import Espaco


def get_public_venues(db: Session) -> list[Espaco]:
    return list_public_venues(db)


def get_owner_venues(db: Session, owner_id: int) -> list[Espaco]:
    return list_owner_venues(db, owner_id)

