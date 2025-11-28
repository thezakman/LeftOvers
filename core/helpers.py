"""
LeftOvers Scanner Helpers

Provides utility functions to filter and organize scanner configurations
based on priority, language, complexity level, and other criteria.
"""

from leftovers.core.config import (
    CRITICAL_BACKUP_EXTENSIONS,
    SECURITY_EXTENSIONS,
    CODE_BACKUP_EXTENSIONS,
    CONFIG_LOG_EXTENSIONS,
    DATABASE_EXTENSIONS,
    CONFIG_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    IDE_LEFTOVER_EXTENSIONS,
    VCS_LEFTOVER_EXTENSIONS,
    DOCUMENT_BACKUP_EXTENSIONS,
    BUILD_CONFIG_EXTENSIONS,
    DEFAULT_EXTENSIONS,
    DEFAULT_FILES_WORDS,
    EN_COMMON_WORDS,
    BACKUP_DIRECTORY_WORDS,
    WEB_RELATED_WORDS,
    VERSION_CONTROL_WORDS,
    DATE_VERSION_WORDS,
    PTBR_COMMON_WORDS,
    PTBR_BUSINESS_WORDS,
    PTBR_CORPORATE_WORDS,
    PTBR_TECHNICAL_WORDS,
    DEFAULT_BACKUP_WORDS,
    CRITICAL_SPECIFIC_FILES,
    SPECIFIC_FILES,
    VCS_SPECIFIC_FILES,
    BACKUP_SUFFIXES,
    DATABASE_CONFIG_WORDS,
    PTBR_TECHNICAL_WORDS,
)


def get_extensions_by_priority(priority: str = "all") -> list:
    """
    Get extensions filtered by priority level.
    
    Args:
        priority: Priority level - "critical", "high", "medium", "all"
    
    Returns:
        List of extensions for the specified priority
    """
    if priority == "critical":
        return CRITICAL_BACKUP_EXTENSIONS
    elif priority == "high":
        return [*CRITICAL_BACKUP_EXTENSIONS, *SECURITY_EXTENSIONS, *CODE_BACKUP_EXTENSIONS]
    elif priority == "medium":
        return [*CRITICAL_BACKUP_EXTENSIONS, *SECURITY_EXTENSIONS, 
                *CODE_BACKUP_EXTENSIONS, *CONFIG_LOG_EXTENSIONS]
    else:  # all
        return DEFAULT_EXTENSIONS


def get_extensions_by_category(category: str) -> list:
    """
    Get extensions by specific category.
    
    Args:
        category: Category name - "backup", "database", "config", "security", 
                  "archive", "code", "ide", "vcs", "document", "build"
    
    Returns:
        List of extensions for the specified category
    """
    categories = {
        "backup": CRITICAL_BACKUP_EXTENSIONS,
        "database": DATABASE_EXTENSIONS,
        "config": CONFIG_EXTENSIONS,
        "security": SECURITY_EXTENSIONS,
        "archive": ARCHIVE_EXTENSIONS,
        "code": CODE_BACKUP_EXTENSIONS,
        "ide": IDE_LEFTOVER_EXTENSIONS,
        "vcs": VCS_LEFTOVER_EXTENSIONS,
        "document": DOCUMENT_BACKUP_EXTENSIONS,
        "build": BUILD_CONFIG_EXTENSIONS,
    }
    return categories.get(category, [])


def get_optimized_extension_set(max_extensions: int = 50) -> list:
    """
    Get an optimized set of most effective extensions for fast scanning.
    
    Args:
        max_extensions: Maximum number of extensions to return
    
    Returns:
        List of most effective extensions limited to max_extensions
    """
    # Prioritize most common and dangerous leftovers
    priority_order = [
        *CRITICAL_BACKUP_EXTENSIONS[:15],  # Top backup extensions
        *SECURITY_EXTENSIONS[:10],          # Top security files
        *DATABASE_EXTENSIONS[:8],           # Top database files
        *CODE_BACKUP_EXTENSIONS[:10],       # Top code backups
        *CONFIG_EXTENSIONS[:7],             # Top config files
    ]
    return priority_order[:max_extensions]


def get_words_by_language(language: str = "all") -> list:
    """
    Get backup words filtered by language.
    
    Args:
        language: Language filter - "en", "pt-br", "all"
    
    Returns:
        List of backup words for the specified language
    """
    if language == "en":
        return [*DEFAULT_FILES_WORDS, *EN_COMMON_WORDS, *BACKUP_DIRECTORY_WORDS,
                *WEB_RELATED_WORDS, *VERSION_CONTROL_WORDS, *DATE_VERSION_WORDS]
    elif language == "pt-br":
        return [*DEFAULT_FILES_WORDS, *PTBR_COMMON_WORDS, *PTBR_BUSINESS_WORDS,
                *PTBR_CORPORATE_WORDS, *PTBR_TECHNICAL_WORDS, *BACKUP_DIRECTORY_WORDS]
    else:  # all
        return DEFAULT_BACKUP_WORDS


