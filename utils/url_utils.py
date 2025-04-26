"""
URL generation and manipulation utilities.
"""

from typing import List, Tuple, Dict, Any
import urllib.parse

from utils.logger import logger
from utils.http_utils import parse_url
from core.detection import establish_baseline, perform_sanity_check

def generate_test_urls(
        http_client, 
        target_url: str, 
        brute_mode: bool = False, 
        backup_words: List[str] = None,
        verbose: bool = False) -> Tuple[List[Tuple[str, str]], Dict, Dict]:
    """Generate URLs to be tested based on the target URL."""
    parsed_url = parse_url(target_url)
    if not parsed_url:
        logger.error(f"Invalid URL: {target_url}")
        return [], {}, {}

    # Extract URL information
    scheme = parsed_url.get("scheme", "http")
    hostname = parsed_url.get("host", "")
    subdomain = parsed_url.get("subdomain", "")
    domain = parsed_url.get("domain", "")
    suffix = parsed_url.get("suffix", "")
    path = parsed_url.get("path", "")
    
    full_hostname = hostname
    base_domain = f"{scheme}://{full_hostname}"

    # Establish baseline responses for the domain
    main_page, baseline_responses = establish_baseline(http_client, base_domain, verbose)

    # Perform a global sanity check only once for the base domain
    sanity_result, sanity_data = perform_sanity_check(http_client, base_domain, verbose)

    # Check if there's a path in the URL
    path_label = None
    path_segments = []
    if path and path != "/":
        segments = parsed_url.get("path_segments", [])
        if segments:
            path_label = "/".join(segments)
            path_segments = segments

    # To ensure that segments are correctly captured, let's log some information
    if verbose:
        path = parsed_url.get("path", "").strip('/')
        if path:
            segments = path.split('/')
            logger.debug(f"URL path: {path}")
            logger.debug(f"Segments found: {len(segments)}")
            for i, segment in enumerate(segments):
                logger.debug(f"Segment {i+1}: '{segment}'")

    # Create a list of base URLs to test
    tests = []

    # Add test for full URL (original URL with path but without query parameters)
    full_url_base = f"{scheme}://{full_hostname}"
    if path_label:
        full_url_base += f"/{path_label}"
        test_url = full_url_base
        tests.append((test_url, "Full URL"))

        # Test based on the complete path
        base_url = f"{scheme}://{full_hostname}/{path_label}"
        tests.append((base_url, "Path"))

        # Test each path segment
        for i, segment in enumerate(path_segments):
            if '.' not in segment:  # Don't test files
                test_url = f"{scheme}://{full_hostname}/{segment}"
                tests.append((test_url, f"Segment {i+1}"))
        
        # NEW FEATURE: Test subdomain, domain name and domain in each path
        # For each path segment, we'll create a base path for testing
        path_bases = []
        
        # Add each partial path to the list of paths to test
        # For example, for URL /a/b/c:
        # - /a
        # - /a/b
        # - /a/b/c (already tested above as "Path")
        current_path = ""
        for i, segment in enumerate(path_segments):
            if current_path:
                current_path += f"/{segment}"
            else:
                current_path = segment
                
            # Skip the last segment as it's already tested as "Path"
            if i == len(path_segments) - 1:
                continue
                
            path_bases.append(current_path)
        
        # For each partial path, test subdomain, domain name and domain
        for path_base in path_bases:
            # Test based on subdomain (if exists)
            if subdomain:
                test_url = f"{scheme}://{full_hostname}/{path_base}/{subdomain}"
                tests.append((test_url, f"Path-Subdomain: /{path_base}"))
            
            # Test based on domain name
            if domain:
                test_url = f"{scheme}://{full_hostname}/{path_base}/{domain}"
                tests.append((test_url, f"Path-Domain-Name: /{path_base}"))
            
            # Test based on domain
            if domain and suffix:
                domain_with_suffix = f"{domain}.{suffix}"
                test_url = f"{scheme}://{full_hostname}/{path_base}/{domain_with_suffix}"
                tests.append((test_url, f"Path-Domain: /{path_base}"))
    else:
        # If no path, just test the base URL
        tests.append((full_url_base, "Base URL"))

    # Test based on subdomain (if exists)
    if subdomain:
        test_url = f"{scheme}://{full_hostname}/{subdomain}"
        tests.append((test_url, "Subdomain"))

    # IMPORTANT: Now testing Domain Name before Domain (inverted order)
    # Test based on domain name
    if domain:
        test_url = f"{scheme}://{full_hostname}/{domain}"
        tests.append((test_url, "Domain Name"))

    # Test based on domain
    if domain and suffix:
        domain_with_suffix = f"{domain}.{suffix}"
        test_url = f"{scheme}://{full_hostname}/{domain_with_suffix}"
        tests.append((test_url, "Domain"))

    # Add brute force tests if enabled
    if brute_mode and backup_words:
        for word in backup_words:
            # Use better test type naming without redundancy
            test_type = f"Brute Force: {word}"
            
            # If we have a path, we prefer to test domain.com/path/word (more specific)
            if path_label:
                test_url = f"{scheme}://{full_hostname}/{path_label}/{word}"
                tests.append((test_url, test_type))
            else:
                # If we don't have a path, we just test domain.com/word
                test_url = f"{scheme}://{full_hostname}/{word}"
                tests.append((test_url, test_type))

    # For advanced debugging
    if verbose:
        from utils.debug_utils import debug_url_segments
        debug_url_segments(target_url)
        
        # Specifically check the segments that will be generated
        for i, (url, test_type) in enumerate(tests):
            if test_type.startswith("Segment"):
                segment_num = int(test_type.split(' ')[-1])
                parsed = urllib.parse.urlparse(url)
                path = parsed.path.strip('/')
                if path:
                    segments = path.split('/')
                    print(f"[DEBUG-GENERATE] Base URL for {test_type}: {url}")
                    if segment_num <= len(segments):
                        print(f"[DEBUG-GENERATE] Real Segment {segment_num}: '{segments[segment_num-1]}'")
                    else:
                        print(f"[DEBUG-GENERATE] Segment {segment_num} doesn't exist in {url}")

    return tests, main_page, baseline_responses
