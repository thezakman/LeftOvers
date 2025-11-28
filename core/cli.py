"""
Command-line interface for LeftOvers scanner.
"""

import os
import sys
import argparse
import traceback
import signal

from leftovers.app_settings import VERSION
from leftovers.core.config import (
    DEFAULT_TIMEOUT, DEFAULT_THREADS, DEFAULT_EXTENSIONS,
    DEFAULT_BACKUP_WORDS, DEFAULT_HEADERS
)
from leftovers.core.scanner import LeftOver
from leftovers.core.detection import parse_status_codes
from leftovers.utils.logger import logger
from leftovers.utils.console import console, print_banner, print_info_panel
from leftovers.utils.file_utils import load_wordlist, load_url_list, export_results

class ArgumentParserWithBanner(argparse.ArgumentParser):
    """Custom ArgumentParser that shows the banner before help"""
    
    def __init__(self, *args, **kwargs):
        self.silent_mode = kwargs.pop('silent_mode', False)
        super().__init__(*args, **kwargs)
        
    def print_help(self, file=None):
        if not self.silent_mode:
            print_banner(True, False)
        super().print_help(file)
        
    def error(self, message):
        if not self.silent_mode:
            print_banner(True, False)
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")

def parse_arguments():
    """Parse command line arguments."""
    # Check for silent mode in args before creating parser
    silent_mode = '-s' in sys.argv or '--silent' in sys.argv
    
    parser = ArgumentParserWithBanner(
        description="LeftOver - Advanced scanner to find residual files on web servers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        silent_mode=silent_mode
    )
    
    # Target group (mutually exclusive)
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("-u", "--url", help="Single URL or domain to scan")
    target_group.add_argument("-l", "--list", help="File with list of URLs/domains")
    
    # Extension options (mutually exclusive)
    ext_group = parser.add_mutually_exclusive_group()
    ext_group.add_argument("-e", "--extensions", help="Comma-separated extensions")
    ext_group.add_argument("-w", "--wordlist", help="File with list of words to use as extensions")
    
    # Configuration options
    parser.add_argument("-to", "--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds for each request")
    parser.add_argument("-t", "--threads", type=int, default=DEFAULT_THREADS, help="Number of parallel threads")
    parser.add_argument("-a", "--user-agent", help="Custom User-Agent")
    parser.add_argument("-ra", "--rotate-agents", action="store_true", help="Randomly rotate User-Agents")
    parser.add_argument("-H", "--header", action="append", help="Custom header in format 'Name: Value' (can be used multiple times)")
    parser.add_argument("-c", "--cookie", help="Cookies to include with requests")
    parser.add_argument("-o", "--output", help="File to save results (JSON)")
    parser.add_argument("--output-per-url", action="store_true", help="Create a separate output file for each URL (when used with --list)")
    parser.add_argument("--test-index", action="store_true", help="Test for index.{extension} on domain URLs")
    parser.add_argument("--rate-limit", type=float, help="Maximum requests per second (e.g., 10 for 10 req/s, 0.5 for 1 req per 2s)")
    parser.add_argument("--delay", type=int, help="Delay in milliseconds between requests (alternative to rate-limit)")
    
    # Brute force options
    parser.add_argument("-b", "--brute", action="store_true", help="Enable brute force mode with common backup words (recommended for leftover discovery)")
    parser.add_argument("-br", "--brute-recursive", action="store_true", help="Enable recursive brute force mode (test each path level)")
    parser.add_argument("-d", "--domain-wordlist", action="store_true", help="Enable dynamic domain-based wordlist generation (generates domain-specific permutations)")
    parser.add_argument("--fast-scan", action="store_true", help="Quick scan mode: brute force + domain wordlist + optimized extensions")
    parser.add_argument("--level", type=int, choices=[0, 1, 2, 3, 4], default=2, 
                       help="Scan complexity level: 0=Critical only (~10-15), 1=Quick (~500), 2=Balanced (~2-3K, default), 3=Deep (~5-8K), 4=Exhaustive (~5-10K, ~100K+ with -b)")
    parser.add_argument("--lang", type=str, choices=["en", "pt-br", "all"], default="all",
                       help="Language filter for brute force words: en=English only, pt-br=Portuguese only, all=Both (default)")
    
    # Filters
    parser.add_argument("-sc", "--status", help="Filter by status codes (e.g., 200,301,403)")
    parser.add_argument("--min-size", type=int, help="Minimum content size in bytes")
    parser.add_argument("--max-size", type=int, help="Maximum content size in bytes")
    parser.add_argument(
        '-ic', '--ignore-content', 
        action='append', 
        default=[], 
        help='Ignore results with specific content types (e.g., "text/html"). Can be used multiple times.'
    )
    parser.add_argument("--no-fp", action="store_true", help="Disable false positive detection (show all results)")
    
    # Boolean flags
    parser.add_argument("-nc", "--no-color", action="store_true", help="Disable colors in output")
    parser.add_argument("-k", "--no-ssl-verify", action="store_true", help="Disable SSL certificate verification")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode (show more details)")
    parser.add_argument("-s", "--silent", action="store_true", help="Silent mode (show only errors)")
    parser.add_argument("--metrics", action="store_true", help="Show performance metrics at the end of scan")
    parser.add_argument("--version", action="version", version=f"LeftOver v{VERSION}")
    
    return parser.parse_args()

