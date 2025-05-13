"""
Logging configuration for the LeftOvers scanner.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler

# Create a central logger instance
logger = logging.getLogger('leftovers')

def setup_logger(verbose: bool = False, silent: bool = False, 
                log_file: Optional[str] = None, log_level: Optional[str] = None) -> logging.Logger:
    """
    Set up the logger with the appropriate level and handlers based on application settings.
    
    Args:
        verbose: Whether to enable verbose output (DEBUG level)
        silent: Whether to enable silent mode (ERROR level only)
        log_file: Path to log file (if logging to file is enabled)
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Clear any existing handlers to avoid duplicate log entries
    if logger.handlers:
        logger.handlers.clear()
    
    # Determine log level based on parameters
    if silent:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        
    # Override with specified log level if provided
    if log_level:
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        level = level_map.get(log_level.upper(), level)
    
    logger.setLevel(level)
    
    # Set up console handler with appropriate formatting
    _setup_console_handler(level)
    
    # Set up file handler if a log file is specified
    if log_file:
        _setup_file_handler(log_file, level)
    
    return logger

def _setup_console_handler(level: int) -> None:
    """
    Set up console handler for logging.
    
    Args:
        level: Logging level for the handler
    """
    # Set up the handler for console output
    handler = logging.StreamHandler(sys.stderr)
    
    # Use different formatter based on level
    if level <= logging.DEBUG:
        # More detailed formatter for debug mode
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        # Simpler formatter for normal operation
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)

def _setup_file_handler(log_file: str, level: int) -> None:
    """
    Set up file handler for logging with rotation.
    
    Args:
        log_file: Path to log file
        level: Logging level for the handler
    """
    # Create directory for log file if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError:
            logger.warning(f"Could not create log directory: {log_dir}")
            return
    
    try:
        # Use rotating file handler to prevent log files from growing too large
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # Keep up to 5 backup files
            delay=True  # Don't open the file until first log
        )
        
        # Always use detailed formatter for file logs
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to file: {log_file}")
    except (IOError, PermissionError) as e:
        logger.warning(f"Could not set up log file {log_file}: {str(e)}")

def get_logging_stats() -> Dict[str, Any]:
    """
    Get statistics about the logging configuration.
    
    Returns:
        Dictionary with logging statistics
    """
    stats = {
        "level": logging.getLevelName(logger.level),
        "handlers": [],
        "log_files": []
    }
    
    # Collect information about handlers
    for handler in logger.handlers:
        handler_info = {
            "type": handler.__class__.__name__,
            "level": logging.getLevelName(handler.level)
        }
        
        # Add file path for file handlers
        if isinstance(handler, (logging.FileHandler, RotatingFileHandler)):
            handler_info["file"] = handler.baseFilename
            stats["log_files"].append(handler.baseFilename)
            
            # Add rotation info for RotatingFileHandler
            if isinstance(handler, RotatingFileHandler):
                handler_info["max_bytes"] = handler.maxBytes
                handler_info["backup_count"] = handler.backupCount
        
        stats["handlers"].append(handler_info)
    
    return stats