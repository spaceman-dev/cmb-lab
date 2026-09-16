"""Environment-driven configuration shared by all services."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Postgres ---
    postgres_user: str = "cmblab"
    postgres_password: str = "cmblab_dev_password"
    postgres_db: str = "cmblab"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Object storage ---
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "cmblab"
    s3_secret_key: str = "cmblab_dev_password"
    s3_bucket: str = "cmblab"
    s3_region: str = "us-east-1"

    # --- Peer services ---
    catalog_url: str = "http://localhost:8001"
    ingest_url: str = "http://localhost:8002"
    spectrum_url: str = "http://localhost:8003"
    cosmology_url: str = "http://localhost:8004"
    anomaly_url: str = "http://localhost:8005"
    literature_url: str = "http://localhost:8006"

    # --- External ---
    ads_api_token: str = ""
    #: Optional. Enables the stage-2 (LLM-backed) chat assistant. Get one free at
    #: https://aistudio.google.com/apikey — without it the assistant stays in stage 1.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # --- Runtime ---
    log_level: str = "INFO"
    data_dir: Path = Field(default=Path("./data"))
    max_workers: int = 12

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def download_cache(self) -> Path:
        path = self.data_dir / "downloads"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
