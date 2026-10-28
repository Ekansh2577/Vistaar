import sqlite3
import inspect

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from auth import RegisterInput, SESSION_COOKIE, get_current_user, router
from rate_limiter import limiter


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VISTAAR_AUTH_DB", str(tmp_path / "accounts.sqlite3"))
    monkeypatch.setenv("VISTAAR_ENV", "development")
    monkeypatch.setenv("VISTAAR_CORS_ORIGINS", "")
    monkeypatch.setenv("VISTAAR_COOKIE_SECURE", "false")
    monkeypatch.setattr(limiter, "enabled", False, raising=False)
    monkeypatch.delenv("VISTAAR_SMTP_HOST", raising=False)
    monkeypatch.delenv("VISTAAR_SMTP_FROM", raising=False)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(router)

    @app.get("/private")
    def private_route(user=Depends(get_current_user)):
        return {"user": user}

    with TestClient(app) as test_client:
        yield test_client


def register(client, email="reader@example.com", password="safe-password-123"):
    return client.post("/auth/register", json={
        "full_name": "Research Reader",
        "email": email,
        "password": password,
    })


def test_register_model_is_resolved_in_route_and_openapi(client):
    endpoint = next(route.endpoint for route in router.routes if route.path == "/auth/register")
    assert inspect.signature(endpoint).parameters["payload"].annotation is RegisterInput

    operation = client.app.openapi()["paths"]["/auth/register"]["post"]
    body_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert body_schema["$ref"].endswith("/RegisterInput")
    properties = client.app.openapi()["components"]["schemas"]["RegisterInput"]["properties"]
    assert {"full_name", "email", "password"}.issubset(properties)


def test_registration_hashes_password_and_creates_persistent_session(client, tmp_path, monkeypatch):
    response = register(client)
    assert response.status_code == 201
    assert response.json()["user"]["email"] == "reader@example.com"
    assert client.cookies.get(SESSION_COOKIE)
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/auth/me").status_code == 200
    assert client.get("/private").json()["user"]["email"] == "reader@example.com"

    db_path = tmp_path / "accounts.sqlite3"
    with sqlite3.connect(db_path) as connection:
        stored_row = connection.execute("SELECT id, full_name, email, password_hash, created_at FROM users").fetchone()
        session_hash = connection.execute("SELECT token_hash FROM sessions").fetchone()[0]
    stored = stored_row[3]
    assert stored_row[0] > 0
    assert stored_row[1] == "Research Reader"
    assert stored_row[2] == "reader@example.com"
    assert stored_row[4]
    assert stored != "safe-password-123"
    assert stored.startswith("$argon2")
    assert session_hash != client.cookies.get(SESSION_COOKIE)


def test_account_survives_app_restart(client):
    import auth

    assert register(client).status_code == 201
    client.post("/auth/logout")
    auth._engine_for(auth.database_url()).dispose()
    auth._engine_for.cache_clear()

    with TestClient(client.app) as restarted_client:
        response = restarted_client.post("/auth/login", json={
            "email": "reader@example.com",
            "password": "safe-password-123",
        })
        assert response.status_code == 200
        assert restarted_client.get("/auth/me").json()["user"]["email"] == "reader@example.com"


def test_login_accepts_correct_credentials_and_rejects_incorrect(client):
    register(client)
    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401

    valid = client.post("/auth/login", json={"email": "READER@example.com", "password": "safe-password-123"})
    assert valid.status_code == 200
    assert client.get("/private").status_code == 200

    client.post("/auth/logout")
    invalid = client.post("/auth/login", json={"email": "reader@example.com", "password": "wrong-password"})
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "Invalid email or password"


def test_duplicate_registration_is_rejected_case_insensitively(client):
    assert register(client).status_code == 201
    duplicate = register(client, email="READER@EXAMPLE.COM")
    assert duplicate.status_code == 409


def test_logout_revokes_session_and_private_route_rejects_anonymous(client):
    assert client.get("/private").status_code == 401
    register(client)
    assert client.get("/private").status_code == 200
    assert client.post("/auth/logout").status_code == 200
    assert client.get("/auth/me").status_code == 401
    assert client.get("/private").status_code == 401


def test_two_users_receive_separate_sessions(client):
    first = register(client, email="first@example.com")
    assert first.status_code == 201
    first_cookie = client.cookies.get(SESSION_COOKIE)

    with TestClient(client.app) as second_client:
        second = register(second_client, email="second@example.com")
        assert second.status_code == 201
        assert second_client.get("/private").json()["user"]["email"] == "second@example.com"
        assert second_client.cookies.get(SESSION_COOKIE) != first_cookie

    assert client.get("/private").json()["user"]["email"] == "first@example.com"


def test_registration_validates_email_and_password(client):
    invalid_email = client.post("/auth/register", json={"full_name": "Reader", "email": "bad", "password": "safe-password-123"})
    short_password = client.post("/auth/register", json={"full_name": "Reader", "email": "valid@example.com", "password": "short"})
    assert invalid_email.status_code == 422
    assert short_password.status_code == 422


def test_auth_rejects_untrusted_browser_origin(client):
    response = client.post("/auth/register", headers={"Origin": "https://attacker.invalid"}, json={
        "full_name": "Research Reader",
        "email": "reader@example.com",
        "password": "safe-password-123",
    })
    assert response.status_code == 403


def test_registration_allows_project_vite_proxy_origin(client):
    response = client.post(
        "/auth/register",
        headers={"Host": "127.0.0.1:8000", "Origin": "http://localhost:5173"},
        json={
            "full_name": "Research Reader",
            "email": "reader@example.com",
            "password": "safe-password-123",
        },
    )
    assert response.status_code == 201
    assert client.get("/auth/me").status_code == 200


def test_forgot_password_reports_missing_smtp_configuration(client):
    response = client.post("/auth/forgot-password", json={"email": "reader@example.com"})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_password_reset_requires_token_and_invalidates_existing_sessions(client, monkeypatch):
    import auth

    register(client)
    monkeypatch.setenv("VISTAAR_SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("VISTAAR_SMTP_FROM", "no-reply@example.test")
    sent = {}
    monkeypatch.setattr(auth, "_send_reset_email", lambda email, token: sent.update(email=email, token=token))

    requested = client.post("/auth/forgot-password", json={"email": "reader@example.com"})
    assert requested.status_code == 202
    assert sent["email"] == "reader@example.com"
    assert client.get("/private").status_code == 200

    reset = client.post("/auth/reset-password", json={"token": sent["token"], "password": "new-safe-password-456"})
    assert reset.status_code == 200
    assert client.get("/private").status_code == 401
    assert client.post("/auth/login", json={"email": "reader@example.com", "password": "new-safe-password-456"}).status_code == 200

    replay = client.post("/auth/reset-password", json={"token": sent["token"], "password": "another-safe-password-789"})
    assert replay.status_code == 400
