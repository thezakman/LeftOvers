"""
URL generation and manipulation utilities - Optimized for maximum performance.
"""

from typing import List, Tuple, Dict, Any, Set, Optional
import urllib.parse
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import tldextract

from utils.logger import logger
from utils.http_utils import parse_url
from core.detection import establish_baseline, perform_sanity_check
# Compile IP pattern only once for reuse
IP_PATTERN = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')

# Cache for already processed URLs
@lru_cache(maxsize=128)
def is_ip_address(hostname: str) -> bool:
    """Checks if the hostname is an IP address (with cache)."""
    return bool(IP_PATTERN.match(hostname))

# Common directory list for IP tests pre-defined
COMMON_IP_PATH_TESTS = [
    "admin", "dashboard", "api", "app", "backup", "config", "data",
    "files", "logs", "private", "public", "system", "temp", "upload"
]

# Common ports pre-defined
COMMON_PORTS = ["8080", "8443", "9000"]

def generate_test_urls(
        http_client, 
        target_url: str, 
        brute_mode: bool = False, 
        backup_words: List[str] = None,
        verbose: bool = False,
        brute_recursive: bool = False) -> Tuple[List[Tuple[str, str]], Dict, Dict]:
    """Generate URLs to be tested based on the target URL - Optimized version."""
    # Parse URL returns (base_url, domain, path)
    base_url, domain, path = parse_url(target_url)
    
    # Extract URL components using urllib.parse
    parsed = urllib.parse.urlparse(target_url)
    scheme = parsed.scheme or "http"
    hostname = parsed.netloc
    
    # Extract subdomain and domain using tldextract
    extracted = tldextract.extract(target_url)
    subdomain = extracted.subdomain
    domain_name = extracted.domain
    suffix = extracted.suffix
    
    full_hostname = hostname
    
    # Detect if the hostname is an IP address - using cache
    is_ip = is_ip_address(hostname)
    
    if is_ip and verbose:
        logger.info(f"Detected IP address: {hostname}. Domain-specific tests will be skipped.")

    # Start parallel tasks to establish baseline and sanity checks
    with ThreadPoolExecutor(max_workers=2) as executor:
        baseline_future = executor.submit(establish_baseline, http_client, base_url, verbose)
        sanity_future = executor.submit(perform_sanity_check, http_client, base_url, verbose)
        
        # Process path information while waiting for HTTP responses
        path_label = None
        path_segments = []
        if path:
            segments = path.split('/')
            if segments:
                path_label = path
                path_segments = segments
        
        # Debug logging for path segments
        if verbose:
            _log_path_segments(path)
        
        # Collect results from parallel tasks
        main_page, baseline_responses = baseline_future.result()
        sanity_result, sanity_data = sanity_future.result()

    # Use efficient data structure for duplicate control
    tests = []
    added_urls = set()

    # Optimized helper function to add URL to the test set
    def add_test(url, test_type):
        if url not in added_urls:
            added_urls.add(url)
            tests.append((url, test_type))

    # Execute test generations in parallel when possible
    tasks = []
    
    # Always run base tests
    tasks.append((_generate_base_tests, (add_test, scheme, full_hostname, path_label, path_segments)))
    
    # Domain-specific or IP-specific tests
    if not is_ip:
        tasks.append((_generate_domain_tests, (add_test, scheme, full_hostname, subdomain, domain_name, suffix)))
    
    # Path-based tests
    if path_label:
        if is_ip:
            tasks.append((_generate_ip_path_tests, (add_test, scheme, full_hostname, path_label, path_segments)))
        else:
            tasks.append((_generate_path_tests, (add_test, scheme, full_hostname, path_label, path_segments, 
                        subdomain, domain_name, suffix)))
    
    # Execute tasks in parallel
    with ThreadPoolExecutor(max_workers=min(len(tasks), 4)) as executor:
        # Submit each task for execution
        futures = []
        for func, args in tasks:
            futures.append(executor.submit(func, *args))
        
        # Wait for all tasks to complete
        for future in futures:
            future.result()
    
    # Brute force tests (run sequentially as they modify the same set)
    if brute_mode and backup_words:
        _generate_brute_force_tests(
            add_test, scheme, full_hostname, path_label, path_segments, 
            backup_words, brute_recursive
        )

    # Advanced debugging
    if verbose:
        _debug_generated_tests(target_url, tests, verbose)
        
    return tests, main_page, baseline_responses

