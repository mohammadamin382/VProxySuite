# services/api/src/config/settings.py
from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    ENV: Literal["development", "staging", "production"] = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = "DEBUG"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Storage / Infra
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@db:5432/vproxy"
    REDIS_URL: AnyUrl = "redis://redis:6379/0"  # type: ignore[assignment]

    # Auth/JWT (for future stages)
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: Literal["HS256", "RS256"] = "HS256"
    ACCESS_TOKEN_EXPIRES_MINUTES: int = 60 * 24

    # Service metadata
    SERVICE_NAME: str = "VProxySuite API"

    @property
    def is_dev(self) -> bool:
        return self.ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
