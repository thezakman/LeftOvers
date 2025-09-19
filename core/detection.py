"""
Functions for detection of false positives and baseline establishment.
"""

import re
import random
import hashlib
import difflib
import time
from typing import Dict, Tuple, Any, Set
from functools import lru_cache
import sys

# Add workaround for pkg_resources issues
try:
    import pkg_resources
except (ImportError, PermissionError, Exception) as e:
    # Create a more complete mock of pkg_resources to prevent errors in tldextract
    class MockPkgResources:
        class DistributionNotFound(Exception):
            pass
            
        class Distribution:
            def __init__(self, version):
                self.version = version
                
        def get_distribution(self, name):
            """Mock implementation of get_distribution to fix tldextract import"""
            versions = {
                'tldextract': '3.4.0',  # Assume a reasonable version
                'requests': '2.31.0',
                'urllib3': '2.0.4'
            }
            if name in versions:
                dist = self.Distribution(versions[name])
                return dist
            raise self.DistributionNotFound(f"Distribution '{name}' not found")
    
    # Replace pkg_resources with our enhanced mock
    pkg_resources_mock = MockPkgResources()
    sys.modules['pkg_resources'] = pkg_resources_mock
    print(f"Warning: pkg_resources import failed. Using enhanced fallback implementation.")

from core.result import ScanResult
from utils.logger import logger

# Safe import of http_utils - try/except pattern to handle import errors
try:
    from utils.http_utils import calculate_content_hash, HttpClient
except ImportError as e:
    # Define fallback functions if imports fail
    def calculate_content_hash(content):
        if not content:
            return "empty"
        return hashlib.md5(content).hexdigest()
        
    print(f"Warning: Failed to import from http_utils: {str(e)}. Using fallback implementation.")

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
        size_frequency: Dict[str, int],
        hash_frequency: Dict[str, set] = None) -> Tuple[bool, str]:
    """
    Check if a result is likely a false positive using multiple advanced heuristics.
    
    Args:
        result: ScanResult object with response metadata
        response_content: Raw content bytes from the response
        baseline_responses: Dictionary of baseline responses keyed by status code
        main_page: Information about the main page response
        size_frequency: Dictionary tracking frequency of response sizes by status
        hash_frequency: Dictionary tracking content hashes and the URLs that returned them

    Returns:
        Tuple of (is_false_positive: bool, reason: str)
    """
    from app_settings import SUCCESS_STATUSES
    
    # Calculate content hash for comparison - only once
    content_hash = calculate_content_hash(response_content)
    result.content_hash = content_hash

    # Track hash frequency across different URLs to detect same content for different extensions
    if hash_frequency is None:
        hash_frequency = {}

    if content_hash not in hash_frequency:
        hash_frequency[content_hash] = set()
    hash_frequency[content_hash].add(result.url)
    
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

    # Check if same content hash is returned for multiple different file extensions
    if len(hash_frequency[content_hash]) >= 3:
        # Extract file extensions from URLs with this hash
        extensions = set()
        for url in hash_frequency[content_hash]:
            if '.' in url:
                ext = url.split('.')[-1].lower()
                if len(ext) <= 5:  # Reasonable extension length
                    extensions.add(ext)

        # If we have the same content for 3+ different extensions, it's likely a generic response
        if len(extensions) >= 3:
            return True, f"Same content returned for multiple file extensions: {', '.join(sorted(extensions))}"
    
    # Cache the extracted text content for reuse in multiple comparisons
    text_content = None
    if "text" in result.content_type.lower() and response_content:
        text_content = _extract_text_content(response_content)
    
    # Multiple identical responses with same size/content-type are likely generic error pages
    # This applies to both error codes AND success codes that might be returning error content
    if size_frequency[size_key] >= 3:
        # For success codes, be more careful - check if it's really an error page
        if result.status_code in SUCCESS_STATUSES:
            # If it's a success code but returning HTML content, it might be a custom error page
            if "text/html" in result.content_type.lower() and result.content_length < 2000:
                # Small HTML responses with success codes that repeat are suspicious
                return True, f"Multiple identical small HTML responses with status {result.status_code} (likely custom error page)"
            # For non-HTML content or larger files, require more repetitions
            elif size_frequency[size_key] >= 5:
                return True, f"Multiple identical responses with status {result.status_code}"
        else:
            # For error codes, 3 repetitions is enough
            return True, f"Multiple identical responses with status {result.status_code}"
    
    # Enhanced baseline comparison for success codes returning same content
    if result.status_code in SUCCESS_STATUSES and baseline_responses:
        # Check if this response matches any baseline response (especially 404s)
        for baseline_status, baselines in baseline_responses.items():
            for baseline in baselines:
                if content_hash == baseline.get("content_hash"):
                    return True, f"Response hash matches baseline {baseline_status} response (server returns same content for non-existent files)"

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
    
    # Compare with main page to detect generic responses and SPA fallbacks
    if main_page and content_hash:
        # Exact hash match is a strong indicator
        if content_hash == main_page.get("hash"):
            return True, "Response hash matches main page (SPA fallback or site returns same content)"
        
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

    # Check for SPA (Single Page Application) fallback behavior
    if result.status_code in SUCCESS_STATUSES and response_content:
        try:
            # Use raw HTML content for SPA detection, not the stripped text
            html_content = response_content.decode('utf-8', errors='ignore')
            spa_indicators = _check_spa_fallback(html_content, result.url)
            if spa_indicators:
                return True, f"Detected SPA fallback: {spa_indicators}"
        except:
            pass

    # Check for legitimate leftover/backup patterns
    is_likely_leftover = _is_likely_leftover_file(result, response_content)
    if is_likely_leftover:
        # Files that match leftover patterns are less likely to be false positives
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

