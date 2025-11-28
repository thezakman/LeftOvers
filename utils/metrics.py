"""
Performance metrics and statistics tracking for LeftOvers scanner.
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ScanMetrics:
    """Track scanning metrics and statistics."""
    
    # Timing metrics
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_errors: int = 0
    connection_errors: int = 0
    
    # Response metrics
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    # Content metrics
    total_bytes_downloaded: int = 0
    total_bytes_scanned: int = 0
    
    # Discovery metrics
    files_found: int = 0
    false_positives: int = 0
    unique_extensions_found: List[str] = field(default_factory=list)
    
    # Performance metrics
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    
    def record_request(self, success: bool, status_code: Optional[int] = None, 
                       response_time: Optional[float] = None, 
                       bytes_downloaded: int = 0, error_type: Optional[str] = None):
        """
        Record a request and its metrics.
        
        Args:
            success: Whether the request was successful
            status_code: HTTP status code (if applicable)
            response_time: Time taken for the request in seconds
            bytes_downloaded: Number of bytes downloaded
            error_type: Type of error if request failed
        """
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            
            if error_type == 'timeout':
                self.timeout_errors += 1
            elif error_type == 'connection':
                self.connection_errors += 1
        
        if status_code:
            self.status_codes[status_code] += 1
        
        if response_time is not None:
            self.response_times.append(response_time)
            self.min_response_time = min(self.min_response_time, response_time)
            self.max_response_time = max(self.max_response_time, response_time)
            
            # Update average
            if self.response_times:
                self.avg_response_time = sum(self.response_times) / len(self.response_times)
        
        if bytes_downloaded > 0:
            self.total_bytes_downloaded += bytes_downloaded
            self.total_bytes_scanned += bytes_downloaded
    
    def record_discovery(self, is_false_positive: bool = False, extension: Optional[str] = None):
        """
        Record a file discovery.
        
        Args:
            is_false_positive: Whether this is a false positive
            extension: File extension discovered
        """
        self.files_found += 1
        
        if is_false_positive:
            self.false_positives += 1
        
        if extension and extension not in self.unique_extensions_found:
            self.unique_extensions_found.append(extension)
    
    def finalize(self):
        """Mark the scan as complete and record end time."""
        self.end_time = time.time()
    
    def get_duration(self) -> float:
        """
        Get total scan duration in seconds.
        
        Returns:
            Duration in seconds
        """
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    def get_requests_per_second(self) -> float:
        """
        Calculate requests per second rate.
        
        Returns:
            Requests per second
        """
        duration = self.get_duration()
        if duration > 0:
            return self.total_requests / duration
        return 0.0
    
    def get_success_rate(self) -> float:
        """
        Calculate success rate percentage.
        
        Returns:
            Success rate as percentage (0-100)
        """
        if self.total_requests > 0:
            return (self.successful_requests / self.total_requests) * 100
        return 0.0
    
    def get_false_positive_rate(self) -> float:
        """
        Calculate false positive rate percentage.
        
        Returns:
            False positive rate as percentage (0-100)
        """
        if self.files_found > 0:
            return (self.false_positives / self.files_found) * 100
        return 0.0
    
    def get_summary(self) -> Dict:
        """
        Get a comprehensive summary of all metrics.
        
        Returns:
            Dictionary containing all metrics
        """
        return {
            'timing': {
                'duration': round(self.get_duration(), 2),
                'start_time': self.start_time,
                'end_time': self.end_time,
            },
            'requests': {
                'total': self.total_requests,
                'successful': self.successful_requests,
                'failed': self.failed_requests,
                'success_rate': round(self.get_success_rate(), 2),
                'requests_per_second': round(self.get_requests_per_second(), 2),
            },
            'errors': {
                'timeout': self.timeout_errors,
                'connection': self.connection_errors,
            },
            'performance': {
                'avg_response_time': round(self.avg_response_time, 3),
                'min_response_time': round(self.min_response_time, 3) if self.min_response_time != float('inf') else 0,
                'max_response_time': round(self.max_response_time, 3),
            },
            'data': {
                'bytes_downloaded': self.total_bytes_downloaded,
                'bytes_scanned': self.total_bytes_scanned,
                'mb_downloaded': round(self.total_bytes_downloaded / (1024 * 1024), 2),
            },
            'discoveries': {
                'files_found': self.files_found,
                'false_positives': self.false_positives,
                'false_positive_rate': round(self.get_false_positive_rate(), 2),
                'unique_extensions': len(self.unique_extensions_found),
                'extensions_found': self.unique_extensions_found,
            },
            'status_codes': dict(self.status_codes),
        }
    
    def print_summary(self, use_color: bool = True):
        """
        Print a formatted summary of metrics.
        
        Args:
            use_color: Whether to use colored output
        """
        from leftovers.utils.console import console
        from rich.table import Table
        
        summary = self.get_summary()
        
        if use_color:
            # Create performance metrics table
            table = Table(show_header=True, header_style="bold cyan", border_style="cyan")
            table.add_column("Metric", style="white", width=25)
            table.add_column("Value", justify="right", style="green")
            table.add_column("Details", style="dim")
            
            # Timing
            duration = summary['timing']['duration']
            table.add_row(
                "Scan Duration",
                f"{duration:.2f}s",
                f"({duration/60:.1f} minutes)" if duration > 60 else ""
            )
            
            # Requests
            total_req = summary['requests']['total']
            success_req = summary['requests']['successful']
            failed_req = summary['requests']['failed']
            table.add_row(
                "Total Requests",
                f"{total_req:,}",
                f"✓ {success_req:,} success, ✗ {failed_req:,} failed" if failed_req > 0 else f"✓ All successful"
            )
            
            # Success rate
            success_rate = summary['requests']['success_rate']
            rate_style = "green" if success_rate >= 95 else "yellow" if success_rate >= 80 else "red"
            table.add_row(
                "Success Rate",
                f"[{rate_style}]{success_rate:.1f}%[/{rate_style}]",
                ""
            )
            
            # Throughput
            rps = summary['requests']['requests_per_second']
            table.add_row(
                "Throughput",
                f"{rps:.2f} req/s",
                ""
            )
            
            # Response times
            avg_time = summary['performance']['avg_response_time']
            min_time = summary['performance']['min_response_time']
            max_time = summary['performance']['max_response_time']
            table.add_row(
                "Response Times",
                f"{avg_time:.3f}s avg",
                f"min: {min_time:.3f}s, max: {max_time:.3f}s"
            )
            
            # Data transfer
            mb_down = summary['data']['mb_downloaded']
            table.add_row(
                "Data Downloaded",
                f"{mb_down:.2f} MB",
                f"({summary['data']['bytes_downloaded']:,} bytes)"
            )
            
            # Discoveries
            files = summary['discoveries']['files_found']
            fp = summary['discoveries']['false_positives']
            fp_rate = summary['discoveries']['false_positive_rate']
            files_text = f"{files:,}"
            if fp > 0:
                files_text = f"[yellow]{files:,}[/yellow]"
            table.add_row(
                "Files Found",
                files_text,
                f"[dim]{fp} false positives ({fp_rate:.1f}%)[/dim]" if fp > 0 else "[green]✓ No false positives[/green]"
            )
            
            # Errors (if any)
            timeout_err = summary['errors']['timeout']
            conn_err = summary['errors']['connection']
            if timeout_err > 0 or conn_err > 0:
                table.add_row(
                    "[red]Errors[/red]",
                    f"[red]{timeout_err + conn_err}[/red]",
                    f"[dim]{timeout_err} timeouts, {conn_err} connection errors[/dim]"
                )
            
            # Status codes breakdown (if interesting)
            if len(summary['status_codes']) > 1:
                status_text = ", ".join([f"{code}: {count}" for code, count in sorted(summary['status_codes'].items())])
                table.add_row(
                    "Status Codes",
                    f"{len(summary['status_codes'])} types",
                    f"[dim]{status_text}[/dim]"
                )
            
            # Print without panel (just title and table)
            console.print()
            console.print("Performance Metrics:")
            console.print(table)
            
        else:
            print("\n" + "="*60)
            print("Performance Metrics".center(60))
            print("="*60)
            print(f"Scan Duration:       {summary['timing']['duration']:.2f}s")
            print(f"Total Requests:      {summary['requests']['total']:,}")
            print(f"Success Rate:        {summary['requests']['success_rate']:.1f}%")
            print(f"Throughput:          {summary['requests']['requests_per_second']:.2f} req/s")
            print(f"Avg Response Time:   {summary['performance']['avg_response_time']:.3f}s")
            print(f"Data Downloaded:     {summary['data']['mb_downloaded']:.2f} MB")
            print(f"Files Found:         {summary['discoveries']['files_found']}")
            
            if summary['discoveries']['false_positives'] > 0:
                print(f"False Positives:     {summary['discoveries']['false_positives']} ({summary['discoveries']['false_positive_rate']:.1f}%)")
            
            if summary['errors']['timeout'] > 0 or summary['errors']['connection'] > 0:
                print(f"Errors:              {summary['errors']['timeout']} timeouts, {summary['errors']['connection']} connection errors")
            print("="*60)
