from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 8080
    node_env: str = "development"

    primary_llm_url: str = "https://inference.do-ai.run/v1/chat/completions"
    candidate_llm_url: str = "https://inference.do-ai.run/v1/chat/completions"
    primary_llm_api_key: str = ""
    primary_llm_model: str = "llama3.3-70b-instruct"
    candidate_llm_api_key: str = ""
    candidate_llm_model: str = "openai-gpt-oss-120b"

    primary_timeout_ms: int = 30000
    shadow_job_timeout_ms: int = 30000

    shadow_max_concurrency: int = 50
    shadow_max_queue_size: int = 500

    redis_url: str = "redis://localhost:6379"

    db_driver: Literal["sqlite", "postgres"] | None = None
    database_url: str | None = None
    sqlite_path: str = "./data/shadow_evaluator.db"
    enable_audit_log: bool = False

    @property
    def resolved_db_driver(self) -> Literal["sqlite", "postgres"]:
        if self.db_driver in ("sqlite", "postgres"):
            return self.db_driver
        if self.database_url and self.database_url.startswith(
            ("postgres://", "postgresql://")
        ):
            return "postgres"
        return "sqlite"

    @property
    def sqlalchemy_url(self) -> str:
        if self.resolved_db_driver == "postgres":
            if not self.database_url:
                raise ValueError("DATABASE_URL is required when DB_DRIVER=postgres")
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"sqlite+aiosqlite:///{Path(self.sqlite_path).as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
