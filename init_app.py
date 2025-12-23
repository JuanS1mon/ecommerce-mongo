"""
Initialization utilities for the application
"""
import os
import logging
from typing import Callable

logger = logging.getLogger(__name__)

def create_all_tables(create_tables_func: Callable, logger: logging.Logger):
    """
    Create all database tables - placeholder for MongoDB/Beanie
    Since Beanie handles collections automatically, this is a no-op
    """
    logger.info("[OK] MongoDB collections will be created automatically by Beanie")
    return True

def ensure_directories():
    """
    Ensure necessary directories exist
    """
    directories = [
        "static/uploads",
        "static/img",
        "logs",
        "temp"
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"[OK] Created directory: {directory}")
        else:
            logger.debug(f"Directory already exists: {directory}")
