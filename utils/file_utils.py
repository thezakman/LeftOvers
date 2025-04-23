"""
File utilities for LeftOvers. Handles loading wordlists, URL lists, and exporting results.
"""

import json
from datetime import datetime
from typing import List, Dict, Any

from utils.logger import logger
from core.config import DEFAULT_EXTENSIONS
from app_settings import VERSION

def load_wordlist(wordlist_file: str) -> List[str]:
    """Load words from a file."""
    try:
        with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
            words = [line.strip().lower() for line in f if line.strip()]
        
        if not words:
            logger.error(f"Empty wordlist: {wordlist_file}")
            return []
            
        logger.info(f"Loaded {len(words)} words from wordlist {wordlist_file}")
        return words
    except Exception as e:
        logger.error(f"Error loading wordlist: {str(e)}")
        return []

def load_url_list(url_list_file: str) -> List[str]:
    """Load URLs from a file."""
    try:
        with open(url_list_file, 'r', encoding='utf-8', errors='ignore') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
        if not urls:
            logger.error(f"Empty URL list file: {url_list_file}")
            return []
            
        logger.info(f"Loaded {len(urls)} URLs from file {url_list_file}")
        return urls
    except Exception as e:
        logger.error(f"Error loading URL list: {str(e)}")
        return []

def export_results(results: List[Any], output_file: str) -> bool:
    """Export results to a JSON file."""
    if not results:
        logger.warning("No results to export")
        return False
        
    try:
        # Convert result objects to dictionaries
        results_dicts = [r.to_dict() if hasattr(r, 'to_dict') else r for r in results]
        
        # Filter out false positives and 404s
        filtered_results = [
            r for r in results_dicts 
            if ((isinstance(r, dict) and 
                r.get('status_code', 0) != 404 and 
                not r.get('false_positive', False)) or 
               (hasattr(r, 'status_code') and 
                r.status_code != 404 and 
                not getattr(r, 'false_positive', False)))
        ]
        
        export_data = {
            "scan_info": {
                "timestamp": datetime.now().isoformat(),
                "version": VERSION,
                "total_tests": len(results),
                "interesting_findings": len(filtered_results)
            },
            "results": filtered_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Results exported to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error exporting results: {str(e)}")
        return False
