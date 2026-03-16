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
import threading

from leftovers.app_settings import VERSION
from leftovers.core.config import (
    DEFAULT_TIMEOUT, DEFAULT_THREADS, DEFAULT_EXTENSIONS,
    DEFAULT_BACKUP_WORDS, DEFAULT_HEADERS, USER_AGENTS
)
from leftovers.core.result import ScanResult
from leftovers.core.detection import check_false_positive
from leftovers.utils.logger import logger, setup_logger
from leftovers.utils.console import (
    console, print_banner, print_info_panel, 
    create_progress_bar, format_and_print_result, create_url_list_progress,
    print_section_separator
)
from leftovers.utils.file_utils import load_url_list
from leftovers.utils.http_utils import HttpClient
from leftovers.utils.url_utils import generate_test_urls
from leftovers.utils.extension_optimizer import ExtensionOptimizer
from leftovers.utils.domain_generator import DomainWordlistGenerator
from leftovers.utils.metrics import ScanMetrics

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
                 disable_fp: bool = False,
                 rate_limit: float = None,
                 delay_ms: int = None):
        """Initialize the scanner with the provided settings."""
        self.extensions = extensions if extensions is not None else DEFAULT_EXTENSIONS
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
        self.output_per_url = False
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
        
        # Set logging level based on verbose and silent flags
        global logger
        logger = setup_logger(verbose, silent)
        
        # HTTP client for requests - optimized with rate limiting
        self.http_client = HttpClient(
            headers=self.headers,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
            rotate_user_agent=self.rotate_user_agent,
            rate_limit=rate_limit,
            delay_ms=delay_ms
        )
        
        # Optimization: use defaultdict for false positive control and size tracking
        self.error_fingerprints = defaultdict(int)
        self.baseline_responses = {}
        self._size_frequency = defaultdict(int)
        self._hash_frequency = defaultdict(set)
        self._main_page = None

        # Thread-safe locks for shared dictionaries (prevent race conditions)
        self._stats_lock = threading.Lock()
        self._tested_urls_lock = threading.Lock()
        self._size_frequency_lock = threading.Lock()
        self._hash_frequency_lock = threading.Lock()
        self._found_urls_lock = threading.Lock()
        self._results_lock = threading.Lock()
        # Per-thread baseline data so concurrent URL workers don't overwrite each other
        self._thread_local = threading.local()
        
        # Performance metrics tracking
        self.metrics = ScanMetrics()
        
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

        # Adaptive threading configuration
        self._enable_adaptive_threading = True
        self._initial_threads = threads
        self._min_threads = max(2, threads // 4)  # Minimum 2 or 25% of initial
        self._max_threads = min(threads * 2, 50)  # Maximum 2x initial or 50
        self._latency_samples = []
        self._max_latency_samples = 20  # Track last 20 requests
        self._adaptive_lock = threading.Lock()
        self._adjustment_interval = 50  # Adjust every 50 requests
    
    def _track_request_latency(self, latency: float) -> None:
        """
        Track request latency and adjust thread count if needed.

        Args:
            latency: Request latency in seconds
        """
        if not self._enable_adaptive_threading:
            return

        with self._adaptive_lock:
            # Add latency sample
            self._latency_samples.append(latency)

            # Keep only recent samples
            if len(self._latency_samples) > self._max_latency_samples:
                self._latency_samples.pop(0)

            # Adjust threads every N requests
            if self.stats['requests'] % self._adjustment_interval == 0 and len(self._latency_samples) >= 10:
                self._adjust_thread_count()

    def _adjust_thread_count(self) -> None:
        """
        Adjust thread count based on average latency.

        Fast targets (low latency) get more threads.
        Slow targets (high latency) get fewer threads.
        """
        if not self._latency_samples:
            return

        # Calculate average latency in milliseconds
        avg_latency = sum(self._latency_samples) / len(self._latency_samples) * 1000

        current_threads = self.max_workers
        new_threads = current_threads

        # Thresholds for adjustment
        FAST_THRESHOLD = 100  # < 100ms = fast target
        MEDIUM_THRESHOLD = 300  # 100-300ms = medium target
        SLOW_THRESHOLD = 500  # > 500ms = slow target

        if avg_latency < FAST_THRESHOLD:
            # Fast target: increase threads by 20% (gradual increase)
            new_threads = min(int(current_threads * 1.2), self._max_threads)
            adjustment_reason = f"fast target ({avg_latency:.0f}ms avg latency)"

        elif avg_latency > SLOW_THRESHOLD:
            # Slow target: decrease threads by 30% (more aggressive decrease)
            new_threads = max(int(current_threads * 0.7), self._min_threads)
            adjustment_reason = f"slow target ({avg_latency:.0f}ms avg latency)"

        elif avg_latency > MEDIUM_THRESHOLD:
            # Medium-slow target: decrease threads by 15%
            new_threads = max(int(current_threads * 0.85), self._min_threads)
            adjustment_reason = f"medium-slow target ({avg_latency:.0f}ms avg latency)"

        if new_threads != current_threads:
            self.max_workers = new_threads
            if self.verbose:
                logger.info(f"Adaptive threading: {current_threads} → {new_threads} threads ({adjustment_reason})")

    def _thread_safe_add_result(self, scan_result: ScanResult) -> None:
        """
        Thread-safe method to add a result to the results list.

        Args:
            scan_result: The scan result to add
        """
        with self._results_lock:
            self.results.append(scan_result)
            
            # Track metrics
            if hasattr(self, 'metrics'):
                # Extract extension from URL
                extension = scan_result.url.split('.')[-1].split('?')[0].split('#')[0] if '.' in scan_result.url else None
                is_fp = getattr(scan_result, 'false_positive', False)
                self.metrics.record_discovery(is_false_positive=is_fp, extension=extension)

    def _thread_safe_add_found_url(self, url: str) -> None:
        """
        Thread-safe method to add a URL to the found URLs set.

        Args:
            url: The URL to add
        """
        with self._found_urls_lock:
            self.found_urls.add(url)

    def _inc_stats(self, requests: int = 0, req_time: float = 0.0, hits: int = 0) -> None:
        """Thread-safe increment of scan statistics."""
        with self._stats_lock:
            self.stats['requests'] += requests
            self.stats['total_time'] += req_time
            self.stats['hits'] += hits

    def _thread_safe_check_false_positive(
            self,
            result: ScanResult,
            response_content: bytes) -> Tuple[bool, str]:
        """
        Thread-safe wrapper for check_false_positive.

        Args:
            result: ScanResult object
            response_content: Raw response content bytes

        Returns:
            Tuple of (is_false_positive, reason)
        """
        # Use per-thread baseline when available (set by _process_url_without_progress)
        # so concurrent list-mode workers don't read each other's baselines.
        main_page = getattr(self._thread_local, 'main_page', self._main_page)
        baseline_responses = getattr(self._thread_local, 'baseline_responses', self.baseline_responses)
        with self._size_frequency_lock, self._hash_frequency_lock:
            return check_false_positive(
                result,
                response_content,
                baseline_responses,
                main_page,
                self._size_frequency,
                self._hash_frequency
            )

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
        
        # Atomically check-and-claim URLs to avoid duplicate testing across threads
        urls_to_test = []
        with self._tested_urls_lock:
            if exact_match_url and exact_match_url not in self.tested_urls:
                self.tested_urls.add(exact_match_url)
                urls_to_test.append(exact_match_url)
            if full_url not in self.tested_urls:
                self.tested_urls.add(full_url)
                urls_to_test.append(full_url)
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

            # Calculate request time
            req_time = time.time() - start_time
            self._inc_stats(requests=1, req_time=req_time)

            # Track latency for adaptive threading
            self._track_request_latency(req_time)

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
            from leftovers.app_settings import MAX_FILE_SIZE_MB, SUCCESS_STATUSES
            if content_length > MAX_FILE_SIZE_MB * 1024 * 1024:
                scan_result.large_file = True
                
            # Flag partial content
            if status_code == 206:
                scan_result.partial_content = True
            
            # 6. Finally, perform false positive check (most costly) - THREAD SAFE
            is_false_positive, reason = self._thread_safe_check_false_positive(
                scan_result,
                content
            )
            scan_result.false_positive = is_false_positive
            scan_result.false_positive_reason = reason

            # Special handling for successful status codes (200, 206)
            # These are important but we still need to respect false positive detection
            if status_code in SUCCESS_STATUSES:
                if self.disable_fp or not is_false_positive:
                    self._inc_stats(hits=1)
                    self._thread_safe_add_found_url(scan_result.url)
                    self._thread_safe_add_result(scan_result)
                    return scan_result
                return None

            # Non-success status codes
            if self.disable_fp or not is_false_positive:
                self._inc_stats(hits=1)
                self._thread_safe_add_found_url(scan_result.url)
                self._thread_safe_add_result(scan_result)
                return scan_result

            return None
            
        except Exception as e:
            # Optimized error handling with specific logging
            if self.verbose:
                error_type = type(e).__name__
                logger.debug(f"Error testing URL {full_url}: {error_type}: {str(e)}")
            return None
    
    def _perform_important_extension_tests(self, target_url: str, optimized_extensions: List[str], suppress_print: bool = False) -> bool:
        """
        Perform direct tests for important file extensions (PDF, Office docs, archives).

        Args:
            target_url: The target URL to test
            optimized_extensions: List of extensions optimized for the target

        Returns:
            True if any important files were found, False otherwise
        """
        important_extensions = ["pdf", "docx", "xlsx", "pptx", "zip", "rar", "tar.gz", "tar"]
        important_exts_to_test = [ext for ext in optimized_extensions if ext.lower() in important_extensions]

        found_files = False

        for extension in important_exts_to_test:
            # Determine if it's a domain-only URL
            is_domain_only = '/' not in target_url[8:] if target_url.startswith('http://') else (
                '/' not in target_url[9:] if target_url.startswith('https://') else False
            )

            if is_domain_only and not target_url.endswith('/'):
                direct_url = f"{target_url}/.{extension}"
            else:
                direct_url = f"{target_url}.{extension}"

            if self.verbose:
                logger.debug(f"HIGH PRIORITY: Testing direct URL for important file: {direct_url}")

            try:
                import requests
                start_time = time.time()

                headers = self.http_client.session.headers.copy()
                headers['Range'] = 'bytes=0-8191'

                with requests.Session() as special_session:
                    special_session.verify = False
                    response = special_session.get(
                        direct_url,
                        headers=headers,
                        timeout=self.timeout,
                        allow_redirects=True
                    )

                req_time = time.time() - start_time
                self._inc_stats(requests=1, req_time=req_time)

                if response.status_code in [200, 206]:
                    content_type = response.headers.get('Content-Type', 'Unknown')
                    content_type_base = content_type.split(';')[0].strip()

                    if self.ignore_content and any(ignore == content_type_base for ignore in self.ignore_content):
                        if self.verbose:
                            logger.debug(f"Ignoring result with filtered content type: {content_type_base}")
                        continue

                    if 'Content-Length' in response.headers:
                        try:
                            content_length = int(response.headers['Content-Length'])
                        except (ValueError, TypeError):
                            content_length = len(response.content) if response.content else 0
                    else:
                        content_length = len(response.content) if response.content else 0

                    scan_result = ScanResult(
                        url=direct_url,
                        status_code=response.status_code,
                        content_type=content_type,
                        content_length=content_length,
                        response_time=req_time,
                        test_type="Direct URL",
                        extension=extension
                    )

                    is_false_positive, reason = self._thread_safe_check_false_positive(
                        scan_result,
                        response.content
                    )
                    scan_result.false_positive = is_false_positive
                    scan_result.false_positive_reason = reason

                    if self.disable_fp or not is_false_positive:
                        self._inc_stats(hits=1)
                        self._thread_safe_add_found_url(direct_url)
                        self._thread_safe_add_result(scan_result)
                        found_files = True

                        if not self.silent and not suppress_print:
                            format_and_print_result(console, scan_result, self.use_color, self.verbose, self.silent)

            except Exception as e:
                if self.verbose:
                    error_type = type(e).__name__
                    logger.debug(f"Error testing important file {direct_url}: {error_type}: {str(e)}")

        return found_files

    def _perform_direct_extension_tests(self, target_url: str, optimized_extensions: List[str], suppress_print: bool = False) -> bool:
        """
        Perform direct tests for non-important extensions.

        Args:
            target_url: The target URL to test
            optimized_extensions: List of extensions optimized for the target

        Returns:
            True if any files were found, False otherwise
        """
        if len(optimized_extensions) > 5:
            return False

        important_extensions = ["pdf", "docx", "xlsx", "pptx", "zip", "rar", "tar.gz", "tar"]
        found_files = False

        for extension in optimized_extensions:
            if extension.lower() in important_extensions:
                continue

            is_domain_only = '/' not in target_url[8:] if target_url.startswith('http://') else (
                '/' not in target_url[9:] if target_url.startswith('https://') else False
            )

            if is_domain_only and not target_url.endswith('/'):
                direct_url = f"{target_url}/.{extension}"
            else:
                direct_url = f"{target_url}.{extension}"

            if self.verbose:
                logger.debug(f"Testing direct URL: {direct_url}")

            try:
                start_time = time.time()
                result = self.http_client.get(direct_url)
                req_time = time.time() - start_time
                self._inc_stats(requests=1, req_time=req_time)

                if result["success"]:
                    response = result["response"]
                    response_time = result["time"]

                    status_code = response.status_code
                    headers = response.headers
                    content_type = headers.get('Content-Type', 'N/A')

                    content_type_base = content_type.split(';')[0].strip()
                    if self.ignore_content and any(ignore == content_type_base for ignore in self.ignore_content):
                        if self.verbose:
                            logger.debug(f"Ignoring direct URL result with filtered content type: {content_type_base}")
                        continue

                    content = response.content

                    if 'Content-Length' in response.headers:
                        try:
                            content_length = int(response.headers['Content-Length'])
                        except (ValueError, TypeError):
                            content_length = len(content) if content else 0
                    else:
                        content_length = len(content) if content else 0

                    scan_result = ScanResult(
                        url=direct_url,
                        status_code=status_code,
                        content_type=content_type,
                        content_length=content_length,
                        response_time=response_time,
                        test_type="Direct URL",
                        extension=extension
                    )

                    if status_code == 200 or status_code == 206:
                        is_false_positive, reason = self._thread_safe_check_false_positive(
                            scan_result,
                            content
                        )
                        scan_result.false_positive = is_false_positive
                        scan_result.false_positive_reason = reason

                        if self.disable_fp or not is_false_positive:
                            self._inc_stats(hits=1)
                            self._thread_safe_add_found_url(direct_url)
                            self._thread_safe_add_result(scan_result)
                            found_files = True

                            if not self.silent and not suppress_print:
                                format_and_print_result(console, scan_result, self.use_color, self.verbose, self.silent)

            except Exception as e:
                if self.verbose:
                    error_type = type(e).__name__
                    logger.debug(f"Error in direct test: {direct_url}: {error_type}: {str(e)}")

        return found_files

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
            from leftovers.utils.debug_utils import debug_url_segments
            debug_url_segments(target_url)

        # Perform important extension tests (PDF, Office docs, archives)
        self._perform_important_extension_tests(target_url, optimized_extensions)

        # Perform direct extension tests for other extensions
        self._perform_direct_extension_tests(target_url, optimized_extensions)
        
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
        # Calculate total tests more accurately based on URL type
        total_tests = 0
        for base_url, test_type in test_urls:
            # Critical-specific files are tested exactly once (no extensions added)
            if test_type == "critical-specific":
                total_tests += 1
            else:
                # Check if URL already has extension
                url_path = base_url.split('/')[-1]
                has_extension = False
                if '.' in url_path:
                    parts = url_path.split('.')
                    if len(parts) >= 2 and 2 <= len(parts[-1]) <= 5 and parts[-1].isalnum():
                        has_extension = True
                
                # URLs with extensions are tested once, without extensions test all extensions
                total_tests += 1 if has_extension else len(self.extensions)
        
        # Always use progress bar, even in silent mode
        progress, task = create_progress_bar(total_tests, self.use_color)
        
        # Optimization: preprocess URLs to group by test type
        test_url_groups = defaultdict(list)
        for base_url, test_type in test_urls:
            test_url_groups[test_type].append(base_url)
        
        with progress:
            # Process groups by test type
            for test_type, urls_for_type in test_url_groups.items():
                # Track if we found any results in this test type to show header
                found_results_in_group = False
                header_shown = False
                
                # Process in batches for better balancing and avoiding overload
                batch_size = min(100, len(urls_for_type))
                url_batches = [urls_for_type[i:i + batch_size] for i in range(0, len(urls_for_type), batch_size)]
                
                for batch in url_batches:
                    # Parallel tests for each URL in the current batch
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        # Create mapping of futures to arguments
                        futures = {}
                        for base_url in batch:
                            # Critical-specific files should NEVER have extensions added
                            # These are exact filenames that we want to test as-is
                            if test_type == "critical-specific":
                                future = executor.submit(self._test_single_url, base_url, "", test_type)
                                futures[future] = (base_url, "")
                                continue
                            
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
                                # Show header only when first result is found
                                if not header_shown:
                                    self._display_test_type_header(test_type, urls_for_type[0])
                                    header_shown = True
                                    found_results_in_group = True
                                
                                # Display result if found
                                format_and_print_result(console, result, self.use_color, self.verbose, self.silent)
                
                # Add a blank line after each test group ONLY if we showed results
                if found_results_in_group:
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
        if self.silent or not self.verbose:
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
                print_section_separator()
                console.print(f"\n[bold green]Testing:[/bold green] {test_type} [bold cyan]({url_display})[/bold cyan]")
        else:
            print_section_separator(use_color=False)
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
        """Process multiple URLs from a file with URL-level parallelism.

        --workers  controls how many URLs scan at the same time (default = -t).
        -t/--threads controls the inner extension-testing pool per URL.

        A fixed-size task-pool is pre-allocated so the Rich live display never
        grows after it starts, preventing the progress block from "jumping down".
        """
        import queue as _queue
        from rich.progress import (
            Progress, SpinnerColumn, TextColumn, BarColumn,
            MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn,
        )

        urls = load_url_list(url_list_file)
        if not urls:
            return

        total_urls = len(urls)

        if self.use_color:
            console.print(f"[bold cyan]Processing {total_urls} URLs from list: {url_list_file}[/bold cyan]")
        else:
            print(f"Processing {total_urls} URLs from list: {url_list_file}")

        global_start_time = time.time()
        total_requests = 0
        total_hits = 0
        done_count = 0
        stats_lock = threading.Lock()

        # --workers sets URL-level concurrency; fall back to -t if not set.
        # output_per_url needs serialised self.results → force sequential.
        if self.output_per_url:
            n_url_workers = 1
        else:
            n_url_workers = min(
                getattr(self, 'url_workers', None) or self.max_workers,
                total_urls,
            )
            n_url_workers = max(1, n_url_workers)

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=28),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console if self.use_color else None,
            transient=False,
        )

        # Summary row — always first, never hidden
        summary_task = progress.add_task(
            f"[bold cyan]0/{total_urls} URLs • 0 hits",
            total=total_urls,
        )

        # Pre-allocate exactly n_url_workers task slots so the display height
        # is fixed from the moment `with progress:` starts.  Workers claim and
        # release slots via the task_pool queue; no add_task calls after this.
        task_pool: "_queue.Queue[int]" = _queue.Queue()
        for _ in range(n_url_workers):
            tid = progress.add_task("", total=None, visible=False)
            task_pool.put(tid)

        def _scan_one(idx: int, url: str):
            nonlocal total_requests, total_hits, done_count

            # Claim a slot — blocks only if all workers are busy (never deadlocks
            # because the pool has exactly n_url_workers slots and the executor
            # runs at most n_url_workers threads concurrently).
            url_task = task_pool.get()
            progress.update(url_task, description=f"[cyan]{url}", completed=0, total=None, visible=True)

            if self.output_per_url:
                with stats_lock:
                    self.results = []

            url_stats = self._process_url_without_progress(
                url,
                shared_progress=progress,
                url_task_id=url_task,
            )

            if self.output_per_url and self.output_file:
                self._export_url_results(url)

            # Hide slot and return it to the pool for the next URL
            progress.update(url_task, visible=False)
            task_pool.put(url_task)

            with stats_lock:
                total_requests += url_stats.get('requests', 0)
                total_hits += url_stats.get('hits', 0)
                done_count += 1
                progress.update(
                    summary_task,
                    advance=1,
                    description=f"[bold cyan]{done_count}/{total_urls} URLs • {total_hits} hits",
                )

        with progress:
            with concurrent.futures.ThreadPoolExecutor(max_workers=n_url_workers) as executor:
                futures = {
                    executor.submit(_scan_one, i + 1, url): url
                    for i, url in enumerate(urls)
                }
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        url = futures[future]
                        if not self.silent:
                            console.print(f"[red]Error processing {url}: {exc}[/red]")

        global_elapsed = time.time() - global_start_time

        # Print all accumulated hits now that the progress display is done.
        if not self.silent and self.results:
            if self.use_color:
                console.print()
                console.rule("[bold green]Findings[/bold green]", style="green")
            else:
                print("\n--- Findings ---")
            for result in self.results:
                format_and_print_result(console, result, self.use_color, self.verbose, self.silent)

        if not self.silent:
            rps = total_requests / global_elapsed if global_elapsed > 0 else 0
            if self.use_color:
                console.print()
                console.print("[bold green]List Processing Completed![/bold green]")
                console.print(f"[bold cyan]Global Statistics:[/bold cyan]")
                console.print(f"  Total time:     {global_elapsed:.2f}s")
                console.print(f"  URLs processed: {total_urls}")
                console.print(f"  Total requests: {total_requests}")
                console.print(f"  Total hits:     {total_hits}")
                console.print(f"  Req/second:     {rps:.2f}")
            else:
                print("\nList Processing Completed!")
                print(f"  Total time:     {global_elapsed:.2f}s")
                print(f"  URLs processed: {total_urls}")
                print(f"  Total requests: {total_requests}")
                print(f"  Total hits:     {total_hits}")
                print(f"  Req/second:     {rps:.2f}")
    
    def _process_url_without_progress(
        self,
        target_url: str,
        shared_progress=None,
        url_task_id=None,
    ) -> dict:
        """Process a URL without an outer progress bar.

        If *shared_progress* and *url_task_id* are supplied the method updates
        that task's total (once known) and advances it after every completed
        future so the caller can render per-URL progress rows.

        Returns a dict with 'requests', 'hits', and 'elapsed'.
        Does NOT reset self.stats (delta approach for thread safety).
        """
        with self._stats_lock:
            req_start = self.stats['requests']
            hit_start = self.stats['hits']
            self.stats['start_time'] = time.time()
        scan_start = self.stats['start_time']

        optimized_extensions = self.extension_optimizer.optimize_extensions(
            self.extensions, target_url
        )

        # In list mode the console.rule would fight the live progress display;
        # only emit it in verbose mode or when running a single URL.
        if self.verbose:
            if self.use_color:
                console.rule(f"[bold blue]Target: {target_url}[/bold blue]", style="blue")
            else:
                title = f"Target: {target_url}"
                print("\n" + "-" * len(title))
                print(title)
                print("-" * len(title))

        if self.verbose:
            from leftovers.utils.debug_utils import debug_url_segments
            debug_url_segments(target_url)

        in_list_mode = shared_progress is not None
        self._perform_important_extension_tests(target_url, optimized_extensions, suppress_print=in_list_mode)
        self._perform_direct_extension_tests(target_url, optimized_extensions, suppress_print=in_list_mode)

        # Only reset frequency trackers in single-URL mode; in list mode concurrent
        # workers share these dicts and resetting mid-scan corrupts other threads.
        if not in_list_mode:
            with self._size_frequency_lock:
                self._size_frequency = defaultdict(int)
            with self._hash_frequency_lock:
                self._hash_frequency = defaultdict(set)

        enhanced_backup_words = self.backup_words
        if hasattr(self, 'domain_wordlist') and self.domain_wordlist and self.brute_mode:
            if self.verbose:
                logger.info(f"Enhancing wordlist with domain-based words from {target_url}")
            enhanced_backup_words = self.domain_generator.enhance_existing_wordlist(
                self.backup_words, target_url
            )
            if self.verbose:
                logger.info(f"Wordlist enhanced: {len(self.backup_words)} -> {len(enhanced_backup_words)} words")

        test_urls, local_main_page, local_baseline = generate_test_urls(
            self.http_client,
            target_url,
            self.brute_mode,
            enhanced_backup_words,
            self.verbose,
            self.brute_recursive,
            self.domain_wordlist
        )
        # Store per-thread baseline so concurrent workers don't overwrite each other
        self._thread_local.main_page = local_main_page
        self._thread_local.baseline_responses = local_baseline
        self._main_page = local_main_page
        self.baseline_responses = local_baseline

        if not test_urls:
            elapsed = time.time() - scan_start
            return {'requests': 0, 'hits': 0, 'elapsed': elapsed}

        # Now that we know the full test list, set the task total so the bar
        # renders correctly.
        if shared_progress is not None and url_task_id is not None:
            total_tests = 0
            for base_url, test_type in test_urls:
                if test_type == "critical-specific":
                    total_tests += 1
                else:
                    url_path = base_url.split('/')[-1]
                    has_ext = (
                        '.' in url_path
                        and len(url_path.split('.')[-1]) in range(2, 6)
                        and url_path.split('.')[-1].isalnum()
                    )
                    total_tests += 1 if has_ext else len(optimized_extensions)
            shared_progress.update(url_task_id, total=total_tests, visible=True)

        test_url_groups = defaultdict(list)
        for base_url, test_type in test_urls:
            test_url_groups[test_type].append(base_url)

        for test_type, urls_for_type in test_url_groups.items():
            if not self.silent and urls_for_type:
                self._display_test_type_header(test_type, urls_for_type[0])

            batch_size = min(100, len(urls_for_type))
            url_batches = [urls_for_type[i:i+batch_size] for i in range(0, len(urls_for_type), batch_size)]

            found_in_group = False
            for batch in url_batches:
                # Inner pool for extension testing within this URL.
                # Uses self.max_workers (-t) regardless of list vs single mode.
                inner_workers = self.max_workers
                with concurrent.futures.ThreadPoolExecutor(max_workers=inner_workers) as executor:
                    futures = {}
                    for base_url in batch:
                        if test_type == "critical-specific":
                            future = executor.submit(self._test_single_url, base_url, "", test_type)
                            futures[future] = (base_url, "")
                        else:
                            url_path = base_url.split('/')[-1]
                            has_ext = (
                                '.' in url_path
                                and len(url_path.split('.')[-1]) in range(2, 6)
                                and url_path.split('.')[-1].isalnum()
                            )
                            if has_ext:
                                future = executor.submit(self._test_single_url, base_url, "", test_type)
                                futures[future] = (base_url, "")
                            else:
                                for ext in optimized_extensions:
                                    future = executor.submit(self.test_url, base_url, ext, test_type)
                                    futures[future] = (base_url, ext)

                    for future in concurrent.futures.as_completed(futures):
                        if shared_progress is not None and url_task_id is not None:
                            shared_progress.advance(url_task_id)
                        result = future.result()
                        if result:
                            found_in_group = True
                            if not in_list_mode:
                                format_and_print_result(console, result, self.use_color, self.verbose, self.silent)

            # Only add spacing in single-URL mode; in list mode the progress
            # display manages layout and extra blank lines push it down.
            if not self.silent and (self.verbose or found_in_group) and shared_progress is None:
                if self.use_color:
                    console.print()
                else:
                    print()

        scan_end = time.time()
        self.stats['end_time'] = scan_end

        if self.verbose:
            self._display_performance_stats()

        elapsed = scan_end - scan_start
        with self._stats_lock:
            req_delta = self.stats['requests'] - req_start
            hit_delta = self.stats['hits'] - hit_start
        return {
            'requests': req_delta,
            'hits': hit_delta,
            'elapsed': elapsed,
        }
    
    def _export_url_results(self, url: str):
        """Export specific results for a URL."""
        from urllib.parse import urlparse
        from leftovers.utils.file_utils import export_results
        
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
        
        url_workers = getattr(self, 'url_workers', None) or self.max_workers
        info_text = f"Version: {VERSION} | Workers: {url_workers} | Threads: {self.max_workers} | Extensions: {len(self.extensions)}"

        # Add domain wordlist info if enabled
        if hasattr(self, 'domain_wordlist') and self.domain_wordlist:
            info_text += " | Domain Wordlist: Enabled"
        
        # Now we will pass the number of words to the info panel
        # instead of including it directly in the text
        backup_words_count = len(self.backup_words) if self.brute_mode else None
        
        print_info_panel(info_text, self.use_color, backup_words_count)
    
    def print_summary(self):
        """Print a summary of the found results - optimized version."""
        from leftovers.utils.report import generate_summary_report
        
        if not self.results or self.silent:
            return
            
        generate_summary_report(self.results, console, self.use_color, self.verbose)
    
    def run(self):
        """Run the scanner with the current settings - optimized version."""
        # Clear tracking sets when starting a new scan
        self.tested_urls.clear()
        self.found_urls.clear()
        self._url_parse_cache.clear()  # Clear parsed URL cache