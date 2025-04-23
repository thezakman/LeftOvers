"""
Console utilities for LeftOvers. Handles pretty output and formatting.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Initialize Rich console
console = Console()

def print_banner(use_color=True, silent=False):
    """Print the ASCII banner for the application."""
    if silent:
        return

    banner_text = r"""
    ___/-\___   _           __ _    ____                     
   |---------| | |         / _| |  / __ \                    
    | | | | |  | |     ___| |_| |_| |  | |_   _____ _ __ ___ 
    | | | | |  | |    / _ \  _| __| |  | \ \ / / _ \ '__/ __| 
    | | | | |  | |___|  __/ | | |_| |__| |\ V /  __/ |  \__ \ 
    |_______|  |______\___|_|  \__|\____/  \_/ \___|_|  |___/ 
 """
    if use_color:
        console.print(banner_text, style="bold cyan")
    else:
        print(banner_text)

def print_info_panel(info_text, use_color=True):
    """Print an info panel with the given text."""
    if use_color:
        console.print(Panel(info_text, title="[bold]Scanner Info[/bold]", border_style="blue"))
    else:
        print(f"Scanner Info: {info_text}")

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

    table = Table(title="Scan Results")
    table.add_column("URL", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Size", style="green")
    table.add_column("Type", style="blue")
    table.add_column("Notes", style="yellow")

    for result in results:
        status_style = ""
        status_code = result.get("Status", 0)
        file_size = result.get("Tamanho", "")
        notes = ""
        
        # Check if this is a large file
        if "MB" in file_size:
            try:
                size_value = float(file_size.replace("MB", "").strip())
                if size_value > max_size_mb:
                    notes = "Large file detected!"
            except ValueError:
                pass
        
        if use_color:
            if status_code == 200:
                status_style = "[green]"
            elif status_code in [401, 403]:
                status_style = "[yellow]"
            elif status_code >= 400:
                status_style = "[red]"
                
            status_text = f"{status_style}{status_code}[/]" if status_style else str(status_code)
        else:
            status_text = str(status_code)
            
        table.add_row(
            result.get("URL", ""),
            status_text,
            file_size,
            result.get("Tipo", ""),
            notes
        )

    console.print(table)

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
        
    # Get file size in MB (if available)
    file_size_mb = None
    if hasattr(result, 'content_length') and result.content_length:
        file_size_mb = result.content_length / (1024 * 1024)
        
    large_file = file_size_mb and file_size_mb > max_size_mb
    
    details = f"(TYPE: {result.content_type}, SIZE: "
    
    # Format size with warning for large files
    if large_file and use_color:
        details += f"[bold yellow]{file_size_mb:.2f}MB[/bold yellow]"
    elif hasattr(result, 'content_length'):
        details += f"{result.content_length:,} bytes" if result.content_length else "Unknown"
    else:
        details += "Unknown"
        
    details += f", TIME: {result.response_time:.2f}s, STATUS: "
    
    if use_color:
        if result.status_code == 200:
            status_style = "green"
        elif result.status_code in (401, 403):
            status_style = "yellow"
        elif result.status_code >= 400:
            status_style = "red"
        else:
            status_style = "cyan"
            
        details += f"[{status_style}]{result.status_code}[/{status_style}])"
        
        # Add false positive indicator if applicable
        if result.false_positive:
            details += f" [dim red][FP: {result.false_positive_reason}][/dim red]"
            
        # Add large file warning
        if large_file:
            details += " [bold yellow][LARGE FILE - Partial scan only][/bold yellow]"

        line = f"{result.url} {details}"
        
        if result.status_code == 404:
            if verbose:
                console.print(f"[dim]{line}[/dim]")
        elif result.false_positive and result.status_code != 200:
            if verbose:
                console.print(f"[dim yellow]{line}[/dim yellow]")
        else:
            if result.status_code == 200:
                console.print(f"[bold green]{line}[/bold green]")
            else:
                console.print(line)
    else:
        details += f"{result.status_code})"
        if result.false_positive:
            details += f" [FP: {result.false_positive_reason}]"
            
        # Add large file warning in non-color mode
        if large_file:
            details += " [LARGE FILE - Partial scan only]"
            
        line = f"{result.url} {details}"
        if result.status_code != 404 or verbose:
            if not result.false_positive or result.status_code == 200 or verbose:
                print(line)

def print_large_file_skipped(url, size_mb, max_size_mb, use_color=True):
    """Print a message when a large file is skipped."""
    message = f"Skipped full download: {url} (Size: {size_mb:.2f}MB exceeds limit of {max_size_mb}MB)"
    if use_color:
        console.print(f"[yellow]{message}[/yellow]")
    else:
        print(message)
