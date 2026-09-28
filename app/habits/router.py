import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_today
from app.database import get_db
from app.game import rules, service
from app.habits.schemas import (
    GameEventResponse,
    HabitCreate,
    HabitResponse,
    HabitUpdate,
    LogRequest,
    TodayHabit,
    TodayResponse,
)
from app.models import City, Habit, HabitLog, User

router = APIRouter(tags=["habits"])


def to_response(habit: Habit) -> HabitResponse:
    return HabitResponse(
        id=habit.id,
        name=habit.name,
        category=habit.category,
        days=rules.mask_to_days(habit.days_of_week),
        reminder_time=habit.reminder_time,
    )


def get_own_habit(habit_id: uuid.UUID, user: User, db: Session) -> Habit:
    habit = db.get(Habit, habit_id)
    if habit is None or habit.user_id != user.id or not habit.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hábito no encontrado")
    return habit


def event_response(event: service.GameEvent) -> GameEventResponse:
    return GameEventResponse(
        bricks_earned=event.bricks_earned,
        day_completed=event.day_completed,
        streak=event.streak,
        new_buildings=event.new_buildings,
        removed_buildings=event.removed_buildings,
    )


# ---------- CRUD de hábitos ----------

@router.get("/habits", response_model=list[HabitResponse])
def list_habits(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    habits = db.scalars(
        select(Habit).where(Habit.user_id == user.id, Habit.active).order_by(Habit.created_at)
    )
    return [to_response(h) for h in habits]


@router.post("/habits", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(
    data: HabitCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    habit = Habit(
        user_id=user.id,
        name=data.name,
        category=data.category,
        days_of_week=rules.days_to_mask(data.days),
        reminder_time=data.reminder_time,
    )
    db.add(habit)
    db.commit()
    return to_response(habit)


@router.put("/habits/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: uuid.UUID,
    data: HabitUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    habit = get_own_habit(habit_id, user, db)
    changes = data.model_dump(exclude_unset=True)
    if "days" in changes:
        habit.days_of_week = rules.days_to_mask(changes.pop("days"))
    for key, value in changes.items():
        setattr(habit, key, value)
    db.commit()
    return to_response(habit)


@router.delete("/habits/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_habit(
    habit_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Archiva el hábito: no se borra, así la ciudad y el historial se mantienen."""
    habit = get_own_habit(habit_id, user, db)
    habit.active = False
    db.commit()


# ---------- Marcar / desmarcar ----------

def check_log_date(habit: Habit, day: date, today: date) -> None:
    if day not in rules.allowed_log_dates(today):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo podés marcar hoy o ayer")
    if not rules.is_scheduled(habit.days_of_week, day):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ese hábito no está programado para ese día")


@router.put("/habits/{habit_id}/logs/{day}", response_model=GameEventResponse)
def mark_habit(
    habit_id: uuid.UUID,
    day: date,
    data: LogRequest = Body(default=LogRequest()),
    user: User = Depends(get_current_user),
    today: date = Depends(get_user_today),
    db: Session = Depends(get_db),
):
    """Marca el hábito como cumplido. Es idempotente: repetirlo no suma de nuevo."""
    habit = get_own_habit(habit_id, user, db)
    check_log_date(habit, day, today)
    return event_response(service.mark_done(db, user, habit, day, today, data.id))


@router.delete("/habits/{habit_id}/logs/{day}", response_model=GameEventResponse)
def unmark_habit(
    habit_id: uuid.UUID,
    day: date,
    user: User = Depends(get_current_user),
    today: date = Depends(get_user_today),
    db: Session = Depends(get_db),
):
    habit = get_own_habit(habit_id, user, db)
    check_log_date(habit, day, today)
    return event_response(service.unmark(db, user, habit, day, today))


# ---------- Pantalla del día ----------

@router.get("/today", response_model=TodayResponse)
def get_today(
    user: User = Depends(get_current_user),
    today: date = Depends(get_user_today),
    db: Session = Depends(get_db),
):
    habits = [
        h
        for h in db.scalars(
            select(Habit).where(Habit.user_id == user.id, Habit.active).order_by(Habit.created_at)
        )
        if rules.is_scheduled(h.days_of_week, today)
    ]
    done = set()
    if habits:
        done = set(
            db.scalars(
                select(HabitLog.habit_id).where(
                    HabitLog.habit_id.in_([h.id for h in habits]), HabitLog.log_date == today
                )
            )
        )
    city = db.get(City, user.id)
    return TodayResponse(
        date=today,
        habits=[TodayHabit(**to_response(h).model_dump(), completed=h.id in done) for h in habits],
        day_completed=rules.is_day_completed({h.id for h in habits}, done),
        streak=city.current_streak,
        bricks=city.bricks,
    )
