"""
Classes for storing and processing scan results.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class ScanResult:
    """Class to store results of each URL test."""
    url: str
    status_code: int
    content_type: str
    content_length: int
    response_time: float
    test_type: str
    extension: str
    content_hash: str = ""
    false_positive: bool = False
    false_positive_reason: str = ""
    large_file: bool = False  # New flag for large files
    partial_content: bool = False  # New flag for partial content
    timestamp: datetime = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary for export."""
        result = {
            "url": self.url,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "content_length": self.content_length,
            "response_time": self.response_time,
            "test_type": self.test_type,
            "extension": self.extension,
            "content_hash": self.content_hash,
            "false_positive": self.false_positive,
            "false_positive_reason": self.false_positive_reason,
            "timestamp": self.timestamp.isoformat()
        }
        
        # Add information about large files when applicable
        if self.large_file:
            result["large_file"] = True
        if self.partial_content:
            result["partial_content"] = True
            
        return result