def configure_scanner_from_args(args):
    """Configure the scanner based on command line arguments."""
    from leftovers.utils.validators import validate_thread_count, validate_timeout
    
    # Check for incompatible arguments
    if args.verbose and args.silent:
        raise ValueError("Cannot use --verbose and --silent simultaneously")

    # Validate thread count
    is_valid, error_msg = validate_thread_count(args.threads)
    if not is_valid:
        raise ValueError(f"Invalid thread count: {error_msg}")
    
    # Validate timeout
    is_valid, error_msg = validate_timeout(args.timeout)
    if not is_valid:
        raise ValueError(f"Invalid timeout: {error_msg}")

    # Validate rate limiting options
    if args.rate_limit and args.delay:
        raise ValueError("Cannot use both --rate-limit and --delay. Choose one.")

    if args.rate_limit and args.rate_limit <= 0:
        raise ValueError("--rate-limit must be greater than 0")

    if args.delay and args.delay < 0:
        raise ValueError("--delay must be greater than or equal to 0")
    
    # Configure color usage
    use_color = not (args.no_color or os.environ.get("NO_COLOR"))
    
    # Update global VERBOSE setting for HTTP request logging
    if args.verbose:
        from leftovers import app_settings
        app_settings.VERBOSE = True
    
    # Configure extensions and words based on level
    from leftovers.core.helpers import get_config_by_level, get_words_by_language
    level_config = get_config_by_level(args.level)
    
    # Show level info
    if not args.silent:
        logger.info(f"Scan level {args.level}: {level_config['description']}")
        if args.lang != "all" and not args.silent:
            logger.info(f"Language filter: {args.lang}")
    
    extensions = None
    # Apply language filter to words
    if args.lang != "all":
        backup_words = get_words_by_language(args.lang)
    else:
        backup_words = level_config['words']  # Get words from level config
    
    if args.extensions:
        # User specified extensions override level
        extensions = [e.strip().lstrip('.').lower() for e in args.extensions.split(',')]
    elif args.wordlist:
        # User specified wordlist overrides level
        extensions = load_wordlist(args.wordlist)
        if not extensions:
            logger.error("Failed to load wordlist. Using level-based extensions.")
            extensions = level_config['extensions']
    else:
        # Use level-based extensions
        extensions = level_config['extensions']
    
    # Configure HTTP headers
    headers = DEFAULT_HEADERS.copy()
    if args.user_agent:
        headers["User-Agent"] = args.user_agent
        
    # Add custom headers if provided
    if args.header:
        for header_str in args.header:
            try:
                name, value = header_str.split(':', 1)
                headers[name.strip()] = value.strip()
            except ValueError:
                raise ValueError(f"Invalid header format: {header_str}. Use 'Name: Value' format.")
    
    # Add cookies if provided
    if args.cookie:
        headers["Cookie"] = args.cookie
    
    # Configure filters
    status_filter = parse_status_codes(args.status) if args.status else None
    
    # Calculate rate limit parameters
    rate_limit = args.rate_limit if hasattr(args, 'rate_limit') else None
    delay_ms = args.delay if hasattr(args, 'delay') else None

    # Initialize scanner
    scanner = LeftOver(
        extensions=extensions,
        timeout=args.timeout,
        threads=args.threads,
        headers=headers,
        verify_ssl=not args.no_ssl_verify,
        use_color=use_color,
        verbose=args.verbose,
        silent=args.silent,
        output_file=args.output,
        status_filter=status_filter,
        min_content_length=args.min_size,
        max_content_length=args.max_size,
        rotate_user_agent=args.rotate_agents,
        test_index=args.test_index,
        ignore_content=args.ignore_content,
        disable_fp=args.no_fp,
        rate_limit=rate_limit,
        delay_ms=delay_ms
    )
            
    # Add brute force capability if requested, including fast-scan mode
    if args.brute or args.brute_recursive or args.domain_wordlist or args.fast_scan:
        # If brute mode is enabled, use full word list (override level for brute)
        if args.brute and args.level < 3:
            backup_words = DEFAULT_BACKUP_WORDS.copy()
        # Otherwise backup_words already set from level_config above

        # Configure fast-scan mode (enables multiple features at once)
        if args.fast_scan:
            if not args.silent:
                logger.info("Fast scan mode enabled: brute force + domain wordlist + extension optimization")
            scanner.brute_mode = True
            scanner.domain_wordlist = True
            scanner.backup_words = backup_words
            # Fast scan also reduces extensions to most effective ones for speed
            if not extensions:  # Only if no custom extensions specified
                from leftovers.core.config import CRITICAL_BACKUP_EXTENSIONS, SECURITY_EXTENSIONS
                scanner.extensions = CRITICAL_BACKUP_EXTENSIONS[:20] + SECURITY_EXTENSIONS[:10]
        else:
            # Regular brute force configuration
            if not args.silent:
                if args.brute or args.brute_recursive:
                    logger.info(f"Brute force mode enabled with {len(backup_words)} common backup words")
                    if args.brute_recursive:
                        logger.info("Recursive brute force mode enabled - testing all path levels")

                if args.domain_wordlist:
                    logger.info("Domain-based wordlist generation enabled")

            scanner.brute_mode = True
            scanner.brute_recursive = args.brute_recursive
            scanner.domain_wordlist = args.domain_wordlist
            scanner.backup_words = backup_words
    
    return scanner

