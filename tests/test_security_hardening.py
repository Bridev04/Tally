import jwt
import pytest
from fastapi.testclient import TestClient
from jwt import InvalidTokenError
from pydantic import ValidationError

from app.core.config import Settings
from app.core.data_sources import ALLOWED_IMPORT_SOURCES, DISALLOWED_IMPORT_SOURCES
from app.core.security import decode_access_token


def test_auth_responses_include_no_store_headers(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.post(
        "/auth/register",
        json={"email": "headers@example.com", "password": "correct-horse-battery"},
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_access_token_contains_and_requires_access_type(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.post(
        "/auth/register",
        json={"email": "token-type@example.com", "password": "correct-horse-battery"},
    )

    assert response.status_code == 201
    token = response.json()["access_token"]
    unverified_payload = jwt.decode(token, options={"verify_signature": False})
    assert unverified_payload["typ"] == "access"


def test_decode_access_token_rejects_wrong_token_type() -> None:
    settings = Settings(
        database_url="sqlite://",
        jwt_secret="test-only-jwt-secret-with-enough-length",
    )
    token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "typ": "refresh"},
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(
            token=token,
            secret=settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )


def test_settings_reject_placeholder_or_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite://", jwt_secret="change-me")

    with pytest.raises(ValidationError):
        Settings(database_url="sqlite://", jwt_secret="short")


def test_settings_parse_cors_origins_from_comma_separated_env() -> None:
    settings = Settings(
        database_url="sqlite://",
        jwt_secret="test-only-jwt-secret-with-enough-length",
        cors_allowed_origins="http://localhost:8081, https://tally.example.com/",
    )

    assert settings.cors_origins == ("http://localhost:8081", "https://tally.example.com")


def test_production_settings_reject_wildcard_cors_and_weak_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example.com/tally",
            jwt_secret="test-only-jwt-secret-with-enough-length",
            cors_allowed_origins="https://tally.example.com",
        )

    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example.com/tally",
            jwt_secret="production-secret-with-enough-random-length-for-tests",
            cors_allowed_origins="*",
        )


def test_production_settings_reject_debug_and_sqlite_database() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            debug=True,
            database_url="postgresql+psycopg://user:pass@db.example.com/tally",
            jwt_secret="production-secret-with-enough-random-length-for-tests",
            cors_allowed_origins="https://tally.example.com",
        )

    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="sqlite:///prod.db",
            jwt_secret="production-secret-with-enough-random-length-for-tests",
            cors_allowed_origins="https://tally.example.com",
        )


def test_allowed_import_sources_are_csv_manual_paste_or_synthetic_only() -> None:
    assert ALLOWED_IMPORT_SOURCES == (
        "csv_upload",
        "manual_entry",
        "paste_import",
        "synthetic_demo",
    )
    assert set(DISALLOWED_IMPORT_SOURCES).isdisjoint(ALLOWED_IMPORT_SOURCES)
