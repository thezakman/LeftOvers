"""
Extension optimization and prioritization for LeftOvers scanner.
"""

from typing import List, Dict, Set
from urllib.parse import urlparse
import tldextract

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
        """Analyze target URL for context clues."""
        context = {
            'likely_backup_site': False,
            'likely_development': False,
            'likely_admin': False,
            'likely_api': False
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

        # Check for admin indicators
        admin_indicators = ['admin', 'manage', 'control', 'panel', 'dashboard']

        if any(indicator in hostname or indicator in path for indicator in admin_indicators):
            context['likely_admin'] = True

        # Check for API indicators
        api_indicators = ['api', 'service', 'webservice', 'rest', 'graphql']

        if any(indicator in hostname or indicator in path for indicator in api_indicators):
            context['likely_api'] = True

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

    def add_contextual_extensions(self, base_extensions: List[str],
                                target_url: str) -> List[str]:
        """
        Add contextual extensions based on target analysis.

        Args:
            base_extensions: Base extension list
            target_url: Target URL for analysis

        Returns:
            Extended list with contextual extensions
        """
        context = self._analyze_target_context(target_url)
        additional_extensions = set()

        # Add extensions based on context
        if context['likely_backup_site']:
            additional_extensions.update([
                'sql.gz', 'sql.bz2', 'db.gz', 'dump.gz',
                'tar.bz2', 'tar.xz', 'backup.zip'
            ])

        if context['likely_development']:
            additional_extensions.update([
                'env.backup', 'config.bak', 'settings.old',
                'local.env', 'dev.config', 'test.json'
            ])

        if context['likely_admin']:
            additional_extensions.update([
                'users.sql', 'admin.bak', 'passwords.txt',
                'credentials.json', 'keys.txt'
            ])

        if context['likely_api']:
            additional_extensions.update([
                'swagger.json', 'openapi.yaml', 'api.json',
                'endpoints.txt', 'routes.js'
            ])

        # Combine and remove duplicates
        extended_extensions = list(set(base_extensions + list(additional_extensions)))

        return self.optimize_extensions(extended_extensions, target_url)