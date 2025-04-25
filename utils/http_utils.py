"""
HTTP client utilities for the LeftOvers scanner.
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
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from utils.logger import logger
from app_settings import USER_AGENTS, CHUNK_SIZE, MAX_FILE_SIZE_MB

# Suppress only the InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def calculate_content_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of content."""
    if not content:
        return ""
    return hashlib.sha256(content).hexdigest()

class HttpClient:
    """HTTP client for making requests with configurable options."""
    
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
    
    def rotate_agent(self):
        """Rotate the User-Agent to a random one from the list."""
        if self.rotate_user_agent and USER_AGENTS:
            self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
    
    def get(self, url: str) -> Dict[str, Any]:
        """
        Make a GET request to the specified URL.
        
        Returns:
            Dictionary containing:
            - 'success': Boolean indicating if request was successful
            - 'response': Response object if successful
            - 'error': Error string if not successful 
            - 'time': Time taken in seconds
        """
        # Rotate User-Agent if needed
        if self.rotate_user_agent:
            self.rotate_agent()
        
        start_time = time.time()
        result = {
            "success": False,
            "response": None,
            "error": None,
            "time": 0
        }
        
        try:
            # Start with HEAD request to check size
            try:
                head_response = self.session.head(
                    url, 
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # Check for large files based on Content-Length header
                content_length = head_response.headers.get('Content-Length')
                if content_length and int(content_length) > MAX_FILE_SIZE_MB * 1024 * 1024:
                    # If file is too large, make a partial GET request
                    headers = self.session.headers.copy()
                    headers['Range'] = 'bytes=0-8191'  # Get first 8KB only
                    
                    response = self.session.get(
                        url, 
                        timeout=self.timeout,
                        headers=headers,
                        stream=True,
                        allow_redirects=True
                    )
                    
                    # Just read the partial content
                    content = next(response.iter_content(CHUNK_SIZE), b'')
                    
                    # Store the content in the response
                    response._content = content
                    
                    result["success"] = True
                    result["response"] = response
                    result["large_file"] = True
                    result["partial_content"] = True
                else:
                    # Normal GET request if file is not too large
                    response = self.session.get(
                        url, 
                        timeout=self.timeout,
                        allow_redirects=True
                    )
                    
                    result["success"] = True
                    result["response"] = response
            except requests.exceptions.RequestException:
                # If HEAD request fails, try normal GET
                response = self.session.get(
                    url, 
                    timeout=self.timeout,
                    allow_redirects=True
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
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        finally:
            result["time"] = time.time() - start_time
            
        return result

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
