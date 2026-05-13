from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: SecretStr
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)
    auth_rate_limit_requests: int = Field(default=5, gt=0)
    auth_rate_limit_window_seconds: int = Field(default=60, gt=0)
    import_rate_limit_requests: int = Field(default=20, gt=0)
    import_rate_limit_window_seconds: int = Field(default=60, gt=0)
    max_request_body_bytes: int = Field(default=1_048_576, gt=0)
    max_upload_bytes: int = Field(default=5_242_880, gt=0)
    max_import_rows: int = Field(default=1_000, gt=0, le=10_000)
    max_paste_import_bytes: int = Field(default=100_000, gt=0, le=1_048_576)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
