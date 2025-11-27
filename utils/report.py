"""
Report generation utilities for LeftOvers.
"""

from typing import List, Dict, Any
from rich.table import Table
from rich.console import Console
from rich import box

from leftovers.core.result import ScanResult
from leftovers.utils.logger import logger
from leftovers.utils.file_utils import format_size

def group_results_by_status(results: List[ScanResult]) -> Dict[int, Dict[str, int]]:
    """Group results by status code and count false positives."""
    status_counts = {}
    fp_counts = 0
    
    for result in results:
        key = result.status_code
        if key not in status_counts:
            status_counts[key] = {"total": 0, "false_positive": 0}
                
        status_counts[key]["total"] += 1
        if result.false_positive:
            status_counts[key]["false_positive"] += 1
            fp_counts += 1
    
    return status_counts, fp_counts

def filter_interesting_results(results: List[ScanResult]) -> List[ScanResult]:
    """Filter interesting results (not 404 and not false positives, except 200s)."""
    # Optimized version using a single list comprehension
    return [
        r for r in results 
        if (r.status_code != 404 and (not r.false_positive or r.status_code == 200))
    ]

def find_duplicate_content(results: List[ScanResult]) -> tuple:
    """Find duplicate content by grouping by content hash."""
    grouped_by_hash = {}
    for result in results:
        if result.content_hash:
            if result.content_hash not in grouped_by_hash:
                grouped_by_hash[result.content_hash] = []
            grouped_by_hash[result.content_hash].append(result)
    
    # Find potential duplicates (same content hash)
    duplicate_sets = [results for hash_val, results in grouped_by_hash.items() if len(results) > 1]
    
    # Calculate total duplicates
    total_duplicates = 0
    if duplicate_sets:
        total_duplicates = sum(len(dupe_set) for dupe_set in duplicate_sets) - len(duplicate_sets)
        
    return duplicate_sets, total_duplicates

def generate_summary_report(results: List[ScanResult], console: Console, use_color: bool = True, verbose: bool = False):
    """
    Generate and print a summary report for scan results with enhanced analytics and performance.
    
    Args:
        results: List of ScanResult objects
        console: Rich console object for output
        use_color: Whether to use color in output
        verbose: Whether to show verbose output
    """
    if not results:
        console.print("[yellow]No results to display.[/yellow]" if use_color else "No results to display.")
        return
        
    # Use more efficient grouping with a single pass through the data
    status_counts = {}
    fp_counts = 0
    content_types = {}
    content_hashes = {}
    total_size = 0
    
    # Process all results in a single pass for better performance
    for result in results:
        # Status code counts
        key = result.status_code
        if key not in status_counts:
            status_counts[key] = {"total": 0, "false_positive": 0}
                
        status_counts[key]["total"] += 1
        if result.false_positive:
            status_counts[key]["false_positive"] += 1
            fp_counts += 1
            
        # Content type statistics
        content_type = result.content_type.split(';')[0] if result.content_type else "Unknown"
        if content_type not in content_types:
            content_types[content_type] = 0
        content_types[content_type] += 1
        
        # Content hash for duplicate detection
        if result.content_hash:
            if result.content_hash not in content_hashes:
                content_hashes[result.content_hash] = []
            content_hashes[result.content_hash].append(result)
            
        # Total size calculation
        if result.content_length:
            total_size += result.content_length
    
    # Fix false positive count - can't be greater than total
    if fp_counts > len(results):
        fp_counts = len(results)
    
    # Find interesting results using the optimized approach
    interesting = [
        r for r in results 
        if (r.status_code != 404 and (not r.false_positive or r.status_code == 200))
    ]
    
    # Detect duplicates using the content_hashes we computed earlier
    duplicate_sets = [results for hash_val, results in content_hashes.items() if len(results) > 1]
    total_duplicates = sum(len(dupe_set) - 1 for dupe_set in duplicate_sets) if duplicate_sets else 0
    
    # Log debug information
    if verbose:
        logger.debug(f"Total results: {len(results)}")
        logger.debug(f"False positives: {fp_counts}")
        logger.debug(f"Interesting results: {len(interesting)}")
        logger.debug(f"Content types found: {len(content_types)}")
        logger.debug(f"Duplicate content sets: {len(duplicate_sets)}")
        logger.debug(f"Total size of all content: {format_size(total_size)}")
        
    # Create a summary table with enhanced styling
    title_style = "bold cyan" if use_color else ""
    table = Table(title="Results Summary", title_style=title_style, box=box.ROUNDED)
    table.add_column("Statistic", style="cyan" if use_color else "", no_wrap=True)
    table.add_column("Value", style="magenta" if use_color else "", justify="right")
    table.add_column("Notes", style="dim" if use_color else "")
    
    table.add_row("Total Tests", str(len(results)), "")
    table.add_row(
        "Files Found", 
        str(len(interesting)),
        f"(Excluding {fp_counts} false positives)"
    )
    
    # Add unique content information if duplicates were detected
    if total_duplicates > 0:
        table.add_row(
            "Unique Content", 
            str(len(interesting) - total_duplicates),
            f"({total_duplicates} are duplicates)"
        )
    
    # Total content size
    if total_size > 0:
        table.add_row(
            "Total Size", 
            format_size(total_size),
            ""
        )
    
    # Add counts by status code with improved presentation
    sorted_statuses = sorted(status_counts.keys())
    for status in sorted_statuses:
        counts = status_counts[status]
        style = _get_status_style(status) if use_color else ""
            
        fp_info = ""
        if counts["false_positive"] > 0:
            fp_info = f"({counts['false_positive']} false positives)"
            
        table.add_row(
            f"Status {status}", 
            f"[{style}]{counts['total']}[/{style}]" if use_color else str(counts["total"]), 
            fp_info
        )
    
    # Add top content types if we found many different ones
    if len(content_types) > 1 and verbose:
        # Get top content types
        top_types = sorted(content_types.items(), key=lambda x: x[1], reverse=True)[:3]
        top_types_str = ", ".join(f"{t} ({c})" for t, c in top_types)
        
        table.add_row(
            "Top Content Types",
            str(len(content_types)),
            f"Most common: {top_types_str}"
        )
    
    console.print(table)
    
    # If found interesting results, show the top findings with the enhanced report
    if interesting:
        generate_top_findings_report(interesting, console)

