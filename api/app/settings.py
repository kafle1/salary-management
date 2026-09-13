from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 5433 to match compose, which keeps off 5432 so it does not fight a local postgres
    database_url: str = "postgresql+psycopg://salary:salary@localhost:5433/salary_management"
    # comma separated rather than json, because a json list in a compose env var is a foot gun
    cors_origins: str = "http://localhost:3000"
    sql_echo: bool = False

    @field_validator("database_url")
    @classmethod
    def _use_psycopg(cls, url: str) -> str:
        # hosted postgres hands out postgres:// urls, which sqlalchemy maps to psycopg2
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
