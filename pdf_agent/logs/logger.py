"""
logger.py
Responsibility: Initialize structlog + Rich for structured console and file logging.
Inputs: LOG_LEVEL, LOG_FILE from config.py
Outputs: logger instance (used across all modules)
Dependencies: config.py
"""

import os
import sys
import logging
import structlog
from datetime import datetime
from config import LOG_LEVEL, LOG_FILE

def get_logger(name: str):
    """
    Exposes a single bound logger with the given name.
    Configures structlog to write JSON to a file and colored text to the console.
    """
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Convert string log level to logging constant
    level = getattr(logging, LOG_LEVEL.upper(), logging.DEBUG)

    # Shared processors for both console and file
    shared_processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.contextvars.merge_contextvars,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Standard logging configuration for handlers
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )

    # File handler (JSON)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)

    # Console handler (Rich/Colored)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.handlers = [file_handler, console_handler]
    root_logger.setLevel(level)

    # Silence noisy libraries
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("chromadb").setLevel(logging.INFO)

    return structlog.get_logger(name)

def log_event(event: 'LogEvent'):
    """
    Logs a LogEvent dataclass using the root logger.
    Useful for system-level event tracking.
    """
    logger = structlog.get_logger("agent.event")
    logger.info(event.event_type, **event.payload)
