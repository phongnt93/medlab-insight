from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "MedLab Insight"
    app_version: str = "0.1.0"

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.5-flash", alias="GEMINI_MODEL")
    gemini_timeout_seconds: float = Field(default=20.0, alias="GEMINI_TIMEOUT_SECONDS", gt=0)
    gemini_max_retries: int = Field(default=2, alias="GEMINI_MAX_RETRIES", ge=0, le=5)
    llm_mode: Literal["auto", "gemini", "offline"] = Field(default="auto", alias="MEDLAB_LLM_MODE")

    risk_model_path: Path = Field(
        default=Path("artifacts/risk_model.joblib"), alias="MEDLAB_RISK_MODEL_PATH"
    )
    risk_model_meta_path: Path = Field(
        default=Path("artifacts/model_card.json"), alias="MEDLAB_RISK_MODEL_META_PATH"
    )
    risk_low_threshold: float = Field(default=0.35, alias="MEDLAB_RISK_LOW", ge=0, le=1)
    risk_high_threshold: float = Field(default=0.65, alias="MEDLAB_RISK_HIGH", ge=0, le=1)

    max_note_chars: int = Field(default=500, alias="MEDLAB_MAX_NOTE_CHARS", ge=0, le=2000)
    log_level: str = Field(default="INFO", alias="MEDLAB_LOG_LEVEL")

    def llm_enabled(self) -> bool:
        if self.llm_mode == "offline":
            return False
        if self.llm_mode == "gemini":
            return bool(self.gemini_api_key)
        return bool(self.gemini_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