def get_specific_files(priority: str = "all") -> list:
    """
    Get list of specific complete filenames to test directly.
    
    These files are tested as-is without extension manipulation.
    Critical files (certificates, keys, .env) are returned first.
    
    Args:
        priority: Filter by priority - "critical", "all"
    
    Returns:
        List of specific filenames to test, ordered by priority
    """
    if priority == "critical":
        return CRITICAL_SPECIFIC_FILES
    else:
        # Return critical files first, then others
        return [*CRITICAL_SPECIFIC_FILES, *SPECIFIC_FILES, *VCS_SPECIFIC_FILES]


def get_all_test_targets() -> dict:
    """
    Get all test targets organized by type.
    
    Returns:
        Dictionary with extensions, words, and specific files
    """
    return {
        "extensions": DEFAULT_EXTENSIONS,
        "words": DEFAULT_BACKUP_WORDS,
        "specific_files": get_specific_files()
    }


def get_config_by_level(level: int = 2) -> dict:
    """
    Get scanner configuration based on complexity level.
    
    Levels:
        0 - Critical Only (Only critical specific files) ~10-15 tests
        1 - Quick (Critical files + minimal extensions) ~300-500 tests
        2 - Balanced (Common files + standard extensions) ~2-3K tests [DEFAULT]
        3 - Deep (Comprehensive scan) ~5-6K tests
        4 - Exhaustive (Maximum coverage) ~6-10K tests
    
    Args:
        level: Complexity level (0-4)
    
    Returns:
        Dictionary with extensions, words, and specific files for the level
    """
    if level == 0:
        # CRITICAL ONLY - Only test critical specific files (certificate.pfx, .env, etc)
        return {
            "extensions": [],  # No extensions at all
            "words": [],  # No brute force words
            "specific_files": CRITICAL_SPECIFIC_FILES,  # Only critical files
            "description": "Critical only - test only specific critical files (~10-15 tests)"
        }
    
    elif level == 1:
        # QUICK - Critical files + minimal extensions (~300-500 tests)
        return {
            "extensions": CRITICAL_BACKUP_EXTENSIONS[:15],  # Top 15 most critical
            "words": [],  # No brute force words in level 1
            "specific_files": CRITICAL_SPECIFIC_FILES,
            "description": "Quick scan - critical files only (~300-500 tests)"
        }
    
    elif level == 2:
        # BALANCED - Common extensions + standard files (~2-3K tests) [DEFAULT]
        return {
            "extensions": [
                *CRITICAL_BACKUP_EXTENSIONS,
                *CONFIG_LOG_EXTENSIONS,
                *SECURITY_EXTENSIONS[:20],
                *DATABASE_EXTENSIONS[:10],
                *CONFIG_EXTENSIONS[:15],
                *CODE_BACKUP_EXTENSIONS[:20],
            ],
            "words": [
                "backup", "old", "temp", "test", "dev", "staging",
                "archive", "copy", "original", "previous"
            ],
            "specific_files": [*CRITICAL_SPECIFIC_FILES, *SPECIFIC_FILES[:30]],
            "description": "Balanced scan - common targets (~2-3K tests)"
        }
    
    elif level == 3:
        # DEEP - Many extensions (NO extras) + all specific files (~5-6K tests)
        return {
            "extensions": [
                *CRITICAL_BACKUP_EXTENSIONS,
                *CONFIG_LOG_EXTENSIONS,
                *SECURITY_EXTENSIONS,
                *CODE_BACKUP_EXTENSIONS,
                *DATABASE_EXTENSIONS,
                *CONFIG_EXTENSIONS,
                *ARCHIVE_EXTENSIONS,
                *DOCUMENT_BACKUP_EXTENSIONS,
                *BUILD_CONFIG_EXTENSIONS,
                *IDE_LEFTOVER_EXTENSIONS,
                *VCS_LEFTOVER_EXTENSIONS,
                # NOTE: EXTRAS_EXTENSIONS is intentionally excluded for level 3
            ],
            "words": [
                *DEFAULT_FILES_WORDS,
                *BACKUP_DIRECTORY_WORDS[:40],
                *WEB_RELATED_WORDS,
                *EN_COMMON_WORDS[:40],
                *PTBR_COMMON_WORDS[:30],
                *VERSION_CONTROL_WORDS,
                *DATE_VERSION_WORDS[:20],
            ],
            "specific_files": get_specific_files(),  # ALL 52 specific files
            "description": "Deep scan - comprehensive coverage (~5-6K tests)"
        }
    
    else:  # level >= 4
        # EXHAUSTIVE - ALL extensions + ALL words for brute (~100K+ with -b)
        return {
            "extensions": DEFAULT_EXTENSIONS,  # All 233 extensions
            "words": DEFAULT_BACKUP_WORDS,     # All 581 words (for -b mode)
            "specific_files": get_specific_files(),
            "description": "Exhaustive scan - maximum coverage (~5-10K tests, ~100K+ with -b)"
        }


# Default scan level
DEFAULT_SCAN_LEVEL = 2
