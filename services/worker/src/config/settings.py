# services/worker/src/config/settings.py
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Env
    ENV: Literal["development", "staging", "production"] = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = "DEBUG"

    # Celery / MQ
    BROKER_URL: str = "redis://redis:6379/1"
    RESULT_BACKEND: str = "redis://redis:6379/2"
    CELERY_NAMESPACE: str = "vproxysuite"

    # Runtime safety limits (defaults conservative)
    DEFAULT_TASK_TIMEOUT_SEC: int = 75
    DEFAULT_SUBPROCESS_TIMEOUT_SEC: int = 30
    DEFAULT_SUBPROCESS_MAX_OUTPUT_BYTES: int = 1_000_000  # 1 MB

    # Safety toggles (advanced tests gate — must be explicitly enabled later)
    ENABLE_SECURITY_ADVANCED: bool = False

    # Network safety knobs
    DNS_RESOLVE_TIMEOUT_SEC: int = 5
    MAX_PARALLEL_PLUGINS: int = 4  # soft cap

    # Service metadata
    SERVICE_NAME: str = "VProxySuite Worker"

    @property
    def is_dev(self) -> bool:
        return self.ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
