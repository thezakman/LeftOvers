"""
Debug utilities for the LeftOvers scanner.
"""

import sys
import re
import urllib.parse
from typing import List, Dict, Any, Optional

from leftovers.utils.http_utils import parse_url
from leftovers.utils.logger import logger

def debug_url_segments(url: str) -> None:
    """
    Debug all segments in a URL path.
    
    Args:
        url: URL to debug
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip('/')
    
    if path and path != "/":
        segments = path.split('/')
        logger.debug(f"URL {url} has {len(segments)} path segments:")
        
        for i, segment in enumerate(segments):
            logger.debug(f"  Segment {i+1}: '{segment}'")
            
        # Test base URL as well
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        logger.debug(f"Base URL: {base_url}")
    else:
        logger.debug(f"URL {url} has no path segments")

def debug_segment_display(url: str, segment_num: int) -> None:
    """
    Debug the display of a specific segment in a URL.
    
    Args:
        url: URL to debug
        segment_num: Segment number to display (1-based)
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip('/')
    
    if not path:
        logger.debug(f"URL {url} has no path segments")
        return
        
    segments = path.split('/')
    
    if segment_num < 1 or segment_num > len(segments):
        logger.debug(f"Segment {segment_num} is out of range. URL has {len(segments)} segments")
        return
        
    segment = segments[segment_num - 1]
    logger.debug(f"Segment {segment_num} of {url}: '{segment}'")
    
    # Test URL for this segment
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    test_url = f"{base_url}/{segment}"
    
    logger.debug(f"Test URL for segment {segment_num}: {test_url}")

def debug_brute_force_path(url: str, test_type: str) -> None:
    """
    Debug brute force path tests - optimized version.
    
    Args:
        url: URL being tested
        test_type: Type of test being performed
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip('/')
    
    if not path:
        logger.debug(f"Brute force URL {url} has no path")
        return
    
    # Efficient extraction of the test word using partition
    word = ""
    if ": " in test_type:
        _, _, word = test_type.partition(": ")
    
    # Efficiently split the path
    segments = path.split('/')
    
    # Use startswith instead of full string comparison for faster check
    if test_type.startswith("Brute Force Recursive:"):
        # For recursive tests, the word is the last segment
        parent_path = "/".join(segments[:-1]) if len(segments) > 1 else ""
        logger.debug(f"Recursive brute force: Testing '{word}' at /{parent_path}")
        
        # Add path pattern analysis to help with problem detection
        if parent_path:
            depth = len(parent_path.split('/'))
            logger.debug(f"Path depth: {depth} levels deep")
    else:
        # For regular brute force, the path is the parent and we append the word
        if word and word in segments:
            # Optimization: use list index instead of loop
            word_index = segments.index(word)
            parent_path = "/".join(segments[:word_index])
            logger.debug(f"Brute force: Testing '{word}' at /{parent_path}")
            
            # Additional helpful debugging information
            remaining_path = "/".join(segments[word_index+1:])
            if remaining_path:
                logger.debug(f"Path continuation after test point: /{remaining_path}")
        else:
            logger.debug(f"Brute force: Testing at path /{path}")
            
            # Check if the path appears to be an API or dynamic resource
            if any(segment.isdigit() for segment in segments):
                logger.debug("Warning: Path contains numeric segments, might be dynamic content")
            if any(segment.lower() in ('api', 'rest', 'graphql', 'gql', 'v1', 'v2', 'v3') for segment in segments):
                logger.debug("Note: Path appears to be an API endpoint")

def debug_http_request(url: str, headers: Dict[str, str], method: str = "GET") -> None:
    """
    Debug HTTP request details.
    
    Args:
        url: URL being requested
        headers: HTTP headers
        method: HTTP method
    """
    logger.debug(f"HTTP {method} Request: {url}")
    logger.debug("Headers:")
    for name, value in headers.items():
        logger.debug(f"  {name}: {value}")

def debug_http_response(status_code: int, content_type: str, content_length: int, 
                        elapsed_time: float, headers: Dict[str, str]) -> None:
    """
    Debug HTTP response details.
    
    Args:
        status_code: HTTP status code
        content_type: Content-Type header
        content_length: Content length in bytes
        elapsed_time: Time taken in seconds
        headers: Response headers
    """
    logger.debug(f"Response: HTTP {status_code}")
    logger.debug(f"Content-Type: {content_type}")
    logger.debug(f"Content-Length: {content_length} bytes")
    logger.debug(f"Time: {elapsed_time:.3f} seconds")
    
    # Log specific important headers
    important_headers = ["Server", "X-Powered-By", "X-Generator", "X-Content-Type-Options", 
                        "X-Frame-Options", "X-XSS-Protection", "Content-Security-Policy"]
                        
    for header in important_headers:
        if header.lower() in [h.lower() for h in headers.keys()]:
            for h, v in headers.items():
                if h.lower() == header.lower():
                    logger.debug(f"Header {h}: {v}")

def debug_false_positive_check(url: str, is_false_positive: bool, reason: str) -> None:
    """
    Debug false positive detection.
    
    Args:
        url: URL being checked
        is_false_positive: Whether it's a false positive
        reason: Reason for false positive determination
    """
    if is_false_positive:
        logger.debug(f"False positive detected for {url}: {reason}")
    else:
        logger.debug(f"Potential finding: {url} (not a false positive)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_utils.py URL [SEGMENT_NUM]")
        sys.exit(1)
        
    url = sys.argv[1]
    debug_url_segments(url)
    
    if len(sys.argv) >= 3:
        try:
            segment_num = int(sys.argv[2])
            debug_segment_display(url, segment_num)
        except ValueError:
            print("[ERROR] The segment number must be an integer.")
