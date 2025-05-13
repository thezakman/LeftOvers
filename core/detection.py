"""
Functions for detection of false positives and baseline establishment.
"""

import re
import random
import hashlib
import difflib
from typing import Dict, Tuple, Any, Set
from functools import lru_cache

from core.result import ScanResult
from utils.logger import logger
from utils.http_utils import calculate_content_hash, HttpClient

def establish_baseline(http_client: HttpClient, base_url: str, verbose: bool = False):
    """
    Establish baseline responses for false positive detection with improved accuracy.
    
    Args:
        http_client: HTTP client for making requests
        base_url: Base URL to establish baseline for
        verbose: Whether to log verbose information
        
    Returns:
        Tuple of (main_page, baseline_responses)
    """
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
            
            # Extract more detailed information for better baseline
            content_type = main_response.headers.get('Content-Type', 'N/A')
            server = main_response.headers.get('Server', 'N/A')
            
            # Extract text content for semantic comparison
            main_text = ""
            if content_type and 'text/html' in content_type.lower() and main_response.content:
                try:
                    main_text = _extract_text_content(main_response.content)
                except:
                    pass
            
            # Store enhanced baseline for main page
            main_page = {
                "size": main_size,
                "hash": main_hash,
                "status": main_response.status_code,
                "content_type": content_type,
                "server": server,
                "headers": dict(main_response.headers),
                "text_content": main_text[:5000],  # Limit to first 5000 chars for memory efficiency
                "response_time": result["time"]
            }
            
            if verbose:
                logger.debug(f"Main page baseline: Status {main_response.status_code}, " 
                            f"Size {main_size} bytes, Hash: {main_hash[:8]}...")
    except Exception as e:
        if verbose:
            logger.debug(f"Error establishing main page baseline: {str(e)}")
    
    # Test non-existent resources with randomized paths for better detection
    test_paths = [
        f"/__non_existent_resource_{random.randint(10000, 99999)}__", 
        f"/system/__fake_path_{random.randint(10000, 99999)}__",
        f"/api/__invalid_endpoint_{random.randint(10000, 99999)}__",
        f"/not_found_{random.randint(10000, 99999)}.html"
    ]
    
    for path in test_paths:
        try:
            url = f"{base_url}{path}"
            result = http_client.get(url)
            if result["success"]:
                response = result["response"]
                content_hash = calculate_content_hash(response.content)
                
                # Extract text content for semantic comparison
                text_content = ""
                if response.headers.get('Content-Type', '').lower().startswith('text/'):
                    try:
                        text_content = _extract_text_content(response.content)
                    except:
                        pass
                
                # Store enhanced baseline by status code
                key = response.status_code
                if key not in baseline_responses:
                    baseline_responses[key] = []
                
                baseline_responses[key].append({
                    "content_hash": content_hash,
                    "content_type": response.headers.get('Content-Type', 'N/A'),
                    "content_length": len(response.content) if response.content else 0,
                    "url": url,
                    "headers": dict(response.headers),
                    "text_content": text_content[:2000],  # First 2000 chars for memory efficiency
                    "response_time": result["time"]
                })
                
                if verbose:
                    logger.debug(f"Baseline for {key}: {content_hash[:8]} ({len(response.content)} bytes)")
        except Exception as e:
            if verbose:
                logger.debug(f"Error establishing baseline: {str(e)}")
    
    return main_page, baseline_responses

@lru_cache(maxsize=32)
def _extract_text_content(content: bytes) -> str:
    """
    Extract text content from HTML using regex (cached for performance).
    
    Args:
        content: HTML content as bytes
        
    Returns:
        Text content extracted from HTML
    """
    try:
        # Convert bytes to string
        text = content.decode('utf-8', errors='ignore')
        
        # Remove HTML tags using regex
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    except Exception as e:
        logger.debug(f"Error extracting text content: {str(e)}")
        return ""

