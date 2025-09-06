"""Unit tests for configuration settings."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from .settings import TradingSettings, load_settings


class TestTradingSettings:
    """Test cases for TradingSettings configuration."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        settings = TradingSettings(
            alpaca_api_key="test_key",
            alpaca_secret_key="test_secret"
        )
        
        assert settings.environment == "development"
        assert settings.alpaca_base_url == "https://paper-api.alpaca.markets"
        assert settings.log_level == "INFO"
        assert settings.max_position_size == 10000.0
        assert settings.max_daily_loss == 1000.0
    
    def test_live_environment_url(self):
        """Test that live environment sets correct Alpaca URL."""
        settings = TradingSettings(
            environment="live",
            alpaca_api_key="test_key",
            alpaca_secret_key="test_secret"
        )
        
        assert settings.alpaca_base_url == "https://api.alpaca.markets"
    
    def test_directory_creation(self, tmp_path):
        """Test that directories are created automatically."""
        data_dir = tmp_path / "test_data"
        log_dir = tmp_path / "test_logs"
        
        settings = TradingSettings(
            alpaca_api_key="test_key",
            alpaca_secret_key="test_secret",
            data_directory=data_dir,
            log_directory=log_dir
        )
        
        assert data_dir.exists()
        assert log_dir.exists()
    
    @patch.dict(os.environ, {
        "ALPACA_API_KEY": "env_key",
        "ALPACA_SECRET_KEY": "env_secret",
        "ENVIRONMENT": "paper"
    })
    def test_environment_variable_loading(self):
        """Test loading settings from environment variables."""
        settings = TradingSettings()
        
        assert settings.alpaca_api_key == "env_key"
        assert settings.alpaca_secret_key == "env_secret"
        assert settings.environment == "paper"
