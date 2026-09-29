from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Palm Mind RAG API"
    environment: Literal["local", "test", "production"] = "local"
    database_url: str
    redis_url: str
    qdrant_url: str
    qdrant_collection: str = "documents"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    max_upload_bytes: int = 10 * 1024 * 1024
    chat_history_max_messages: int = 20
    chat_history_ttl_seconds: int = 3600
    llm_api_key: SecretStr
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str
    rag_top_k: int = 4
    rag_min_score: float = 0.35


@lru_cache
def get_settings() -> Settings:
    return Settings()  