"""
Classes for storing and processing scan results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

from leftovers.app_settings import IGNORE_CONTENT

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
    large_file: bool = False
    partial_content: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

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

    def check_ignored_content_type(self) -> bool:
        """
        Check if the content type is in the list of ignored types.
        
        Returns:
            bool: True if content type should be ignored
        """
        if not IGNORE_CONTENT:
            return False
            
        if not self.content_type:
            return False
            
        # Many servers include additional parameters in Content-Type
        # like charset=utf-8, so we extract only the main part
        content_type_base = self.content_type.split(';')[0].strip()
        
        for ignored_type in IGNORE_CONTENT:
            # Exact or "startswith" check for types like application/json vs application/json+ld
            if content_type_base == ignored_type or content_type_base.startswith(f"{ignored_type}+"):
                return True
                
        return False
        
    def mark_as_false_positive(self, reason: str) -> None:
        """Mark a result as false positive with a reason."""
        self.false_positive = True
        self.false_positive_reason = reason

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanResult':
        """Reconstruct a ScanResult from a dictionary (e.g. loaded from JSONL)."""
        ts = data.get("timestamp")
        if isinstance(ts, str):
            try:
                from datetime import datetime as _dt
                ts = _dt.fromisoformat(ts)
            except ValueError:
                ts = datetime.now()
        elif not isinstance(ts, datetime):
            ts = datetime.now()
        return cls(
            url=data.get("url", ""),
            status_code=data.get("status_code", 0),
            content_type=data.get("content_type", ""),
            content_length=data.get("content_length", 0),
            response_time=data.get("response_time", 0.0),
            test_type=data.get("test_type", ""),
            extension=data.get("extension", ""),
            content_hash=data.get("content_hash", ""),
            false_positive=data.get("false_positive", False),
            false_positive_reason=data.get("false_positive_reason", ""),
            large_file=data.get("large_file", False),
            partial_content=data.get("partial_content", False),
            timestamp=ts,
        )
