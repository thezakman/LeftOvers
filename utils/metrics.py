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
        
        summary = self.get_summary()
        
        if use_color:
            console.print("\n[bold cyan]═══ Scan Metrics ═══[/bold cyan]")
            console.print(f"[green]Duration:[/green] {summary['timing']['duration']}s")
            console.print(f"[green]Total Requests:[/green] {summary['requests']['total']}")
            console.print(f"[green]Success Rate:[/green] {summary['requests']['success_rate']}%")
            console.print(f"[green]Requests/sec:[/green] {summary['requests']['requests_per_second']}")
            console.print(f"[green]Avg Response Time:[/green] {summary['performance']['avg_response_time']}s")
            console.print(f"[green]Data Downloaded:[/green] {summary['data']['mb_downloaded']} MB")
            console.print(f"[green]Files Found:[/green] {summary['discoveries']['files_found']}")
            
            if summary['discoveries']['false_positives'] > 0:
                console.print(f"[yellow]False Positives:[/yellow] {summary['discoveries']['false_positives']} ({summary['discoveries']['false_positive_rate']}%)")
            
            if summary['errors']['timeout'] > 0 or summary['errors']['connection'] > 0:
                console.print(f"[red]Errors:[/red] {summary['errors']['timeout']} timeouts, {summary['errors']['connection']} connection errors")
        else:
            print("\n=== Scan Metrics ===")
            print(f"Duration: {summary['timing']['duration']}s")
            print(f"Total Requests: {summary['requests']['total']}")
            print(f"Success Rate: {summary['requests']['success_rate']}%")
            print(f"Requests/sec: {summary['requests']['requests_per_second']}")
            print(f"Avg Response Time: {summary['performance']['avg_response_time']}s")
            print(f"Data Downloaded: {summary['data']['mb_downloaded']} MB")
            print(f"Files Found: {summary['discoveries']['files_found']}")
            
            if summary['discoveries']['false_positives'] > 0:
                print(f"False Positives: {summary['discoveries']['false_positives']} ({summary['discoveries']['false_positive_rate']}%)")
            
            if summary['errors']['timeout'] > 0 or summary['errors']['connection'] > 0:
                print(f"Errors: {summary['errors']['timeout']} timeouts, {summary['errors']['connection']} connection errors")
