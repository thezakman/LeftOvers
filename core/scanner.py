"""
Main implementation of the LeftOvers scanner - Optimized for maximum performance.
"""

import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any, Set
import urllib.parse
from collections import defaultdict
import time
import re
import tldextract

from core.config import (
    VERSION, DEFAULT_TIMEOUT, DEFAULT_THREADS, DEFAULT_EXTENSIONS, 
    DEFAULT_BACKUP_WORDS, DEFAULT_HEADERS, USER_AGENTS
)
from core.result import ScanResult
from core.detection import check_false_positive
from utils.logger import logger, setup_logger
from utils.console import (
    console, print_banner, print_info_panel, 
    create_progress_bar, format_and_print_result, create_url_list_progress
)
from utils.file_utils import load_url_list
from utils.http_utils import HttpClient
from utils.url_utils import generate_test_urls
from utils.extension_optimizer import ExtensionOptimizer
from utils.domain_generator import DomainWordlistGenerator

# Compile regular expressions once for reuse
SEGMENT_PATTERN = re.compile(r'Segment\s+(\d+)')
PATH_PATTERN = re.compile(r'Path-Current-Path:\s+(.+)')
PATH_INDIVIDUAL_PATTERN = re.compile(r'Path-Individual:\s+(.+)')
BRUTE_FORCE_PATTERN = re.compile(r'Brute Force:\s+(.+)')
BRUTE_RECURSIVE_PATTERN = re.compile(r'Brute Force Recursive:\s+(.+)')

