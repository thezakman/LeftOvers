"""Shared pytest fixtures for LeftOvers tests."""

from __future__ import annotations

import os
import sys
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

# Ensure the project root is on sys.path so `import leftovers.*` works without
# requiring an editable install.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002  (override)
        pass


@pytest.fixture
def http_fixture_dir(tmp_path):
    """A directory populated with leftover-looking files.

    File names match the scanner's natural URL permutations so the e2e test
    exercises discovery without relying on --test-index.
    """
    (tmp_path / "index.html").write_bytes(b"<html>ok</html>")
    # Hit via "Common Leftover" pattern /backup + .bak extension
    (tmp_path / "backup.bak").write_bytes(b"backup body")
    # Hit via "Common Leftover" pattern /test + .zip extension
    (tmp_path / "test.zip").write_bytes(b"PK\x03\x04zipbody")
    return tmp_path


@pytest.fixture
def http_server(http_fixture_dir):
    """Spin up a local http.server serving ``http_fixture_dir`` on a free port."""
    port = _free_port()
    cwd = os.getcwd()
    os.chdir(str(http_fixture_dir))
    httpd = HTTPServer(("127.0.0.1", port), _QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    # Tiny wait so the server is accepting before the test hits it.
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.02)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        os.chdir(cwd)
