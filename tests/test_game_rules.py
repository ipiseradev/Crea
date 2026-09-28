"""Tests de las reglas del juego (funciones puras, sin base de datos)."""
from datetime import date, timedelta

from app.game import rules

EVERY_DAY = rules.days_to_mask(range(7))
WEEKDAYS = rules.days_to_mask(range(5))  # lunes a viernes

MONDAY = date(2026, 9, 28)


def days_back(start: date, n: int) -> set[date]:
    return {start - timedelta(days=i) for i in range(n)}


def test_days_mask_roundtrip():
    assert rules.days_to_mask([0, 2, 4]) == 21
    assert rules.mask_to_days(21) == [0, 2, 4]


def test_is_scheduled():
    assert rules.is_scheduled(WEEKDAYS, MONDAY)
    assert not rules.is_scheduled(WEEKDAYS, MONDAY + timedelta(days=5))  # sábado


def test_only_today_or_yesterday():
    assert rules.allowed_log_dates(MONDAY) == {MONDAY, MONDAY - timedelta(days=1)}


def test_day_completed():
    assert rules.is_day_completed({1, 2}, {1, 2, 3})
    assert not rules.is_day_completed({1, 2}, {1})
    assert not rules.is_day_completed(set(), set())  # sin hábitos no hay día completo


def test_streak_counts_consecutive_days():
    completed = days_back(MONDAY, 5)
    assert rules.streak_ending_at(MONDAY, completed, [EVERY_DAY]) == 5


def test_streak_breaks_on_missed_day():
    completed = days_back(MONDAY, 3) | {MONDAY - timedelta(days=5)}
    assert rules.streak_ending_at(MONDAY, completed, [EVERY_DAY]) == 3


def test_rest_days_do_not_break_streak():
    friday = MONDAY - timedelta(days=3)
    completed = {MONDAY, friday, friday - timedelta(days=1)}  # sábado y domingo no hay hábitos
    assert rules.streak_ending_at(MONDAY, completed, [WEEKDAYS]) == 3


def test_today_pending_does_not_break_current_streak():
    completed = days_back(MONDAY - timedelta(days=1), 4)  # completó hasta ayer
    assert rules.current_streak(MONDAY, completed, [EVERY_DAY]) == 4


def test_current_streak_lost_after_missing_yesterday():
    completed = days_back(MONDAY - timedelta(days=2), 4)
    assert rules.current_streak(MONDAY, completed, [EVERY_DAY]) == 0


def test_main_building_uses_most_completed_category():
    assert rules.main_building_type(["READING", "EXERCISE", "READING"]) == "LIBRARY"


def test_special_buildings():
    assert rules.special_building(6) is None
    assert rules.special_building(7) == "TOWER"
    assert rules.special_building(14) == "TOWER"
    assert rules.special_building(30) == "SKYSCRAPER"


def test_spiral_grows_from_center_without_repeating():
    positions = [rules.spiral_position(n) for n in range(49)]
    assert positions[0] == (0, 0)
    assert len(set(positions)) == 49
    assert all(abs(x) <= 3 and abs(y) <= 3 for x, y in positions)  # 7x7 alrededor del centro


def test_first_free_position_fills_gaps():
    occupied = {rules.spiral_position(n) for n in (0, 2, 3)}
    assert rules.first_free_position(occupied) == rules.spiral_position(1)