def handle_interrupt(signum, frame):
    """Handle keyboard interrupt gracefully."""
    # Verify if the signal is from a keyboard interrupt
    import sys
    
    # check if silent mode is enabled
    silent = '-s' in sys.argv or '--silent' in sys.argv
    
    if not silent:
        from leftovers.utils.console import console
        console.print("\n[bold red]Interrupted by user. Cleaning up...[/bold red]")
    sys.exit(0)

def main():
    """Main function for the command-line interface."""
    from leftovers.utils.validators import validate_url
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    try:
        args = parse_arguments()
        
        # Validate single URL if provided
        if args.url:
            is_valid, error_msg = validate_url(args.url)
            if not is_valid:
                console.print(f"[bold red]Invalid URL:[/bold red] {error_msg}")
                sys.exit(1)
        
        scanner = configure_scanner_from_args(args)
        
        # Let the scanner class display the banner and information panel
        # to ensure that all information, including the word count,
        # is displayed correctly
        scanner.print_banner()
        
        # Process URLs
        if args.list:
            scanner.output_per_url = getattr(args, 'output_per_url', False)
            scanner.process_url_list(args.list)
        else:
            scanner.process_url(args.url)
        
        # Always display the summary of results, even in silent mode
        scanner.print_summary()
        
        # Show performance metrics if requested
        if (args.verbose or args.metrics) and hasattr(scanner, 'metrics'):
            scanner.metrics.finalize()
            scanner.metrics.print_summary(use_color=not args.no_color)
        
        # Export results if needed
        if args.output:
            export_results(scanner.results, args.output)
            
    except KeyboardInterrupt:
        if not getattr(args, 'silent', False):
            console.print("\n[bold red]Interrupted by user.[/bold red]")
        sys.exit(1)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        if getattr(args, 'verbose', False):
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
