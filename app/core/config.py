from functools import lru_cache
from typing import Any, Literal, Self

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_LOCAL_CORS_ORIGINS = (
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:8082",
    "http://127.0.0.1:8082",
)


class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )
    debug: bool = False
    database_url: SecretStr
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    cors_allowed_origins: str = ",".join(DEFAULT_LOCAL_CORS_ORIGINS)
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)
    auth_rate_limit_requests: int = Field(default=5, gt=0)
    auth_rate_limit_window_seconds: int = Field(default=60, gt=0)
    import_rate_limit_requests: int = Field(default=20, gt=0)
    import_rate_limit_window_seconds: int = Field(default=60, gt=0)
    transaction_rate_limit_requests: int = Field(default=60, gt=0)
    transaction_rate_limit_window_seconds: int = Field(default=60, gt=0)
    dashboard_rate_limit_requests: int = Field(default=60, gt=0)
    dashboard_rate_limit_window_seconds: int = Field(default=60, gt=0)
    dashboard_low_confidence_threshold: float = Field(default=0.72, ge=0, le=1)
    subscription_rate_limit_requests: int = Field(default=30, gt=0)
    subscription_rate_limit_window_seconds: int = Field(default=60, gt=0)
    anomaly_rate_limit_requests: int = Field(default=30, gt=0)
    anomaly_rate_limit_window_seconds: int = Field(default=60, gt=0)
    report_rate_limit_requests: int = Field(default=20, gt=0)
    report_rate_limit_window_seconds: int = Field(default=60, gt=0)
    privacy_rate_limit_requests: int = Field(default=20, gt=0)
    privacy_rate_limit_window_seconds: int = Field(default=60, gt=0)
    llm_enabled: bool = False
    llm_provider: Literal["fake", "openai"] = "fake"
    llm_api_key: SecretStr | None = None
    llm_model: str = Field(default="gpt-4.1-mini", max_length=100)
    max_request_body_bytes: int = Field(default=1_048_576, gt=0)
    max_upload_bytes: int = Field(default=5_242_880, gt=0)
    max_import_rows: int = Field(default=1_000, gt=0, le=10_000)
    max_paste_import_bytes: int = Field(default=100_000, gt=0, le=1_048_576)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: Any) -> bool | Any:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> str | Any:
        if isinstance(value, list):
            return ",".join(str(origin).strip().rstrip("/") for origin in value if str(origin).strip())
        return value

    @field_validator("jwt_secret")
    @classmethod
    def reject_placeholder_jwt_secret(cls, value: SecretStr) -> SecretStr:
        unsafe_values = {
            "change-me",
            "changeme",
            "secret",
            "supersecret",
            "jwt-secret",
            "your-secret",
        }
        if value.get_secret_value().lower() in unsafe_values:
            raise ValueError("JWT secret must not use a placeholder value.")
        return value

    @model_validator(mode="after")
    def reject_unsafe_production_settings(self) -> Self:
        if self.environment != "production":
            return self

        database_url = self.database_url.get_secret_value().strip()
        jwt_secret = self.jwt_secret.get_secret_value()

        if not database_url:
            raise ValueError("DATABASE_URL is required in production.")
        if database_url.startswith("sqlite"):
            raise ValueError("Production DATABASE_URL must use hosted Postgres, not SQLite.")
        if self.debug:
            raise ValueError("DEBUG must be false in production.")
        cors_origins = self.cors_origins
        if not cors_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must be explicit in production.")
        if "*" in cors_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must not use wildcard origins in production.")
        if jwt_secret.lower().startswith("test-only") or len(jwt_secret) < 48:
            raise ValueError("JWT_SECRET must be a strong production secret.")

        return self

    @property
    def cors_origins(self) -> tuple[str, ...]:
        return tuple(
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
