"""
Logging configuration for the LeftOvers scanner.
"""

import logging
import sys

# Create a logger
logger = logging.getLogger('leftovers')

def setup_logger(verbose: bool = False, silent: bool = False):
    """
    Set up the logger with the appropriate level.
    
    Args:
        verbose: Whether to enable verbose output
        silent: Whether to enable silent mode
        
    Returns:
        Configured logger
    """
    # Clear any existing handlers
    logger.handlers = []
    
    # Set up the handler
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Set the log level based on verbose and silent flags
    if silent:
        logger.setLevel(logging.ERROR)
    elif verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    return logger