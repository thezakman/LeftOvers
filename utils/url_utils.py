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
    
    # Realize o sanity check global apenas uma vez para o domínio base
    sanity_result, sanity_data = perform_sanity_check(http_client, base_domain, verbose)

    # Check if there's a path in the URL
    path_label = None
    path_segments = []
    if path and path != "/":
        segments = parsed_url.get("path_segments", [])
        if segments:
            path_label = "/".join(segments)
            path_segments = segments

    # Para garantir que os segmentos sejam corretamente capturados, vamos registrar alguns logs
    if verbose:
        path = parsed_url.get("path", "").strip('/')
        if path:
            segments = path.split('/')
            logger.debug(f"URL path: {path}")
            logger.debug(f"Segmentos encontrados: {len(segments)}")
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
    else:
        # If no path, just test the base URL
        tests.append((full_url_base, "Base URL"))

    # Test based on subdomain (if exists)
    if subdomain:
        test_url = f"{scheme}://{full_hostname}/{subdomain}"
        tests.append((test_url, "Subdomain"))

    # Test based on domain name
    test_url = f"{scheme}://{full_hostname}/{domain}"
    tests.append((test_url, "Domain"))

    # Test based on hostname (without subdomain) - only if different from full_hostname
    if subdomain and domain and suffix:
        domain_hostname = f"{domain}.{suffix}"
        if domain_hostname != full_hostname:
            test_url = f"{scheme}://{full_hostname}/{domain_hostname}"
            tests.append((test_url, "Domain Name"))

    # Add brute force tests if enabled
    if brute_mode and backup_words:
        for word in backup_words:
            # Use better test type naming without redundancy
            test_type = f"Brute Force: {word}"
            # Add base URL with backup words
            test_url = f"{scheme}://{full_hostname}/{word}"
            tests.append((test_url, test_type))
            
            # If we have a path, also try domain.com/path/word
            if path_label:
                test_url = f"{scheme}://{full_hostname}/{path_label}/{word}"
                tests.append((test_url, f"Brute Force Path: {word}"))

    # Para depuração avançada
    if verbose:
        from utils.debug_utils import debug_url_segments
        debug_url_segments(target_url)
        
        # Verificar especificamente os segmentos que serão gerados
        for i, (url, test_type) in enumerate(tests):
            if test_type.startswith("Segment"):
                segment_num = int(test_type.split(' ')[-1])
                parsed = urllib.parse.urlparse(url)
                path = parsed.path.strip('/')
                if path:
                    segments = path.split('/')
                    print(f"[DEBUG-GENERATE] URL Base para {test_type}: {url}")
                    if segment_num <= len(segments):
                        print(f"[DEBUG-GENERATE] Segment {segment_num} real: '{segments[segment_num-1]}'")
                    else:
                        print(f"[DEBUG-GENERATE] Segment {segment_num} não existe em {url}")

    return tests, main_page, baseline_responses
