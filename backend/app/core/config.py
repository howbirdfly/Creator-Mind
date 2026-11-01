from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_prefix="CREATORMIND_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CreatorMind API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:5173"

    database_url: str = (
        "postgresql+asyncpg://creatormind:creatormind_dev@localhost:5433/creatormind"
    )
    redis_url: str = "redis://localhost:6382/0"
    celery_broker_url: str = "redis://localhost:6382/1"
    celery_result_backend: str = "redis://localhost:6382/2"

    s3_endpoint_url: str = "http://localhost:19000"
    s3_access_key: str = "creatormind"
    s3_secret_key: str = "creatormind_dev_secret"
    s3_bucket: str = "creatormind"

    llm_provider: str = "openai-compatible"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen3"
    llm_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()