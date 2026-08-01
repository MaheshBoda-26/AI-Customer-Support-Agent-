"""
Structured logging configuration.
"""
import logging
import sys
from typing import Any, Dict
from pythonjsonlogger import jsonlogger

from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["service"] = "support-agent-backend"
        log_record["environment"] = settings.ENVIRONMENT


def setup_logging() -> None:
    """Configure structured JSON logging for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with JSON formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s",
        timestamp=True,
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Reduce noise from third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)