from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Reserva


def list_user_reservations(db: Session, user_id: int) -> list[Reserva]:
    return (
        db.scalars(
            select(Reserva)
            .where(Reserva.id_usuario == user_id)
            .order_by(Reserva.data_reserva.desc(), Reserva.hora_inicio.desc())
        )
        .unique()
        .all()
    )


def list_owner_reservations(
    db: Session,
    venue_ids: list[int],
    reservation_date: date | None = None,
) -> list[Reserva]:
    if not venue_ids:
        return []
    query = select(Reserva).where(Reserva.id_espaco.in_(venue_ids))
    if reservation_date:
        query = query.where(Reserva.data_reserva == reservation_date)
    return db.scalars(query.order_by(Reserva.data_reserva.desc(), Reserva.hora_inicio.desc())).all()