def _generate_base_tests(add_test, scheme, full_hostname, path_label, path_segments):
    """Generate basic URL tests based on the original URL structure."""
    full_url_base = f"{scheme}://{full_hostname}"
    
    # Base tests for the given URL
    if path_label:
        # Test full URL path
        full_url = f"{full_url_base}/{path_label}"
        add_test(full_url, "Full URL")
        
        # Test based on the complete path
        add_test(full_url, "Path")
        
        # Test each path segment individually
        for i, segment in enumerate(path_segments):
            if '.' not in segment:  # Don't test files
                test_url = f"{scheme}://{full_hostname}/{segment}"
                add_test(test_url, f"Segment {i+1}")
    else:
        # If no path, just test the base URL
        add_test(full_url_base, "Base URL")

def _generate_domain_tests(add_test, scheme, full_hostname, subdomain, domain, suffix):
    """Generate tests based on domain components."""
    # Test based on each subdomain level (if exists)
    if subdomain:
        subdomains = subdomain.split('.')
        for sub in subdomains:
            test_url = f"{scheme}://{full_hostname}/{sub}"
            # Usar "Subdomain:level" para poder identificar qual nível está sendo testado
            add_test(test_url, f"Subdomain:{sub}")

    # Test based on domain name
    if domain:
        test_url = f"{scheme}://{full_hostname}/{domain}"
        add_test(test_url, "Domain Name")

    # Test based on domain with suffix
    if domain and suffix:
        domain_with_suffix = f"{domain}.{suffix}"
        test_url = f"{scheme}://{full_hostname}/{domain_with_suffix}"
        add_test(test_url, "Domain")
def _generate_path_tests(add_test, scheme, full_hostname, path_label, path_segments, 
                       subdomain, domain, suffix):
    """Generate tests based on path components and their combinations with domain parts."""
    # Generate partial paths for testing
    path_bases = _generate_partial_paths(path_segments)
    
    # Test domain components in each partial path
    for path_base in path_bases:
        _test_domain_in_path(add_test, scheme, full_hostname, path_base, subdomain, domain, suffix)
    
    # Test each path segment in the full path
    for segment in path_segments:
        if '.' not in segment:  # Don't test files
            test_url = f"{scheme}://{full_hostname}/{path_label}/{segment}"
            add_test(test_url, f"Path-Current-Path: /{segment}")
    
    # Create a list of all path levels for testing
    path_levels = _generate_path_levels(path_segments, path_label)
    
    # For each path level, test domain components
    for path_level in path_levels:
        _test_domain_in_path_level(add_test, scheme, full_hostname, path_level, subdomain, domain, suffix)

def _generate_ip_path_tests(add_test, scheme, full_hostname, path_label, path_segments):
    """Generate path-based tests for IP addresses without domain-related tests."""
    # Generate partial paths for testing
    path_bases = _generate_partial_paths(path_segments)
    
    # Test each path segment individually
    for segment in path_segments:
        if '.' not in segment:  # Don't test files
            test_url = f"{scheme}://{full_hostname}/{segment}"
            add_test(test_url, f"IP-Path-Segment: {segment}")
    
    # Test each path segment in the full path context
    for segment in path_segments:
        if '.' not in segment:  # Don't test files
            test_url = f"{scheme}://{full_hostname}/{path_label}/{segment}"
            add_test(test_url, f"IP-Path-Current-Path: /{segment}")
    
    # Create a list of all path levels for testing
    path_levels = _generate_path_levels(path_segments, path_label)
    
    # For IP addresses, test only common directories and control numbers
    # For each path level, apply specific tests for IP
    for path_level in path_levels:
        # Test for common paths specific to IP
        for test_path in COMMON_IP_PATH_TESTS:
            test_url = f"{scheme}://{full_hostname}/{path_level}/{test_path}"
            add_test(test_url, f"IP-Path-Common: /{path_level}/{test_path}")
        
        # Test with the IP itself as a directory (common in some servers)
        test_url = f"{scheme}://{full_hostname}/{path_level}/{full_hostname}"
        add_test(test_url, f"IP-Path-Self: /{path_level}/{full_hostname}")
        
        # Test for common port numbers as directories (common practice in some services)
        for port in COMMON_PORTS:
            test_url = f"{scheme}://{full_hostname}/{path_level}/{port}"
            add_test(test_url, f"IP-Path-Port: /{path_level}/{port}")
    
    # Additionally, test common patterns in server roots with IP
    if not path_segments:
        for test_path in COMMON_IP_PATH_TESTS:
            test_url = f"{scheme}://{full_hostname}/{test_path}"
            add_test(test_url, f"IP-Root-Common: /{test_path}")

def _generate_partial_paths(path_segments):
    """Generate partial paths from path segments, excluding the complete path."""
    path_bases = []
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
    
    return path_bases

