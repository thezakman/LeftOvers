"""
File utilities for the LeftOvers scanner.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any

from typing import IO
from leftovers.utils.logger import logger

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

def create_autosave_file(directory: str = "leftovers") -> str:
    """
    Create the autosave directory and return a timestamped JSONL file path.
    The file is created immediately so the path is valid from the start.

    Args:
        directory: Directory to create autosave files in

    Returns:
        Absolute path to the autosave file
    """
    os.makedirs(directory, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(directory, f"{timestamp}.jsonl")
    # Touch the file so it exists even if no hits are found
    open(path, 'a', encoding='utf-8').close()
    return path


def append_result_to_jsonl(file_handle, result: Any) -> None:
    """
    Append a single scan result as a JSON line to an open file handle.
    Caller must hold any necessary locks.

    Args:
        file_handle: Open file handle (append mode)
        result: ScanResult or dict to serialize
    """
    try:
        if hasattr(result, 'to_dict'):
            data = result.to_dict()
        elif isinstance(result, dict):
            data = result
        else:
            return
        file_handle.write(json.dumps(data, ensure_ascii=False) + "\n")
        file_handle.flush()
    except Exception:
        pass  # Never crash the scan due to autosave issues


def load_autosave(file_path: str) -> List[Any]:
    """
    Load scan results from a JSONL autosave file.

    Args:
        file_path: Path to the .jsonl file

    Returns:
        List of ScanResult objects
    """
    from leftovers.core.result import ScanResult

    if not os.path.isfile(file_path):
        logger.error(f"Autosave file not found: {file_path}")
        return []

    results = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    results.append(ScanResult.from_dict(data))
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Skipping malformed line {lineno} in {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error reading autosave file: {e}")
        return []

    return results


def export_results(results: List[Any], output_file: str) -> bool:
    """
    Export scan results to a JSON file.
    
    Args:
        results: List of results to export
        output_file: Path to output file
        
    Returns:
        Boolean indicating if export was successful
    """
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
