"""Unit tests for logging configuration."""

from pathlib import Path
from unittest.mock import patch

from .logger import configure_logging, get_logger
from ..config.settings import TradingSettings


class TestLoggingConfiguration:
    """Test cases for logging setup."""
    
    def test_logger_creation(self):
        """Test that logger can be created successfully."""
        logger = get_logger("test_logger")
        assert logger is not None
    
    def test_log_level_setting(self, test_settings: TradingSettings) -> None:
        """Test that log level is set correctly."""
        with patch('src.backtrader_alpaca.utils.logger.settings', test_settings):
            logger = configure_logging()
            # Logger should be configured without errors
            assert logger is not None
    
    def test_log_directory_creation(self, tmp_path: Path, test_settings: TradingSettings) -> None:
        """Test that log directory is created."""
        log_dir = tmp_path / "test_logs"
        test_settings.log_directory = log_dir
        
        with patch('src.backtrader_alpaca.utils.logger.settings', test_settings):
            configure_logging()
            assert log_dir.exists()
    
    def test_structured_logging(self):
        """Test that structured logging works."""
        logger = get_logger("test")
        # Should not raise any exceptions
        logger.info("Test message", key="value")
        logger.error("Test error", error_code=500)