def _test_domain_in_path(add_test, scheme, full_hostname, path_base, subdomain, domain, suffix):
    """Test domain components in a specific path base."""
    # Test based on subdomain
    if subdomain:
        test_url = f"{scheme}://{full_hostname}/{path_base}/{subdomain}"
        add_test(test_url, f"Path-Subdomain: /{path_base}")
    
    # Test based on domain name
    if domain:
        test_url = f"{scheme}://{full_hostname}/{path_base}/{domain}"
        add_test(test_url, f"Path-Domain-Name: /{path_base}")
    
    # Test based on domain with suffix
    if domain and suffix:
        domain_with_suffix = f"{domain}.{suffix}"
        test_url = f"{scheme}://{full_hostname}/{path_base}/{domain_with_suffix}"
        add_test(test_url, f"Path-Domain: /{path_base}")

def _generate_path_levels(path_segments, path_label):
    """Generate all path levels from the path segments."""
    path_levels = [path_label]  # Start with the complete path
    
    current_path = ""
    for i, segment in enumerate(path_segments):
        if i == 0:
            current_path = segment
        else:
            current_path = f"{current_path}/{segment}"
            
        # Add this path level (avoid duplicating the full path)
        if current_path != path_label:
            path_levels.append(current_path)
    
    return path_levels

def _test_domain_in_path_level(add_test, scheme, full_hostname, path_level, subdomain, domain, suffix):
    """Test domain components in a specific path level."""
    # Test subdomain in path level
    if subdomain:
        test_url = f"{scheme}://{full_hostname}/{path_level}/{subdomain}"
        add_test(test_url, f"Path-Current-Subdomain: /{path_level}")
    
    # Test domain name in path level
    if domain:
        test_url = f"{scheme}://{full_hostname}/{path_level}/{domain}"
        add_test(test_url, f"Path-Current-Domain-Name: /{path_level}")
    
    # Test full domain in path level
    if domain and suffix:
        domain_with_suffix = f"{domain}.{suffix}"
        test_url = f"{scheme}://{full_hostname}/{path_level}/{domain_with_suffix}"
        add_test(test_url, f"Path-Current-Domain: /{path_level}")
    
    # Test the full hostname in path level
    test_url = f"{scheme}://{full_hostname}/{path_level}/{full_hostname}"
    add_test(test_url, f"Path-Current-Hostname: /{path_level}")

def _generate_brute_force_tests(add_test, scheme, full_hostname, path_label, path_segments, 
                              backup_words, brute_recursive):
    """Generate brute force test URLs."""
    # Filter backup words to avoid direct concatenation of terms with "." in IPs
    filtered_backup_words = backup_words
    if is_ip_address(full_hostname):
        # For IPs, remove words that start with "." or contain ".env" or ".git", etc.
        # as these would be interpreted as part of the IP (causing errors like 187.86.59.16.env.dev)
        filtered_backup_words = [
            word for word in backup_words 
            if not (word.startswith('.') or '.env.' in word or '.git' in word)
        ]
    
    # Normal brute force (only at the leaf directory)
    if path_label:
        for word in filtered_backup_words:
            test_url = f"{scheme}://{full_hostname}/{path_label}/{word}"
            add_test(test_url, f"Brute Force: {word}")
    else:
        for word in filtered_backup_words:
            test_url = f"{scheme}://{full_hostname}/{word}"
            add_test(test_url, f"Brute Force: {word}")

    # Recursive brute force (test each level of the path)
    if brute_recursive and path_segments:
        # Create a list of path levels to test
        path_levels = [f"{scheme}://{full_hostname}"]  # Start with the root level
        
        # Add each intermediate level
        current_path = ""
        for segment in path_segments[:-1]:  # Skip the last segment
            if not current_path:
                current_path = segment
            else:
                current_path = f"{current_path}/{segment}"
            
            path_levels.append(f"{scheme}://{full_hostname}/{current_path}")
        
        # For each path level, run brute force tests
        for level in path_levels:
            for word in filtered_backup_words:
                test_url = f"{level}/{word}"
                add_test(test_url, f"Brute Force Recursive: {word}")

def _log_path_segments(path):
    """Log detailed information about path segments for debugging."""
    path = path.strip('/')
    if path:
        segments = path.split('/')
        logger.debug(f"URL path: {path}")
        logger.debug(f"Segments found: {len(segments)}")
        for i, segment in enumerate(segments):
            logger.debug(f"Segment {i+1}: '{segment}'")

def _debug_generated_tests(target_url, tests, verbose):
    """Run debug routines on the generated test URLs."""
    from utils.debug_utils import debug_url_segments
    debug_url_segments(target_url)
    
    # Check segment-specific test URLs
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
