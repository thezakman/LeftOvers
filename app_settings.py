"""
Global application settings for LeftOvers tool.
"""

# Version information
VERSION = "1.2.5"

# General settings
DEBUG = False
VERBOSE = False
SILENT = False
USE_COLOR = True

# Network settings
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_THREADS = 10
FOLLOW_REDIRECTS = True
VERIFY_SSL = False  # Explicitly disabled - we're a security tool and need to test insecure servers

# Disable SSL warnings globally to avoid console clutter
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# File handling settings
MAX_FILE_SIZE_MB = 10  # Maximum size to notify user (in MB)
CHUNK_SIZE = 8192      # Chunk size for streaming downloads (in bytes)

# Success status codes to recognize (200 = OK, 206 = Partial Content)
# Code 206 is essential for handling large files like PDFs when using Range requests
SUCCESS_STATUSES = {200, 206}

# Output settings
OUTPUT_FORMAT = "console"  # Options: console, json, csv

# Content type filtering - DO NOT FILTER PDF files
IGNORE_CONTENT = [
    "text/html",               # Uncomment to ignore normal HTML pages
    # "application/javascript",  # Uncomment to ignore JavaScript files
    # "application/xml",         # Uncomment to ignore XML files
]

# User-Agent settings
# Default User-Agent (will be used if no rotation is enabled)
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"

# Complete list of User-Agents for rotation
USER_AGENTS = [
    DEFAULT_USER_AGENT,  # Use the default as first item
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0.1 Mobile/15E148 Safari/604.1"
]