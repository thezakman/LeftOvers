#!/usr/bin/env python3
"""
URL analysis tool for debugging segmentation issues.
"""

import sys
import urllib.parse

def analyze_url(url):
    """Analyzes a URL and shows all its components."""
    print(f"\nAnalyzing URL: {url}")
    
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Show basic components
    print("\nBasic components:")
    print(f"Scheme: {parsed.scheme}")
    print(f"Netloc: {parsed.netloc}")
    print(f"Path: {parsed.path}")
    print(f"Params: {parsed.params}")
    print(f"Query: {parsed.query}")
    print(f"Fragment: {parsed.fragment}")
    
    # Analyze the netloc (domain)
    print("\nDomain analysis:")
    netloc = parsed.netloc
    parts = netloc.split('.')
    
    print(f"Domain parts: {parts}")
    
    if len(parts) >= 3:
        print(f"Possible subdomain: {parts[0]}")
        print(f"Main domain: {'.'.join(parts[1:])}")
    else:
        print(f"Domain without subdomain: {netloc}")
    
    # Analyze the path
    print("\nPath analysis:")
    path = parsed.path.strip('/')
    
    if not path:
        print("Empty path")
    else:
        segments = path.split('/')
        print(f"Number of segments: {len(segments)}")
        
        for i, segment in enumerate(segments, 1):
            print(f"Segment {i}: '{segment}'")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python url_analyzer.py URL")
        sys.exit(1)
    
    analyze_url(sys.argv[1])
