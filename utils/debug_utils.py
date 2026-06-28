"""
Debug utilities for the LeftOvers scanner.
"""

import urllib.parse

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
