from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_path: Path = Path("/data/landing-leads.sqlite3")
    data_encryption_key: SecretStr
    data_hash_key: SecretStr
    allowed_origins: str = "https://annaelle.uz,https://www.annaelle.uz"
    allowed_landing_hosts: str = "annaelle.uz,www.annaelle.uz"
    schema_path: Path = Path("/app/config/landing-kommo.schema.json")
    kommo_domain: str = "annaellelaser.kommo.com"
    kommo_long_lived_token: SecretStr = Field(
        validation_alias=AliasChoices("KOMMO_LONG_LIVED_TOKEN", "kommo_token")
    )
    kommo_webhook_secret: SecretStr = Field(
        validation_alias=AliasChoices("KOMMO_WEBHOOK_SECRET", "kommo_webhook_secret")
    )
    kommo_timeout_seconds: float = 8.0
    meta_website_dataset_id: str = Field(
        validation_alias=AliasChoices("META_WEBSITE_DATASET_ID", "meta_dataset_id")
    )
    meta_website_access_token: SecretStr = Field(
        validation_alias=AliasChoices("META_WEBSITE_ACCESS_TOKEN", "meta_access_token")
    )
    meta_graph_api_version: str = "v25.0"
    meta_test_event_code: str | None = None
    meta_timeout_seconds: float = 8.0
    task_delay_seconds: int = 900
    worker_interval_seconds: float = 5.0
    max_body_bytes: int = 32_768
    max_phone_submissions_per_hour: int = 3
    max_ip_submissions_per_hour: int = 12

    @field_validator("kommo_domain")
    @classmethod
    def validate_kommo_domain(cls, value: str) -> str:
        cleaned = value.strip().lower().removeprefix("https://").rstrip("/")
        if not cleaned.endswith(".kommo.com"):
            raise ValueError("KOMMO_DOMAIN must end with .kommo.com")
        return cleaned

    @field_validator("meta_graph_api_version")
    @classmethod
    def validate_meta_version(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned.startswith("v") or not cleaned[1:].replace(".", "").isdigit():
            raise ValueError("META_GRAPH_API_VERSION must look like v25.0")
        return cleaned

    @property
    def origin_set(self) -> frozenset[str]:
        return frozenset(
            item.strip().rstrip("/") for item in self.allowed_origins.split(",") if item.strip()
        )

    @property
    def landing_host_set(self) -> frozenset[str]:
        return frozenset(
            item.strip().lower() for item in self.allowed_landing_hosts.split(",") if item.strip()
        )


def load_schema(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        schema = json.load(stream)
    required = (
        ("kommo", "pipeline_id"),
        ("kommo", "tag", "id"),
        ("source", "source_uid"),
        ("lead_fields", "submission_id", "id"),
    )
    for keys in required:
        value: Any = schema
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                raise ValueError(f"Schema is missing {'.'.join(keys)}")
            value = value[key]
    return schema


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
