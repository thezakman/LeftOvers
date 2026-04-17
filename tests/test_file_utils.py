"""Tests for utils.file_utils."""

import json
import os

from leftovers.core.result import ScanResult
from leftovers.utils.file_utils import (
    append_completed_url_to_jsonl,
    append_result_to_jsonl,
    export_results,
    format_size,
    load_autosave,
    load_completed_urls,
    load_url_list,
    load_wordlist,
)


def test_format_size_thresholds():
    assert format_size(0) == "0 B"
    assert format_size(1023) == "1023 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(5 * 1024 * 1024) == "5.0 MB"


def test_load_wordlist_strips_comments_and_blanks(tmp_path):
    p = tmp_path / "w.txt"
    p.write_text("a\n\n# comment\nb\n   c\n")
    assert load_wordlist(str(p)) == ["a", "b", "c"]


def test_load_url_list_prepends_http(tmp_path):
    p = tmp_path / "u.txt"
    p.write_text("example.com\nhttps://secure.example.com\n")
    assert load_url_list(str(p)) == [
        "http://example.com",
        "https://secure.example.com",
    ]


def test_jsonl_roundtrip(tmp_path):
    p = tmp_path / "auto.jsonl"
    r = ScanResult(
        url="http://x/a.bak", status_code=200, content_type="text/plain",
        content_length=5, response_time=0.1, test_type="Base URL", extension="bak",
    )
    with open(p, "a", encoding="utf-8") as fh:
        append_result_to_jsonl(fh, r)
        append_completed_url_to_jsonl(fh, "http://x")

    completed = load_completed_urls(str(p))
    results = load_autosave(str(p))

    assert completed == {"http://x"}
    assert len(results) == 1
    assert results[0].url == r.url


def test_export_results_writes_valid_json(tmp_path):
    out = tmp_path / "out.json"
    r = ScanResult(
        url="http://y/b.bak", status_code=200, content_type="text/plain",
        content_length=3, response_time=0.2, test_type="Base URL", extension="bak",
    )
    ok = export_results([r], str(out))
    assert ok is True
    data = json.loads(out.read_text())
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["url"] == r.url
