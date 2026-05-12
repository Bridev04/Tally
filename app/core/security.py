from datetime import UTC, datetime, timedelta
import uuid

import bcrypt
import jwt
from jwt import InvalidTokenError
from pydantic import SecretStr


def hash_password(password: SecretStr) -> str:
    password_bytes = password.get_secret_value().encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: SecretStr, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.get_secret_value().encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    *,
    user_id: uuid.UUID,
    secret: SecretStr,
    algorithm: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, secret.get_secret_value(), algorithm=algorithm)


def decode_access_token(*, token: str, secret: SecretStr, algorithms: list[str]) -> uuid.UUID:
    try:
        payload = jwt.decode(token, secret.get_secret_value(), algorithms=algorithms)
        subject = payload.get("sub")
        token_type = payload.get("typ")
        if not isinstance(subject, str) or token_type != "access":
            raise InvalidTokenError
        return uuid.UUID(subject)
    except (InvalidTokenError, ValueError) as exc:
        raise InvalidTokenError from exc