def generate_top_findings_report(results: List[ScanResult], console: Console):
    """
    Generate and print a report of top findings with enhanced formatting and more efficient sorting.
    
    Args:
        results: List of ScanResult objects
        console: Rich console object for output
    """
    # Use a more optimized multi-key sorting approach
    # This avoids multiple sorts and uses tuple comparison for better performance
    top_results = sorted(
        results, 
        key=lambda r: (
            # Primary criterion: Status 200 (True sorts higher than False)
            r.status_code == 200,
            # Secondary criterion: Not false positive (True sorts higher)
            not r.false_positive,
            # Third criterion: Interesting content types (True sorts higher)
            _is_interesting_content_type(r.content_type),
            # Fourth criterion: Higher content length
            r.content_length if r.content_length is not None else 0
        ),
        reverse=True
    )
    
    # Limit to 10 most relevant results
    top_results = top_results[:10]
    
    console.print("\n[bold]Top Findings:[/bold]")
    
    if not top_results:
        console.print("[dim italic]No significant findings to display.[/dim italic]")
        return
    
    # Create a results table with better styling
    results_table = Table(show_header=True, header_style="bold", border_style="bright_black")
    results_table.add_column("#", style="dim", width=3, justify="center")
    results_table.add_column("URL", style="bold white", no_wrap=False, max_width=80)
    results_table.add_column("Status", justify="center", width=8)
    results_table.add_column("Size", justify="right", width=12)
    results_table.add_column("Type", width=20)
    
    for idx, result in enumerate(top_results, 1):
        # Use proper style based on status code with more distinctive colors
        status_style = _get_status_style(result.status_code)
        status_text = f"[{status_style}]{result.status_code}[/{status_style}]"
        
        # Format content size with appropriate units for better readability
        size_text = format_size(result.content_length)
        
        # Format content type more clearly
        content_type = result.content_type.split(';')[0] if result.content_type else "N/A"
        
        # Truncate URL if it's too long
        url_display = result.url
        if len(url_display) > 80:
            url_display = url_display[:77] + "..."
            
        results_table.add_row(
            str(idx),
            url_display,
            status_text,
            size_text,
            content_type
        )
            
    console.print(results_table)
    
    # Add a helpful guide about the findings
    console.print("[bright][Status colors]: [green]200/206 OK[/green], [yellow]403/401 Protected[/yellow], "
                 "[red]Error[/red], [blue]Other[/blue][/bright]\n")

def _is_interesting_content_type(content_type: str) -> bool:
    """
    Determine if a content type is likely to be interesting.
    
    Args:
        content_type: Content type string
        
    Returns:
        Boolean indicating if content type is interesting
    """
    if not content_type:
        return False
        
    interesting_types = {
        'application/json', 'application/xml', 'text/csv', 
        'application/zip', 'application/x-tar', 'application/gzip',
        'application/pdf', 'application/msword', 'application/vnd.ms-excel',
        'application/x-sh', 'application/x-sql', 'text/x-php', 'text/x-python',
        'application/sql', 'application/x-httpd-php', 'application/x-javascript',
        'text/yaml', 'text/x-yaml', 'application/x-ruby', 'text/x-perl',
        'text/x-config', 'application/x-perl', 'text/x-java-source'
    }
    
    base_type = content_type.split(';')[0].lower()
    return any(base_type.startswith(t) for t in interesting_types)

def _get_status_style(status_code: int) -> str:
    """
    Get the appropriate color style for a status code.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        String with Rich color style name
    """
    from leftovers.app_settings import SUCCESS_STATUSES
    
    if status_code in SUCCESS_STATUSES:  # 200 OK, 206 Partial Content
        return "bold green"  # Use bold for emphasis on successful responses
    elif status_code == 403:  # Forbidden
        return "yellow"
    elif status_code == 401:  # Unauthorized
        return "yellow"
    elif status_code >= 400:  # Other errors
        return "red"
    else:  # 3xx redirects, etc
        return "blue"
