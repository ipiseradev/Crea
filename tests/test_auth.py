"""Tests del login."""
USER = {"email": "nacho@crea.app", "password": "secreta123", "name": "Nacho"}


def test_register_login_and_me(client):
    r = client.post("/auth/register", json=USER)
    assert r.status_code == 201

    r = client.post("/auth/login", json={"email": USER["email"], "password": USER["password"]})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["name"] == "Nacho"


def test_duplicate_email(client):
    client.post("/auth/register", json=USER)
    assert client.post("/auth/register", json=USER).status_code == 409


def test_wrong_password(client):
    client.post("/auth/register", json=USER)
    r = client.post("/auth/login", json={"email": USER["email"], "password": "incorrecta"})
    assert r.status_code == 401


def test_me_without_token(client):
    assert client.get("/auth/me").status_code in (401, 403)
