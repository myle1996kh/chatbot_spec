"""Structured JSON logging configuration using structlog."""
import structlog
import logging
from src.config import settings


def configure_logging():
    """Configure structured JSON logging with structlog."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None):
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


# Initialize logging on module import
configure_logging()