class LeftOver:
    """Main scanner for finding leftover files on web servers (optimized version)."""
    
    def __init__(self, 
                 extensions: List[str] = None, 
                 timeout: int = DEFAULT_TIMEOUT,
                 threads: int = DEFAULT_THREADS,
                 headers: Dict[str, str] = None,
                 verify_ssl: bool = False,
                 use_color: bool = True,
                 verbose: bool = False,
                 silent: bool = False,
                 output_file: str = None,
                 status_filter: Set[int] = None,
                 min_content_length: int = None,
                 max_content_length: int = None,
                 rotate_user_agent: bool = False,
                 test_index: bool = False,
                 ignore_content: List[str] = None,
                 disable_fp: bool = False):
        """Initialize the scanner with the provided settings."""
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.extension_optimizer = ExtensionOptimizer()
        self.domain_generator = DomainWordlistGenerator()
        self.timeout = timeout
        self.max_workers = threads
        self.headers = headers or DEFAULT_HEADERS.copy()
        self.verify_ssl = verify_ssl
        self.use_color = use_color
        self.verbose = verbose
        self.silent = silent
        self.output_file = output_file
        self.results = []
        self.rotate_user_agent = rotate_user_agent
        self.test_index = test_index
        self.disable_fp = disable_fp
        
        # Brute force settings (default empty, set by CLI)
        self.brute_mode = False
        self.brute_recursive = False
        self.domain_wordlist = False
        self.backup_words = []
        
        # Filters
        self.status_filter = status_filter
        self.min_content_length = min_content_length
        self.max_content_length = max_content_length
        self.ignore_content = ignore_content or []
        
        # Output settings
        self.output_file = output_file
        self.output_per_url = False  # New option
        
        # Set logging level based on verbose and silent flags
        global logger
        logger = setup_logger(verbose, silent)
        
        # HTTP client for requests - optimized
        self.http_client = HttpClient(
            headers=self.headers,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
            rotate_user_agent=self.rotate_user_agent
        )
        
        # Optimization: use defaultdict for false positive control and size tracking
        self.error_fingerprints = defaultdict(int)
        self.baseline_responses = {}
        self._size_frequency = defaultdict(int)
        self._hash_frequency = defaultdict(set)
        self._main_page = None
        
        # Global sanity check results
        self._global_sanity_check_results = {}
        
        # Optimization: use sets for tested and found URLs control
        self.tested_urls = set()
        self.found_urls = set()
        
        # Cache for parsed URL information
        self._url_parse_cache = {}
        
        # Statistics storage
        self.stats = {
            'requests': 0,
            'hits': 0,
            'total_time': 0,
            'start_time': 0,
            'end_time': 0
        }
    
    def test_url(self, base_url: str, extension: str, test_type: str) -> Optional[ScanResult]:
        """Test a single URL with a given extension - Optimized version."""
        # Check if we are testing only a domain or a specific path efficiently
        is_domain_only = '/' not in base_url[8:] if base_url.startswith('http://') else ('/' not in base_url[9:] if base_url.startswith('https://') else False)
        
        # Ensure base_url ends with / for domain-only URLs to properly append extensions
        if is_domain_only and not base_url.endswith('/'):
            base_url = f"{base_url}/"
        
        # Build the full URL efficiently
        if is_domain_only and self.test_index:
            # If it's a domain and the test_index flag is enabled, test index.{extension}
            full_url = f"{base_url.rstrip('/')}/index.{extension}"
        else:
            # Otherwise, add the extension to the end of the URL normally with a dot
            full_url = f"{base_url}.{extension}"
        
        # For PDF and document files, we need additional tests
        important_extensions = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"]
        is_important_extension = extension.lower() in important_extensions
        
        # Add test case for direct extension test
        exact_match_url = None
        if is_important_extension and not base_url.lower().endswith("." + extension.lower()):
            # Check if base_url already ends with a path component that might be the file name without extension
            # This handles cases like "/path/filename" -> "/path/filename.pdf"
            if '/' in base_url and not base_url.endswith('/'):
                exact_match_url = full_url
        
        # Add test case for specific path (direct test with full extension)
        # This ensures that extensions like .pdf are tested both as part of the path and as an extension
        path_test_url = None
        if not is_domain_only and not base_url.endswith(extension):
            path_parts = base_url.split('/')
            if len(path_parts) > 3:  # scheme://domain/path
                path_test_url = f"{'/'.join(path_parts[:-1])}/{path_parts[-1]}.{extension}"
        
        # Check if these URLs have already been tested to avoid duplication
        urls_to_test = []
        
        # First check exact match if it exists
        if exact_match_url and exact_match_url not in self.tested_urls:
            self.tested_urls.add(exact_match_url)
            urls_to_test.append(exact_match_url)
            
        # Then check standard full URL if not already tested
        if full_url not in self.tested_urls:
            self.tested_urls.add(full_url)
            urls_to_test.append(full_url)
            
        # Finally check path-based URL if not already tested
        if path_test_url and path_test_url not in self.tested_urls:
            self.tested_urls.add(path_test_url)
            urls_to_test.append(path_test_url)
        
        # Test all URLs in order (prioritizing exact match)
        for url_to_test in urls_to_test:
            result = self._test_single_url(url_to_test, extension, test_type)
            if result:
                return result
                
        return None
        
    def _test_single_url(self, full_url: str, extension: str, test_type: str) -> Optional[ScanResult]:
        """Internal helper method to test a single URL with optimized status code handling"""
        try:
            # Record the start of the request for statistics
            start_time = time.time()
            
            # Perform the HTTP request
            result = self.http_client.get(full_url)
            self.stats['requests'] += 1
            
            # Calculate request time
            req_time = time.time() - start_time
            self.stats['total_time'] += req_time
            
            if not result["success"]:
                return None
                
            response = result["response"]
            response_time = result["time"]
            
            # Extract response data efficiently
            status_code = response.status_code
            headers = response.headers
            content_type = headers.get('Content-Type', 'N/A')
            content = response.content
            content_length = len(content) if content else 0
            
            # Create the ScanResult object with the response data
            scan_result = ScanResult(
                url=full_url,
                status_code=status_code,
                content_type=content_type,
                content_length=content_length,
                response_time=response_time,
                test_type=test_type,
                extension=extension
            )
            
            # Use cascading filters for better performance (from fastest to slowest)
            
            # 1. Check status code first (very fast operation)
            if self.status_filter and status_code not in self.status_filter:
                return None
            
            # 2. Check content size (fast operation)
            if ((self.min_content_length is not None and content_length < self.min_content_length) or 
                (self.max_content_length is not None and content_length > self.max_content_length)):
                return None
            
            # 3. Check if content type should be ignored (simple string check)
            if scan_result.check_ignored_content_type():
                return None
                
            # 4. Check ignored content by the -ic parameter (normalize content_type first)
            if self.ignore_content and content_type:
                # Extract base content type without parameters like charset
                content_type_base = content_type.split(';')[0].strip()
                if any(ignore == content_type_base or content_type_base.startswith(f"{ignore}+") for ignore in self.ignore_content):
                    return None
            
            # 5. Check if the URL has already been found previously
            if scan_result.url in self.found_urls:
                return None  # URL already reported, ignore this result
            
            # Flag file as large if needed
            from app_settings import MAX_FILE_SIZE_MB, SUCCESS_STATUSES
            if content_length > MAX_FILE_SIZE_MB * 1024 * 1024:
                scan_result.large_file = True
                
            # Flag partial content
            if status_code == 206:
                scan_result.partial_content = True
            
            # 6. Finally, perform false positive check (most costly)
            is_false_positive, reason = check_false_positive(
                scan_result,
                content,
                self.baseline_responses,
                self._main_page,
                self._size_frequency,
                self._hash_frequency
            )
            scan_result.false_positive = is_false_positive
            scan_result.false_positive_reason = reason
            
            # Special handling for successful status codes (200, 206)
            # These are important but we still need to respect false positive detection
            if status_code in SUCCESS_STATUSES:
                # Only bypass false positive detection if explicitly disabled
                if self.disable_fp or not is_false_positive:
                    self.stats['hits'] += 1
                    self.found_urls.add(scan_result.url)
                    self.results.append(scan_result)
                    return scan_result
                else:
                    # Even success codes can be false positives (like SPA fallbacks)
                    # Still return the result but don't add to results list
                    return scan_result
            
            # If disable_fp is enabled, report regardless of false positive classification
            if self.disable_fp:
                # We still keep the classification for informational purposes
                self.stats['hits'] += 1
                self.found_urls.add(scan_result.url)
                self.results.append(scan_result)
                return scan_result
            
            # If false positive detection is not disabled, only report if not FP
            if not is_false_positive:
                self.stats['hits'] += 1
                self.found_urls.add(scan_result.url)
                self.results.append(scan_result)
                return scan_result
                
            return None
            
        except Exception as e:
            # Optimized error handling with specific logging
            if self.verbose:
                error_type = type(e).__name__
                logger.debug(f"Error testing URL {full_url}: {error_type}: {str(e)}")
            return None
    
    def process_url(self, target_url: str):
        """Process a URL, testing all extensions on all derived targets - Optimized version."""
        # Record the start time for statistics
        self.stats['start_time'] = time.time()

        # Optimize extensions based on target context
        optimized_extensions = self.extension_optimizer.optimize_extensions(
            self.extensions, target_url
        )
        
        # Always show target information, even in silent mode
        if self.use_color:
            console.rule(f"[bold blue]Target: {target_url}[/bold blue]", style="blue")
        else:
            title = f"Target: {target_url}"
            print("\n" + "-" * len(title))
            print(title)
            print("-" * len(title))
        
        # Debug: check URL segments before processing
        if self.verbose:
            from utils.debug_utils import debug_url_segments
            debug_url_segments(target_url)
            
        # *** DIRECT URL CHECK WITH SPECIAL HANDLING FOR PDF AND OTHER IMPORTANT FORMATS ***
        # Always check for exact match with extension first, especially for PDF files
        important_extensions = ["pdf", "docx", "xlsx", "pptx", "zip", "rar", "tar.gz", "tar"]
        
        # Check important extensions regardless of the total number of extensions
        important_exts_to_test = [ext for ext in optimized_extensions if ext.lower() in important_extensions]
        
        # If there are important extensions to test, do it first
        for extension in important_exts_to_test:
            # Ensure target_url ends with / if it's a domain-only URL (for consistent formatting)
            is_domain_only = '/' not in target_url[8:] if target_url.startswith('http://') else ('/' not in target_url[9:] if target_url.startswith('https://') else False)
            if is_domain_only and not target_url.endswith('/'):
                direct_url = f"{target_url}/.{extension}"
            else:
                direct_url = f"{target_url}.{extension}"
            
            if self.verbose:
                logger.debug(f"HIGH PRIORITY: Testing direct URL for important file: {direct_url}")
                
            # Special handling for important files (force request with modified parameters)
            try:
                # Create a specialized request for PDF/important files
                start_time = time.time()
                
                # Use a custom session for this request to ensure SSL verification is disabled
                import requests
                special_session = requests.Session()
                special_session.verify = False  # Disable SSL verification
                
                # Add headers from our client
                headers = self.http_client.session.headers.copy()
                # Add Range header to get partial content for large files
                headers['Range'] = 'bytes=0-8191'  # Get first 8KB to confirm file exists
                
                # Make the direct request
                response = special_session.get(
                    direct_url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # Update stats
                req_time = time.time() - start_time
                self.stats['requests'] += 1
                self.stats['total_time'] += req_time
                
                # Check for successful or partial content (206)
                if response.status_code in [200, 206]:
                    # File found!
                    content_type = response.headers.get('Content-Type', 'Unknown')
                    
                    # Apply content-type filter here as well before processing
                    content_type_base = content_type.split(';')[0].strip()
                    if self.ignore_content and any(ignore == content_type_base for ignore in self.ignore_content):
                        if self.verbose:
                            logger.debug(f"Ignoring result with filtered content type: {content_type_base}")
                        continue
                    
                    # Try to get accurate content length
                    if 'Content-Length' in response.headers:
                        try:
                            content_length = int(response.headers['Content-Length'])
                        except (ValueError, TypeError):
                            content_length = len(response.content) if response.content else 0
                    else:
                        content_length = len(response.content) if response.content else 0
                    
                    # Create result object
                    scan_result = ScanResult(
                        url=direct_url,
                        status_code=response.status_code,
                        content_type=content_type,
                        content_length=content_length,
                        response_time=req_time,
                        test_type="Direct URL",
                        extension=extension
                    )
                    
                    # Perform false positive check for important files too
                    is_false_positive, reason = check_false_positive(
                        scan_result,
                        response.content,
                        self.baseline_responses,
                        self._main_page,
                        self._size_frequency,
                        self._hash_frequency
                    )
                    scan_result.false_positive = is_false_positive
                    scan_result.false_positive_reason = reason

                    # Add important files to results only if not false positive (unless FP detection disabled)
                    if self.disable_fp or not is_false_positive:
                        self.stats['hits'] += 1
                        self.found_urls.add(direct_url)
                        self.results.append(scan_result)
                    
                    # Show result immediately
                    if not self.silent:
                        format_and_print_result(console, scan_result, self.use_color, self.verbose, self.silent)
                
            except Exception as e:
                if self.verbose:
                    error_type = type(e).__name__
                    logger.debug(f"Error testing important file {direct_url}: {error_type}: {str(e)}")
        
        # Flag to track if we've already found files in direct testing
        direct_check_found_files = False
            
        # ***DIRECT URL VERIFICATION***
        # Direct test for each configured extension
        if len(optimized_extensions) <= 5:  # Limit to avoid overhead with many extensions
            for extension in optimized_extensions:
                # Skip if already tested as an important extension
                if extension.lower() in important_extensions:
                    continue
                   
                # Ensure proper URL formatting with / for domain-only URLs 
                is_domain_only = '/' not in target_url[8:] if target_url.startswith('http://') else ('/' not in target_url[9:] if target_url.startswith('https://') else False)
                if is_domain_only and not target_url.endswith('/'):
                    direct_url = f"{target_url}/.{extension}"
                else:
                    direct_url = f"{target_url}.{extension}"
                    
                if self.verbose:
                    logger.debug(f"Testing direct URL: {direct_url}")
                    
                try:
                    start_time = time.time()
                    result = self.http_client.get(direct_url)
                    self.stats['requests'] += 1
                    
                    req_time = time.time() - start_time
                    self.stats['total_time'] += req_time
                    
                    if result["success"]:
                        response = result["response"]
                        response_time = result["time"]
                        
                        # Process direct response
                        status_code = response.status_code
                        headers = response.headers
                        content_type = headers.get('Content-Type', 'N/A')
                        
                        # Apply content-type filter before processing
                        content_type_base = content_type.split(';')[0].strip()
                        if self.ignore_content and any(ignore == content_type_base for ignore in self.ignore_content):
                            if self.verbose:
                                logger.debug(f"Ignoring direct URL result with filtered content type: {content_type_base}")
                            continue
                        
                        content = response.content
                        
                        # Get Content-Length from header which is more accurate for large files
                        if 'Content-Length' in response.headers:
                            try:
                                content_length = int(response.headers['Content-Length'])
                            except (ValueError, TypeError):
                                content_length = len(content) if content else 0
                        else:
                            content_length = len(content) if content else 0
                        
                        # Create result object
                        scan_result = ScanResult(
                            url=direct_url,
                            status_code=status_code,
                            content_type=content_type,
                            content_length=content_length,
                            response_time=response_time,
                            test_type="Direct URL",
                            extension=extension
                        )
                        
                        # Consider both 200 and 206 (Partial Content) as success
                        if status_code == 200 or status_code == 206:
                            # Perform false positive check
                            is_false_positive, reason = check_false_positive(
                                scan_result,
                                content,
                                self.baseline_responses,
                                self._main_page,
                                self._size_frequency,
                                self._hash_frequency
                            )
                            scan_result.false_positive = is_false_positive
                            scan_result.false_positive_reason = reason

                            # Add to results only if not false positive (unless FP detection disabled)
                            if self.disable_fp or not is_false_positive:
                                self.stats['hits'] += 1
                                self.found_urls.add(direct_url)
                                self.results.append(scan_result)
                                direct_check_found_files = True
                            
                            # Show result immediately
                            if not self.silent:
                                format_and_print_result(console, scan_result, self.use_color, self.verbose, self.silent)
                            
                            # MODIFIED: Removed early return to continue with all tests
                            # Now we'll continue with regular scanning even if we found a match
                        
                except Exception as e:
                    if self.verbose:
                        error_type = type(e).__name__
                        logger.debug(f"Error in direct test: {direct_url}: {error_type}: {str(e)}")
        
        # Reset size tracker for this target
        self._size_frequency = defaultdict(int)
        self._hash_frequency = defaultdict(set)

        # Enhance backup words with domain-based wordlist if enabled
        enhanced_backup_words = self.backup_words
        if hasattr(self, 'domain_wordlist') and self.domain_wordlist and self.brute_mode:
            if self.verbose:
                logger.info(f"Enhancing wordlist with domain-based words from {target_url}")
            enhanced_backup_words = self.domain_generator.enhance_existing_wordlist(
                enhanced_backup_words, target_url
            )
            if self.verbose:
                logger.info(f"Wordlist enhanced: {len(self.backup_words)} -> {len(enhanced_backup_words)} words")

        # Generate base URLs for testing - using the optimized version of generate_test_urls
        test_urls, self._main_page, self.baseline_responses = generate_test_urls(
            self.http_client,
            target_url,
            self.brute_mode,
            enhanced_backup_words,
            self.verbose,
            self.brute_recursive,
            self.domain_wordlist
        )
        
        if not test_urls:
            return
        
        # Create a progress bar to display status
        total_tests = len(test_urls) * len(self.extensions)
        
        # Always use progress bar, even in silent mode
        progress, task = create_progress_bar(total_tests, self.use_color)
        
        # Optimization: preprocess URLs to group by test type
        test_url_groups = defaultdict(list)
        for base_url, test_type in test_urls:
            test_url_groups[test_type].append(base_url)
        
        with progress:
            # Process groups by test type
            for test_type, urls_for_type in test_url_groups.items():
                self._display_test_type_header(test_type, urls_for_type[0])
                
                # Process in batches for better balancing and avoiding overload
                batch_size = min(100, len(urls_for_type))
                url_batches = [urls_for_type[i:i + batch_size] for i in range(0, len(urls_for_type), batch_size)]
                
                for batch in url_batches:
                    # Parallel tests for each URL in the current batch
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        # Create mapping of futures to arguments
                        futures = {}
                        for base_url in batch:
                            # Check if URL already has an extension (from domain wordlist generation)
                            url_path = base_url.split('/')[-1]  # Get the last part of the URL
                            has_extension = False

                            if '.' in url_path:
                                parts = url_path.split('.')
                                if len(parts) >= 2 and 2 <= len(parts[-1]) <= 5 and parts[-1].isalnum():
                                    has_extension = True

                            if has_extension:
                                # URL already has extension, test it directly without adding more extensions
                                future = executor.submit(self._test_single_url, base_url, "", test_type)
                                futures[future] = (base_url, "")
                            else:
                                # For each URL without extension, test all extensions in parallel
                                for ext in optimized_extensions:
                                    future = executor.submit(self.test_url, base_url, ext, test_type)
                                    futures[future] = (base_url, ext)
                        
                        # Process results as they are completed
                        for future in concurrent.futures.as_completed(futures):
                            progress.update(task, advance=1)
                            
                            result = future.result()
                            if result:
                                # Display result if found
                                format_and_print_result(console, result, self.use_color, self.verbose, self.silent)
                
                # Add a blank line after each test group
                if self.use_color:
                    console.print()
                else:
                    print()
        
        # Record end time for statistics
        self.stats['end_time'] = time.time()
        
        # Display performance statistics if verbose
        if self.verbose:
            self._display_performance_stats()
    
    def _display_test_type_header(self, test_type: str, example_url: str):
        """Display header for the current test type - optimized format."""
        if self.silent:
            return
            
        # Optimization: use precompiled regular expressions for extraction
        url_display = self._get_display_url(example_url, test_type)
        
        if self.use_color:
            # Special cases with specific formatting
            match_brute_force = BRUTE_FORCE_PATTERN.search(test_type)
            match_recursive = BRUTE_RECURSIVE_PATTERN.search(test_type)
            match_path = PATH_PATTERN.search(test_type)
            match_path_individual = PATH_INDIVIDUAL_PATTERN.search(test_type)
            
            if match_brute_force:
                word = match_brute_force.group(1)
                parsed = urllib.parse.urlparse(example_url)
                path = parsed.path.strip('/')
                if path:
                    console.print(f"[bold yellow]Testing Brute Force:[/bold yellow] {word} [bold cyan](at /{path})[/bold cyan]")
                else:
                    console.print(f"[bold yellow]Testing Brute Force:[/bold yellow] {word} [bold cyan](at root)[/bold cyan]")
                    
            elif match_recursive:
                word = match_recursive.group(1)
                parsed = urllib.parse.urlparse(example_url)
                path = parsed.path.strip('/')
                parent_path = "/".join(path.split('/')[:-1]) if '/' in path else ""
                
                if parent_path:
                    console.print(f"[bold yellow]Testing Recursive Brute Force:[/bold yellow] {word} [bold cyan](at /{parent_path})[/bold cyan]")
                else:
                    console.print(f"[bold yellow]Testing Recursive Brute Force:[/bold yellow] {word} [bold cyan](at root)[/bold cyan]")
                
            elif test_type.startswith("Path-Current-") and not match_path:
                segment = test_type.replace("Path-Current-", "")
                console.print(f"[bold blue]Testing Path:[/bold blue] {segment} [bold cyan]({url_display})[/bold cyan]")
                
            elif match_path:
                path_segment = match_path.group(1)
                console.print(f"[bold blue]Testing Path:{path_segment}[/bold blue] [bold cyan]({url_display})[/bold cyan]")
                
            elif match_path_individual:
                segment_num = match_path_individual.group(1)
                console.print(f"[bold magenta]Testing Path Segment {segment_num}[/bold magenta] [bold cyan]({url_display})[/bold cyan]")
                
            else:
                # Default format for other test types
                console.print(f"[bold green]Testing:[/bold green] {test_type} [bold cyan]({url_display})[/bold cyan]")
        else:
            if match_brute_force:
                word = match_brute_force.group(1)
                parsed = urllib.parse.urlparse(example_url)
                path = parsed.path.strip('/')
                print(f"Testing Brute Force: {word} (at /{path if path else 'root'})")
            elif test_type.startswith("Path-"):
                print(f"Testing Path: {test_type.replace('Path-', '')} ({url_display})")
            else:
                print(f"Testing: {test_type} ({url_display})")
    
    def _display_performance_stats(self):
        """Display performance statistics of the execution."""
        if self.silent:
            return
            
        total_time = self.stats['end_time'] - self.stats['start_time']
        req_time = self.stats['total_time']
        
        # Calculate average time per request
        avg_req_time = req_time / self.stats['requests'] if self.stats['requests'] > 0 else 0
        
        # Calculate requests per second
        rps = self.stats['requests'] / total_time if total_time > 0 else 0
        
        if self.use_color:
            console.print()
            console.print("[bold cyan]Performance Statistics:[/bold cyan]")
            console.print(f"  Total time: {total_time:.2f} seconds")
            console.print(f"  Requests: {self.stats['requests']}")
            console.print(f"  Hits: {self.stats['hits']}")
            console.print(f"  Req/second: {rps:.2f}")
            console.print(f"  Avg req time: {avg_req_time*1000:.2f} ms")
        else:
            print("\nPerformance Statistics:")
            print(f"  Total time: {total_time:.2f} seconds")
            print(f"  Requests: {self.stats['requests']}")
            print(f"  Hits: {self.stats['hits']}")
            print(f"  Req/second: {rps:.2f}")
            print(f"  Avg req time: {avg_req_time*1000:.2f} ms")
    
    def _get_display_url(self, base_url: str, test_type: str) -> str:
        """
        Returns the appropriate representation of the URL being tested based on the test type - optimized version.
        """
        # Use parsed URL cache to avoid repetitive processing
        if base_url in self._url_parse_cache:
            parsed = self._url_parse_cache[base_url]
        else:
            parsed = urllib.parse.urlparse(base_url)
            self._url_parse_cache[base_url] = parsed
        
        # Optimization: avoid unnecessary split operations using pattern matching first
        match_segment = SEGMENT_PATTERN.search(test_type)
        match_brute_force = BRUTE_FORCE_PATTERN.search(test_type)
        match_path = PATH_PATTERN.search(test_type)
        match_path_individual = PATH_INDIVIDUAL_PATTERN.search(test_type)
        
        if test_type == "Base URL":
            # For Base URL, show the full domain
            return parsed.netloc

        elif test_type == "Full URL":
            # For Full URL, show domain + full path
            path = parsed.path.strip('/')
            if path:
                return f"{parsed.netloc}/{path}"
            return parsed.netloc

        elif test_type == "Path":
            # For Path, show only the path
            path = parsed.path.strip('/')
            if path:
                return f"/{path}"
            return "/"

        elif match_path:
            # For Path-Current-Path, extract from precompiled regex
            return match_path.group(1)

        elif match_path_individual:
            # For Path-Individual, extract from precompiled regex
            return match_path_individual.group(1)

        elif test_type.startswith("Path-Current-"):
            # For tests without the component name in the type
            path = parsed.path.strip('/')
            if not path:
                return ""
                
            # Efficiently extract the last component of the URL
            parts = path.split("/")
            return parts[-1] if parts else ""

        elif match_segment:
            # For Segment, use precompiled regex to extract the number
            # Return the base path itself to simplify and avoid computation
            return parsed.path.strip('/')

        elif test_type.startswith("Path-Subdomain:") or test_type.startswith("Path-Domain-Name:") or test_type.startswith("Path-Domain:"):
            # Extract the last part of the path containing the tested value
            path = parsed.path.strip('/')
            if not path:
                return ""
                
            # Direct extraction without lambdas or list comprehensions
            parts = path.split('/')
            return parts[-1] if parts else ""

        elif test_type.startswith("Subdomain:"):
            # Formato novo: "Subdomain:level" - extrair o nível específico do tipo
            subdomain_level = test_type.split(':', 1)[1]
            return subdomain_level

        elif test_type == "Subdomain":
            hostname = parsed.netloc.split(':')[0]  # Remove port if exists
            
            # Cache of compound domains to avoid repetitive checks
            compound_tlds = {'co.uk', 'com.br', 'com.au', 'org.br', 'net.br', 'com.vc', 'edu.br', 'gov.br'}
            
            # Usar tldextract para obter o subdomínio completo
            extracted = tldextract.extract(base_url)
            if extracted.subdomain:
                return extracted.subdomain  # Retorna o subdomínio completo incluindo níveis compostos
            
            # Fallback para o método antigo se tldextract falhar
            parts = hostname.split('.')
            if len(parts) >= 3:
                return parts[0]
            elif len(parts) == 2 and not any(hostname.endswith(f".{tld}") for tld in compound_tlds):
                return parts[0]
            return "[none]"

        elif test_type == "Domain Name":
            hostname = parsed.netloc.split(':')[0]  # Remove port if exists
            parts = hostname.split('.')
            
            # Identify common compound TLDs - using set for O(1) lookup
            compound_tlds = {'co.uk', 'com.br', 'com.au', 'org.br', 'net.br', 'com.vc', 'edu.br', 'gov.br'}
            
            # Check special cases for domains with compound TLDs
            for tld in compound_tlds:
                if hostname.endswith(f".{tld}"):
                    # If it's a domain with subdomain and compound TLD: sub.domain.com.br
                    if len(parts) > 3:
                        return parts[-3]  # Return 'domain'
                    # If it's a normal domain with compound TLD: domain.com.br
                    else:
                        return parts[0]  # Return 'domain'

            # For normal non-compound domains
            if len(parts) >= 3:  # sub.domain.com
                return parts[-2]  # Return 'domain'
            elif len(parts) == 2:  # domain.com
                return parts[0]  # Return 'domain'

            return hostname

        elif test_type == "Domain":
            hostname = parsed.netloc.split(':')[0]  # Remove port if exists
            parts = hostname.split('.')
            
            # Identify common compound TLDs - using set for O(1) lookup
            compound_tlds = {
                "co.uk", "com.br", "com.au", "org.br", "net.br",
                "com.vc", "edu.br", "gov.br", "gov.uk", "gov.au",
                "gov.za", "edu.au", "edu.uk", "ac.uk", "org.uk",
                "net.uk", "com.mx", "com.ar", "com.co", "com.pe",
                "com.cl", "com.ec", "com.bo", "com.uy", "com.pa",
                "org.mx", "org.ar", "org.co", "org.pe", "org.cl",
                "org.ec", "org.bo", "org.uy", "org.pa", "gov.mx",
                "gov.ar", "gov.co", "gov.pe", "gov.cl", "gov.ec",
                "gov.bo", "gov.uy", "gov.pa"
            }
            
            # Check special cases for domains with compound TLDs
            for tld in compound_tlds:
                if hostname.endswith(f".{tld}"):
                    # If it's a domain with subdomain and compound TLD: sub.domain.com.br
                    if len(parts) > 3:
                        return f"{parts[-3]}.{tld}"  # Return 'domain.com.br'
                    # If it's a normal domain with compound TLD: domain.com.br
                    else:
                        return hostname  # Return 'domain.com.br'
            
            # For normal non-compound domains
            if len(parts) >= 3:  # sub.domain.com
                return f"{parts[-2]}.{parts[-1]}"  # Return 'domain.com'
            elif len(parts) == 2:  # domain.com
                return hostname  # Return 'domain.com'
            
            return hostname
            
        elif match_brute_force:
            # For Brute Force, show only the keyword being tested
            return match_brute_force.group(1)
        
        # Fallback for any other test type
        return base_url
    
    def process_url_list(self, url_list_file: str):
        """Process multiple URLs from a file - optimized version."""
        urls = load_url_list(url_list_file)
        if not urls:
            return
        
        total_urls = len(urls)
        
        # Display initial information (even in silent mode)
        if self.use_color:
            console.print(f"[bold cyan]Processing {total_urls} URLs from list: {url_list_file}[/bold cyan]")
        else:
            print(f"Processing {total_urls} URLs from list: {url_list_file}")
        
        # Use a single progress bar for all URLs
        progress, task_id = create_url_list_progress(total_urls, self.use_color)
        
        # Global statistics
        global_start_time = time.time()
        total_requests = 0
        total_hits = 0
        
        with progress:
            # Process URLs in batches for better memory performance
            batch_size = 5  # Ideal number for batch processing
            for i in range(0, total_urls, batch_size):
                batch = urls[i:i+batch_size]
                
                for j, url in enumerate(batch, 1):
                    current_index = i + j
                    # Update progress bar description with the current URL
                    progress.update(task_id, description=f"[cyan]URL {current_index}/{total_urls}: {url}")
                    
                    # Clear previous results if we are generating a file per URL
                    if self.output_per_url:
                        self.results = []
                    
                    # Process the current URL (with display disabled to avoid conflict)
                    self._process_url_without_progress(url)
                    
                    # Export results for this specific URL, if necessary
                    if self.output_per_url and self.output_file:
                        self._export_url_results(url)
                    
                    # Accumulate statistics
                    total_requests += self.stats['requests']
                    total_hits += self.stats['hits']
                    
                    # Advance the progress bar
                    progress.update(task_id, advance=1)
        
        # Display final statistics
        global_end_time = time.time()
        global_elapsed = global_end_time - global_start_time
        
        if not self.silent:
            if self.use_color:
                console.print()
                console.print("[bold green]List Processing Completed![/bold green]")
                console.print(f"[bold cyan]Global Statistics:[/bold cyan]")
                console.print(f"  Total time: {global_elapsed:.2f} seconds")
                console.print(f"  URLs processed: {total_urls}")
                console.print(f"  Total requests: {total_requests}")
                console.print(f"  Total hits: {total_hits}")
                console.print(f"  Req/second: {total_requests/global_elapsed:.2f}")
            else:
                print("\nList Processing Completed!")
                print(f"Global Statistics:")
                print(f"  Total time: {global_elapsed:.2f} seconds")
                print(f"  URLs processed: {total_urls}")
                print(f"  Total requests: {total_requests}")
                print(f"  Total hits: {total_hits}")
                print(f"  Req/second: {total_requests/global_elapsed:.2f}")
    
    def _process_url_without_progress(self, target_url: str):
        """Process a URL without using progress bars - optimized version."""
        # Reset statistics counters for this URL
        self.stats = {
            'requests': 0,
            'hits': 0,
            'total_time': 0,
            'start_time': time.time(),
            'end_time': 0
        }

        # Optimize extensions based on target context
        optimized_extensions = self.extension_optimizer.optimize_extensions(
            self.extensions, target_url
        )
        
        # Display target information
        if self.use_color:
            console.rule(f"[bold blue]Target: {target_url}[/bold blue]", style="blue")
        else:
            title = f"Target: {target_url}"
            print("\n" + "-" * len(title))
            print(title)
            print("-" * len(title))
        
        # Debug: check URL segments
        if self.verbose:
            from utils.debug_utils import debug_url_segments
            debug_url_segments(target_url)

        # *** DIRECT URL CHECK WITH SPECIAL HANDLING FOR PDF AND OTHER IMPORTANT FORMATS ***
        # Always check for exact match with extension first, especially for PDF files
        important_extensions = ["pdf", "docx", "xlsx", "pptx", "zip", "rar", "tar.gz", "tar"]

        # Check important extensions regardless of the total number of extensions
        important_exts_to_test = [ext for ext in optimized_extensions if ext.lower() in important_extensions]

        # If there are important extensions to test, do it first
        for extension in important_exts_to_test:
            # Ensure target_url ends with / if it's a domain-only URL (for consistent formatting)
            is_domain_only = '/' not in target_url[8:] if target_url.startswith('http://') else ('/' not in target_url[9:] if target_url.startswith('https://') else False)
            if is_domain_only and not target_url.endswith('/'):
                direct_url = f"{target_url}/.{extension}"
            else:
                direct_url = f"{target_url}.{extension}"

            if self.verbose:
                logger.debug(f"HIGH PRIORITY: Testing direct URL for important file: {direct_url}")

            # Special handling for important files (force request with modified parameters)
            try:
                # Create a specialized request for PDF/important files
                start_time = time.time()

                # Use a custom session for this request to ensure SSL verification is disabled
                import requests
                special_session = requests.Session()
                special_session.verify = False  # Disable SSL verification

                # Add headers from our client
                headers = self.http_client.session.headers.copy()
                # Add Range header to get partial content for large files
                headers['Range'] = 'bytes=0-8191'  # Get first 8KB to confirm file exists

                # Make the direct request
                response = special_session.get(
                    direct_url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )

                # Update stats
                req_time = time.time() - start_time
                self.stats['requests'] += 1
                self.stats['total_time'] += req_time

                # Check for successful or partial content (206)
                if response.status_code in [200, 206]:
                    # File found!
                    content_type = response.headers.get('Content-Type', 'Unknown')

                    # Apply content-type filter here as well before processing
                    content_type_base = content_type.split(';')[0].strip()
                    if self.ignore_content and any(ignore == content_type_base for ignore in self.ignore_content):
                        if self.verbose:
                            logger.debug(f"Ignoring result with filtered content type: {content_type_base}")
                        continue

                    # Try to get accurate content length
                    if 'Content-Length' in response.headers:
                        try:
                            content_length = int(response.headers['Content-Length'])
                        except (ValueError, TypeError):
                            content_length = len(response.content) if response.content else 0
                    else:
                        content_length = len(response.content) if response.content else 0

                    # Create result object
                    scan_result = ScanResult(
                        url=direct_url,
                        status_code=response.status_code,
                        content_type=content_type,
                        content_length=content_length,
                        response_time=req_time,
                        test_type="Direct URL",
                        extension=extension
                    )

                    # Perform false positive check for important files too
                    is_false_positive, reason = check_false_positive(
                        scan_result,
                        response.content,
                        self.baseline_responses,
                        self._main_page,
                        self._size_frequency,
                        self._hash_frequency
                    )
                    scan_result.false_positive = is_false_positive
                    scan_result.false_positive_reason = reason

                    # Add important files to results only if not false positive (unless FP detection disabled)
                    if self.disable_fp or not is_false_positive:
                        self.stats['hits'] += 1
                        self.found_urls.add(direct_url)
                        self.results.append(scan_result)

                    # Show result immediately
                    if not self.silent:
                        format_and_print_result(console, scan_result, self.use_color, self.verbose, self.silent)

            except Exception as e:
                if self.verbose:
                    error_type = type(e).__name__
                    logger.debug(f"Error testing important file {direct_url}: {error_type}: {str(e)}")

        # Flag to track if we've already found files in direct testing
        direct_check_found_files = False

        # ***DIRECT URL VERIFICATION***
        # Direct test for each configured extension
        if len(optimized_extensions) <= 5:  # Limit to avoid overhead with many extensions
            for extension in optimized_extensions:
                # Skip if already tested as an important extension
                if extension.lower() in important_extensions:
                    continue

                # Ensure proper URL formatting with / for domain-only URLs
                is_domain_only = '/' not in target_url[8:] if target_url.startswith('http://') else ('/' not in target_url[9:] if target_url.startswith('https://') else False)
                if is_domain_only and not target_url.endswith('/'):
                    direct_url = f"{target_url}/.{extension}"
                else:
                    direct_url = f"{target_url}.{extension}"

                if self.verbose:
                    logger.debug(f"Testing direct URL: {direct_url}")

                try:
                    start_time = time.time()
                    result = self.http_client.get(direct_url)
                    self.stats['requests'] += 1

                    req_time = time.time() - start_time
                    self.stats['total_time'] += req_time

                    if result["success"]:
                        response = result["response"]
                        response_time = result["time"]

                        # Process direct response
                        status_code = response.status_code
                        headers = response.headers
                        content_type = headers.get('Content-Type', 'N/A')

                        # Apply content-type filter before processing
                        content_type_base = content_type.split(';')[0].strip()
                        if self.ignore_content and any(ignore == content_type_base for ignore in self.ignore_content):
                            if self.verbose:
                                logger.debug(f"Ignoring direct URL result with filtered content type: {content_type_base}")
                            continue

                        content = response.content

                        # Get Content-Length from header which is more accurate for large files
                        if 'Content-Length' in response.headers:
                            try:
                                content_length = int(response.headers['Content-Length'])
                            except (ValueError, TypeError):
                                content_length = len(content) if content else 0
                        else:
                            content_length = len(content) if content else 0

                        # Create result object
                        scan_result = ScanResult(
                            url=direct_url,
                            status_code=status_code,
                            content_type=content_type,
                            content_length=content_length,
                            response_time=response_time,
                            test_type="Direct URL",
                            extension=extension
                        )

                        # Consider both 200 and 206 (Partial Content) as success
                        if status_code == 200 or status_code == 206:
                            # Perform false positive check
                            is_false_positive, reason = check_false_positive(
                                scan_result,
                                content,
                                self.baseline_responses,
                                self._main_page,
                                self._size_frequency,
                                self._hash_frequency
                            )
                            scan_result.false_positive = is_false_positive
                            scan_result.false_positive_reason = reason

                            # Add to results only if not false positive (unless FP detection disabled)
                            if self.disable_fp or not is_false_positive:
                                self.stats['hits'] += 1
                                self.found_urls.add(direct_url)
                                self.results.append(scan_result)
                                direct_check_found_files = True

                            # Show result immediately
                            if not self.silent:
                                format_and_print_result(console, scan_result, self.use_color, self.verbose, self.silent)

                            # MODIFIED: Removed early return to continue with all tests
                            # Now we'll continue with regular scanning even if we found a match

                except Exception as e:
                    if self.verbose:
                        error_type = type(e).__name__
                        logger.debug(f"Error in direct test: {direct_url}: {error_type}: {str(e)}")

        # Reset size tracker for this target
        self._size_frequency = defaultdict(int)
        self._hash_frequency = defaultdict(set)

        # Enhance backup words with domain-based wordlist if enabled
        enhanced_backup_words = self.backup_words
        if hasattr(self, 'domain_wordlist') and self.domain_wordlist and self.brute_mode:
            if self.verbose:
                logger.info(f"Enhancing wordlist with domain-based words from {target_url}")
            enhanced_backup_words = self.domain_generator.enhance_existing_wordlist(
                self.backup_words, target_url
            )
            if self.verbose:
                logger.info(f"Wordlist enhanced: {len(self.backup_words)} -> {len(enhanced_backup_words)} words")

        # Generate base URLs for testing
        test_urls, self._main_page, self.baseline_responses = generate_test_urls(
            self.http_client,
            target_url,
            self.brute_mode,
            enhanced_backup_words,
            self.verbose,
            self.brute_recursive,
            self.domain_wordlist
        )
        
        if not test_urls:
            return
        
        # Group URLs by type for more efficient processing
        test_url_groups = defaultdict(list)
        for base_url, test_type in test_urls:
            test_url_groups[test_type].append(base_url)
        
        # Process each group of URLs
        for test_type, urls_for_type in test_url_groups.items():
            # Display header for the current test type
            if not self.silent and urls_for_type:
                self._display_test_type_header(test_type, urls_for_type[0])
            
            # Process in batches for better resource utilization
            batch_size = min(100, len(urls_for_type))
            url_batches = [urls_for_type[i:i+batch_size] for i in range(0, len(urls_for_type), batch_size)]
            
            for batch in url_batches:
                # Parallel tests for URLs in this batch
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {}
                    for base_url in batch:
                        # For each URL, test all extensions in parallel
                        for ext in optimized_extensions:
                            future = executor.submit(self.test_url, base_url, ext, test_type)
                            futures[future] = (base_url, ext)
                    
                    # Process results as they are completed
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        if result:
                            format_and_print_result(console, result, self.use_color, self.verbose, self.silent)
            
            # Add a blank line after each test group
            if not self.silent:
                if self.use_color:
                    console.print()
                else:
                    print()
        
        # Record end time for statistics
        self.stats['end_time'] = time.time()
        
        # Display performance statistics if verbose
        if self.verbose:
            self._display_performance_stats()
    
    def _export_url_results(self, url: str):
        """Export specific results for a URL."""
        from urllib.parse import urlparse
        from utils.file_utils import export_results
        
        # Create filename based on the URL efficiently
        parsed = urlparse(url)
        domain = parsed.netloc.replace(':', '_')
        path = parsed.path.replace('/', '_').strip('_')
        
        if path:
            filename = f"{self.output_file.split('.')[0]}_{domain}_{path}.json"
        else:
            filename = f"{self.output_file.split('.')[0]}_{domain}.json"
        
        export_results(self.results, filename)
        
        if not self.silent:
            logger.info(f"Results for {url} exported to {filename}")
    
    def print_banner(self):
        """Display the ASCII banner - optimized version."""
        if self.silent:
            return
            
        print_banner(self.use_color, self.silent)
        
        info_text = f"Version: {VERSION} | Threads: {self.max_workers} | Extensions: {len(self.extensions)}"

        # Add domain wordlist info if enabled
        if hasattr(self, 'domain_wordlist') and self.domain_wordlist:
            info_text += " | Domain Wordlist: Enabled"
        
        # Now we will pass the number of words to the info panel
        # instead of including it directly in the text
        backup_words_count = len(self.backup_words) if self.brute_mode else None
        
        print_info_panel(info_text, self.use_color, backup_words_count)
    
    def print_summary(self):
        """Print a summary of the found results - optimized version."""
        from utils.report import generate_summary_report
        
        if not self.results or self.silent:
            return
            
        generate_summary_report(self.results, console, self.use_color, self.verbose)
    
    def run(self):
        """Run the scanner with the current settings - optimized version."""
        # Clear tracking sets when starting a new scan
        self.tested_urls.clear()
        self.found_urls.clear()
        self._url_parse_cache.clear()  # Clear parsed URL cache