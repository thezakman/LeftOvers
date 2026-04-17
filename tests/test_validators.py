"""Tests for utils.validators."""

from leftovers.utils.validators import (
    is_valid_http_method,
    sanitize_filename,
    sanitize_header_value,
    validate_extension,
    validate_file_path,
    validate_thread_count,
    validate_timeout,
    validate_url,
    validate_wordlist_size,
)


def test_validate_url_accepts_http_and_https():
    assert validate_url("http://example.com")[0] is True
    assert validate_url("https://example.com/path")[0] is True


def test_validate_url_rejects_non_http_schemes():
    ok, _ = validate_url("javascript:alert(1)")
    assert ok is False
    ok, _ = validate_url("file:///etc/passwd")
    assert ok is False


def test_validate_url_rejects_empty():
    assert validate_url("")[0] is False
    assert validate_url(None)[0] is False  # type: ignore[arg-type]


def test_validate_url_rejects_hostname_with_spaces():
    assert validate_url("http://bad host/")[0] is False


def test_validate_file_path_rejects_traversal_and_null():
    assert validate_file_path("../etc/passwd")[0] is False
    assert validate_file_path("ok\x00.txt")[0] is False
    assert validate_file_path("good.txt")[0] is True


def test_validate_extension_allows_dotted_compound():
    assert validate_extension("tar.gz")[0] is True
    assert validate_extension(".php")[0] is True


def test_validate_extension_rejects_invalid_chars():
    assert validate_extension("b!d")[0] is False


def test_validate_thread_count_bounds():
    assert validate_thread_count(0)[0] is False
    assert validate_thread_count(1)[0] is True
    assert validate_thread_count(100)[0] is True
    assert validate_thread_count(101)[0] is False


def test_validate_timeout_bounds():
    assert validate_timeout(0.05)[0] is False
    assert validate_timeout(5)[0] is True
    assert validate_timeout(301)[0] is False


def test_sanitize_header_value_strips_newlines():
    assert "\n" not in sanitize_header_value("a\r\nInjected: x")
    assert "\x00" not in sanitize_header_value("a\x00b")


def test_sanitize_filename_removes_path_and_unsafe_chars():
    assert sanitize_filename("../../etc/pa<>ss") == "pa__ss"


def test_is_valid_http_method():
    assert is_valid_http_method("get") is True
    assert is_valid_http_method("TRACE") is False


def test_validate_wordlist_size():
    assert validate_wordlist_size(0)[0] is False
    assert validate_wordlist_size(10)[0] is True
    assert validate_wordlist_size(10_000_001)[0] is False
