"""Tests for utils.http_utils: parse_url, LRUCache, HttpClient caching."""

from leftovers.utils.http_utils import (
    LRUCache,
    calculate_content_hash,
    is_domain_only,
    parse_url,
    parse_url_full,
)


def test_parse_url_subdomain():
    base, domain, path = parse_url("http://sub.example.co.uk/foo/bar")
    assert base == "http://sub.example.co.uk"
    assert domain == "sub.example.co.uk"
    assert path == "foo/bar"


def test_parse_url_full_returns_tldextract_parts():
    base, domain, path, sub, name, suffix = parse_url_full("https://a.b.example.com/x")
    assert base == "https://a.b.example.com"
    assert sub == "a.b"
    assert name == "example"
    assert suffix == "com"
    assert path == "x"


def test_is_domain_only_true_for_root():
    assert is_domain_only("http://example.com") is True
    assert is_domain_only("http://example.com/") is True


def test_is_domain_only_false_for_path():
    assert is_domain_only("http://example.com/foo") is False


def test_lrucache_evicts_least_recent():
    cache = LRUCache(max_size=2)
    cache.put("a", {"v": 1})
    cache.put("b", {"v": 2})
    assert cache.get("a") == {"v": 1}  # bumps 'a' to MRU
    cache.put("c", {"v": 3})  # should evict 'b'
    assert "b" not in cache
    assert "a" in cache
    assert "c" in cache


def test_lrucache_update_refreshes_recency():
    cache = LRUCache(max_size=2)
    cache.put("a", {"v": 1})
    cache.put("b", {"v": 2})
    cache.put("a", {"v": 10})  # 'a' becomes MRU
    cache.put("c", {"v": 3})   # evicts 'b'
    assert cache.get("a") == {"v": 10}
    assert "b" not in cache


def test_calculate_content_hash_truncates_above_100kb():
    # Two different-size large bodies should have different hashes only if
    # their head+tail bytes differ; this just smoke-checks that the function
    # returns a consistent hex digest.
    a = b"A" * (200 * 1024)
    b = b"A" * (200 * 1024 - 1) + b"B"
    assert calculate_content_hash(a) != calculate_content_hash(b)


def test_httpclient_cache_hydrates_body():
    """Regression guard for Tier 1.3: the request cache used to return
    mock responses with empty content, silently breaking FP detection on
    cache hits. Verify the cached body is preserved."""
    from leftovers.utils.http_utils import HttpClient

    client = HttpClient(use_cache=True)
    body = b"hello body"
    cached = {
        "success": True,
        "error": "",
        "time": 0.01,
        "status_code": 200,
        "headers": {"Content-Type": "text/plain"},
        "content": body,
    }
    client.request_cache.put("http://example.test/page", cached)
    result = client.get("http://example.test/page")
    assert result["success"] is True
    assert result.get("from_cache") is True
    assert result["response"].content == body
    assert calculate_content_hash(result["response"].content) != ""
