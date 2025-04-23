"""
Main implementation of the LeftOvers scanner.
"""

import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any, Set

from core.config import (
    VERSION, DEFAULT_TIMEOUT, DEFAULT_THREADS, DEFAULT_EXTENSIONS, 
    DEFAULT_BACKUP_WORDS, DEFAULT_HEADERS, USER_AGENTS
)
from core.result import ScanResult
from core.detection import check_false_positive
from utils.logger import logger, setup_logger
from utils.console import (
    console, print_banner, print_info_panel, 
    create_progress_bar, format_and_print_result
)
from utils.file_utils import load_url_list
from utils.http_utils import HttpClient
from utils.url_utils import generate_test_urls

class LeftOver:
    """Main scanner for finding leftover files on web servers."""
    
    def __init__(self, 
                 extensions: List[str] = None, 
                 timeout: int = DEFAULT_TIMEOUT,
                 threads: int = DEFAULT_THREADS,
                 headers: Dict[str, str] = None,
                 verify_ssl: bool = True,
                 use_color: bool = True,
                 verbose: bool = False,
                 silent: bool = False,
                 output_file: str = None,
                 status_filter: Set[int] = None,
                 min_content_length: int = None,
                 max_content_length: int = None,
                 rotate_user_agent: bool = False,
                 test_index: bool = False):
        """Initialize the scanner with the provided settings."""
        self.extensions = extensions or DEFAULT_EXTENSIONS
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
        
        # Brute force settings (default empty, set by CLI)
        self.brute_mode = False
        self.backup_words = []
        
        # Filters
        self.status_filter = status_filter
        self.min_content_length = min_content_length
        self.max_content_length = max_content_length
        
        # Set logging level based on verbose and silent flags
        global logger
        logger = setup_logger(verbose, silent)
        
        # HTTP client for requests
        self.http_client = HttpClient(
            headers=self.headers,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
            rotate_user_agent=self.rotate_user_agent
        )
        
        # For false positive detection
        self.error_fingerprints = {}
        self.baseline_responses = {}
        self._size_frequency = {}
        self._main_page = None
        
        # For storing global sanity check results
        self._global_sanity_check_results = {}
        
        # Set to track already tested URLs to avoid duplications
        self.tested_urls = set()
        
        # Set to track found URLs for result deduplication
        self.found_urls = set()

    def print_banner(self):
        """Display the ASCII banner."""
        if self.silent:
            return
            
        print_banner(self.use_color, self.silent)

        info_text = f"Version: {VERSION} | Threads: {self.max_workers} | Extensions: {len(self.extensions)}"

        # Add brute force info if enabled
        if self.brute_mode:
            info_text += f" | Brute Force: Enabled ({len(self.backup_words)} words)"

        print_info_panel(info_text, self.use_color)
    
    def test_url(self, base_url: str, extension: str, test_type: str) -> Optional[ScanResult]:
        """Test a single URL with a given extension."""
        # Check if we're testing only a domain or a specific path
        is_domain_only = base_url.rstrip('/').count('/') <= 2  # Ex: https://example.com
        
        if is_domain_only and self.test_index:
            # If domain and test_index flag is enabled, test index.{extension}
            full_url = f"{base_url.rstrip('/')}/index.{extension}"
        else:
            # Otherwise, add the extension to the end of the URL normally
            full_url = f"{base_url}.{extension}"
        
        # Check if this URL has already been tested to avoid duplications
        if full_url in self.tested_urls:
            return None
            
        # Add to the list of tested URLs
        self.tested_urls.add(full_url)
        
        try:
            result = self.http_client.get(full_url)
            
            if not result["success"]:
                return None
                
            response = result["response"]
            response_time = result["time"]
            
            scan_result = ScanResult(
                url=full_url,
                status_code=response.status_code,
                content_type=response.headers.get('Content-Type', 'N/A'),
                content_length=len(response.content) if response.content else 0,
                response_time=response_time,
                test_type=test_type,
                extension=extension
            )
            
            # Check for false positives
            is_false_positive, reason = check_false_positive(
                scan_result, 
                response.content, 
                self.baseline_responses,
                self._main_page,
                self._size_frequency
            )
            scan_result.false_positive = is_false_positive
            scan_result.false_positive_reason = reason
            
            # Apply status code filters
            if self.status_filter and scan_result.status_code not in self.status_filter:
                return None
                
            # Apply content length filters
            if (self.min_content_length is not None and scan_result.content_length < self.min_content_length) or \
               (self.max_content_length is not None and scan_result.content_length > self.max_content_length):
                return None
                
            # Check if this URL has already been found previously
            if scan_result.url in self.found_urls:
                return None  # URL already reported, ignore this result
                
            # Add to the list of found URLs
            self.found_urls.add(scan_result.url)
            
            self.results.append(scan_result)
            return scan_result
            
        except Exception as e:
            if self.verbose:
                logger.debug(f"Error testing URL {full_url}: {str(e)}")
            return None
    
    def process_url(self, target_url: str):
        """Process a URL, testing all extensions on all derived targets."""
        if not self.silent:
            if self.use_color:
                console.rule(f"[bold blue]Target: {target_url}[/bold blue]", style="blue")
            else:
                title = f"Target: {target_url}"
                print("\n" + "-" * len(title))
                print(title)
                print("-" * len(title))
        
        # Reset size tracker for this target
        self._size_frequency = {}
        
        # Generate base URLs to test
        test_urls, self._main_page, self.baseline_responses = generate_test_urls(
            self.http_client, 
            target_url,
            self.brute_mode, 
            self.backup_words,
            self.verbose
        )
        
        if not test_urls:
            return
        
        # Create a progress bar to display status
        total_tests = len(test_urls) * len(self.extensions)
        
        # In silent mode, don't display progress bar
        if self.silent:
            # For each base URL, test all extensions
            for base_url, test_type in test_urls:
                # Use a thread pool to test all extensions in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_ext = {
                        executor.submit(self.test_url, base_url, ext, test_type): ext 
                        for ext in self.extensions
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_ext):
                        result = future.result()
                        if result:
                            format_and_print_result(console, result, self.use_color, self.verbose, self.silent)
        else:
            progress, task = create_progress_bar(total_tests, self.use_color)
            with progress:
                # For each base URL, test all extensions
                for base_url, test_type in test_urls:
                    if not self.silent:
                        if self.use_color:
                            # Avoid duplication in brute force messages
                            if test_type.startswith("Brute"):
                                console.print(f"[bold yellow]Testing {test_type}[/bold yellow]")
                            else:
                                console.print(f"[bold yellow]Testing {test_type}:[/bold yellow] {base_url.split('/')[-1]}")
                        else:
                            # Non-color version with the same improvement
                            if test_type.startswith("Brute"):
                                print(f"Testing {test_type}")
                            else:
                                print(f"Testing {test_type}: {base_url.split('/')[-1]}")
                    
                    # Use a thread pool to test all extensions in parallel
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        future_to_ext = {
                            executor.submit(self.test_url, base_url, ext, test_type): ext 
                            for ext in self.extensions
                        }
                        
                        for future in concurrent.futures.as_completed(future_to_ext):
                            progress.update(task, advance=1)
                            result = future.result()
                            if result:
                                format_and_print_result(console, result, self.use_color, self.verbose, self.silent)
                    
                    # Add a blank line after each test group
                    if not self.silent and self.use_color:
                        console.print()
                    elif not self.silent:
                        print()
    
    def process_url_list(self, url_list_file: str):
        """Process multiple URLs from a file."""
        urls = load_url_list(url_list_file)
        if not urls:
            return
            
        for url in urls:
            self.process_url(url)
    
    def print_summary(self):
        """Print a summary of the results found."""
        from utils.report import generate_summary_report
        
        if not self.results or self.silent:
            return
            
        generate_summary_report(self.results, console, self.use_color, self.verbose)
    
    def run(self):
        """Run the scanner with current settings."""
        # Clear tracking sets when starting a new scan
        self.tested_urls.clear()
        self.found_urls.clear()
        
        # ...existing code for running the scan...
        
        # When displaying results, duplicates will already have been filtered
        # ...existing code...