def _is_likely_leftover_file(result: ScanResult, response_content: bytes) -> bool:
    """
    Check if the response appears to be a legitimate leftover/backup file.

    Args:
        result: ScanResult object with response metadata
        response_content: Raw content bytes from the response

    Returns:
        Boolean indicating if the file is likely a legitimate leftover
    """
    from app_settings import SUCCESS_STATUSES

    # Only apply special leftover detection for success status codes
    if result.status_code not in SUCCESS_STATUSES:
        return False

    url_path = result.url.split('/')[-1].lower() if '/' in result.url else ""

    # 1. Check for typical backup file patterns in URL
    backup_indicators = [
        'backup', 'bak', 'old', 'orig', 'save', 'copy', 'tmp', 'temp',
        'archive', 'dump', '_old', '_bak', '_backup', '_copy', '_save',
        'test', 'dev', 'staging', 'debug', 'log'
    ]

    has_backup_pattern = any(indicator in url_path for indicator in backup_indicators)

    # 2. Check for date patterns common in backup files
    date_patterns = ['2023', '2024', '2025', '_2023', '_2024', '_2025']
    has_date_pattern = any(pattern in url_path for pattern in date_patterns)

    # 3. Check for specific file extensions commonly found in leftovers
    leftover_extensions = [
        '.sql', '.dump', '.db', '.sqlite', '.zip', '.tar', '.gz', '.bak',
        '.old', '.orig', '.log', '.txt', '.env', '.config', '.ini'
    ]

    has_leftover_extension = any(url_path.endswith(ext) for ext in leftover_extensions)

    # 4. Analyze content for leftover patterns (if it's text-based)
    content_indicates_leftover = False
    if response_content and result.content_type:
        content_type = result.content_type.lower()

        if 'text/' in content_type or 'application/json' in content_type:
            try:
                text_content = response_content.decode('utf-8', errors='ignore')[:2000]

                # Look for SQL dump patterns
                sql_patterns = ['insert into', 'create table', 'drop table', 'mysqldump']
                has_sql_pattern = any(pattern in text_content.lower() for pattern in sql_patterns)

                # Look for config file patterns
                config_patterns = ['password=', 'api_key=', 'secret=', '[database]', 'db_host=']
                has_config_pattern = any(pattern in text_content.lower() for pattern in config_patterns)

                # Look for debug/log patterns
                log_patterns = ['error:', 'warning:', 'debug:', 'exception:', 'traceback']
                has_log_pattern = any(pattern in text_content.lower() for pattern in log_patterns)

                content_indicates_leftover = has_sql_pattern or has_config_pattern or has_log_pattern

            except:
                pass

    # 5. Binary files with appropriate content types and sizes
    is_legitimate_binary = False
    if result.content_type:
        content_type = result.content_type.lower()
        binary_types = ['application/zip', 'application/x-gzip', 'application/octet-stream',
                       'application/x-tar', 'application/sql', 'text/x-sql']

        if any(btype in content_type for btype in binary_types):
            # Binary files with reasonable size (not too small, which might indicate error pages)
            if result.content_length > 100:  # At least 100 bytes
                is_legitimate_binary = True

    # Combine all indicators - if multiple indicators present, likely a real leftover
    score = sum([
        has_backup_pattern,
        has_date_pattern,
        has_leftover_extension,
        content_indicates_leftover,
        is_legitimate_binary
    ])

    # If 2 or more indicators, consider it a likely leftover
    return score >= 2

