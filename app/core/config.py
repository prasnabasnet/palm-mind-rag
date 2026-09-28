from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Palm Mind RAG API"
    environment: Literal["local", "test", "production"] = "local"
    database_url: str
    redis_url: str
    qdrant_url: str
    qdrant_collection: str = "documents"
    chat_history_ttl_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()  