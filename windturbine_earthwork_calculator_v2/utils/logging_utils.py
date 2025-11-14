"""
Logging utilities for Wind Turbine Earthwork Calculator V2

Provides consistent logging across all modules.
"""

import logging
import os
from pathlib import Path
from datetime import datetime


def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up a logger with file and console handlers.

    Args:
        name (str): Logger name
        log_file (str): Path to log file (optional)
        level: Logging level (default: INFO)

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not create log file {log_file}: {e}")

    return logger


def get_plugin_logger(debug=False):
    """
    Get the main plugin logger.

    Args:
        debug (bool): If True, set to DEBUG level

    Returns:
        logging.Logger: Plugin logger instance
    """
    # Use workspace directory for logs
    log_dir = Path.home() / '.qgis3' / 'windturbine_calculator_v2'
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f'windturbine_calculator_{datetime.now().strftime("%Y%m%d")}.log'

    level = logging.DEBUG if debug else logging.INFO
    return setup_logger('WindTurbineCalculator', str(log_file), level)
