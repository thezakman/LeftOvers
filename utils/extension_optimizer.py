"""
Extension optimization and prioritization for LeftOvers scanner.
"""

from typing import List, Dict
from urllib.parse import urlparse

from leftovers.core.config import (
    ARCHIVE_EXTENSIONS, BACKUP_SUFFIXES, DATABASE_EXTENSIONS,
    CONFIG_LOG_EXTENSIONS, DOCUMENT_BACKUP_EXTENSIONS, CODE_BACKUP_EXTENSIONS
)


class ExtensionOptimizer:
    """Optimize and prioritize extensions based on target analysis."""

    def __init__(self):
        """Initialize with extension categories."""
        self.high_priority = ARCHIVE_EXTENSIONS + BACKUP_SUFFIXES + DATABASE_EXTENSIONS
        self.medium_priority = CONFIG_LOG_EXTENSIONS + DOCUMENT_BACKUP_EXTENSIONS
        self.low_priority = CODE_BACKUP_EXTENSIONS

    def optimize_extensions(self, extensions: List[str], target_url: str) -> List[str]:
        """
        Optimize and reorder extensions based on target analysis.

        Args:
            extensions: Current extension list
            target_url: Target URL for analysis

        Returns:
            Optimized extension list with high-priority extensions first
        """
        if not extensions:
            return extensions

        # Analyze target for context clues
        context = self._analyze_target_context(target_url)

        # Create priority groups
        high_priority_exts = []
        medium_priority_exts = []
        low_priority_exts = []
        unknown_exts = []

        for ext in extensions:
            if ext in self.high_priority:
                high_priority_exts.append(ext)
            elif ext in self.medium_priority:
                medium_priority_exts.append(ext)
            elif ext in self.low_priority:
                low_priority_exts.append(ext)
            else:
                unknown_exts.append(ext)

        # Apply context-based reordering
        if context.get('likely_backup_site'):
            # Prioritize backup and archive extensions
            optimized = (
                self._sort_by_backup_likelihood(high_priority_exts) +
                medium_priority_exts +
                unknown_exts +
                low_priority_exts
            )
        elif context.get('likely_development'):
            # Prioritize config and text files
            optimized = (
                medium_priority_exts +
                high_priority_exts +
                unknown_exts +
                low_priority_exts
            )
        else:
            # Default ordering: high -> medium -> unknown -> low
            optimized = (
                high_priority_exts +
                medium_priority_exts +
                unknown_exts +
                low_priority_exts
            )

        return optimized

    def _analyze_target_context(self, target_url: str) -> Dict[str, bool]:
        """Analyze target URL for context clues that reorder extensions."""
        context = {
            'likely_backup_site': False,
            'likely_development': False,
        }

        parsed = urlparse(target_url)
        hostname = parsed.netloc.lower()
        path = parsed.path.lower()

        # Check for backup-related keywords
        backup_indicators = [
            'backup', 'bkp', 'archive', 'old', 'temp', 'tmp',
            'staging', 'test', 'dev', 'development'
        ]

        if any(indicator in hostname or indicator in path for indicator in backup_indicators):
            context['likely_backup_site'] = True

        # Check for development indicators
        dev_indicators = [
            'dev', 'test', 'staging', 'beta', 'alpha',
            'demo', 'sandbox', 'lab', 'experimental'
        ]

        if any(indicator in hostname for indicator in dev_indicators):
            context['likely_development'] = True

        return context

    def _sort_by_backup_likelihood(self, extensions: List[str]) -> List[str]:
        """Sort extensions by their likelihood of containing backups."""
        # Define backup extension priority
        backup_priority = {
            'sql': 10, 'dump': 10, 'db': 10,
            'zip': 9, 'rar': 9, 'tar.gz': 9, '7z': 9,
            'bak': 8, 'backup': 8, 'old': 8,
            'tar': 7, 'gz': 7, 'bz2': 7,
            'tmp': 6, 'temp': 6, 'save': 6
        }

        return sorted(extensions, key=lambda x: backup_priority.get(x, 0), reverse=True)