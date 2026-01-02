"""
Structured logging configuration using structlog.

Outputs JSON-formatted logs for production monitoring and analysis.
Follows best practices: log events, not data; never log secrets.
Includes request ID tracking for distributed tracing.
"""

import structlog
import logging
import sys
from typing import Any
from contextvars import ContextVar

# Context variable for storing request ID across async contexts
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def add_request_id(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Processor to add request ID to all log entries.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with request_id
    """
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def setup_logging(debug: bool = False) -> None:
    """
    Configure structured JSON logging with request ID tracking.

    Args:
        debug: If True, set log level to DEBUG, otherwise INFO
    """

    # Determine log level
    log_level = logging.DEBUG if debug else logging.INFO

    # Configure structlog processors
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            add_request_id,  # Add request ID to all logs
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance with request ID tracking
    """
    return structlog.get_logger(name)


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for the current context.

    Args:
        request_id: Unique request identifier
    """
    request_id_var.set(request_id)


def get_request_id() -> str:
    """
    Get the current request ID from context.

    Returns:
        Current request ID or empty string if not set
    """
    return request_id_var.get()
