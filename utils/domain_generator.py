"""
Dynamic domain-based wordlist generator.
Integrates with existing LeftOvers structure and extensions.
"""

import re
import tldextract
from typing import List, Set
from urllib.parse import urlparse

from leftovers.core.config import ARCHIVE_EXTENSIONS, BACKUP_SUFFIXES, DATABASE_EXTENSIONS


class DomainWordlistGenerator:
    """Generate intelligent domain-based wordlists for LeftOvers scanner."""

    def __init__(self):
        """Initialize with existing LeftOvers extensions."""
        # Use existing categorized extensions from config, but drop pseudo
        # "extensions" that don't form a real filename when appended as
        # ``name.ext`` — BACKUP_SUFFIXES contains "~" and ".~", which produced
        # garbage words like "domain.~" / "domain..~". Dedup while we're at it.
        _raw = ARCHIVE_EXTENSIONS + BACKUP_SUFFIXES + DATABASE_EXTENSIONS
        self.backup_extensions = list(dict.fromkeys(
            e for e in _raw if e and e != '~' and not e.startswith('.')
        ))

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

        # Optimize: limit variations to prevent memory issues. Use the full
        # (already deduped/filtered) extension set so compound DB dumps like
        # sql.gz / db.gz aren't silently dropped by an arbitrary slice.
        limited_variations = list(base_variations)[:100]

        # Add extensions to each variation
        for variation in limited_variations:
            for ext in self.backup_extensions:
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
                f"{subdomain}-{domain}",
                f"{domain}-{subdomain}",
            ])

        # Priority 2: Common backup patterns (dot, underscore, and hyphen separators)
        if domain:
            backup_patterns = ["backup", "bak", "old", "temp"]
            for pattern in backup_patterns:
                variations.update([
                    f"{pattern}{domain}",
                    f"{domain}{pattern}",
                    f"{pattern}_{domain}",
                    f"{domain}_{pattern}",
                    f"{pattern}-{domain}",
                    f"{domain}-{pattern}",
                ])

        # Priority 2b: Year and version suffix combos with domain
        if domain:
            import datetime
            current_year = datetime.datetime.now().year
            for year in range(current_year - 2, current_year + 1):
                variations.update([
                    f"{domain}_{year}",
                    f"{domain}-{year}",
                    f"{domain}{year}",
                ])
            for v in range(1, 4):
                variations.update([
                    f"{domain}_v{v}",
                    f"{domain}-v{v}",
                    f"{domain}v{v}",
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

        # Split on ALL common separators at once so "dev-banco_honda" yields
        # ["dev", "banco", "honda"] (the old code split on the first separator
        # only and used just the first two parts, dropping the rest).
        parts = [p for p in re.split(r'[-._]+', subdomain) if p]
        if len(parts) < 2:
            return variations

        # Each individual token is a useful candidate on its own.
        variations.update(parts)

        # Full-sequence joins (and reversed) with each separator / concatenation.
        for sep in ('.', '_', '-', ''):
            variations.add(sep.join(parts))
            variations.add(sep.join(reversed(parts)))

        # Adjacent pairwise combinations cover the common two-token intent for
        # subdomains with 3+ parts without a full combinatorial blowup.
        for i in range(len(parts) - 1):
            a, b = parts[i], parts[i + 1]
            for sep in ('.', '_', ''):
                variations.add(f"{a}{sep}{b}")
                variations.add(f"{b}{sep}{a}")

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

        # Combine with existing words, removing duplicates while PRESERVING
        # order (existing curated words first). list(set(...)) scrambled the
        # priority ordering non-deterministically on every run.
        return list(dict.fromkeys(existing_words + domain_variations))