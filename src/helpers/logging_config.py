# """
# Logging Configuration module for Healthcare GraphRAG system.

# This module configures the logging system for the entire application,
# setting up consistent log formatting, log levels based on environment variables,
# and providing a global logger instance that can be imported by other modules.
# """
# import os
# import logging


# def setup_logging():
#     """Configure logging globally."""
#     logging.basicConfig(
#         level=os.getenv("LOG_LEVEL", "INFO"),
#         format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
#     )
#     return logging.getLogger(__name__)


# logger = setup_logging()

"""
Logging Configuration module.

This module provides a centralized logging configuration for the application.
It ensures consistent logging format, level management via environment variables,
and safe initialization with error handling.

The logger returned can be reused across the project to maintain uniform logging behavior.
"""

import os
import logging


def setup_logging() -> logging.Logger:
    """
    Configure global logging settings for the application.

    This function initializes the logging system using Python's built-in
    logging module. The log level is determined by the environment variable
    `LOG_LEVEL`, defaulting to "INFO" if not set.

    Returns:
        logging.Logger: Configured logger instance for the current module.

    Raises:
        RuntimeError: If logging configuration fails.
    """
    try:
        log_level = os.getenv("LOG_LEVEL", "INFO")

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )

        logger = logging.getLogger(__name__)
        logger.info("Logging has been configured successfully with level: %s", log_level)

        return logger

    except Exception as e:
        # Fallback logger (minimal)
        logging.basicConfig(level="ERROR")
        fallback_logger = logging.getLogger(__name__)
        fallback_logger.error(
            "Failed to configure logging: %s", str(e), exc_info=True
        )

        raise RuntimeError(f"Logging configuration failed: {str(e)}") from e


# Initialize global logger
logger = setup_logging()