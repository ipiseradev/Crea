"""Tests de la sincronización offline y las estadísticas."""
import uuid
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
    return client.post("/habits", json=body, headers=auth).json()["id"]


def item(habit_id, day, action="done"):
    return {"id": str(uuid.uuid4()), "habit_id": habit_id, "date": str(day), "action": action}


def test_sync_applies_in_order_and_builds(client, auth):
    habit = create(client, auth, "Leer", "READING")
    # llegan desordenados: se aplican por fecha
    r = client.post(
        "/sync", json={"items": [item(habit, TODAY), item(habit, YESTERDAY)]}, headers=auth
    ).json()
    assert [x["status"] for x in r["results"]] == ["applied", "applied"]
    assert r["bricks"] == 20
    assert r["streak"] == 2
    assert len(r["new_buildings"]) == 2


def test_resending_same_batch_does_not_duplicate(client, auth):
    habit = create(client, auth, "Leer", "READING")
    batch = {"items": [item(habit, TODAY)]}
    client.post("/sync", json=batch, headers=auth)
    r = client.post("/sync", json=batch, headers=auth).json()
    assert r["bricks"] == 10
    assert r["new_buildings"] == []


def test_sync_rejects_invalid_items_but_applies_the_rest(client, auth):
    habit = create(client, auth, "Leer", "READING")
    r = client.post(
        "/sync",
        json={
            "items": [
                item(habit, TODAY - timedelta(days=5)),
                item(str(uuid.uuid4()), TODAY),
                item(habit, TODAY),
            ]
        },
        headers=auth,
    ).json()
    statuses = [x["status"] for x in r["results"]]
    assert statuses.count("rejected") == 2
    assert statuses.count("applied") == 1


def test_sync_undone(client, auth):
    habit = create(client, auth, "Leer", "READING")
    r = client.post(
        "/sync", json={"items": [item(habit, TODAY), item(habit, TODAY, "undone")]}, headers=auth
    ).json()
    assert r["bricks"] == 0
    assert r["new_buildings"] == []
    assert client.get("/city", headers=auth).json()["buildings"] == []


def test_stats(client, auth):
    read = create(client, auth, "Leer", "READING")
    gym = create(client, auth, "Gimnasio", "EXERCISE")
    client.put(f"/habits/{read}/logs/{TODAY}", headers=auth)

    r = client.get(f"/stats?from={TODAY}&to={TODAY}", headers=auth).json()
    assert r["habits_completed"] == 1
    assert r["completion_rate"] == 0.5
    assert r["completed_days"] == 0
    assert r["by_category"]["READING"]["rate"] == 1.0
    assert r["by_category"]["EXERCISE"]["rate"] == 0.0

    client.put(f"/habits/{gym}/logs/{TODAY}", headers=auth)
    r = client.get(f"/stats?from={TODAY}&to={TODAY}", headers=auth).json()
    assert r["completion_rate"] == 1.0
    assert r["completed_days"] == 1


def test_stats_default_range_and_validation(client, auth):
    r = client.get("/stats", headers=auth).json()
    assert r["to_date"] == str(TODAY)
    assert len(r["daily"]) == 30
    assert client.get(f"/stats?from={TODAY}&to={YESTERDAY}", headers=auth).status_code == 400