def _check_spa_fallback(html_content: str, url: str) -> str:
    """
    Check if the response appears to be a Single Page Application fallback.

    Args:
        html_content: Raw HTML content from the response
        url: The requested URL

    Returns:
        String describing SPA indicators if detected, empty string otherwise
    """
    # Get the file extension from the URL
    url_lower = url.lower()
    requested_extension = ""
    if '.' in url:
        requested_extension = url.split('.')[-1].lower()

    # Only check for SPA fallback if requesting a non-HTML file
    # (SPAs should not return HTML for actual HTML file requests)
    html_extensions = {'html', 'htm', 'php', 'asp', 'aspx', 'jsp'}
    if requested_extension in html_extensions:
        return ""

    # Common SPA indicators in HTML content
    spa_patterns = [
        # React, Vue, Angular app root elements
        ('id="root"', 'React app root element'),
        ('id="app"', 'Vue/generic app root element'),
        ('<div id="root"', 'React root div'),
        ('<div id="app"', 'App root div'),
        ('ng-app', 'AngularJS app'),

        # Common SPA build artifacts
        ('src="/assets/', 'Vite/modern build assets'),
        ('src="/static/', 'Create React App static assets'),
        ('crossorigin src=', 'Modern module script'),
        ('/assets/index-', 'Vite build pattern'),

        # Meta tags common in SPAs
        ('name="viewport"', 'SPA viewport meta tag'),
        ('type="module"', 'ES6 module script'),

        # Common SPA frameworks/libraries
        ('react', 'React framework reference'),
        ('vue', 'Vue framework reference'),
        ('angular', 'Angular framework reference'),

        # Build tool signatures
        ('webpack', 'Webpack bundler'),
        ('vite', 'Vite bundler'),
        ('parcel', 'Parcel bundler')
    ]

    detected_indicators = []
    html_lower = html_content.lower()

    for pattern, description in spa_patterns:
        if pattern in html_lower:
            detected_indicators.append(description)

    # Also check for file extension mismatch with HTML content
    non_html_extensions = {
        'zip', 'rar', 'tar', 'gz', 'pdf', 'doc', 'docx', 'xls', 'xlsx',
        'ppt', 'pptx', 'json', 'xml', 'txt', 'csv', 'sql', 'bak', 'log'
    }

    if requested_extension in non_html_extensions:
        # If we're requesting a binary/data file but getting HTML with SPA patterns
        if any(indicator in html_lower for indicator, _ in spa_patterns[:6]):  # Check main SPA patterns
            detected_indicators.append(f"HTML content returned for .{requested_extension} file")

    if len(detected_indicators) >= 2:
        return f"SPA serving HTML for .{requested_extension} request ({', '.join(detected_indicators[:3])})"

    return ""
