"""
Console utilities for LeftOvers. Handles pretty output and formatting.
"""

# Fix for macOS permission issues with os.getcwd() in rich module
import os
import sys

# Patch os.getcwd to avoid permission issues in macOS
original_getcwd = os.getcwd
def safe_getcwd():
    try:
        return original_getcwd()
    except (OSError, PermissionError):
        # Fallback to a safe directory if getcwd() fails
        home_dir = os.path.expanduser('~')
        return home_dir

# Apply the patch before importing rich
os.getcwd = safe_getcwd

# Now it's safe to import rich
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, 
    TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
)
from rich import box
 
from utils.file_utils import format_size

# Initialize Rich console with colors enabled
console = Console(force_terminal=True, width=120)

def print_banner(use_color=True, silent=False):
    """Print the ASCII banner for the application."""
    if silent:
        return

    banner_text = r"""   
    ___/—\___   _           __ _    ____
   |………………………| | |         / _| |  / __ \                   ©
    | ¦ ¦ ¦ |  | |     ___| |_| |_| |  | |_   _____ _ __ ___
    | ¦ ¦ ¦ |  | |    / _ \  _| __| |  | \ \ / / _ \ '__/ __|
    | ¦ ¦ ¦ |  | |___|  __/ | | |_| |__| |\ V /  __/ |  \__ \
    \_______/  |______\___|_|  \__|\____/  \_/ \___|_|  |___/
    """

    if use_color:
        console.print(banner_text, style="bold bright_white")
        console.print("       [bold bright_green][Advanced Web Scanner for Leftover Files Discovery][/bold bright_green]")
        console.print()
    else:
        print(banner_text)
        print("    Advanced Web Scanner for Leftover Files Discovery")
        print()

def print_info_panel(text: str, use_color: bool = True, backup_words_count: int = None):
    """Print an info panel with the given text."""
    # Add backup words count information if available
    full_text = text
    if backup_words_count is not None and backup_words_count > 0:
        full_text += f" | Words: {backup_words_count}"
        
    if use_color:
        console.print(Panel(full_text, title="Scanner Info", border_style="cyan", expand=False, padding=(0, 7)))
    else:
        print("\n" + "=" * 50)
        print(f" {full_text}")
        print("=" * 50 + "\n")

def print_large_file_warning(max_size_mb, use_color=True):
    """Print a warning about large file handling."""
    warning = f"Files larger than {max_size_mb}MB will not be fully downloaded for performance reasons."
    if use_color:
        console.print(Panel(warning, title="[bold yellow]Large Files Warning[/bold yellow]", border_style="yellow"))
    else:
        print(f"WARNING: {warning}")

def create_progress_bar(total, use_color=True):
    """Create and return a progress bar."""
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console if use_color else None
    )
    task_id = progress.add_task("[cyan]Scanning...", total=total)
    return progress, task_id

