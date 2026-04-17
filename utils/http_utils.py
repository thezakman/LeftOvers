"""
HTTP client and URL processing utilities for LeftOvers scanner.
"""

import hashlib
import random
import time
import threading
from urllib.parse import urlparse
from typing import Dict, Optional, Any, Tuple
from collections import OrderedDict

import requests
import tldextract
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from leftovers.utils.logger import logger
from leftovers.app_settings import USER_AGENTS, CHUNK_SIZE, MAX_FILE_SIZE_MB, VERIFY_SSL

# Suppress only the InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache implementation.

    More efficient than FIFO as it keeps frequently accessed items in cache longer.
    Uses OrderedDict for O(1) operations.
    """

    def __init__(self, max_size: int = 128):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items to keep in cache
        """
        self.max_size = max_size
        self.cache = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get item from cache and mark as recently used.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        with self._lock:
            if key in self.cache:
                # Move to end to mark as recently used
                self.cache.move_to_end(key)
                return self.cache[key]
            return None

    def put(self, key: str, value: Dict[str, Any]) -> None:
        """
        Add item to cache. Removes least recently used if cache is full.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            if key in self.cache:
                # Update existing item and mark as recently used
                self.cache.move_to_end(key)
            elif len(self.cache) >= self.max_size:
                # Remove least recently used item (first item)
                self.cache.popitem(last=False)

            self.cache[key] = value

    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self.cache.clear()

    def __len__(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self.cache)

    def __contains__(self, key: str) -> bool:
        """Check if key is in cache."""
        with self._lock:
            return key in self.cache

def calculate_content_hash(content: bytes) -> str:
    """
    Calculate a hash of content bytes for comparison.
    
    Args:
        content: Bytes to hash
        
    Returns:
        Hash as hex string
    """
    if not content:
        return ""
        
    # For large content, only hash the first and last parts to save CPU
    if len(content) > 1024 * 100:  # 100KB
        return hashlib.md5(content[:4096] + content[-4096:]).hexdigest()
    
    # For smaller content, hash everything
    return hashlib.md5(content).hexdigest()

class HttpClient:
    """HTTP client for making requests with proper error handling and metrics."""

    def __init__(self,
                 headers: Dict[str, str] = None,
                 timeout: int = 5,
                 verify_ssl: bool = VERIFY_SSL,  # Use global setting as default
                 rotate_user_agent: bool = False,
                 max_retries: int = 1,
                 backoff_factor: float = 0.5,
                 use_cache: bool = True,
                 max_cache_size: int = 128,
                 rate_limit: float = None,
                 delay_ms: int = None):
        """
        Initialize the HTTP client with enhanced performance options.

        Args:
            headers: Dictionary of custom headers
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates (defaults to global setting)
            rotate_user_agent: Whether to rotate User-Agents randomly
            max_retries: Maximum number of retries for failed requests
            backoff_factor: Exponential backoff factor between retries
            use_cache: Whether to use request caching
            max_cache_size: Maximum number of responses to cache
            rate_limit: Maximum requests per second (e.g., 10.0 for 10 req/s)
            delay_ms: Fixed delay in milliseconds between requests
        """
        self.headers = headers or {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl  # This will now default to False based on the global setting
        self.rotate_user_agent = rotate_user_agent
        self.use_cache = use_cache

        # Rate limiting setup
        self.rate_limit = rate_limit
        self.delay_ms = delay_ms
        self._last_request_time = 0
        self._rate_limit_lock = threading.Lock()

        # Calculate minimum delay between requests based on rate_limit
        if rate_limit:
            self._min_request_interval = 1.0 / rate_limit  # seconds
        elif delay_ms:
            self._min_request_interval = delay_ms / 1000.0  # convert ms to seconds
        else:
            self._min_request_interval = 0
        
        # Optimized connection management
        self.session = self._create_optimized_session(max_retries, backoff_factor)

        # Request cache using LRU for better performance
        self.request_cache = LRUCache(max_cache_size) if use_cache else None
        self.cache_hits = 0
        self.cache_misses = 0
        
        
        # Pre-populated set for faster lookups of known large content types
        self._large_content_types = {
            'application/pdf', 
            'application/zip', 'application/x-rar-compressed',
            'application/octet-stream',
            'application/x-msdownload',
            'application/x-executable',
            'application/vnd.ms-excel', 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'image/jpeg', 'image/png', 'image/gif', 'image/tiff',
            'video/mp4', 'video/mpeg', 'video/quicktime', 'audio/mpeg'
        }

    def _create_optimized_session(self, max_retries: int, backoff_factor: float):
        """Create an optimized requests session with connection pooling."""
        # Configure retry strategy
        retry_strategy = requests.packages.urllib3.util.Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )

        # Create adapter with optimized connection pooling
        adapter = requests.adapters.HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,  # Number of connection pools to cache
            pool_maxsize=100,     # Increased for high concurrency
            pool_block=False      # Don't block when pool is full
        )

        # Create and configure session
        session = requests.Session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self.headers)
        session.verify = self.verify_ssl

        return session

    def rotate_agent(self):
        """Rotate the User-Agent to a random one from the list."""
        if self.rotate_user_agent and USER_AGENTS:
            self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
    
    def _apply_rate_limit(self):
        """Apply rate limiting delay if configured."""
        if self._min_request_interval > 0:
            with self._rate_limit_lock:
                current_time = time.time()
                time_since_last_request = current_time - self._last_request_time

                if time_since_last_request < self._min_request_interval:
                    sleep_time = self._min_request_interval - time_since_last_request
                    time.sleep(sleep_time)

                self._last_request_time = time.time()

    def get(self, url: str,
            extra_headers: Optional[Dict[str, str]] = None,
            range_bytes: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        """Make a GET request with optimized handling and rate limiting.

        Args:
            url: URL to request.
            extra_headers: Per-request headers merged on top of session headers.
            range_bytes: Optional (start, end) byte range to request. When set,
                caching is bypassed and streaming is used to avoid buffering.

        Returns:
            Dict with success/response/error/time/large_file/partial_content.
        """
        # Apply rate limiting before making the request
        self._apply_rate_limit()

        # Ranged requests bypass the cache (different semantics, different body)
        cacheable = self.request_cache is not None and range_bytes is None

        # Always log requests in verbose mode, regardless of where called from
        # Import VERBOSE directly here to avoid circular imports
        from leftovers.app_settings import VERBOSE
        if VERBOSE:
            logger.debug(f"HTTP Request: GET {url}")

        # Check cache first if enabled
        if cacheable:
            cached = self.request_cache.get(url)
            if cached:
                self.cache_hits += 1
                if VERBOSE:
                    logger.debug(f"Cache hit for {url}")
                if cached["success"]:
                    mock_response = type('MockResponse', (), {
                        'status_code': cached["status_code"],
                        'headers': cached["headers"],
                        'content': cached.get("content", b""),
                    })()
                    return {
                        "success": True,
                        "response": mock_response,
                        "time": cached["time"],
                        "error": cached.get("error", ""),
                        "from_cache": True,
                    }
                return cached
            self.cache_misses += 1
        elif self.request_cache is not None:
            self.cache_misses += 1
        
        # Rotate User-Agent if needed
        if self.rotate_user_agent:
            self.rotate_agent()
        
        start_time = time.time()
        result = {
            "success": False,
            "response": None,
            "error": None,
            "time": 0,
            "large_file": False,
            "partial_content": False,
            "from_cache": False
        }
        
        # Caller-requested range: behave as a streaming ranged GET and skip
        # the large-file autodetect (the caller already decided).
        if range_bytes is not None:
            req_headers = {k: v for k, v in self.session.headers.items()}
            if extra_headers:
                req_headers.update(extra_headers)
            start, end = range_bytes
            req_headers['Range'] = f'bytes={start}-{end}'
            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    headers=req_headers,
                    stream=True,
                    allow_redirects=True,
                )
                # Read up to (end-start+1) bytes
                max_read = max(0, end - start + 1)
                content = b''
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    content += chunk
                    if len(content) >= max_read:
                        content = content[:max_read]
                        break
                response._content = content
                result["success"] = True
                result["response"] = response
                result["partial_content"] = True
            except requests.exceptions.Timeout:
                result["error"] = "Request timed out"
            except requests.exceptions.SSLError:
                result["error"] = "SSL verification failed"
            except requests.exceptions.ConnectionError:
                result["error"] = "Connection error"
            except requests.exceptions.RequestException as e:
                result["error"] = f"Request error: {str(e)}"
            result["time"] = time.time() - start_time
            return result

        try:
            # First check if URL might contain a large file based on extension
            likely_large_file = self._check_if_likely_large_file(url)

            # For potentially large files or unknown files, check with HEAD first
            head_response = None
            content_length = None
            content_type = None
            is_large = False

            try:
                # Use HEAD to check file size and type before downloading
                head_headers = None
                if extra_headers:
                    head_headers = {**self.session.headers, **extra_headers}
                head_response = self.session.head(
                    url,
                    timeout=max(1, self.timeout / 2),
                    allow_redirects=True,
                    headers=head_headers,
                )

                # Check size based on Content-Length header
                content_length = head_response.headers.get('Content-Length')
                content_type = head_response.headers.get('Content-Type', '')

                if content_length:
                    try:
                        size = int(content_length)
                        is_large = size > MAX_FILE_SIZE_MB * 1024 * 1024
                    except (ValueError, TypeError):
                        is_large = any(ct in content_type.lower() for ct in self._large_content_types)
                elif any(ct in content_type.lower() for ct in self._large_content_types):
                    is_large = True

                if not is_large and likely_large_file:
                    is_large = True

            except requests.exceptions.RequestException:
                # If HEAD fails, continue with normal GET
                pass

            # Handle large files - get partial content
            if is_large:
                headers = {k: v for k, v in self.session.headers.items()}
                if extra_headers:
                    headers.update(extra_headers)
                headers['Range'] = 'bytes=0-8191'

                try:
                    response = self.session.get(
                        url,
                        timeout=self.timeout,
                        headers=headers,
                        stream=True,
                        allow_redirects=True,
                    )

                    content = next(response.iter_content(CHUNK_SIZE), b'')
                    response._content = content

                    if content_length and head_response:
                        for header in ('Content-Length', 'Content-Type', 'Last-Modified', 'ETag'):
                            if header in head_response.headers and header not in response.headers:
                                response.headers[header] = head_response.headers[header]

                    result["success"] = True
                    result["response"] = response
                    result["large_file"] = True
                    result["partial_content"] = True

                except requests.exceptions.RequestException:
                    # Fallback: stream without Range header
                    try:
                        fallback_headers = {**self.session.headers, **(extra_headers or {})}
                        response = self.session.get(
                            url,
                            timeout=self.timeout,
                            stream=True,
                            allow_redirects=True,
                            headers=fallback_headers,
                        )

                        content = b''
                        max_chunks = 5
                        for idx, chunk in enumerate(response.iter_content(chunk_size=CHUNK_SIZE)):
                            content += chunk
                            if idx + 1 >= max_chunks:
                                break

                        response._content = content
                        result["success"] = True
                        result["response"] = response
                        result["large_file"] = True
                        result["partial_content"] = True

                    except requests.exceptions.RequestException as inner_e:
                        result["error"] = f"Failed to fetch partial content: {str(inner_e)}"
            else:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    headers={**self.session.headers, **extra_headers} if extra_headers else None,
                )

                result["success"] = True
                result["response"] = response

        except requests.exceptions.Timeout:
            result["error"] = "Request timed out"
        except requests.exceptions.SSLError:
            result["error"] = "SSL verification failed"
        except requests.exceptions.ConnectionError:
            result["error"] = "Connection error"
        except requests.exceptions.RequestException as e:
            result["error"] = f"Request error: {str(e)}"
        finally:
            result["time"] = time.time() - start_time

        # Cache body + status + headers so repeated GETs don't collapse FP detection.
        # Skip caching for ranged or large-file responses (different semantics).
        if cacheable and result["success"] and not result["large_file"]:
            resp = result["response"]
            try:
                content = resp.content if resp is not None else b""
            except Exception:
                content = b""
            # Guardrail: don't cache bodies above 256 KB to bound memory
            if content is not None and len(content) <= 256 * 1024:
                cached_result = {
                    "success": True,
                    "error": result.get("error", ""),
                    "time": result["time"],
                    "status_code": getattr(resp, "status_code", 0),
                    "headers": dict(getattr(resp, "headers", {})),
                    "content": content,
                }
                self.request_cache.put(url, cached_result)

        return result
    
    def _check_if_likely_large_file(self, url: str) -> bool:
        """
        Check if URL likely points to a large file based on extension.
        
        Args:
            url: URL to check
            
        Returns:
            Boolean indicating if URL likely points to a large file
        """
        # Common extensions for large files
        large_file_extensions = {
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
            # Audio/Video
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',
            '.wav', '.ogg', '.webm',
            # Archives
            '.zip', '.rar', '.tar', '.gz', '.7z', '.bz2', '.tgz',
            # Documents
            '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
            '.csv', '.odt', '.ods', '.odp',
            # Executables
            '.exe', '.dll', '.bin', '.iso', '.dmg', '.apk',
            # Database
            '.mdb', '.accdb', '.db', '.sqlite', '.bak'
        }
        
        # Check if URL ends with any of these extensions
        return any(url.lower().endswith(ext) for ext in large_file_extensions)
    
    def clear_cache(self):
        """Clear the request cache."""
        if self.request_cache:
            self.request_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0

        return {
            "enabled": bool(self.request_cache),
            "size": len(self.request_cache) if self.request_cache else 0,
            "max_size": self.request_cache.max_size if self.request_cache else 0,
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }

def parse_url(url: str) -> Tuple[str, str, str]:
    """Parse a URL into its base, domain and path components."""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    domain_info = tldextract.extract(url)
    domain = f"{domain_info.domain}.{domain_info.suffix}"
    if domain_info.subdomain:
        domain = f"{domain_info.subdomain}.{domain}"

    path = parsed.path.strip('/')
    return base_url, domain, path


def parse_url_full(url: str) -> Tuple[str, str, str, str, str, str]:
    """Like parse_url but also returns the tldextract parts so callers avoid
    a second tldextract.extract() call. Returns
    (base_url, domain, path, subdomain, domain_name, suffix)."""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    domain_info = tldextract.extract(url)
    domain_name = domain_info.domain
    suffix = domain_info.suffix
    subdomain = domain_info.subdomain
    domain = f"{domain_name}.{suffix}" if suffix else domain_name
    if subdomain:
        domain = f"{subdomain}.{domain}"

    path = parsed.path.strip('/')
    return base_url, domain, path, subdomain, domain_name, suffix


def is_domain_only(url: str) -> bool:
    """Return True if URL has no path segment beyond '/'."""
    parsed = urlparse(url)
    return not parsed.path.strip('/')
