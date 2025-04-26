"""
Utilities for debugging LeftOvers scanner.
"""

import os
import urllib.parse
import sys
from typing import List, Tuple, Any

def debug_url_segments(url: str) -> None:
    """
    Analyzes a URL and prints detailed information about its segments for debugging.
    """
    print(f"\n[DEBUG] Analyzing URL: {url}")
    
    parsed = urllib.parse.urlparse(url)
    print(f"[DEBUG] Scheme: {parsed.scheme}")
    print(f"[DEBUG] Netloc: {parsed.netloc}")
    print(f"[DEBUG] Path: {parsed.path}")
    
    path = parsed.path.strip('/')
    if not path:
        print("[DEBUG] Empty path, no segments.")
        return
        
    segments = path.split('/')
    print(f"[DEBUG] Segments found: {len(segments)}")
    
    for i, segment in enumerate(segments, 1):
        print(f"[DEBUG] Segment {i}: '{segment}'")

def debug_test_urls(test_urls: List[Tuple[str, str]]) -> None:
    """
    Prints information about the URLs to be tested.
    """
    print("\n[DEBUG] URLs that will be tested:")
    for base_url, test_type in test_urls:
        parsed = urllib.parse.urlparse(base_url)
        path = parsed.path
        print(f"[DEBUG] Type: {test_type}, URL: {base_url}")
        
        if test_type.startswith("Segment") and path:
            path_clean = path.strip('/')
            if path_clean:
                segments = path_clean.split('/')
                segment_num = int(test_type.split(' ')[-1])
                if segment_num <= len(segments):
                    print(f"[DEBUG]   Segment {segment_num}: '{segments[segment_num-1]}'")
                else:
                    print(f"[DEBUG]   Segment {segment_num}: Does not exist (total: {len(segments)})")

def debug_segment_display(base_url: str, segment_num: int) -> None:
    """
    Specific function to debug segment display.
    """
    print(f"\n[DEBUG-SEGMENT] Analyzing segment {segment_num} of URL: {base_url}")
    
    parsed = urllib.parse.urlparse(base_url)
    path = parsed.path.strip('/')
    
    if not path:
        print("[DEBUG-SEGMENT] Empty path, no segments.")
        return
    
    segments = path.split('/')
    print(f"[DEBUG-SEGMENT] Segments found: {len(segments)}")
    print(f"[DEBUG-SEGMENT] List of segments: {segments}")
    
    if 1 <= segment_num <= len(segments):
        print(f"[DEBUG-SEGMENT] Segment {segment_num}: '{segments[segment_num-1]}'")
    else:
        print(f"[DEBUG-SEGMENT] Segment {segment_num} does not exist (total: {len(segments)})")

def debug_segment_url(url: str, test_type: str) -> None:
    """
    Analyzes a specific URL for a test type and extracts segment information.
    """
    print(f"\n[DEBUG-SEGMENT-URL] Analyzing URL for {test_type}: {url}")
    
    if not test_type.startswith("Segment"):
        print(f"[DEBUG-SEGMENT-URL] Test type '{test_type}' is not a segment. Ignoring.")
        return
    
    try:
        segment_num = int(test_type.split(' ')[-1])
        
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            print("[DEBUG-SEGMENT-URL] Empty path, no segments to analyze.")
            return
        
        segments = path.split('/')
        print(f"[DEBUG-SEGMENT-URL] Total number of segments: {len(segments)}")
        print(f"[DEBUG-SEGMENT-URL] Complete list of segments: {segments}")
        
        if 1 <= segment_num <= len(segments):
            segment = segments[segment_num - 1]
            print(f"[DEBUG-SEGMENT-URL] Segment {segment_num} is: '{segment}'")
        else:
            print(f"[DEBUG-SEGMENT-URL] Segment {segment_num} does not exist. Total segments: {len(segments)}")
    
    except Exception as e:
        print(f"[DEBUG-SEGMENT-URL] Error in segment analysis: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_utils.py URL [segment_number]")
        sys.exit(1)
    
    url = sys.argv[1]
    debug_url_segments(url)
    
    if len(sys.argv) >= 3:
        try:
            segment_num = int(sys.argv[2])
            debug_segment_display(url, segment_num)
        except ValueError:
            print("[ERROR] The segment number must be an integer.")
