"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from unittest.mock import Mock

from src.backtrader_alpaca.config.settings import TradingSettings


@pytest.fixture
def test_settings():
    """Provide test configuration settings."""
    return TradingSettings(
        environment="development",
        alpaca_api_key="test_key",
        alpaca_secret_key="test_secret",
        alpaca_base_url="https://paper-api.alpaca.markets",
        max_position_size=1000.0,
        max_daily_loss=100.0,
        log_level="DEBUG"
    )


@pytest.fixture
def mock_alpaca_client():
    """Mock Alpaca API client."""
    mock_client = Mock()
    mock_client.get_account.return_value = Mock(
        buying_power=10000.0,
        cash=5000.0,
        portfolio_value=15000.0
    )
    return mock_client


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {
        "AAPL": {
            "price": 150.00,
            "volume": 1000000,
            "bid": 149.99,
            "ask": 150.01
        }
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir
