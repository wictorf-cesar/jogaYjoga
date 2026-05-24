from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.backend.repositories.reservations import (
    list_owner_reservations,
    list_user_reservations,
)
from app.models.entities import Reserva


def get_user_reservations(db: Session, user_id: int) -> list[Reserva]:
    return list_user_reservations(db, user_id)


def get_owner_reservations(
    db: Session,
    venue_ids: list[int],
    reservation_date: date | None = None,
) -> list[Reserva]:
    return list_owner_reservations(db, venue_ids, reservation_date)

