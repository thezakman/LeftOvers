"""
File utilities for the LeftOvers scanner.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any

from utils.logger import logger
from core.config import DEFAULT_EXTENSIONS
from app_settings import VERSION

def load_wordlist(file_path: str) -> List[str]:
    """
    Load a wordlist from a file, one per line.
    
    Args:
        file_path: Path to the wordlist file
        
    Returns:
        List of words
    """
    if not os.path.isfile(file_path):
        logger.error(f"Wordlist file not found: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Strip whitespace and ignore empty lines and comment lines
            return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except Exception as e:
        logger.error(f"Error loading wordlist: {str(e)}")
        return []

def load_url_list(file_path: str) -> List[str]:
    """
    Load a list of URLs from a file, one per line.
    
    Args:
        file_path: Path to the URL list file
        
    Returns:
        List of URLs
    """
    if not os.path.isfile(file_path):
        logger.error(f"URL list file not found: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Strip whitespace and ignore empty lines and comment lines
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            
            # Ensure all URLs have a scheme
            normalized_urls = []
            for url in urls:
                if not url.startswith(('http://', 'https://')):
                    url = 'http://' + url
                normalized_urls.append(url)
            
            return normalized_urls
    except Exception as e:
        logger.error(f"Error loading URL list: {str(e)}")
        return []

def format_size(size_bytes: int) -> str:
    """
    Format a size in bytes to a human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "2.5 KB", "1.2 MB")
    """
    if size_bytes is None or size_bytes == 0:
        return "0 B"
        
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    
    unit = 0
    while size_bytes >= 1024 and unit < len(units) - 1:
        size_bytes /= 1024.0
        unit += 1
    
    if unit == 0:  # bytes
        return f"{int(size_bytes)} {units[unit]}"
    else:
        return f"{size_bytes:.1f} {units[unit]}"

def export_results(results: List[Any], output_file: str) -> bool:
    """
    Export scan results to a JSON file.
    
    Args:
        results: List of results to export
        output_file: Path to output file
        
    Returns:
        Boolean indicating if export was successful
    """
    import json
    from utils.logger import logger
            
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("{\n  \"results\": [\n")
            
            for i, result in enumerate(results):
                try:
                    # Convert result to dictionary if it has a to_dict method
                    if hasattr(result, 'to_dict'):
                        result_dict = result.to_dict()
                    elif isinstance(result, dict):
                        result_dict = result
                    else:
                        result_dict = {"error": "Unable to serialize result"}
                    
                    # Convert to JSON string with indentation
                    result_json = json.dumps(result_dict, indent=4)
                    
                    # Add comma between items
                    if i > 0:
                        f.write(",\n")
                    
                    # Write the JSON string
                    f.write(result_json)
                    
                except Exception as e:
                    logger.warning(f"Error serializing result {i}: {str(e)}")
                    # Write a placeholder to keep JSON valid
                    if i > 0:
                        f.write(",\n")
                    f.write('    {"error": "Failed to serialize this result"}')
            
            # Close the array and JSON object
            f.write("\n  ]\n}")
            
        logger.info(f"Results exported to {output_file}")
        return True
        
    except PermissionError:
        logger.error(f"Permission denied when writing to {output_file}")
        return False
    except OSError as e:
        logger.error(f"File system error when writing to {output_file}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error exporting results: {str(e)}")
        return False
