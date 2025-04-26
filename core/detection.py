"""
Functions for detection of false positives and baseline establishment.
"""

import re
import random
import hashlib
from typing import Dict, Tuple, Any, Set

from core.result import ScanResult
from utils.logger import logger
from utils.http_utils import calculate_content_hash, HttpClient

def establish_baseline(http_client: HttpClient, base_url: str, verbose: bool = False):
    """Establish baseline responses for false positive detection."""
    if verbose:
        logger.debug(f"Establishing baseline responses for: {base_url}")
    
    baseline_responses = {}
    main_page = None
    
    # First, get the main page to establish a baseline for normal content
    try:
        result = http_client.get(base_url)
        if result["success"]:
            main_response = result["response"]
            main_size = len(main_response.content) if main_response.content else 0
            main_hash = calculate_content_hash(main_response.content)
            
            # Store baseline for main page
            main_page = {
                "size": main_size,
                "hash": main_hash,
                "status": main_response.status_code,
                "content_type": main_response.headers.get('Content-Type', 'N/A')
            }
            
            if verbose:
                logger.debug(f"Main page baseline: Status {main_response.status_code}, " 
                            f"Size {main_size} bytes, Hash: {main_hash[:8]}...")
    except Exception as e:
        if verbose:
            logger.debug(f"Error establishing main page baseline: {str(e)}")
    
    # Test non-existent resources
    test_paths = ["/__non_existent_resource_12345__", "/system/__fake_path_54321__"]
    
    for path in test_paths:
        try:
            url = f"{base_url}{path}"
            result = http_client.get(url)
            if result["success"]:
                response = result["response"]
                content_hash = calculate_content_hash(response.content)
                
                # Store baseline by status code
                key = response.status_code
                if key not in baseline_responses:
                    baseline_responses[key] = []
                
                baseline_responses[key].append({
                    "content_hash": content_hash,
                    "content_type": response.headers.get('Content-Type', 'N/A'),
                    "content_length": len(response.content) if response.content else 0,
                    "url": url
                })
                
                if verbose:
                    logger.debug(f"Baseline for {key}: {content_hash} ({len(response.content)} bytes)")
        except Exception as e:
            if verbose:
                logger.debug(f"Error establishing baseline: {str(e)}")
    
    return main_page, baseline_responses

def check_false_positive(
        result: ScanResult, 
        response_content: bytes, 
        baseline_responses: Dict[int, list],
        main_page: Dict[str, Any], 
        size_frequency: Dict[str, int]) -> Tuple[bool, str]:
    """Check if a result is likely a false positive."""
    # Calculate content hash for comparison
    content_hash = calculate_content_hash(response_content)
    result.content_hash = content_hash
    
    # 1. Track identical response sizes by status code
    size_key = f"{result.status_code}:{result.content_length}"
    if size_key not in size_frequency:
        size_frequency[size_key] = 0
    size_frequency[size_key] += 1
    
    # If we've seen this exact status+size combination multiple times, likely a false positive
    if size_frequency[size_key] >= 2 and result.status_code in (401, 403):
        return True, f"Multiple responses with identical size ({result.content_length} bytes)"
    
    # 2. Compare with main page - if a 403 response has same size as other 403s but different 
    # from main page, it's likely a generic error
    if main_page and result.status_code in (401, 403):
        main_size = main_page["size"]
        
        # If response size is very different from main page but we've seen it multiple times
        # it's likely a generic error page
        if main_size > 0 and abs(result.content_length - main_size) / main_size > 0.2:
            if size_frequency[size_key] >= 2:
                return True, "Size differs from main page, matches other error responses"
    
    # 3. Check against baseline responses
    if result.status_code in baseline_responses:
        for baseline in baseline_responses[result.status_code]:
            if content_hash == baseline["content_hash"]:
                reason = f"Matches generic {result.status_code} response"
                return True, reason
            
            # Also check for similar content length (within 5% margin)
            baseline_length = baseline["content_length"]
            if baseline_length > 0 and abs(result.content_length - baseline_length) / baseline_length < 0.05:
                reason = f"Similar size to generic {result.status_code} response"
                return True, reason

    # 4. For 403/401 responses, check specific patterns
    if result.status_code in (403, 401):
        # Very small responses are likely generic errors
        if result.content_length < 150:
            return True, "Response too small, likely generic"
            
        # Look for common strings in error pages
        if response_content:
            try:
                content_str = response_content.decode('utf-8', errors='ignore').lower()
                
                # Common words in error pages
                error_indicators = [
                    "access denied", "forbidden", "not allowed", 
                    "authorization required", "not authorized",
                    "permission denied", "access forbidden"
                ]
                
                # Check if page contains common error phrases
                for indicator in error_indicators:
                    if indicator in content_str:
                        return True, f"Contains common error text: '{indicator}'"
                
                # If text/html with small amount of text content, likely an error page
                if (result.content_type.startswith("text/html") and 
                    len(content_str) > 0 and
                    len(re.sub(r'<[^>]+>', '', content_str)) < 100):
                    return True, "Generic error page with minimal text content"
            except:
                pass
    
    # 5. For 404 errors, nearly always false positives
    if result.status_code == 404:
        return True, "404 responses are typically not residual files"
            
    return False, ""

