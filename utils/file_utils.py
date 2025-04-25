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

def export_results(results: List[Any], output_file: str) -> bool:
    """
    Export scan results to a file in JSON format.
    
    Args:
        results: List of ScanResult objects
        output_file: Path to the output file
        
    Returns:
        Boolean indicating if export was successful
    """
    try:
        # Convert results to dictionaries
        result_dicts = [result.to_dict() for result in results]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_dicts, f, indent=2)
            
        logger.info(f"Results exported to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error exporting results: {str(e)}")
        return False
