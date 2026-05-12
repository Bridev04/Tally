from fastapi.testclient import TestClient
import jwt
from sqlmodel import Session, select

from app.api.routes.auth import get_auth_rate_limiter
from app.core.config import get_settings
from app.core.rate_limit import InMemoryRateLimiter
from app.models import AuditLog, User


def register_user(test_client: TestClient, email: str = "person@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def test_register_route_hashes_password_and_returns_safe_user(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    payload = register_user(test_client)

    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["email"] == "person@example.com"
    assert "password_hash" not in payload
    assert "password_hash" not in payload["user"]

    user = session.exec(select(User).where(User.email == "person@example.com")).one()
    assert user.password_hash != "correct-horse-battery"
    assert user.password_hash.startswith("$2")


def test_duplicate_email_error_is_safe(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    register_user(test_client)

    response = test_client.post(
        "/auth/register",
        json={"email": "person@example.com", "password": "correct-horse-battery"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "An account with this email already exists."}


def test_login_route_returns_token(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    register_user(test_client)

    response = test_client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "correct-horse-battery"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "person@example.com"
    assert "password_hash" not in payload
    assert "password_hash" not in payload["user"]


def test_invalid_login_does_not_reveal_which_field_failed(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    register_user(test_client)

    wrong_password = test_client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "wrong-password"},
    )
    wrong_email = test_client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )

    assert wrong_password.status_code == 401
    assert wrong_email.status_code == 401
    assert wrong_password.json() == {"detail": "Invalid email or password."}
    assert wrong_email.json() == {"detail": "Invalid email or password."}


def test_auth_me_with_valid_token(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    payload = register_user(test_client)

    response = test_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "person@example.com"
    assert "password_hash" not in response.json()


def test_protected_route_rejects_missing_token(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.get("/protected/ping")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_protected_route_rejects_invalid_token(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.get("/protected/ping", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_protected_route_rejects_expired_token(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    settings = get_settings()
    expired_token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "exp": 1},
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    response = test_client.get("/protected/ping", headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_protected_route_accepts_valid_token(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    payload = register_user(test_client)

    response = test_client.get(
        "/protected/ping",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["user_id"] == payload["user"]["id"]


def test_audit_log_is_created_on_register(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    register_user(test_client)

    audit_log = session.exec(select(AuditLog).where(AuditLog.action == "auth.registered")).one()
    assert audit_log.user_id is not None
    assert audit_log.metadata_json == {}


def test_audit_log_is_created_on_login(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    register_user(test_client)

    response = test_client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "correct-horse-battery"},
    )

    assert response.status_code == 200
    audit_log = session.exec(select(AuditLog).where(AuditLog.action == "auth.logged_in")).one()
    assert audit_log.user_id is not None
    assert audit_log.metadata_json == {}


def test_auth_endpoints_reject_malformed_payloads(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.post("/auth/register", json={"email": "not-an-email"})
    mass_assignment_response = test_client.post(
        "/auth/register",
        json={
            "email": "extra@example.com",
            "password": "correct-horse-battery",
            "password_hash": "attacker-controlled",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request payload."}
    assert mass_assignment_response.status_code == 422
    assert mass_assignment_response.json() == {"detail": "Invalid request payload."}


def test_auth_rate_limit_behavior(client) -> None:  # noqa: ANN001
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    client.dependency_overrides[get_auth_rate_limiter] = lambda: limiter
    test_client = TestClient(client)

    first_response = test_client.post(
        "/auth/register",
        json={"email": "first@example.com", "password": "correct-horse-battery"},
    )
    second_response = test_client.post(
        "/auth/register",
        json={"email": "second@example.com", "password": "correct-horse-battery"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 429
    assert second_response.json() == {"detail": "Too many requests. Please try again later."}


def test_request_body_size_limit(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.post(
        "/auth/login",
        content="x" * 1_048_577,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
