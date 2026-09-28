"""Aplica las reglas del juego sobre la base de datos."""
import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.game import rules
from app.models import Building, City, Habit, HabitLog, User


@dataclass
class GameEvent:
    bricks_earned: int = 0
    day_completed: bool = False
    streak: int = 0
    new_buildings: list[Building] = field(default_factory=list)
    removed_buildings: int = 0


def _active_habits(db: Session, user: User) -> list[Habit]:
    return list(db.scalars(select(Habit).where(Habit.user_id == user.id, Habit.active)))


def _completed_days(db: Session, user: User) -> set[date]:
    return set(db.scalars(select(Building.built_on).where(Building.user_id == user.id).distinct()))


def _logs_for_day(db: Session, habit_ids: list, day: date) -> list[HabitLog]:
    if not habit_ids:
        return []
    return list(
        db.scalars(select(HabitLog).where(HabitLog.habit_id.in_(habit_ids), HabitLog.log_date == day))
    )


def _day_status(db: Session, user: User, day: date):
    habits = _active_habits(db, user)
    scheduled = {h.id: h for h in habits if rules.is_scheduled(h.days_of_week, day)}
    logs = _logs_for_day(db, list(scheduled), day)
    logged_ids = {log.habit_id for log in logs}
    completed = rules.is_day_completed(set(scheduled), logged_ids)
    return habits, scheduled, logged_ids, completed


def _refresh_streaks(db: Session, user: User, city: City, today: date, masks: list[int]) -> None:
    city.current_streak = rules.current_streak(today, _completed_days(db, user), masks)
    city.best_streak = max(city.best_streak, city.current_streak)
    days = _completed_days(db, user)
    city.last_completed_day = max(days) if days else None


def mark_done(db: Session, user: User, habit: Habit, day: date, today: date, log_id=None) -> GameEvent:
    event = GameEvent()
    city = db.get(City, user.id)

    existing = db.scalar(select(HabitLog).where(HabitLog.habit_id == habit.id, HabitLog.log_date == day))
    if existing is None:
        db.add(HabitLog(id=log_id or uuid.uuid4(), habit_id=habit.id, log_date=day))
        city.bricks += rules.BRICKS_PER_HABIT
        event.bricks_earned = rules.BRICKS_PER_HABIT
        db.flush()

    habits, scheduled, logged_ids, completed = _day_status(db, user, day)
    masks = [h.days_of_week for h in habits]
    event.day_completed = completed

    already_built = day in _completed_days(db, user)
    if completed and not already_built:
        occupied = {(b.x, b.y) for b in db.scalars(select(Building).where(Building.user_id == user.id))}

        categories = [scheduled[hid].category for hid in logged_ids if hid in scheduled]
        types = [rules.main_building_type(categories)]

        streak_that_day = rules.streak_ending_at(day, _completed_days(db, user) | {day}, masks)
        special = rules.special_building(streak_that_day)
        if special:
            types.append(special)

        for building_type in types:
            x, y = rules.first_free_position(occupied)
            occupied.add((x, y))
            building = Building(user_id=user.id, type=building_type, x=x, y=y, built_on=day)
            db.add(building)
            event.new_buildings.append(building)
        db.flush()

    _refresh_streaks(db, user, city, today, masks)
    event.streak = city.current_streak
    db.commit()
    return event


def unmark(db: Session, user: User, habit: Habit, day: date, today: date) -> GameEvent:
    event = GameEvent()
    city = db.get(City, user.id)

    log = db.scalar(select(HabitLog).where(HabitLog.habit_id == habit.id, HabitLog.log_date == day))
    if log is not None:
        db.delete(log)
        city.bricks = max(0, city.bricks - rules.BRICKS_PER_HABIT)
        event.bricks_earned = -rules.BRICKS_PER_HABIT
        db.flush()

    habits, _, _, completed = _day_status(db, user, day)
    if not completed:
        result = db.execute(
            delete(Building).where(Building.user_id == user.id, Building.built_on == day)
        )
        event.removed_buildings = result.rowcount or 0
        db.flush()

    _refresh_streaks(db, user, city, today, [h.days_of_week for h in habits])
    event.streak = city.current_streak
    db.commit()
    return event
