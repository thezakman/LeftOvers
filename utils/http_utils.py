"""
HTTP utilities for LeftOvers. Handles making HTTP requests and processing URLs.
"""

import time
import random
import hashlib
import re
import os
from urllib.parse import urlparse
from typing import Dict, Optional, Any, Tuple

import requests
import tldextract
from requests.exceptions import RequestException, Timeout, ConnectionError

from utils.logger import logger
from core.config import USER_AGENTS
from app_settings import MAX_FILE_SIZE_MB, CHUNK_SIZE

class HttpClient:
    """HTTP client for making requests with various options."""
    
    def __init__(self, 
                 headers: Dict[str, str] = None, 
                 timeout: int = 5, 
                 verify_ssl: bool = True,
                 rotate_user_agent: bool = False):
        """Initialize the HTTP client."""
        self.headers = headers or {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.rotate_user_agent = rotate_user_agent
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = verify_ssl
    
    def _rotate_user_agent(self):
        """Rotate to a new random User-Agent if enabled."""
        if self.rotate_user_agent:
            new_agent = random.choice(USER_AGENTS)
            self.session.headers.update({"User-Agent": new_agent})
            logger.debug(f"Rotating User-Agent: {new_agent}")
    
    def get(self, url: str, allow_redirects: bool = False) -> Dict[str, Any]:
        """Make a GET request to the specified URL."""
        if self.rotate_user_agent:
            self._rotate_user_agent()
        
        result = {
            "success": False,
            "url": url,
            "time": 0,
            "error": None
        }
        
        try:
            start_time = time.time()
            
            # Use streams to avoid downloading large files completely
            with self.session.get(
                url, 
                timeout=self.timeout, 
                allow_redirects=allow_redirects,
                stream=True  # Enable streaming to control the download
            ) as response:
                result["response"] = response
                result["success"] = True
                
                # Check file size from Content-Length header
                content_length = int(response.headers.get('content-length', 0))
                result["content_length"] = content_length
                
                # Calculate size limit in bytes
                max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
                
                if content_length > max_size_bytes:
                    # Large file - download only initial portion for identification
                    file_size_mb = content_length / (1024 * 1024)
                    logger.warning(f"Large file detected: {url} ({file_size_mb:.2f}MB) - exceeds the limit of {MAX_FILE_SIZE_MB}MB")
                    
                    # Download only first bytes for type identification
                    content = b""
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        content += chunk
                        # Stop after getting enough data for identification
                        if len(content) >= 16 * 1024:  # 16KB is enough for identification
                            break
                    
                    result["content"] = content
                    result["large_file"] = True
                    result["partial_content"] = True
                    
                    # Terminate the connection
                    response.close()
                else:
                    # For normal files, download completely
                    result["content"] = response.content
            
            result["time"] = time.time() - start_time
            return result
            
        except Timeout:
            result["error"] = "Timeout"
            logger.debug(f"Timeout: {url}")
        except ConnectionError:
            result["error"] = "Connection Error"
            logger.debug(f"Connection error: {url}")
        except RequestException as e:
            result["error"] = str(e)
            logger.debug(f"Request error: {url} - {str(e)}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Unexpected error: {url} - {str(e)}")
        
        return result

def calculate_content_hash(content: bytes) -> str:
    """Calculate MD5 hash of content."""
    if not content:
        return ""
    return hashlib.md5(content).hexdigest()

def parse_url(url: str) -> Dict[str, Any]:
    """Parse a URL and extract its components."""
    if not url:
        return {}
        
    # Ensure URL has a scheme
    if not re.match(r'^https?://', url, re.IGNORECASE):
        url = f"http://{url}"
    
    try:
        parsed = urlparse(url)
        ext = tldextract.extract(url)
        
        # Create a dictionary with URL components
        result = {
            "scheme": parsed.scheme or "http",
            "host": parsed.netloc,
            "path": parsed.path,
            "params": parsed.params,
            "query": parsed.query,
            "fragment": parsed.fragment,
            "subdomain": ext.subdomain,
            "domain": ext.domain,
            "suffix": ext.suffix
        }
        
        # Add port if specified
        if ":" in parsed.netloc:
            host, port = parsed.netloc.split(":", 1)
            result["host"] = host
            try:
                result["port"] = int(port)
            except ValueError:
                pass
                
        # Process path into segments and detect if there's a file
        if parsed.path and parsed.path != "/":
            segments = [s for s in parsed.path.split('/') if s]
            result["path_segments"] = segments
            
            # Check if the last segment might be a file
            if segments and '.' in segments[-1]:
                filename, extension = os.path.splitext(segments[-1])
                result["filename"] = filename
                result["file_extension"] = extension.lstrip('.')
                result["is_file"] = True
            else:
                result["is_file"] = False
            
        return result
    except Exception as e:
        logger.error(f"Error parsing URL '{url}': {str(e)}")
        return {}
