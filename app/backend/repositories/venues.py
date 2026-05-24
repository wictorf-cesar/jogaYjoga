from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Espaco


def list_public_venues(db: Session) -> list[Espaco]:
    return db.scalars(select(Espaco).order_by(Espaco.nome_espaco)).unique().all()


def list_owner_venues(db: Session, owner_id: int) -> list[Espaco]:
    return (
        db.scalars(
            select(Espaco)
            .where(Espaco.id_proprietario == owner_id)
            .order_by(Espaco.nome_espaco)
        )
        .unique()
        .all()
    )


def get_venue(db: Session, venue_id: int) -> Espaco | None:
    return db.get(Espaco, venue_id)

