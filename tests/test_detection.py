"""Tests for core.detection and http_utils.calculate_content_hash."""

from collections import defaultdict

import pytest

from leftovers.core.detection import check_false_positive
from leftovers.core.result import ScanResult
from leftovers.utils.http_utils import calculate_content_hash


def _make_result(status=200, ctype="text/html", length=None, url="http://x/a.bak", ext="bak"):
    content = b""
    return ScanResult(
        url=url,
        status_code=status,
        content_type=ctype,
        content_length=length if length is not None else 0,
        response_time=0.1,
        test_type="Base URL",
        extension=ext,
    )


def test_hash_empty_returns_empty_string():
    assert calculate_content_hash(b"") == ""


def test_hash_deterministic_for_same_bytes():
    assert calculate_content_hash(b"abc") == calculate_content_hash(b"abc")
    assert calculate_content_hash(b"abc") != calculate_content_hash(b"abd")


def test_hash_truncates_large_content():
    big = b"A" * (200 * 1024)
    out = calculate_content_hash(big)
    assert len(out) == 32  # md5 hex


def test_404_is_always_false_positive():
    result = _make_result(status=404, length=100)
    is_fp, reason = check_false_positive(result, b"not found", {}, None, defaultdict(int), defaultdict(set))
    assert is_fp is True
    assert "404" in reason


def test_zero_byte_response_is_false_positive():
    result = _make_result(status=200, length=0)
    is_fp, reason = check_false_positive(result, b"", {}, None, defaultdict(int), defaultdict(set))
    assert is_fp is True
    assert "empty" in reason.lower()


def test_hash_match_to_main_page_flagged():
    body = b"<html>spa shell</html>"
    main_page = {
        "size": len(body),
        "hash": calculate_content_hash(body),
        "content_type": "text/html",
        "text_content": "spa shell",
    }
    result = _make_result(status=200, length=len(body))
    is_fp, reason = check_false_positive(
        result, body, {}, main_page, defaultdict(int), defaultdict(set)
    )
    assert is_fp is True


def test_pdf_signature_bypasses_fp():
    body = b"%PDF-1.4 body bytes"
    result = _make_result(
        status=200, ctype="application/pdf", length=len(body),
        url="http://x/report.pdf", ext="pdf",
    )
    is_fp, _ = check_false_positive(result, body, {}, None, defaultdict(int), defaultdict(set))
    assert is_fp is False
