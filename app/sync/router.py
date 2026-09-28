"""Sincronización offline: la app guarda lo que marcás sin conexión y lo sube en lote."""
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_today
from app.database import get_db
from app.game import rules, service
from app.habits.schemas import BuildingResponse
from app.models import Building, City, Habit, User

router = APIRouter(tags=["sync"])


class SyncItem(BaseModel):
    id: uuid.UUID = Field(description="UUID que generó el celular para este registro")
    habit_id: uuid.UUID
    date: date
    action: Literal["done", "undone"] = "done"


class SyncRequest(BaseModel):
    items: list[SyncItem] = Field(max_length=500)


class SyncResult(BaseModel):
    id: uuid.UUID
    status: Literal["applied", "rejected"]
    reason: str | None = None


class SyncResponse(BaseModel):
    results: list[SyncResult]
    bricks: int
    streak: int
    new_buildings: list[BuildingResponse]


@router.post("/sync", response_model=SyncResponse)
def sync(
    data: SyncRequest,
    user: User = Depends(get_current_user),
    today: date = Depends(get_user_today),
    db: Session = Depends(get_db),
):
    """Aplica en orden cronológico. Reenviar el mismo lote es seguro: no duplica nada."""
    results: list[SyncResult] = []
    new_buildings = []

    for item in sorted(data.items, key=lambda i: i.date):
        habit = db.get(Habit, item.habit_id)
        if habit is None or habit.user_id != user.id or not habit.active:
            results.append(SyncResult(id=item.id, status="rejected", reason="Hábito no encontrado"))
            continue
        if item.date not in rules.allowed_log_dates(today):
            results.append(SyncResult(id=item.id, status="rejected", reason="Solo se puede marcar hoy o ayer"))
            continue
        if not rules.is_scheduled(habit.days_of_week, item.date):
            results.append(SyncResult(id=item.id, status="rejected", reason="No está programado ese día"))
            continue

        if item.action == "done":
            event = service.mark_done(db, user, habit, item.date, today, item.id)
            new_buildings.extend(b.id for b in event.new_buildings)
        else:
            service.unmark(db, user, habit, item.date, today)
        results.append(SyncResult(id=item.id, status="applied"))

    city = db.get(City, user.id)
    db.refresh(city)
    # si algo se construyó y después se desmarcó en el mismo lote, no lo devolvemos
    alive = []
    if new_buildings:
        alive = list(
            db.scalars(
                select(Building).where(Building.id.in_(new_buildings)).order_by(Building.built_on)
            )
        )
    return SyncResponse(results=results, bricks=city.bricks, streak=city.current_streak, new_buildings=alive)
