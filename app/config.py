"""
Configuration management using Pydantic Settings.
Handles environment variables and YAML configuration loading.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic API Configuration
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-haiku-20240307", alias="ANTHROPIC_MODEL"
    )

    # AI Provider Configuration
    ai_provider: str = Field(
        default="openai",
        alias="AI_PROVIDER",
        description="AI provider to use: 'anthropic' or 'openai'"
    )

    # OpenAI API Configuration (only used if ai_provider='openai')
    openai_api_key: Optional[str] = Field(
        default=None,
        alias="OPENAI_API_KEY"
    )
    openai_model: str = Field(
        default="gpt-5-mini",
        alias="OPENAI_MODEL"
    )

    # Telegram Bot Configuration
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(
        ...,
        alias="TELEGRAM_CHAT_ID",
        description="Default Telegram chat ID for notifications"
    )

    # Application Settings
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    scraper_timeout: int = Field(default=30, alias="SCRAPER_TIMEOUT")
    ai_timeout: int = Field(default=10, alias="AI_TIMEOUT")

    # Logfire Configuration
    logfire_token: Optional[str] = Field(default=None, alias="LOGFIRE_TOKEN")

    # Configuration File Paths
    courses_config_path: str = Field(default="config/courses.yaml")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, v: str) -> str:
        """Validate AI provider is either 'anthropic' or 'openai'."""
        v = v.lower()
        if v not in ["anthropic", "openai"]:
            raise ValueError("AI_PROVIDER must be 'anthropic' or 'openai'")
        return v

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: Optional[str], info) -> Optional[str]:
        """Validate OpenAI API key is provided when using OpenAI provider."""
        ai_provider = info.data.get("ai_provider", "anthropic")
        if ai_provider == "openai" and not v:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER='openai'")
        return v

    def load_courses_config(self) -> dict[str, Any]:
        """Load courses configuration from YAML file."""
        path = Path(self.courses_config_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Courses configuration file not found: {path.absolute()}"
            )

        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config or "targets" not in config:
            raise ValueError(
                f"Invalid courses configuration: missing 'targets' key in {path}"
            )

        return config


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings singleton.
    Uses lru_cache to ensure single instance across application.
    """
    return Settings()
