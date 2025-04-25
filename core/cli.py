"""
Command-line interface for LeftOvers scanner.
"""

import os
import sys
import argparse
import traceback

from core.config import (
    VERSION, DEFAULT_TIMEOUT, DEFAULT_THREADS, DEFAULT_EXTENSIONS, 
    DEFAULT_BACKUP_WORDS, DEFAULT_HEADERS
)
from core.scanner import LeftOver
from core.detection import parse_status_codes
from utils.logger import logger
from utils.console import console
from utils.file_utils import load_wordlist, load_url_list, export_results

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="LeftOver - Advanced scanner to find residual files on web servers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
    parser.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds for each request")
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS, help="Number of parallel threads")
    parser.add_argument("-a", "--user-agent", help="Custom User-Agent")
    parser.add_argument("-ra", "--rotate-agents", action="store_true", help="Randomly rotate User-Agents")
    parser.add_argument("-H", "--header", action="append", help="Custom header in format 'Name: Value' (can be used multiple times)")
    parser.add_argument("-c", "--cookie", help="Cookies to include with requests")
    parser.add_argument("-o", "--output", help="File to save results (JSON)")
    parser.add_argument("--output-per-url", action="store_true", help="Criar um arquivo de saída separado para cada URL (quando usado com --list)")
    parser.add_argument("--test-index", action="store_true", help="Test for index.{extension} on domain URLs")
    
    # Brute force option
    parser.add_argument("-b", "--brute", action="store_true", help="Enable brute force mode with common backup words")
    
    # Filters
    parser.add_argument("-sc", "--status", help="Filter by status codes (e.g., 200,301,403)")
    parser.add_argument("--min-size", type=int, help="Minimum content size in bytes")
    parser.add_argument("--max-size", type=int, help="Maximum content size in bytes")
    parser.add_argument(
        '-ci', '--content-ignore', 
        action='append', 
        default=[], 
        help='Ignore results with specific content types (e.g., "text/html"). Can be used multiple times.'
    )
    
    # Boolean flags
    parser.add_argument("-nc", "--no-color", action="store_true", help="Disable colors in output")
    parser.add_argument("-k", "--no-ssl-verify", action="store_true", help="Disable SSL certificate verification")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode (show more details)")
    parser.add_argument("-s", "--silent", action="store_true", help="Silent mode (show only errors)")
    parser.add_argument("--version", action="version", version=f"LeftOver v{VERSION}")
    
    return parser.parse_args()

def configure_scanner_from_args(args):
    """Configure the scanner based on command line arguments."""
    # Check for incompatible arguments
    if args.verbose and args.silent:
        raise ValueError("Cannot use --verbose and --silent simultaneously")
    
    # Configure color usage
    use_color = not (args.no_color or os.environ.get("NO_COLOR"))
    
    # Configure extensions
    extensions = None
    if args.extensions:
        extensions = [e.strip().lstrip('.').lower() for e in args.extensions.split(',')]
    elif args.wordlist:
        extensions = load_wordlist(args.wordlist)
        if not extensions:
            logger.error("Failed to load wordlist. Using default extensions.")
            extensions = DEFAULT_EXTENSIONS
    
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
        content_ignore=args.content_ignore,
    )
            
    # Add brute force capability if requested
    if args.brute:
        if not args.silent:
            logger.info(f"Brute force mode enabled with {len(DEFAULT_BACKUP_WORDS)} common backup words")
        scanner.brute_mode = True
        scanner.backup_words = DEFAULT_BACKUP_WORDS
    
    return scanner

def main():
    """Main function for the command-line interface."""
    try:
        args = parse_arguments()
        scanner = configure_scanner_from_args(args)
        
        # Display banner only if not in silent mode
        if not args.silent:
            scanner.print_banner()
        
        # Process URLs
        if args.list:
            scanner.output_per_url = getattr(args, 'output_per_url', False)
            scanner.process_url_list(args.list)
        else:
            scanner.process_url(args.url)
        
        # Sempre exibe o resumo dos resultados, mesmo em modo silencioso
        scanner.print_summary()
        
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
