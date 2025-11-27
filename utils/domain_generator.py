"""
Dynamic domain-based wordlist generator.
Integrates with existing LeftOvers structure and extensions.
"""

import tldextract
from typing import List, Set
from urllib.parse import urlparse

from leftovers.core.config import ARCHIVE_EXTENSIONS, BACKUP_SUFFIXES, DATABASE_EXTENSIONS


class DomainWordlistGenerator:
    """Generate intelligent domain-based wordlists for LeftOvers scanner."""

    def __init__(self):
        """Initialize with existing LeftOvers extensions."""
        # Use existing categorized extensions from config
        self.backup_extensions = ARCHIVE_EXTENSIONS + BACKUP_SUFFIXES + DATABASE_EXTENSIONS

    def generate_domain_wordlist(self, url: str) -> List[str]:
        """
        Generate intelligent domain-based wordlist for LeftOvers scanner.

        Args:
            url: Target URL to analyze

        Returns:
            List of domain-based backup file variations
        """
        domain_info = tldextract.extract(url)
        parsed = urlparse(url)

        hostname = parsed.netloc.split(':')[0]  # Remove port
        subdomain = domain_info.subdomain
        domain = domain_info.domain
        suffix = domain_info.suffix

        wordlist = set()

        # Only generate if we have sufficient domain components
        if not domain:
            return []

        # Generate base variations using advanced domain analysis
        base_variations = self._generate_domain_variations(
            hostname, subdomain, domain, suffix
        )

        # Optimize: limit variations to prevent memory issues
        # Take only the most relevant variations (first 100) and most important extensions
        limited_variations = list(base_variations)[:100]
        important_extensions = self.backup_extensions[:50]  # Limit to top 50 extensions

        # Add extensions to each variation
        for variation in limited_variations:
            for ext in important_extensions:
                wordlist.add(f"{variation}.{ext}")

        return list(wordlist)

    def _generate_domain_variations(self, hostname: str, subdomain: str,
                                   domain: str, suffix: str) -> Set[str]:
        """Generate domain variations using advanced LeftOvers algorithms."""
        variations = set()

        # Priority 1: Most common leftover patterns
        if subdomain and domain:
            variations.update([
                f"{domain}.{subdomain}",
                f"{subdomain}.{domain}",
                f"{subdomain}{domain}",
                f"{domain}{subdomain}",
                f"{subdomain}_{domain}",
                f"{domain}_{subdomain}",
            ])

        # Priority 2: Common backup patterns
        if domain:
            backup_patterns = ["backup", "bak", "old", "temp"]  # Reduced to most effective
            for pattern in backup_patterns:
                variations.update([
                    f"{pattern}{domain}",
                    f"{domain}{pattern}",
                    f"{pattern}_{domain}",
                    f"{domain}_{pattern}",
                ])

        # Priority 3: Composite subdomain permutations (most effective for leftovers)
        if subdomain and any(sep in subdomain for sep in ['-', '_']):
            variations.update(self._generate_composite_subdomain_permutations(subdomain))

        # Priority 4: Individual components
        if domain:
            variations.add(domain)
        if subdomain:
            variations.add(subdomain)

        # Remove empty variations and limit size for performance
        variations.discard('')

        return variations

    def _generate_composite_subdomain_permutations(self, subdomain: str) -> Set[str]:
        """
        Generate permutations for composite subdomains (e.g., sub-example).

        Args:
            subdomain: Composite subdomain like "sub-example"

        Returns:
            Set of permutations
        """
        variations = set()

        # Split by common separators
        separators = ['-', '_', '.']
        parts = []

        for sep in separators:
            if sep in subdomain:
                parts = subdomain.split(sep)
                break

        if len(parts) >= 2:
            first_part = parts[0]
            second_part = parts[1]

            # Permutation 1: first.second
            variations.add(f"{first_part}.{second_part}")

            # Permutation 2: first_second
            variations.add(f"{first_part}_{second_part}")

            # Permutation 3: firstsecond
            variations.add(f"{first_part}{second_part}")

            # Permutation 4: second.first
            variations.add(f"{second_part}.{first_part}")

            # Permutation 5: second_first
            variations.add(f"{second_part}_{first_part}")

            # Permutation 6: secondfirst
            variations.add(f"{second_part}{first_part}")

            # Permutation 7: first only
            variations.add(first_part)

            # Permutation 8: second only
            variations.add(second_part)

            # Additional variations with common separators
            for sep in ['-', '_', '']:
                variations.add(f"{first_part}{sep}{second_part}")
                variations.add(f"{second_part}{sep}{first_part}")

        return variations

    def enhance_existing_wordlist(self, existing_words: List[str], url: str) -> List[str]:
        """
        Enhance existing backup words with intelligent domain-specific variations.

        Args:
            existing_words: Current backup word list
            url: Target URL for domain analysis

        Returns:
            Enhanced wordlist combining existing and domain-based words
        """
        domain_variations = self.generate_domain_wordlist(url)

        # Combine with existing words, removing duplicates
        enhanced_list = list(set(existing_words + domain_variations))

        return enhanced_list

    def generate_targeted_extensions(self, url: str) -> List[str]:
        """
        Generate targeted file extensions based on domain analysis.

        Args:
            url: Target URL to analyze

        Returns:
            List of likely extension patterns for this domain
        """
        domain_info = tldextract.extract(url)
        domain = domain_info.domain.lower() if domain_info.domain else ""

        targeted_extensions = []

        # Add standard backup extensions
        targeted_extensions.extend(self.backup_extensions)

        # Domain-specific patterns
        if domain:
            # Add domain as extension (common pattern)
            targeted_extensions.append(domain)

            # Common domain-based patterns
            targeted_extensions.extend([
                f"{domain}.zip",
                f"{domain}.rar",
                f"{domain}.tar.gz",
                f"{domain}.backup",
                f"{domain}.sql",
                f"{domain}.bak",
                f"{domain}.old",
                f"backup.{domain}",
                f"www.{domain}",
                f"{domain}.www",
            ])

        return list(set(targeted_extensions))