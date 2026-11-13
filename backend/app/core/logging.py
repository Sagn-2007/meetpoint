"""Logging configuration for MeetPoint."""

import logging
import sys


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure and return the root logger for the application."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("meetpoint")
    logger.setLevel(numeric_level)
    
    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger


logger = setup_logging()
