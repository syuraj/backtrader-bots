"""Structured logging configuration for the trading platform."""

import logging
import logging.handlers
import sys
from pathlib import Path

import structlog
from structlog.typing import FilteringBoundLogger

from ..config.settings import settings


def configure_logging() -> FilteringBoundLogger:
    """Configure structured logging with rotation and formatting."""
    
    # Ensure log directory exists
    log_dir = Path(settings.log_directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "trading.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, settings.log_level))
    
    # Add file handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer() if settings.environment == "development" 
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()


def get_logger(name: str = __name__) -> FilteringBoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


# Configure logging on module import
logger = configure_logging()
