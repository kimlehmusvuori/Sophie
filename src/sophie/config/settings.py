"""Centralized Sophie configuration.

Loaded once via ``get_settings()``. Nothing else in the codebase should read
``os.environ`` directly for application configuration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    sophie_data_dir: Path = Field(default=Path("./data"))
    sophie_demo_mode: bool = Field(default=True)
    sophie_timezone: str = Field(default="Europe/Helsinki")

    # LLM
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")

    # Microsoft Graph / Outlook
    ms_graph_client_id: str | None = Field(default=None)
    ms_graph_tenant_id: str = Field(default="common")
    ms_graph_redirect_uri: str = Field(default="http://localhost:8765/callback")

    # Weather
    weather_provider: str = Field(default="open-meteo")
    weather_lat: float | None = Field(default=None)
    weather_lon: float | None = Field(default=None)
    weather_location_name: str | None = Field(default=None)

    @field_validator("weather_lat", "weather_lon", mode="before")
    @classmethod
    def _blank_env_value_means_unset(cls, value: object) -> object:
        """An untouched `.env.example` ships these as blank
        (`WEATHER_LAT=`) — pydantic-settings passes that through as the
        literal empty string, which fails float parsing. Treat blank as
        "not configured" rather than crashing the whole app on first run."""
        if value == "":
            return None
        return value

    @property
    def database_path(self) -> Path:
        return self.sophie_data_dir / "sophie.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    @property
    def token_cache_path(self) -> Path:
        return self.sophie_data_dir / "tokens" / "ms_graph_token_cache.bin"

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def calendar_configured(self) -> bool:
        return bool(self.ms_graph_client_id)

    @property
    def weather_configured(self) -> bool:
        return self.weather_lat is not None and self.weather_lon is not None


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.sophie_data_dir.mkdir(parents=True, exist_ok=True)
    (settings.sophie_data_dir / "tokens").mkdir(parents=True, exist_ok=True)
    return settings
