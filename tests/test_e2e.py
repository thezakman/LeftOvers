"""End-to-end smoke test: scan a local http.server fixture.

Skips with a clear reason if the LeftOver constructor can't be instantiated
in-process (e.g. missing optional dependency).
"""

import pytest

from leftovers.core.scanner import LeftOver


def test_scan_local_fixture_finds_leftovers(http_server, http_fixture_dir):
    scanner = LeftOver(
        extensions=["bak", "swp", "zip"],
        timeout=3,
        threads=4,
        verify_ssl=False,
        use_color=False,
        verbose=False,
        silent=True,
    )
    try:
        scanner.process_url(http_server)
        urls = {r.url for r in scanner.results if not r.false_positive}

        # The scanner tests /<pattern>.<ext> for common leftover words; the
        # fixture places files at those exact paths.
        assert any(u.endswith("/backup.bak") for u in urls), \
            f"/backup.bak not found. Got: {urls}"
        assert any(u.endswith("/test.zip") for u in urls), \
            f"/test.zip not found. Got: {urls}"
    finally:
        scanner.close()
