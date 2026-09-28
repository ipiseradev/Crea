"""Estadísticas para la pantalla de progreso."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_today
from app.database import get_db
from app.game import rules
from app.models import Building, City, Habit, HabitLog, User

router = APIRouter(tags=["stats"])

MAX_DAYS = 366


class DayStat(BaseModel):
    date: date
    scheduled: int
    completed: int


class CategoryStat(BaseModel):
    scheduled: int
    completed: int
    rate: float


class StatsResponse(BaseModel):
    from_date: date
    to_date: date
    completion_rate: float
    habits_completed: int
    completed_days: int
    current_streak: int
    best_streak: int
    by_category: dict[str, CategoryStat]
    daily: list[DayStat]


def _local_date(dt: datetime, tz: ZoneInfo) -> date:
    if dt.tzinfo is None:  # SQLite devuelve fechas sin zona: las tomamos como UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date()


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    user: User = Depends(get_current_user),
    today: date = Depends(get_user_today),
    db: Session = Depends(get_db),
):
    """Por defecto, los últimos 30 días. Cuenta solo hábitos activos y desde el día en que se crearon."""
    to_date = min(to_date or today, today)
    from_date = from_date or to_date - timedelta(days=29)
    if from_date > to_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "'from' tiene que ser anterior a 'to'")
    if (to_date - from_date).days >= MAX_DAYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"El rango máximo es de {MAX_DAYS} días")

    tz = ZoneInfo(user.timezone)
    habits = list(db.scalars(select(Habit).where(Habit.user_id == user.id, Habit.active)))
    created = {h.id: _local_date(h.created_at, tz) for h in habits}

    logs = set()
    if habits:
        logs = set(
            db.execute(
                select(HabitLog.habit_id, HabitLog.log_date).where(
                    HabitLog.habit_id.in_([h.id for h in habits]),
                    HabitLog.log_date.between(from_date, to_date),
                )
            ).all()
        )

    daily: list[DayStat] = []
    by_cat: dict[str, list[int]] = {}
    d = from_date
    while d <= to_date:
        scheduled = completed = 0
        for h in habits:
            if d < created[h.id] or not rules.is_scheduled(h.days_of_week, d):
                continue
            done = (h.id, d) in logs
            scheduled += 1
            completed += done
            cat = by_cat.setdefault(h.category, [0, 0])
            cat[0] += 1
            cat[1] += done
        daily.append(DayStat(date=d, scheduled=scheduled, completed=completed))
        d += timedelta(days=1)

    total_scheduled = sum(x.scheduled for x in daily)
    total_completed = sum(x.completed for x in daily)
    completed_days = db.scalars(
        select(Building.built_on)
        .where(Building.user_id == user.id, Building.built_on.between(from_date, to_date))
        .distinct()
    ).all()
    city = db.get(City, user.id)

    return StatsResponse(
        from_date=from_date,
        to_date=to_date,
        completion_rate=round(total_completed / total_scheduled, 3) if total_scheduled else 0.0,
        habits_completed=total_completed,
        completed_days=len(completed_days),
        current_streak=city.current_streak,
        best_streak=city.best_streak,
        by_category={
            c: CategoryStat(scheduled=s, completed=k, rate=round(k / s, 3) if s else 0.0)
            for c, (s, k) in by_cat.items()
        },
        daily=daily,
    )
