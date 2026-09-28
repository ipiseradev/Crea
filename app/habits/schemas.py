import uuid
from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal["EXERCISE", "READING", "SAVINGS", "MEDITATION", "OTHER"]
BuildingType = Literal["HOUSE", "GYM", "LIBRARY", "BANK", "PARK", "TOWER", "SKYSCRAPER"]


class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: Category
    days: list[int] = Field(
        default=[0, 1, 2, 3, 4, 5, 6],
        description="Días de la semana: 0=lunes ... 6=domingo",
    )
    reminder_time: time | None = None

    @field_validator("days")
    @classmethod
    def valid_days(cls, v: list[int]) -> list[int]:
        if not v or any(d < 0 or d > 6 for d in v):
            raise ValueError("Elegí al menos un día entre 0 (lunes) y 6 (domingo)")
        return sorted(set(v))


class HabitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: Category | None = None
    days: list[int] | None = None
    reminder_time: time | None = None

    @field_validator("days")
    @classmethod
    def valid_days(cls, v: list[int] | None) -> list[int] | None:
        return None if v is None else HabitCreate.valid_days(v)


class HabitResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: Category
    days: list[int]
    reminder_time: time | None


class LogRequest(BaseModel):
    id: uuid.UUID | None = Field(
        default=None, description="UUID generado por el celular (para sincronizar sin duplicar)"
    )


class BuildingResponse(BaseModel):
    model_config = {"from_attributes": True}

    type: BuildingType
    x: int
    y: int
    built_on: date


class GameEventResponse(BaseModel):
    bricks_earned: int
    day_completed: bool
    streak: int
    new_buildings: list[BuildingResponse] = []
    removed_buildings: int = 0


class TodayHabit(HabitResponse):
    completed: bool


class TodayResponse(BaseModel):
    date: date
    habits: list[TodayHabit]
    day_completed: bool
    streak: int
    bricks: int


class CityResponse(BaseModel):
    bricks: int
    current_streak: int
    best_streak: int
    buildings: list[BuildingResponse]
