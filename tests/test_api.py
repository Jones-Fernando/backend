import os
import pytest

os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DB_DRIVER", "sqlite")
os.environ.setdefault("TEST_DB_PATH", "/tmp/wepay_api.sqlite3")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALLOW_EMAIL_TEST", "false")

from app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["projeto"] == "wepay"


def test_auth_required(client):
    response = client.get("/api/grupos")
    assert response.status_code == 401


def test_signup_and_login(client):
    email = "api-test@example.com"
    response = client.post(
        "/api/auth/cadastro",
        json={"nome": "API Test", "email": email, "senha": "123456"},
    )
    assert response.status_code == 201
    response = client.post(
        "/api/auth/login",
        json={"email": email, "senha": "123456"},
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["token"]
    assert data["refresh_token"]


def test_duplicate_signup_returns_conflict(client):
    payload = {"nome": "Dup", "email": "dup@example.com", "senha": "123456"}
    assert client.post("/api/auth/cadastro", json=payload).status_code == 201
    assert client.post("/api/auth/cadastro", json=payload).status_code == 409
