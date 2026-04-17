"""Tests for core.result.ScanResult."""

from datetime import datetime

from leftovers.core.result import ScanResult


def test_to_dict_from_dict_roundtrip():
    r = ScanResult(
        url="http://example.com/a.bak",
        status_code=200,
        content_type="text/plain",
        content_length=42,
        response_time=0.123,
        test_type="Base URL",
        extension="bak",
    )
    d = r.to_dict()
    r2 = ScanResult.from_dict(d)
    assert r2.url == r.url
    assert r2.status_code == r.status_code
    assert r2.content_type == r.content_type
    assert r2.content_length == r.content_length
    assert r2.test_type == r.test_type
    assert r2.extension == r.extension


def test_from_dict_accepts_iso_timestamp():
    now = datetime(2026, 1, 1, 12, 0, 0)
    d = {
        "url": "http://x/y",
        "status_code": 200,
        "content_type": "text/plain",
        "content_length": 1,
        "response_time": 0.1,
        "test_type": "Base URL",
        "extension": "",
        "timestamp": now.isoformat(),
    }
    r = ScanResult.from_dict(d)
    assert r.timestamp == now


def test_mark_as_false_positive():
    r = ScanResult(
        url="http://x", status_code=200, content_type="text/html",
        content_length=1, response_time=0.1, test_type="Base URL", extension="",
    )
    r.mark_as_false_positive("reason")
    assert r.false_positive is True
    assert r.false_positive_reason == "reason"
