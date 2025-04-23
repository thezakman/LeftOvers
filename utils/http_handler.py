"""
HTTP handling utilities for LeftOvers with optimizations for large files.
"""

import time
import requests
from requests.exceptions import RequestException
from urllib.parse import urlparse
from .console import print_large_file_skipped, console
# Import default config
from ..config import MAX_FILE_SIZE_MB, CHUNK_SIZE, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT, VERIFY_SSL, FOLLOW_REDIRECTS

class ScanResult:
    """Class to store HTTP scan results."""
    def __init__(self, url, status_code, content_type=None, content_length=None, response_time=0):
        self.url = url
        self.status_code = status_code
        self.content_type = content_type or 'unknown'
        self.content_length = content_length
        self.response_time = response_time
        self.false_positive = False
        self.false_positive_reason = None
        self.is_large_file = False
        self.partial_download = False
        
    def mark_as_false_positive(self, reason):
        """Mark result as a false positive."""
        self.false_positive = True
        self.false_positive_reason = reason

def check_url_with_size_limit(url, timeout=DEFAULT_TIMEOUT, user_agent=DEFAULT_USER_AGENT, 
                             max_size_mb=MAX_FILE_SIZE_MB, verify_ssl=VERIFY_SSL, 
                             use_color=True, follow_redirects=FOLLOW_REDIRECTS):
    """
    Check a URL with protection against large files.
    
    This uses a two-phase approach:
    1. First, send a HEAD request to check file size
    2. If file is small enough, proceed with GET
    3. If file is too large, only download the beginning for analysis
    """
    parsed_url = urlparse(url)
    headers = {'User-Agent': user_agent} if user_agent else {}
    max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
    
    # Result placeholder
    result = ScanResult(url=url, status_code=0)
    
    try:
        # Phase 1: HEAD request to get headers without body
        start_time = time.time()
        head_response = requests.head(
            url, 
            headers=headers,
            timeout=timeout,
            verify=verify_ssl,
            allow_redirects=follow_redirects
        )
        
        # Set initial status code 
        result.status_code = head_response.status_code
        
        # Parse headers
        content_length = head_response.headers.get('Content-Length')
        if content_length:
            try:
                content_length = int(content_length)
                result.content_length = content_length
                result.is_large_file = content_length > max_size_bytes
            except ValueError:
                # If content length is not a valid integer
                pass
                
        # Get content type
        result.content_type = head_response.headers.get('Content-Type', 'unknown')
        
        # If content exists and response is successful
        if head_response.status_code == 200:
            # Phase 2: GET request with appropriate limiting
            if result.is_large_file:
                # For large files, only download a small portion
                print_large_file_skipped(url, result.content_length / (1024 * 1024), max_size_mb, use_color)
                
                # Stream just the beginning of the file
                with requests.get(
                    url, 
                    headers=headers, 
                    timeout=timeout,
                    verify=verify_ssl,
                    allow_redirects=follow_redirects,
                    stream=True
                ) as response:
                    # Just read the first chunk to confirm file exists and get accurate status
                    chunk_size = min(CHUNK_SIZE, max_size_bytes // 100)  # Use config's CHUNK_SIZE
                    next(response.iter_content(chunk_size=chunk_size), None)
                    result.status_code = response.status_code
                    result.partial_download = True
            else:
                # For reasonably sized files, download normally
                response = requests.get(
                    url, 
                    headers=headers,
                    timeout=timeout,
                    verify=verify_ssl,
                    allow_redirects=follow_redirects
                )
                result.status_code = response.status_code
                
                # Update content information from actual response
                result.content_type = response.headers.get('Content-Type', result.content_type)
                content_length = response.headers.get('Content-Length')
                if content_length:
                    try:
                        result.content_length = int(content_length)
                    except ValueError:
                        pass
                else:
                    # If no Content-Length header, use the actual content length
                    result.content_length = len(response.content)
                
                # Store content for further analysis if needed
                # (This can be passed back if you need to analyze the content)
                # result.content = response.content
                
        end_time = time.time()
        result.response_time = end_time - start_time
                
    except RequestException as e:
        result.status_code = 0
        result.false_positive = True
        result.false_positive_reason = f"Request error: {str(e)}"
        
    return result

def check_multiple_urls(urls, timeout=DEFAULT_TIMEOUT, user_agent=DEFAULT_USER_AGENT, 
                        max_size_mb=MAX_FILE_SIZE_MB, verify_ssl=VERIFY_SSL, 
                        use_color=True, follow_redirects=FOLLOW_REDIRECTS,
                        progress=None, task_id=None):
    """
    Check multiple URLs, updating progress if provided.
    """
    results = []
    
    for i, url in enumerate(urls):
        # Update progress if available
        if progress and task_id is not None:
            progress.update(task_id, advance=1, description=f"[cyan]Scanning... ({i+1}/{len(urls)})")
            
        # Check the URL with size limiting
        result = check_url_with_size_limit(
            url, 
            timeout=timeout,
            user_agent=user_agent,
            max_size_mb=max_size_mb,
            verify_ssl=verify_ssl,
            use_color=use_color,
            follow_redirects=follow_redirects
        )
        
        results.append(result)
        
    return results
