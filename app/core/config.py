from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: SecretStr
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)
    auth_rate_limit_requests: int = Field(default=5, gt=0)
    auth_rate_limit_window_seconds: int = Field(default=60, gt=0)
    max_request_body_bytes: int = Field(default=1_048_576, gt=0)
    max_upload_bytes: int = Field(default=5_242_880, gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
