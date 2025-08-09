from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    ENV: Literal["development", "staging", "production"] = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = "DEBUG"

    # Telegram
    BOT_TOKEN: str = Field(..., description="Telegram bot token from @BotFather")

    # API Orchestrator
    BOT_API_BASE: AnyUrl = Field("http://api:8000", description="API base URL")

    # HTTP client
    CONNECT_TIMEOUT: float = 5.0
    READ_TIMEOUT: float = 15.0

    SERVICE_NAME: str = "VProxySuite Bot"

    @property
    def is_dev(self) -> bool:
        return self.ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
