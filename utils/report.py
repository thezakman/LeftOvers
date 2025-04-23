"""
Report generation utilities for LeftOvers.
"""

from typing import List, Dict, Any
from rich.table import Table
from rich.console import Console

from core.result import ScanResult
from utils.logger import logger

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
    """Generate and print a summary report for scan results."""
    # Group and count results
    status_counts, fp_counts = group_results_by_status(results)
    
    # Fix false positive count - can't be greater than total
    if fp_counts > len(results):
        fp_counts = len(results)
    
    # Filter interesting results
    interesting = filter_interesting_results(results)
    
    # Debug counts (when verbose)
    if verbose:
        logger.debug(f"Total results: {len(results)}")
        logger.debug(f"False positives: {fp_counts}")
        logger.debug(f"Interesting results: {len(interesting)}")
        
        # Count by status
        status_summary = {status: len([r for r in results if r.status_code == status]) 
                       for status in set(r.status_code for r in results)}
        logger.debug(f"Status summary: {status_summary}")
        
        # False positives by status
        fp_by_status = {status: len([r for r in results 
                                  if r.status_code == status and r.false_positive]) 
                      for status in set(r.status_code for r in results)}
        logger.debug(f"False positives by status: {fp_by_status}")

    # Find duplicate content
    duplicate_sets, total_duplicates = find_duplicate_content(interesting)
    
    # Create a summary table
    table = Table(title="Results Summary")
    table.add_column("Statistic", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta", justify="right")
    table.add_column("Notes", style="dim")
    
    table.add_row("Total Tests", str(len(results)), "")
    table.add_row(
        "Files Found", 
        str(len(interesting)),
        f"(Excluding {fp_counts} false positives)"
    )
    
    # Check if we detected duplicate content
    if duplicate_sets:
        table.add_row(
            "Unique Content", 
            str(len(interesting) - total_duplicates),
            f"({total_duplicates} are duplicates)"
        )
    
    # Add counts by status code
    for status, counts in sorted(status_counts.items()):
        style = "green" if status == 200 else "yellow" if status in (401, 403) else "red" if status >= 400 else "blue"
        fp_info = ""
        if counts["false_positive"] > 0:
            fp_info = f"({counts['false_positive']} false positives)"
            
        table.add_row(
            f"Status {status}", 
            f"[{style}]{counts['total']}[/{style}]", 
            fp_info
        )
    
    console.print(table)
    
    # If found interesting results, show the top findings
    if interesting:
        generate_top_findings_report(interesting, console)

def generate_top_findings_report(results: List[ScanResult], console: Console):
    """Generate and print a report of top findings."""
    # Sort by:
    # 1) Status 200
    # 2) Not false positive
    # 3) Higher content size (bigger files often more interesting)
    top_results = sorted(
        results, 
        key=lambda r: (
            r.status_code == 200,  # 200s first
            not r.false_positive,  # non-false positives next
            r.content_length       # larger content last
        ),
        reverse=True
    )
    
    # Limit to 10 most relevant results
    top_results = top_results[:10]
    
    console.print("\n[bold]Top Findings:[/bold]")
    
    # Create a results table
    results_table = Table(show_header=True)
    results_table.add_column("#", style="dim", width=3)
    results_table.add_column("URL", style="bold")
    results_table.add_column("Status", width=8)
    results_table.add_column("Size", justify="right", width=10)
    results_table.add_column("Type", width=20)
    
    for idx, result in enumerate(top_results, 1):
        status_style = "green" if result.status_code == 200 else "yellow" if result.status_code in (401, 403) else "red"
        status_text = f"[{status_style}]{result.status_code}[/{status_style}]"
                    
        results_table.add_row(
            str(idx),
            result.url,
            status_text,
            f"{result.content_length:,}",
            result.content_type.split(';')[0] if result.content_type else "N/A"
        )
            
    console.print(results_table)
