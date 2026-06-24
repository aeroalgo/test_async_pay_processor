from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    ENVIRONMENT: Literal["local", "testing", "prod"] = "local"
    POSTGRES_URI: str
    RABBITMQ_URL: str
    API_KEY: str
    OUTBOX_POLL_INTERVAL_SEC: int = 1
    WEBHOOK_MAX_RETRIES: int = 3
    WEBHOOK_RETRY_BASE_DELAY_SEC: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
