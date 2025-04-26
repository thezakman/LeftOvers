"""
Logging configuration for the LeftOvers scanner.
"""

import logging
import sys
from typing import Optional

# Create a central logger instance
logger = logging.getLogger('leftovers')

def setup_logger(verbose: bool = False, silent: bool = False) -> logging.Logger:
    """
    Set up the logger with the appropriate level based on application settings.
    
    Args:
        verbose: Whether to enable verbose output (DEBUG level)
        silent: Whether to enable silent mode (ERROR level only)
        
    Returns:
        Configured logger instance
    """
    # Clear any existing handlers to avoid duplicate log entries
    if logger.handlers:
        logger.handlers.clear()
    
    # Set up the handler for console output
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Set the log level based on configuration
    if silent:
        logger.setLevel(logging.ERROR)
    elif verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    return logger