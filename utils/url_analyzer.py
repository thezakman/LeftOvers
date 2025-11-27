#!/usr/bin/env python3
"""
Advanced URL analyzer for identifying patterns and extracting useful segments.
"""

import sys
import re
import urllib.parse
import tldextract
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
from leftovers.utils.logger import logger

def analyze_url(url: str) -> Dict[str, Any]:
    """
    Perform detailed analysis on a URL to extract useful components and patterns.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Dictionary with URL analysis results
    """
    # Parse the URL
    parsed = urlparse(url)
    
    # Extract domain information using tldextract
    ext = tldextract.extract(url)
    
    # Path components
    path = parsed.path.strip('/')
    path_segments = path.split('/') if path else []
    
    # File name and extension
    filename = ""
    extension = ""
    if path_segments and '.' in path_segments[-1]:
        filename = path_segments[-1]
        parts = filename.split('.')
        if len(parts) > 1:
            extension = parts[-1].lower()
    
    # Query parameters
    query_params = {}
    if parsed.query:
        for param in parsed.query.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                query_params[key] = value
            else:
                query_params[param] = ''
    
    # Base URL (without query params or fragments)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Path hierarchy for recursive testing
    path_hierarchy = []
    current_path = ""
    for segment in path_segments:
        if current_path:
            current_path = f"{current_path}/{segment}"
        else:
            current_path = segment
        path_hierarchy.append({
            "segment": segment,
            "path": current_path,
            "url": f"{base_url}/{current_path}"
        })
    
    # Detect common patterns
    patterns = _detect_patterns(url, parsed, path_segments, filename)
    
    # Identify interesting segments
    interesting_segments = _identify_interesting_segments(path_segments)
    
    return {
        "original_url": url,
        "scheme": parsed.scheme,
        "netloc": parsed.netloc,
        "domain": ext.domain,
        "subdomain": ext.subdomain,
        "suffix": ext.suffix,
        "registered_domain": ext.registered_domain,
        "path": parsed.path,
        "query": parsed.query,
        "fragment": parsed.fragment,
        "base_url": base_url,
        "path_segments": path_segments,
        "path_hierarchy": path_hierarchy,
        "filename": filename,
        "extension": extension,
        "query_params": query_params,
        "patterns": patterns,
        "interesting_segments": interesting_segments
    }

def _detect_patterns(url: str, parsed: urllib.parse.ParseResult, 
                   path_segments: List[str], filename: str) -> Dict[str, Any]:
    """
    Detect common URL patterns for targeted testing.
    
    Args:
        url: The original URL
        parsed: Parsed URL components
        path_segments: List of path segments
        filename: Filename extracted from the URL
        
    Returns:
        Dictionary of detected patterns
    """
    patterns = {
        "is_api": False,
        "is_asset": False,
        "is_admin": False,
        "is_auth": False,
        "is_cms": False,
        "is_static": False,
        "is_numeric_id": False,
        "is_date_based": False,
        "is_file_storage": False,
        "content_type_hints": []
    }
    
    # Check if URL appears to be an API
    api_indicators = ['api', 'rest', 'graphql', 'v1', 'v2', 'v3', 'service', 'services']
    if any(segment.lower() in api_indicators for segment in path_segments):
        patterns["is_api"] = True
    
    # Check for asset/static content
    asset_paths = ['assets', 'static', 'media', 'uploads', 'files', 'images', 'css', 'js']
    if any(segment.lower() in asset_paths for segment in path_segments):
        patterns["is_asset"] = True
        
    # Look for static content based on extension
    static_extensions = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'css', 'js', 'woff', 'ttf']
    if filename and '.' in filename and filename.split('.')[-1].lower() in static_extensions:
        patterns["is_static"] = True
        
    # Check for admin or dashboard URLs
    admin_indicators = ['admin', 'dashboard', 'painel', 'manage', 'management', 'control', 'adm']
    if any(segment.lower() in admin_indicators for segment in path_segments):
        patterns["is_admin"] = True
        
    # Detect authentication related URLs
    auth_indicators = ['login', 'logout', 'auth', 'senha', 'password', 'signup', 'signin', 'register']
    if any(segment.lower() in auth_indicators for segment in path_segments):
        patterns["is_auth"] = True
        
    # Detect CMS indicators
    cms_indicators = ['wp-', 'wordpress', 'joomla', 'drupal', 'moodle', 'typo3', 'magento']
    if any(indicator in url.lower() for indicator in cms_indicators):
        patterns["is_cms"] = True
        
    # Check for numeric IDs in path (common in web apps)
    if any(segment.isdigit() for segment in path_segments):
        patterns["is_numeric_id"] = True
        
    # Check for date-based URLs (common in blogs, news sites)
    date_pattern = re.compile(r'^(19|20)\d{2}[/-]?(0?[1-9]|1[0-2])[/-]?(0?[1-9]|[12]\d|3[01])$')
    if any(date_pattern.match(segment) for segment in path_segments):
        patterns["is_date_based"] = True
        
    # Detect potential file storage URLs
    storage_indicators = ['storage', 'upload', 'uploads', 'files', 'docs', 'documents']
    if any(segment.lower() in storage_indicators for segment in path_segments):
        patterns["is_file_storage"] = True
        
    # Get content type hints based on extension
    if filename:
        extension = filename.split('.')[-1].lower() if '.' in filename else ''
        if extension:
            content_type = _get_content_type_hint(extension)
            if content_type:
                patterns["content_type_hints"].append(content_type)
    
    return patterns

