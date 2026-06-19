"""Tests for scanner-level logic that isn't network-bound."""

import os

from leftovers.core.scanner import LeftOver
from leftovers.core.result import ScanResult


def _r(status, fp=False):
    r = ScanResult(
        url=f"http://x/{status}", status_code=status, content_type="text/plain",
        content_length=10, response_time=0.1, test_type="Base URL", extension="",
    )
    if fp:
        r.mark_as_false_positive("dup")
    return r


def test_count_findings_matches_files_found_rule():
    """count_findings() drives the process exit code; it must count non-404
    results that are not false positives (200s always count)."""
    scanner = LeftOver(silent=True)
    try:
        scanner.results = [
            _r(200),            # counts
            _r(200, fp=True),   # counts (200 overrides FP)
            _r(403),            # counts (non-404, not FP)
            _r(403, fp=True),   # excluded (FP and not 200)
            _r(404),            # excluded (404)
        ]
        assert scanner.count_findings() == 3

        scanner.results = []
        assert scanner.count_findings() == 0
    finally:
        scanner.close()
        # Don't litter the repo with the autosave file the scanner opens on init
        try:
            os.unlink(scanner._autosave_path)
        except OSError:
            pass