def perform_sanity_check(http_client: HttpClient, base_url: str, verbose: bool = False):
    """
    Perform a sanity check on the target to detect if it returns the same response
    for any extension (indicating generic error pages).
    """
    if verbose:
        logger.debug(f"Performing sanity check for: {base_url}")
    
    # Use some random strings that are unlikely to exist
    random_exts = [
        f"nonexistent_{random.randint(10000, 99999)}",
        f"fakefile_{random.randint(10000, 99999)}",
        f"notreal_{random.randint(10000, 99999)}"
    ]
    
    responses = []
    
    # Check if it's just a domain or if it has a specific path
    is_domain_only = base_url.rstrip('/').count('/') <= 2  # Ex: https://example.com
    
    for random_str in random_exts:
        try:
            # Build a valid URL for the sanity test
            if is_domain_only:
                # If it's just a domain, we add a random path
                url = f"{base_url.rstrip('/')}/{random_str}"
            else:
                # If it already has a path, we add an extension to the path
                url = f"{base_url}.{random_str}"
                
            result = http_client.get(url)
            
            if result["success"]:
                response = result["response"]
                responses.append({
                    "status": response.status_code,
                    "length": len(response.content) if response.content else 0,
                    "hash": calculate_content_hash(response.content)
                })
                
                if verbose:
                    logger.debug(f"Sanity check: {url} - Status: {response.status_code}, " 
                                f"Size: {len(response.content)} bytes")
        except Exception as e:
            if verbose:
                logger.debug(f"Sanity check error: {str(e)}")
    
    sanity_check_result = {}
    
    # If we got at least 2 responses and they're identical in size and status
    if len(responses) >= 2:
        # Check if all have same status code
        statuses = {r["status"] for r in responses}
        # Check if all have same content length
        lengths = {r["length"] for r in responses}
        # Check if all have same hash
        hashes = {r["hash"] for r in responses}
        
        # If same status and content across random extensions, server likely returns
        # identical responses for all non-existent resources
        if len(statuses) == 1 and (len(lengths) == 1 or len(hashes) == 1):
            status = list(statuses)[0]
            size = list(lengths)[0]
            
            if verbose:
                logger.debug(f"Detected generic responses: Status {status}, Size {size} bytes")
            
            # Store this information for later false positive detection
            sanity_check_result = {
                "status": status,
                "size": size,
                "consistent_response": True,
                "hash": list(hashes)[0] if len(hashes) == 1 else ""
            }
            
            return True, sanity_check_result
    
    return False, sanity_check_result

def parse_status_codes(codes_str: str) -> Set[int]:
    """Convert a string of status codes to a set of integers."""
    if not codes_str:
        return None
    
    try:
        return {int(code.strip()) for code in codes_str.split(',') if code.strip()}
    except ValueError:
        logger.error("Invalid format for status codes. Use comma-separated numbers (e.g., 200,301,403)")
        return None
