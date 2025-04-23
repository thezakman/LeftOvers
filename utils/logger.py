"""
Logging configuration for LeftOvers.
"""

import logging
import os
from datetime import datetime
from rich.logging import RichHandler

# Configure logging
def setup_logger(verbose=False, silent=False, log_file=None):
    """Configure and return the logger instance.
    
    Args:
        verbose: Enable debug logging if True
        silent: Only log errors if True
        log_file: Path to log file if you want to write logs to disk
    """
    handlers = [RichHandler(rich_tracebacks=True, markup=True)]
    
    # Add file logging if requested
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers
    )
    
    logger = logging.getLogger("leftover")
    
    if silent:
        logger.setLevel(logging.ERROR)
    elif verbose:
        logger.setLevel(logging.DEBUG)
        
    return logger

# Default logger instance
logger = setup_logger()

# Helper functions
def get_log_file_path():
    """Generate a timestamped log file path."""
    log_dir = os.path.join(os.path.expanduser("~"), ".leftover", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(log_dir, f"leftover_{timestamp}.log")