"""
Enhanced HTTP request handler for LeftOvers.
"""

import time
import random
from typing import Dict, Any, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning

from leftovers.app_settings import DEFAULT_TIMEOUT, USER_AGENTS, MAX_FILE_SIZE_MB
from leftovers.utils.logger import logger

class MemoryEfficientHttpHandler:
    """
    Memory efficient HTTP handler that manages connections and streaming responses.
    """
    
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        verify_ssl: bool = True,
        headers: Dict[str, str] = None,
        max_file_size_mb: int = MAX_FILE_SIZE_MB,
        rotate_user_agent: bool = False,
        verbose: bool = False
    ):
        """Initialize the HTTP handler with the given parameters."""
        # Store configuration
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.headers = headers or {}
        self.max_file_size_mb = max_file_size_mb
        self.rotate_user_agent = rotate_user_agent
        self.verbose = verbose
        self.session = None
        self.is_session_created = False
        
        # Suppress only the single InsecureRequestWarning
        if not verify_ssl:
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    
    def _get_session(self) -> requests.Session:
        """
        Get or create an HTTP session with retry logic.
        
        Returns:
            Configured requests session
        """
        # Create session only once to reuse connections
        if not self.session:
            self.session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=2,  # Maximum number of retries
                backoff_factor=0.5,  # Time factor between retries
                status_forcelist=[429, 500, 502, 503, 504],  # Status codes to retry on
                allowed_methods=["GET", "HEAD"]  # HTTP methods to retry
            )
            
            # Apply retry strategy with connection pooling
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=100)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # Set default headers
            self.session.headers.update(self.headers)
            
            self.is_session_created = True
            
        return self.session
    
    def get(
        self, 
        url: str, 
        params: Dict[str, str] = None, 
        headers: Dict[str, str] = None,
        stream: bool = True
    ) -> Dict[str, Any]:
        """
        Perform a GET request with memory efficient streaming.
        
        Args:
            url: The URL to request
            params: URL parameters
            headers: Additional headers to merge with default headers
            stream: Whether to stream the response
            
        Returns:
            Dictionary with request results
        """
        session = self._get_session()
        combined_headers = self.headers.copy()
        
        # Rotate User-Agent if enabled
        if self.rotate_user_agent and USER_AGENTS:
            user_agent = random.choice(USER_AGENTS)
            combined_headers["User-Agent"] = user_agent
            
        # Merge with request-specific headers
        if headers:
            combined_headers.update(headers)
            
        start_time = time.time()
        response = None
        
        try:
            # Make request with streaming enabled for memory efficiency
            response = session.get(
                url,
                params=params,
                headers=combined_headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                stream=stream
            )
            
            elapsed_time = time.time() - start_time
            
            # Check for large files using headers before downloading content
            content_length = int(response.headers.get('Content-Length', 0))
            download_full_content = True
            
            # For large files, only download partial content
            if content_length > (self.max_file_size_mb * 1024 * 1024):
                if self.verbose:
                    logger.debug(f"Large file detected: {url} ({content_length/(1024*1024):.2f} MB)")
                
                # Only read the first chunk for analysis
                content = self._read_partial_content(response, 32768)  # 32KB sample
                download_full_content = False
            else:
                if stream:
                    # For normal files, read all content but in a memory-efficient way
                    content = self._read_streamed_content(response)
                else:
                    # If streaming disabled, use normal content access
                    content = response.content
                    
            return {
                "success": True,
                "url": url,
                "content": content,
                "response": response,
                "time": elapsed_time,
                "download_full": download_full_content,
                "content_length": content_length or len(content) if content else 0,
                "status_code": response.status_code
            }
            
        except requests.RequestException as e:
            elapsed_time = time.time() - start_time
            
            if self.verbose:
                logger.debug(f"Request failed: {url} - {str(e)}")
                
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "time": elapsed_time,
                "response": response,
                "status_code": response.status_code if response else 0
            }
    
    def _read_streamed_content(self, response: requests.Response, chunk_size: int = 8192) -> bytes:
        """
        Read streamed response content in chunks to minimize memory usage.
        
        Args:
            response: Response object to read from
            chunk_size: Size of chunks to read
            
        Returns:
            Complete response content as bytes
        """
        content = b''
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                content += chunk
        return content
    
    def _read_partial_content(self, response: requests.Response, max_size: int = 32768) -> bytes:
        """
        Read only partial content from a large file.
        
        Args:
            response: Response object to read from
            max_size: Maximum bytes to read
            
        Returns:
            Partial content as bytes
        """
        content = b''
        bytes_read = 0
        
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                content += chunk
                bytes_read += len(chunk)
                if bytes_read >= max_size:
                    break
                    
        # Ensure response is closed to free resources
        response.close()
        
        return content
    
    def head(self, url: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Perform a HEAD request to check resource existence and metadata.
        
        Args:
            url: The URL to request
            headers: Additional headers
            
        Returns:
            Dictionary with request results
        """
        session = self._get_session()
        combined_headers = self.headers.copy()
        
        if headers:
            combined_headers.update(headers)
            
        start_time = time.time()
        response = None
        
        try:
            response = session.head(
                url,
                headers=combined_headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            elapsed_time = time.time() - start_time
            
            return {
                "success": True,
                "url": url,
                "response": response,
                "time": elapsed_time,
                "status_code": response.status_code
            }
            
        except requests.RequestException as e:
            elapsed_time = time.time() - start_time
            
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "time": elapsed_time,
                "response": response,
                "status_code": response.status_code if response else 0
            }
    
    def close(self):
        """Close the session and free resources."""
        if self.session:
            self.session.close()
            self.session = None
            self.is_session_created = False