def _identify_interesting_segments(path_segments: List[str]) -> List[Dict[str, Any]]:
    """
    Identify segments in the URL path that might be interesting for testing.
    
    Args:
        path_segments: List of path segments
        
    Returns:
        List of dictionaries with interesting segment information
    """
    interesting_segments = []
    
    for i, segment in enumerate(path_segments):
        segment_info = {
            "segment": segment,
            "position": i,
            "interesting_factor": 0,
            "reasons": []
        }
        
        # Check for IDs (purely numeric segments are often IDs)
        if segment.isdigit():
            segment_info["interesting_factor"] += 1
            segment_info["reasons"].append("numeric_id")
            
        # Check for UUIDs
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        if uuid_pattern.match(segment.lower()):
            segment_info["interesting_factor"] += 2
            segment_info["reasons"].append("uuid")
            
        # Check for potentially sensitive names
        sensitive_keywords = ['private', 'secure', 'admin', 'confidential', 'restricted', 'internal']
        if any(keyword in segment.lower() for keyword in sensitive_keywords):
            segment_info["interesting_factor"] += 3
            segment_info["reasons"].append("sensitive_name")
            
        # Check for version indicators
        version_pattern = re.compile(r'^v\d+$|^v\d+\.\d+$|^\d+\.\d+\.\d+$')
        if version_pattern.match(segment.lower()):
            segment_info["interesting_factor"] += 1
            segment_info["reasons"].append("version_indicator")
            
        # Check for common config/data file names without extensions
        config_keywords = ['config', 'settings', 'env', 'setup', 'data']
        if any(keyword == segment.lower() for keyword in config_keywords):
            segment_info["interesting_factor"] += 2
            segment_info["reasons"].append("config_name")
        
        # Only add segments with some interesting factors
        if segment_info["interesting_factor"] > 0:
            interesting_segments.append(segment_info)
    
    return interesting_segments

def _get_content_type_hint(extension: str) -> Optional[str]:
    """
    Get content type hint based on file extension.
    
    Args:
        extension: File extension
        
    Returns:
        Content type string or None
    """
    # Common extension to content type mappings
    content_types = {
        # Documents
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        
        # Text files
        'txt': 'text/plain',
        'csv': 'text/csv',
        'json': 'application/json',
        'xml': 'application/xml',
        'yaml': 'application/yaml',
        'yml': 'application/yaml',
        'md': 'text/markdown',
        
        # Web files
        'html': 'text/html',
        'htm': 'text/html',
        'css': 'text/css',
        'js': 'application/javascript',
        
        # Image files
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        
        # Archive files
        'zip': 'application/zip',
        'tar': 'application/x-tar',
        'gz': 'application/gzip',
        'rar': 'application/vnd.rar',
        '7z': 'application/x-7z-compressed',
        
        # Audio/Video files
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        
        # Executable & script files
        'exe': 'application/x-msdownload',
        'dll': 'application/x-msdownload',
        'sh': 'application/x-sh',
        'bat': 'application/x-bat',
        'py': 'text/x-python',
        'php': 'application/x-httpd-php',
        'rb': 'text/x-ruby',
        'java': 'text/x-java-source',
        
        # Data files
        'sql': 'application/sql',
        'db': 'application/octet-stream',
        'sqlite': 'application/x-sqlite3',
        'bak': 'application/octet-stream'
    }
    
    return content_types.get(extension.lower())

def generate_path_variants(path: str) -> List[str]:
    """
    Generate useful variants of a path for testing.
    
    Args:
        path: Original path
        
    Returns:
        List of path variants
    """
    variants = []
    path = path.rstrip('/')
    
    # Add base path
    variants.append(path)
    
    # Add with trailing slash
    if not path.endswith('/'):
        variants.append(f"{path}/")
        
    # Handle index.* files
    if path.endswith(('index.html', 'index.php', 'index.jsp')):
        variants.append(path.rsplit('/', 1)[0] + '/')
        
    # Path without extension
    if '.' in path and '/' in path:
        base_path = path[:path.rindex('.')]
        variants.append(base_path)
    
    return variants

def create_url_permutations(url: str, extensions: List[str] = None) -> Tuple[List[str], bool]:
    """
    Create permutations of a URL with different extensions.
    
    Args:
        url: Base URL
        extensions: List of extensions to test
        
    Returns:
        Tuple of (list of URLs to test, is_original_file_url)
    """
    if not extensions:
        extensions = []
        
    # Parse the URL    
    parsed = urlparse(url)
    path = parsed.path
    
    # Check if URL already points to a file
    is_file_url = bool(path and '.' in path.split('/')[-1])
    base_name = ""
    
    urls_to_test = []
    
    if is_file_url:
        # Get the base name without extension
        file_name = path.split('/')[-1]
        if '.' in file_name:
            base_name = path[:path.rindex('.')]
            
        # Test with different extensions
        for ext in extensions:
            new_path = f"{base_name}.{ext}"
            new_url = urljoin(url, new_path)
            urls_to_test.append(new_url)
    else:
        # If it's a directory URL, test for index files
        for ext in extensions:
            # Test for both root and index files
            if path.endswith('/') or not path:
                new_path = f"{path}index.{ext}"
            else:
                # URL might be a file without extension
                new_path = f"{path}.{ext}"
            
            new_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", new_path)
            urls_to_test.append(new_url)
    
    return urls_to_test, is_file_url

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python url_analyzer.py URL [URL...]")
        sys.exit(1)
    
    urls = sys.argv[1:]
    for url in urls:
        try:
            analysis = analyze_url(url)
            print(f"Analysis for {url}:")
            print(analysis)
        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {str(e)}")
