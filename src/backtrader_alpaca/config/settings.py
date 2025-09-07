"""Configuration and settings management for the trading platform."""

from pathlib import Path
from typing import Literal, Any, Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


class TradingSettings(BaseSettings):
    """Main configuration settings for the trading platform."""

    # Environment
    environment: Literal["development", "paper", "live"] = Field(
        default="development", description="Trading environment mode"
    )

    # Alpaca API Configuration
    alpaca_api_key: str = Field(default="", description="Alpaca API key")
    alpaca_secret_key: str = Field(default="", description="Alpaca secret key")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets", description="Alpaca API base URL"
    )

    # Data Configuration
    data_directory: Path = Field(
        default=Path("data"), description="Directory for market data storage"
    )

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_directory: Path = Field(
        default=Path("logs"), description="Directory for log files"
    )

    # Risk Management
    max_position_size: float = Field(
        default=10000.0, description="Maximum position size in USD"
    )
    max_daily_loss: float = Field(
        default=1000.0, description="Maximum daily loss limit in USD"
    )

    @field_validator("alpaca_base_url")
    @classmethod
    def validate_alpaca_url(cls, v: str, info) -> str:
        """Set appropriate Alpaca URL based on environment."""
        env = info.data.get("environment", "development")
        if env == "live":
            return "https://api.alpaca.markets"
        return "https://paper-api.alpaca.markets"

    @field_validator("data_directory", "log_directory")
    @classmethod
    def ensure_directory_exists(cls, v: Path) -> Path:
        """Ensure directories exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


def load_settings() -> TradingSettings:
    """Load and return application settings."""
    # Load environment variables from .env file
    load_dotenv()

    return TradingSettings()


# Global settings instance
settings = load_settings()
