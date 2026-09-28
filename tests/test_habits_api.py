"""Tests de punta a punta: hábitos, marcar cumplido y ciudad."""
from datetime import date, timedelta

import pytest

from app.auth.dependencies import get_user_today
from app.main import app

TODAY = date(2026, 9, 28)  # lunes
YESTERDAY = TODAY - timedelta(days=1)


@pytest.fixture
def auth(client):
    app.dependency_overrides[get_user_today] = lambda: TODAY
    r = client.post(
        "/auth/register", json={"email": "nacho@crea.app", "password": "secreta123", "name": "Nacho"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def create(client, auth, name, category, days=None):
    body = {"name": name, "category": category}
    if days is not None:
        body["days"] = days
    r = client.post("/habits", json=body, headers=auth)
    assert r.status_code == 201
    return r.json()["id"]


def test_crud(client, auth):
    habit_id = create(client, auth, "Leer 20 minutos", "READING", days=[0, 2, 4])
    habits = client.get("/habits", headers=auth).json()
    assert habits[0]["days"] == [0, 2, 4]

    r = client.put(f"/habits/{habit_id}", json={"name": "Leer 30 minutos"}, headers=auth)
    assert r.json()["name"] == "Leer 30 minutos"

    assert client.delete(f"/habits/{habit_id}", headers=auth).status_code == 204
    assert client.get("/habits", headers=auth).json() == []


def test_completing_the_day_builds_something(client, auth):
    gym = create(client, auth, "Gimnasio", "EXERCISE")
    read = create(client, auth, "Leer", "READING")

    r = client.put(f"/habits/{gym}/logs/{TODAY}", headers=auth).json()
    assert r["bricks_earned"] == 10
    assert r["day_completed"] is False
    assert r["new_buildings"] == []

    r = client.put(f"/habits/{read}/logs/{TODAY}", headers=auth).json()
    assert r["day_completed"] is True
    assert r["streak"] == 1
    assert len(r["new_buildings"]) == 1
    assert r["new_buildings"][0]["x"] == 0 and r["new_buildings"][0]["y"] == 0

    city = client.get("/city", headers=auth).json()
    assert city["bricks"] == 20
    assert len(city["buildings"]) == 1


def test_marking_twice_is_idempotent(client, auth):
    habit = create(client, auth, "Meditar", "MEDITATION")
    client.put(f"/habits/{habit}/logs/{TODAY}", headers=auth)
    r = client.put(f"/habits/{habit}/logs/{TODAY}", headers=auth).json()
    assert r["bricks_earned"] == 0
    assert client.get("/city", headers=auth).json()["bricks"] == 10
    assert len(client.get("/city", headers=auth).json()["buildings"]) == 1


def test_unmark_reverts_building(client, auth):
    habit = create(client, auth, "Ahorrar", "SAVINGS")
    client.put(f"/habits/{habit}/logs/{TODAY}", headers=auth)
    r = client.delete(f"/habits/{habit}/logs/{TODAY}", headers=auth).json()
    assert r["bricks_earned"] == -10
    assert r["removed_buildings"] == 1

    city = client.get("/city", headers=auth).json()
    assert city["bricks"] == 0
    assert city["buildings"] == []
    assert city["current_streak"] == 0


def test_grace_day_and_old_dates(client, auth):
    habit = create(client, auth, "Correr", "EXERCISE")
    assert client.put(f"/habits/{habit}/logs/{YESTERDAY}", headers=auth).status_code == 200
    old = TODAY - timedelta(days=2)
    assert client.put(f"/habits/{habit}/logs/{old}", headers=auth).status_code == 400


def test_yesterday_and_today_make_a_streak(client, auth):
    habit = create(client, auth, "Correr", "EXERCISE")
    client.put(f"/habits/{habit}/logs/{YESTERDAY}", headers=auth)
    r = client.put(f"/habits/{habit}/logs/{TODAY}", headers=auth).json()
    assert r["streak"] == 2


def test_not_scheduled_day_is_rejected(client, auth):
    habit = create(client, auth, "Yoga", "MEDITATION", days=[2])  # solo miércoles
    assert client.put(f"/habits/{habit}/logs/{TODAY}", headers=auth).status_code == 400


def test_today_screen(client, auth):
    create(client, auth, "Leer", "READING")
    create(client, auth, "Yoga", "MEDITATION", days=[2])  # no toca hoy
    today = client.get("/today", headers=auth).json()
    assert today["date"] == str(TODAY)
    assert [h["name"] for h in today["habits"]] == ["Leer"]
    assert today["habits"][0]["completed"] is False


def test_cannot_touch_other_users_habits(client, auth):
    habit = create(client, auth, "Leer", "READING")
    r = client.post(
        "/auth/register", json={"email": "otro@crea.app", "password": "secreta123", "name": "Otro"}
    )
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.put(f"/habits/{habit}/logs/{TODAY}", headers=other).status_code == 404
