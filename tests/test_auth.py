"""Tests del login. Usan SQLite en memoria, no tocan tu base real."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-con-al-menos-32-caracteres!!")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)


@pytest.fixture
def client():
    Base.metadata.create_all(engine)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


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