def check_false_positive(
        result: ScanResult, 
        response_content: bytes, 
        baseline_responses: Dict[int, list],
        main_page: Dict[str, Any], 
        size_frequency: Dict[str, int]) -> Tuple[bool, str]:
    """
    Check if a result is likely a false positive using multiple advanced heuristics.
    
    Args:
        result: ScanResult object with response metadata
        response_content: Raw content bytes from the response
        baseline_responses: Dictionary of baseline responses keyed by status code
        main_page: Information about the main page response
        size_frequency: Dictionary tracking frequency of response sizes by status
        
    Returns:
        Tuple of (is_false_positive: bool, reason: str)
    """
    from app_settings import SUCCESS_STATUSES
    
    # Calculate content hash for comparison - only once
    content_hash = calculate_content_hash(response_content)
    result.content_hash = content_hash
    
    # Skip false positive detection for zero-sized responses
    if result.content_length == 0:
        return False, ""
    
    # Special handling for PDF files - PDF files are almost never false positives
    # when they return 200 OK or 206 Partial Content
    if (result.status_code in SUCCESS_STATUSES and 
        (result.content_type and "application/pdf" in result.content_type.lower() or 
         result.url.lower().endswith(".pdf"))):
        # Check for PDF signature in content
        if len(response_content) >= 5 and response_content[:5] in (b'%PDF-', b'%pdf-'):
            return False, ""  # Definitely not a false positive
    
    # Fast path for 404 responses - almost always false positives
    if result.status_code == 404:
        return True, "404 responses are typically not residual files"
    
    # Special treatment for success status codes (200, 206)
    if result.status_code in SUCCESS_STATUSES:
        # For 200/206 responses, only mark as false positive if strong evidence exists
        # We want to be more conservative with these status codes
        false_positive_threshold = 0.9  # Higher threshold for certainty (90%)
    else:
        # For other status codes, we can be more aggressive in marking false positives
        false_positive_threshold = 0.7  # Lower threshold (70%)
    
    # Track identical response sizes by status code with more specific key
    size_key = f"{result.status_code}:{result.content_length}:{result.content_type.split(';')[0]}"
    if size_key not in size_frequency:
        size_frequency[size_key] = 0
    size_frequency[size_key] += 1
    
    # Cache the extracted text content for reuse in multiple comparisons
    text_content = None
    if "text" in result.content_type.lower() and response_content:
        text_content = _extract_text_content(response_content)
    
    # Multiple identical responses with error codes are likely generic error pages
    if result.status_code >= 400 and size_frequency[size_key] >= 2:
        return True, f"Multiple identical responses with status {result.status_code}"
    
    # Check against baseline 404 responses for custom error pages
    if result.status_code >= 400 and 404 in baseline_responses and text_content:
        for baseline in baseline_responses[404]:
            # Get baseline text content
            baseline_text = baseline.get("text_content", "")
            
            # If both have text content, check similarity
            if baseline_text:
                similarity = _compute_text_similarity(text_content, baseline_text)
                
                # High similarity to 404 baseline = likely a custom error page
                if similarity > false_positive_threshold:
                    return True, f"Response text is {similarity:.0%} similar to 404 error page"
    
    # Compare with main page to detect generic responses
    if main_page and content_hash:
        # Exact hash match is a strong indicator
        if content_hash == main_page.get("hash"):
            return True, "Response hash matches main page (site returns same content)"
        
        # Special treatment for 200/206 responses - these are important but need careful validation
        if result.status_code in SUCCESS_STATUSES:
            # Size comparison
            if main_page.get("size") and result.content_length > 0:
                size_ratio = min(result.content_length, main_page["size"]) / max(result.content_length, main_page["size"])
                
                # Content type must match and size must be very similar to consider a false positive
                if size_ratio > 0.97 and result.content_type == main_page.get("content_type"):
                    return True, "Response very similar to main page (likely same content with small variations)"
                
                # For text responses with similar size, compare content
                if size_ratio > 0.8 and result.content_type == main_page.get("content_type") and text_content:
                    main_text = main_page.get("text_content", "")
                    
                    if main_text:
                        similarity = _compute_text_similarity(text_content, main_text)
                        
                        # Very high similarity to main page = likely not a different file
                        if similarity > 0.95:  # 95% similarity threshold for 200/206
                            return True, f"Response text is {similarity:.0%} similar to main page content"

    # Special case for binary content like PDFs - much less likely to be false positives
    # when returning success status codes
    if result.status_code in SUCCESS_STATUSES:
        is_binary = any(ct in result.content_type.lower() for ct in 
                       ['pdf', 'octet-stream', 'image/', 'audio/', 'video/', 
                        'zip', 'excel', 'word', 'powerpoint', 'binary'])
        
        if is_binary:
            # Binary content with success code is very likely a real file
            return False, ""
    
    # Pass - not identified as a false positive
    return False, ""

def _compute_text_similarity(text1: str, text2: str) -> float:
    """
    Compute similarity between two text strings.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Simple case - exact match
    if text1 == text2:
        return 1.0
    
    # Empty text case
    if not text1 or not text2:
        return 0.0
    
    # For very long texts, use a faster approach with token sets
    if len(text1) > 1000 or len(text2) > 1000:
        return _token_set_similarity(text1, text2)
    
    # For shorter texts, use sequence matcher for better accuracy
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def _token_set_similarity(text1: str, text2: str) -> float:
    """
    Compute similarity using token sets (words).
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Tokenize to words and convert to sets
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))
    
    # Handle empty sets
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity: intersection / union
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

def _words_near_each_other(text: str, word1: str, word2: str, window: int = 10) -> bool:
    """
    Check if two words or phrases are near each other in text.
    
    Args:
        text: Text to search in
        word1: First word/phrase to find
        word2: Second word/phrase to find
        window: Maximum number of words between occurrences
        
    Returns:
        Boolean indicating if words are within window words of each other
    """
    # Find all occurrences of word1
    word1_positions = [m.start() for m in re.finditer(re.escape(word1), text)]
    word2_positions = [m.start() for m in re.finditer(re.escape(word2), text)]
    
    if not word1_positions or not word2_positions:
        return False
    
    # Check if any occurrence of word1 is near any occurrence of word2
    for pos1 in word1_positions:
        for pos2 in word2_positions:
            # Get the words between the two positions
            if pos1 < pos2:
                between_text = text[pos1 + len(word1):pos2]
            else:
                between_text = text[pos2 + len(word2):pos1]
                
            # Count words in between
            words_between = len(re.findall(r'\s+', between_text.strip()))
            
            # If words_between is less than our window, they're close enough
            if words_between <= window:
                return True
                
    return False

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
