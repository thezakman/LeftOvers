"""
Main implementation of the LeftOvers scanner.
"""

import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any, Set
import urllib.parse

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
                 test_index: bool = False,
                 ignore_content: List[str] = None):
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
        self.ignore_content = ignore_content or []
        
        # Output settings
        self.output_file = output_file
        self.output_per_url = False  # New option
        
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

        # Now we'll pass the number of words to the information panel instead
        # of including it in the text directly
        backup_words_count = len(self.backup_words) if self.brute_mode else None
        
        print_info_panel(info_text, self.use_color, backup_words_count)
    
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
                
            # Apply content type filters
            if any(ignore in scan_result.content_type for ignore in self.ignore_content):
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
        # Always show target information, even in silent mode
        if self.use_color:
            console.rule(f"[bold blue]Target: {target_url}[/bold blue]", style="blue")
        else:
            title = f"Target: {target_url}"
            print("\n" + "-" * len(title))
            print(title)
            print("-" * len(title))
        
        # Debug: Check URL segments before processing
        if self.verbose:
            from utils.debug_utils import debug_url_segments
            debug_url_segments(target_url)
        
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
        
        # Always use progress bar, even in silent mode
        progress, task = create_progress_bar(total_tests, self.use_color)
        with progress:
            # For each base URL, test all extensions
            for base_url, test_type in test_urls:
                # Always show what is being tested, even in silent mode
                if self.use_color:
                    # Get the correct display information based on test type
                    url_display = self._get_display_url(base_url, test_type)
                    
                    # Special case for Brute Force: show only "Testing Brute Force: [word]" without url_display
                    if test_type.startswith("Brute Force:"):
                        word = test_type.split(": ")[1] if ": " in test_type else ""
                        console.print(f"[bold yellow]Testing Brute Force:[/bold yellow] {word}")
                    # Special case for Brute Force Path: fix display format
                    elif test_type.startswith("Brute Force Path:"):
                        word = test_type.split(": ")[1] if ": " in test_type else ""
                        console.print(f"[bold yellow]Testing Brute Force Path:[/bold yellow] {word}")
                    else:
                        console.print(f"[bold yellow]Testing {test_type}:[/bold yellow] {url_display}")
                else:
                    # Version without color using same logic
                    url_display = self._get_display_url(base_url, test_type)
                    
                    # Special case for Brute Force
                    if test_type.startswith("Brute Force:"):
                        print(f"Testing Brute Force: {test_type.split(': ')[1] if ': ' in test_type else ''}")
                    # Special case for Brute Force Path
                    elif test_type.startswith("Brute Force Path:"):
                        print(f"Testing Brute Force Path: {test_type.split(': ')[1] if ': ' in test_type else ''}")
                    else:
                        print(f"Testing {test_type}: {url_display}")
                
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
                if self.use_color:
                    console.print()
                else:
                    print()
    
    def _get_display_url(self, base_url: str, test_type: str) -> str:
        """
        Returns the appropriate representation of the URL being tested based on the test type.
        """
        parsed = urllib.parse.urlparse(base_url)
        
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
        
        elif test_type.startswith("Segment"):
            # Extract the segment number from the test type
            try:
                segment_num = int(test_type.split(' ')[-1])
                
                # Extract the path from the URL and split into segments
                original_path = parsed.path.strip('/')
                
                if not original_path:
                    return ""
                
                # Check path content for debugging
                if self.verbose:
                    print(f"[DEBUG-DISPLAY] URL: {base_url}, Path: {original_path}")
                
                # The simplest solution is to check the last part of the base_url
                # to identify which segment we're testing
                base_path = original_path  # This is the path in the base_url (e.g. 'Panel')
                
                if self.verbose:
                    print(f"[DEBUG-DISPLAY] Base path: {base_path}")
                
                # Get the correct segment from the full original URL
                # For URLs like `/Panel/Account/Login`, when testing Segment 2,
                # we want to return 'Account'
                
                # In this case, our segment is simply the base path itself
                # since we're testing a specific segment at a time
                return base_path
                
            except (ValueError, IndexError) as e:
                if self.verbose:
                    print(f"[DEBUG-DISPLAY] Error processing segment: {str(e)}")
                return ""
        
        elif test_type.startswith("Path-Subdomain:") or test_type.startswith("Path-Domain-Name:") or test_type.startswith("Path-Domain:"):
            # Extract the last part of the path containing the tested value
            path_parts = parsed.path.strip('/').split('/')
            if path_parts:
                # The last part of the path will be the value we're testing (subdomain, domain name, or domain)
                test_value = path_parts[-1]
                return test_value
            return ""
        
        elif test_type == "Subdomain":
            # For Subdomain, show only the subdomain
            hostname = parsed.netloc
            # Remove port if it exists
            if ':' in hostname:
                hostname = hostname.split(':')[0]
                
            parts = hostname.split('.')
            # If it has at least 3 parts (subdomain.domain.tld) or
            # if it has at least 2 parts but is not a compound TLD (like .com.br)
            if len(parts) >= 3 or (len(parts) == 2 and not any(hostname.endswith(f".{tld}") for tld in ['co.uk', 'com.br', 'com.au', 'org.br', 'net.br', 'com.vc'])):
                return parts[0]
            return "[none]"
        
        elif test_type == "Domain Name":
            # For Domain Name, show the domain name without TLD
            hostname = parsed.netloc
            # Remove port if it exists
            if ':' in hostname:
                hostname = hostname.split(':')[0]
                
            parts = hostname.split('.')
            
            # Identify common compound TLDs
            compound_tlds = ['co.uk', 'com.br', 'com.au', 'org.br', 'net.br', 'com.vc', 'edu.br', 'gov.br']
            
            # Check special case for domains with compound TLDs
            for tld in compound_tlds:
                if hostname.endswith(f".{tld}"):
                    # If it's a domain with subdomain and compound TLD: sub.domain.com.br
                    if len(parts) > 3:
                        return parts[-3]  # Returns 'domain'
                    # If it's a normal domain with compound TLD: domain.com.br
                    else:
                        return parts[0]  # Returns 'domain'
            
            # For normal non-compound domains
            if len(parts) >= 3:  # sub.domain.com
                return parts[-2]  # Returns 'domain'
            elif len(parts) == 2:  # domain.com
                return parts[0]  # Returns 'domain'
            
            return hostname
            
        elif test_type == "Domain":
            # For Domain, show the full domain including TLD (without subdomain)
            hostname = parsed.netloc
            # Remove port if it exists
            if ':' in hostname:
                hostname = hostname.split(':')[0]
                
            parts = hostname.split('.')
            
            # Identify common compound TLDs
            compound_tlds = [
                    "co.uk", "com.br", "com.au", "org.br", "net.br",
                    "com.vc", "edu.br", "gov.br", "gov.uk", "gov.au",
                    "gov.za", "edu.au", "edu.uk", "ac.uk", "org.uk",
                    "net.uk", "com.mx", "com.ar", "com.co", "com.pe",
                    "com.cl", "com.ec", "com.bo", "com.uy", "com.pa",
                    "org.mx", "org.ar", "org.co", "org.pe", "org.cl",
                    "org.ec", "org.bo", "org.uy", "org.pa", "gov.mx",
                    "gov.ar", "gov.co", "gov.pe", "gov.cl", "gov.ec",
                    "gov.bo", "gov.uy", "gov.pa"
            ]
            
            # Check special case for domains with compound TLDs
            for tld in compound_tlds:
                if hostname.endswith(f".{tld}"):
                    # If it's a domain with subdomain and compound TLD: sub.domain.com.br
                    if len(parts) > 3:
                        return f"{parts[-3]}.{tld}"  # Returns 'domain.com.br'
                    # If it's a normal domain with compound TLD: domain.com.br
                    else:
                        return hostname  # Returns 'domain.com.br'
            
            # For normal non-compound domains
            if len(parts) >= 3:  # sub.domain.com
                return f"{parts[-2]}.{parts[-1]}"  # Returns 'domain.com'
            elif len(parts) == 2:  # domain.com
                return hostname  # Returns 'domain.com'
            
            return hostname
            
        elif test_type.startswith("Brute Force:"):
            # For Brute Force, show only the keyword being tested
            # Extract the keyword from the test type (format: "Brute Force: word")
            return test_type.split(": ")[1] if ": " in test_type else ""
    
    def process_url_list(self, url_list_file: str):
        """Process multiple URLs from a file."""
        urls = load_url_list(url_list_file)
        if not urls:
            return
        
        total_urls = len(urls)
        
        # Display initial information (even in silent mode)
        if self.use_color:
            console.print(f"[bold cyan]Processing {total_urls} URLs from list: {url_list_file}[/bold cyan]")
        else:
            print(f"Processing {total_urls} URLs from list: {url_list_file}")
        
        # Use a single progress bar for all URLs (even in silent mode)
        progress, task_id = create_url_list_progress(total_urls, self.use_color)
        
        with progress:
            for i, url in enumerate(urls, 1):
                # Update progress bar description with current URL
                progress.update(task_id, description=f"[cyan]URL {i}/{total_urls}: {url}")
                
                # Clear previous results if we're generating a file per URL
                if self.output_per_url:
                    self.results = []
                
                # Process the current URL (with display deactivated to avoid conflict)
                self._process_url_without_progress(url)
                
                # Export results for this specific URL if needed
                if self.output_per_url and self.output_file:
                    from urllib.parse import urlparse
                    from utils.file_utils import export_results
                    
                    # Create filename based on URL
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
                
                # Advance the progress bar
                progress.update(task_id, advance=1)

    def _process_url_without_progress(self, target_url: str):
        """Process a URL without using progress bars (for use within URL list processing)."""
        # Always show target information, even in silent mode
        if self.use_color:
            console.rule(f"[bold blue]Target: {target_url}[/bold blue]", style="blue")
        else:
            title = f"Target: {target_url}"
            print("\n" + "-" * len(title))
            print(title)
            print("-" * len(title))
        
        # Debug: Check URL segments before processing
        if self.verbose:
            from utils.debug_utils import debug_url_segments
            debug_url_segments(target_url)
        
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
        
        # Without progress bar, we process directly
        for base_url, test_type in test_urls:
            # Always show what is being tested, even in silent mode
            if self.use_color:
                url_display = self._get_display_url(base_url, test_type)
                
                # Special case for Brute Force: show only "Testing Brute Force: [word]" without url_display
                if test_type.startswith("Brute Force:"):
                    word = test_type.split(": ")[1] if ": " in test_type else ""
                    console.print(f"[bold yellow]Testing Brute Force:[/bold yellow] {word}")
                # Special case for Brute Force Path: fix display format
                elif test_type.startswith("Brute Force Path:"):
                    word = test_type.split(": ")[1] if ": " in test_type else ""
                    console.print(f"[bold yellow]Testing Brute Force Path:[/bold yellow] {word}")
                else:
                    console.print(f"[bold yellow]Testing {test_type}:[/bold yellow] {url_display}")
            else:
                # Version without color using the same logic
                url_display = self._get_display_url(base_url, test_type)
                
                # Special case for Brute Force
                if test_type.startswith("Brute Force:"):
                    print(f"Testing Brute Force: {test_type.split(': ')[1] if ': ' in test_type else ''}")
                # Special case for Brute Force Path
                elif test_type.startswith("Brute Force Path:"):
                    print(f"Testing Brute Force Path: {test_type.split(': ')[1] if ': ' in test_type else ''}")
                else:
                    print(f"Testing {test_type}: {url_display}")
            
            # Test all extensions in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_ext = {
                    executor.submit(self.test_url, base_url, ext, test_type): ext 
                    for ext in self.extensions
                }
                
                for future in concurrent.futures.as_completed(future_to_ext):
                    result = future.result()
                    if result:
                        format_and_print_result(console, result, self.use_color, self.verbose, self.silent)
            
            # Always add a blank line after each test group
            if self.use_color:
                console.print()
            else:
                print()

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
