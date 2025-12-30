"""
Structured logging configuration using structlog.

Outputs JSON-formatted logs for production monitoring and analysis.
Follows best practices: log events, not data; never log secrets.
"""

import structlog
import logging
import sys
from typing import Any


def setup_logging(debug: bool = False) -> None:
    """
    Configure structured JSON logging.
    
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
        Structured logger instance
    """
    return structlog.get_logger(name)
