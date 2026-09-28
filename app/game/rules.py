"""Reglas del juego de Crea.

Funciones puras: no tocan la base de datos, así se testean fácil y rápido.
"""
from collections import Counter
from datetime import date, timedelta
from itertools import count

BRICKS_PER_HABIT = 10

CATEGORY_BUILDING = {
    "EXERCISE": "GYM",
    "READING": "LIBRARY",
    "SAVINGS": "BANK",
    "MEDITATION": "PARK",
    "OTHER": "HOUSE",
}
SPECIAL_BUILDINGS = {"TOWER", "SKYSCRAPER"}


# ---------- Días de la semana (máscara de bits: lunes=1, martes=2, ... domingo=64) ----------

def days_to_mask(days: list[int]) -> int:
    """[0, 2, 4] (lunes, miércoles, viernes) -> 21"""
    return sum(1 << d for d in set(days))


def mask_to_days(mask: int) -> list[int]:
    return [d for d in range(7) if mask & (1 << d)]


def is_scheduled(mask: int, day: date) -> bool:
    return bool(mask & (1 << day.weekday()))


# ---------- Fechas válidas para marcar ----------

def allowed_log_dates(today: date) -> set[date]:
    """Solo se puede marcar hoy o ayer (un día de gracia)."""
    return {today, today - timedelta(days=1)}


# ---------- Día completo ----------

def is_day_completed(scheduled_habit_ids: set, logged_habit_ids: set) -> bool:
    """Un día está completo si todos los hábitos programados para ese día se cumplieron."""
    return bool(scheduled_habit_ids) and scheduled_habit_ids <= logged_habit_ids


# ---------- Rachas ----------

def streak_ending_at(day: date, completed_days: set[date], active_masks: list[int]) -> int:
    """Cuenta días completos consecutivos hacia atrás desde `day`.

    Los días sin ningún hábito programado (descanso) no suman pero tampoco cortan la racha.
    """
    if not completed_days:
        return 0
    first = min(completed_days)
    streak = 0
    d = day
    while d >= first:
        if d in completed_days:
            streak += 1
        elif any(is_scheduled(m, d) for m in active_masks):
            break  # día con hábitos que no se completó: se corta
        d -= timedelta(days=1)
    return streak


def current_streak(today: date, completed_days: set[date], active_masks: list[int]) -> int:
    """Racha vigente. Si hoy todavía no está completo, no la corta: cuenta desde ayer."""
    start = today if today in completed_days else today - timedelta(days=1)
    return streak_ending_at(start, completed_days, active_masks)


# ---------- Edificios ----------

def main_building_type(completed_categories: list[str]) -> str:
    """El edificio del día es el de la categoría que más se cumplió."""
    top_category, _ = Counter(completed_categories).most_common(1)[0]
    return CATEGORY_BUILDING[top_category]


def special_building(streak: int) -> str | None:
    if streak > 0 and streak % 30 == 0:
        return "SKYSCRAPER"
    if streak > 0 and streak % 7 == 0:
        return "TOWER"
    return None


def spiral_position(n: int) -> tuple[int, int]:
    """Posición n-ésima de una espiral cuadrada desde el centro: la ciudad crece hacia afuera."""
    x = y = 0
    if n == 0:
        return x, y
    dx, dy = 1, 0
    step = 1
    i = 0
    while True:
        for _ in range(2):
            for _ in range(step):
                x, y = x + dx, y + dy
                i += 1
                if i == n:
                    return x, y
            dx, dy = -dy, dx  # girar 90°
        step += 1


def first_free_position(occupied: set[tuple[int, int]]) -> tuple[int, int]:
    for n in count():
        pos = spiral_position(n)
        if pos not in occupied:
            return pos