def print_results_table(results, use_color=True, max_size_mb=50):
    """Print a table of scan results."""
    if not results:
        return

    table = Table(title="Scan Results", box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("URL", style="cyan" if use_color else "", no_wrap=False, max_width=80)
    table.add_column("Status", style="magenta" if use_color else "", width=8, justify="center")
    table.add_column("Size", style="green" if use_color else "", width=10, justify="right")
    table.add_column("Type", style="blue" if use_color else "", width=24)
    table.add_column("Notes", style="yellow" if use_color else "")

    for result in results:
        # Check if we are dealing with a dictionary or ScanResult object
        is_dict = isinstance(result, dict)
        
        status_code = result.get("status_code", 0) if is_dict else result.status_code
        
        # Process file size with formatting function for better readability
        if is_dict:
            file_size = result.get("content_length", 0)
        else:
            file_size = result.content_length if hasattr(result, "content_length") else 0
        
        # Format file size with helper function
        file_size_str = format_size(file_size)
            
        # Check additional notes
        notes = ""
        
        # Check if it's a large file
        is_large_file = False
        if file_size > max_size_mb * 1024 * 1024:
            notes = "Large file detected!"
            is_large_file = True
                
        # Check false positives
        if hasattr(result, "false_positive") and result.false_positive:
            if notes:
                notes += " | "
            notes += f"False positive: {result.false_positive_reason if hasattr(result, 'false_positive_reason') else 'Yes'}"
        
        # Format status code with colors
        if use_color:
            status_text = _format_status_with_color(status_code)
        else:
            status_text = str(status_code)
        
        # Get URL and content type
        url = result.get("url", "") if is_dict else (result.url if hasattr(result, "url") else "")
        content_type = result.get("content_type", "") if is_dict else (result.content_type if hasattr(result, "content_type") else "")
        
        # Simplify content type for display
        content_type = _format_content_type(content_type)
        
        # Truncate URL if too long
        if len(url) > 80:
            url = url[:77] + "..."
            
        # Apply special style for large files or false positives
        url_style = ""
        if is_large_file and use_color:
            url_style = "dim cyan"
        elif hasattr(result, "false_positive") and result.false_positive and use_color:
            url_style = "dim cyan"
            
        table.add_row(
            f"[{url_style}]{url}[/{url_style}]" if url_style else url,
            status_text,
            file_size_str,
            content_type,
            notes
        )

    console.print(table)

def _format_status_with_color(status_code):
    """Helper function to format status code with appropriate color."""
    if status_code == 200:
        status_style = "green"
    elif status_code in [401, 403]:
        status_style = "yellow"
    elif status_code >= 400:
        status_style = "red"
    else:
        status_style = "blue"
        
    return f"[{status_style}]{status_code}[/{status_style}]"

def _format_content_type(content_type):
    """Helper function to format and simplify content type strings."""
    if not content_type:
        return "Unknown"
        
    # Remove parameters like charset
    if ";" in content_type:
        content_type = content_type.split(";")[0].strip()
        
    # Abbreviate common types for cleaner display
    common_types = {
        "text/html": "HTML",
        "text/plain": "Text",
        "application/json": "JSON",
        "application/xml": "XML",
        "application/javascript": "JavaScript",
        "text/css": "CSS",
        "application/pdf": "PDF",
        "image/jpeg": "JPEG",
        "image/png": "PNG",
        "image/gif": "GIF"
    }
    
    return common_types.get(content_type, content_type)

def print_summary(found_count, total_count, use_color=True):
    """Print a summary of the scan."""
    if use_color:
        if found_count > 0:
            console.print(f"\n[bold green]Found {found_count} residual files out of {total_count} tests.[/bold green]")
        else:
            console.print("\n[yellow]No residual files found.[/yellow]")
    else:
        if found_count > 0:
            print(f"\nFound {found_count} residual files out of {total_count} tests.")
        else:
            print("\nNo residual files found.")

def format_and_print_result(console, result, use_color=True, verbose=False, silent=False, max_size_mb=50):
    """Format and print a result with colors according to HTTP status."""
    if not result or silent:
        return
        
    # Import SUCCESS_STATUSES only when needed to avoid circular imports
    from app_settings import SUCCESS_STATUSES
    
    # Get file size in MB (if available)
    file_size_mb = None
    if hasattr(result, 'content_length') and result.content_length:
        file_size_mb = result.content_length / (1024 * 1024)
        
    large_file = file_size_mb and file_size_mb > max_size_mb
    
    # Build the details part of the output
    details = f"(TYPE: {result.content_type.split(';')[0]}, SIZE: "
    
    # Format size with warning for large files
    if large_file and use_color:
        details += f"[bold yellow]{file_size_mb:.2f}MB[/bold yellow]"
    elif hasattr(result, 'content_length'):
        if result.content_length > 1024 * 1024:
            details += f"{file_size_mb:.2f}MB"
        else:
            details += f"{result.content_length:,} bytes"
    else:
        details += "Unknown"
        
    details += f", TIME: {result.response_time:.2f}s, STATUS: "
    
    if use_color:
        # Determine the appropriate style based on status code
        if result.status_code in SUCCESS_STATUSES:
            status_style = "bold green"  # Bold green for successful responses
        elif result.status_code in (401, 403):
            status_style = "yellow"
        elif result.status_code >= 400:
            status_style = "red"
        else:
            status_style = "cyan"
            
        details += f"[{status_style}]{result.status_code}[/{status_style}])"
        
        # Add false positive indicator if applicable
        if hasattr(result, 'false_positive') and result.false_positive:
            # Use different styling based on status - success codes are important even when marked as FP
            if result.status_code in SUCCESS_STATUSES:
                details += f" [yellow][Possible FP: {result.false_positive_reason}][/yellow]"
            else:
                details += f" [dim red][FP: {result.false_positive_reason}][/dim red]"
            
        # Add large file warning
        if large_file:
            details += " [bold yellow][LARGE FILE - Partial scan only][/bold yellow]"
        
        # Add partial content indicator for 206 responses
        if result.status_code == 206:
            details += " [cyan][Partial Content][/cyan]"

        line = f"{result.url} {details}"
        
        if result.status_code == 404:
            if verbose:
                console.print(f"[dim]{line}[/dim]")
        elif hasattr(result, 'false_positive') and result.false_positive and result.status_code not in SUCCESS_STATUSES:
            if verbose:
                console.print(f"[dim yellow]{line}[/dim yellow]")
        else:
            if result.status_code in SUCCESS_STATUSES:
                console.print(f"[bold green]{line}[/bold green]")
            elif result.status_code == 403:
                console.print(f"[bold yellow]{line}[/bold yellow]")
            else:
                console.print(line)
    else:
        # Non-color mode
        details += f"{result.status_code})"
        
        # Add false positive indicator if applicable (non-color mode)
        if hasattr(result, 'false_positive') and result.false_positive:
            if result.status_code in SUCCESS_STATUSES:
                details += f" [POSSIBLE FP: {result.false_positive_reason}]"
            else:
                details += f" [FP: {result.false_positive_reason}]"
            
        # Add large file warning in non-color mode
        if large_file:
            details += " [LARGE FILE - Partial scan only]"
            
        # Add partial content indicator for 206 responses
        if result.status_code == 206:
            details += " [Partial Content]"
            
        line = f"{result.url} {details}"
        
        # Only print relevant results in non-color mode
        if result.status_code != 404 or verbose:
            if not hasattr(result, 'false_positive') or not result.false_positive or result.status_code in SUCCESS_STATUSES or verbose:
                print(line)

def print_large_file_skipped(url, size_mb, max_size_mb, use_color=True):
    """Print a message when a large file is skipped."""
    message = f"Skipped full download: {url} (Size: {size_mb:.2f}MB exceeds limit of {max_size_mb}MB)"
    if use_color:
        console.print(f"[yellow]{message}[/yellow]")
    else:
        print(message)

def print_url_list_progress(current: int, total: int, url: str, use_color: bool = True):
    """Print progress information for URL list processing."""
    percentage = (current / total) * 100
    
    if use_color:
        # Create a more compact visual progress bar
        filled_blocks = int(percentage / 10)
        progress_bar = f"[{'█' * filled_blocks}{' ' * (10 - filled_blocks)}]"
        
        # Show progress information in a single clean line
        console.print(f"[bold blue]── URL {current}/{total} {progress_bar} {percentage:.1f}% ── [cyan]{url}[/cyan][/bold blue]")
    else:
        progress_bar = f"[{'#' * int(percentage // 10)}{' ' * (10 - int(percentage // 10))}]"
        print(f"── URL {current}/{total} {progress_bar} {percentage:.1f}% ── {url}")

def create_url_list_progress(total: int, use_color: bool = True):
    """Create a progress bar for URL list processing."""
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console if use_color else None
    )
    task_id = progress.add_task("[cyan]Processing URLs...", total=total)
    return progress, task_id
