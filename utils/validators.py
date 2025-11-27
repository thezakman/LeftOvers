"""
Input validation and sanitization utilities for LeftOvers scanner.
"""

import re
from urllib.parse import urlparse
from typing import Optional, Tuple


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a URL is properly formatted and safe to scan.
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"
    
    # Remove whitespace
    url = url.strip()
    
    # Check minimum length
    if len(url) < 7:  # Minimum: http://a
        return False, "URL is too short"
    
    # Check maximum length (common browser limit)
    if len(url) > 2048:
        return False, "URL is too long (max 2048 characters)"
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"
    
    # Validate scheme
    if parsed.scheme not in ['http', 'https']:
        return False, "URL must use http or https scheme"
    
    # Validate netloc (hostname)
    if not parsed.netloc:
        return False, "URL must have a valid hostname"
    
    # Check for suspicious characters in hostname
    if re.search(r'[<>"\'\s]', parsed.netloc):
        return False, "URL contains invalid characters in hostname"
    
    # Check for localhost/private IPs if needed (optional security check)
    private_patterns = [
        r'^localhost$',
        r'^127\.',
        r'^10\.',
        r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',
        r'^192\.168\.',
        r'^::1$',
        r'^fe80:',
    ]
    
    hostname = parsed.netloc.split(':')[0].lower()
    for pattern in private_patterns:
        if re.match(pattern, hostname):
            # This is just a warning, not an error
            # Allow scanning of local networks for testing
            pass
    
    return True, None


def validate_file_path(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a file path is safe to use.
    
    Args:
        file_path: File path to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path or not isinstance(file_path, str):
        return False, "File path must be a non-empty string"
    
    # Check for path traversal attempts
    if '..' in file_path:
        return False, "File path contains suspicious path traversal sequence"
    
    # Check for null bytes
    if '\x00' in file_path:
        return False, "File path contains null bytes"
    
    # Check maximum length
    if len(file_path) > 4096:
        return False, "File path is too long"
    
    return True, None


def validate_extension(extension: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if an extension is properly formatted.
    
    Args:
        extension: File extension to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not extension or not isinstance(extension, str):
        return False, "Extension must be a non-empty string"
    
    # Remove leading dot if present
    ext = extension.lstrip('.')
    
    # Check if extension is valid
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', ext):
        return False, "Extension contains invalid characters"
    
    # Check length
    if len(ext) > 20:
        return False, "Extension is too long"
    
    if len(ext) < 1:
        return False, "Extension is too short"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe for filesystem operations.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_len = 255 - len(ext) - 1
        filename = f"{name[:max_name_len]}.{ext}" if ext else name[:255]
    
    # Ensure it's not empty
    if not filename or filename == '.':
        filename = 'unnamed'
    
    return filename


def validate_thread_count(threads: int) -> Tuple[bool, Optional[str]]:
    """
    Validate if thread count is within acceptable range.
    
    Args:
        threads: Number of threads
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(threads, int):
        return False, "Thread count must be an integer"
    
    if threads < 1:
        return False, "Thread count must be at least 1"
    
    if threads > 100:
        return False, "Thread count is too high (max 100)"
    
    return True, None


def validate_timeout(timeout: float) -> Tuple[bool, Optional[str]]:
    """
    Validate if timeout value is acceptable.
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(timeout, (int, float)):
        return False, "Timeout must be a number"
    
    if timeout < 0.1:
        return False, "Timeout is too short (min 0.1s)"
    
    if timeout > 300:
        return False, "Timeout is too long (max 300s)"
    
    return True, None


def sanitize_header_value(value: str) -> str:
    """
    Sanitize HTTP header value to prevent header injection.
    
    Args:
        value: Header value to sanitize
        
    Returns:
        Sanitized header value
    """
    if not value:
        return ""
    
    # Remove newlines and carriage returns to prevent header injection
    value = value.replace('\r', '').replace('\n', '')
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Trim whitespace
    value = value.strip()
    
    return value


def is_valid_http_method(method: str) -> bool:
    """
    Check if HTTP method is valid and safe.
    
    Args:
        method: HTTP method to check
        
    Returns:
        True if method is valid, False otherwise
    """
    valid_methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
    return method.upper() in valid_methods


def validate_wordlist_size(size: int) -> Tuple[bool, Optional[str]]:
    """
    Validate if wordlist size is reasonable.
    
    Args:
        size: Number of words in wordlist
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(size, int):
        return False, "Wordlist size must be an integer"
    
    if size < 1:
        return False, "Wordlist is empty"
    
    if size > 1000000:
        return False, "Wordlist is too large (max 1,000,000 words)"
    
    return True, None
