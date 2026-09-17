"""
Tests for update_fetch.py. Nothing here ever opens a real socket --
urllib.request.urlopen is swapped out for a small fake context manager,
the same "fake stands in for the one network call site" idea
test_claude_fallback.py uses for the Claude SDK client.
"""

import http.client
import json

from lock_in import update_fetch


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def install_fake_urlopen(monkeypatch, result):
    """result is either a FakeResponse to return, or an Exception instance to raise."""
    def fake_urlopen(request, timeout=None):
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(update_fetch.urllib.request, "urlopen", fake_urlopen)


def test_fetch_latest_release_returns_parsed_json(monkeypatch):
    payload = {"tag_name": "v2.5.3", "assets": []}
    install_fake_urlopen(monkeypatch, FakeResponse(json.dumps(payload).encode("utf-8")))
    assert update_fetch.fetch_latest_release() == payload


def test_fetch_latest_release_returns_none_on_network_error(monkeypatch):
    install_fake_urlopen(monkeypatch, update_fetch.urllib.error.URLError("no internet"))
    assert update_fetch.fetch_latest_release() is None


def test_fetch_latest_release_returns_none_on_bad_json(monkeypatch):
    install_fake_urlopen(monkeypatch, FakeResponse(b"not json"))
    assert update_fetch.fetch_latest_release() is None


def test_fetch_latest_release_returns_none_on_incomplete_read(monkeypatch):
    """http.client.IncompleteRead (server closes the connection mid-body)
    is NOT an OSError, so the old narrow except clause let it escape the
    background thread entirely."""
    install_fake_urlopen(monkeypatch, http.client.IncompleteRead(b"half a body"))
    assert update_fetch.fetch_latest_release() is None


def test_fetch_latest_release_returns_none_on_any_unexpected_error(monkeypatch):
    """The fail-silent contract is "never raise", not "never raise the
    handful of exceptions we thought of"."""
    install_fake_urlopen(monkeypatch, RuntimeError("something nobody predicted"))
    assert update_fetch.fetch_latest_release() is None


def test_fetch_latest_release_returns_none_on_non_utf8_body(monkeypatch):
    """json.loads on non-UTF-8 bytes raises UnicodeDecodeError, not
    JSONDecodeError -- another escape from the old narrow catch."""
    install_fake_urlopen(monkeypatch, FakeResponse(b"\xff\xfe\x00not utf-8"))
    assert update_fetch.fetch_latest_release() is None


def test_download_file_writes_the_body_and_returns_true(monkeypatch, tmp_path):
    install_fake_urlopen(monkeypatch, FakeResponse(b"pretend zip bytes"))
    dest = tmp_path / "download" / "asset.zip"
    assert update_fetch.download_file("http://example.com/asset.zip", dest) is True
    assert dest.read_bytes() == b"pretend zip bytes"


def test_download_file_returns_false_on_network_error(monkeypatch, tmp_path):
    install_fake_urlopen(monkeypatch, update_fetch.urllib.error.URLError("dropped"))
    dest = tmp_path / "asset.zip"
    assert update_fetch.download_file("http://example.com/asset.zip", dest) is False
    assert not dest.exists()


def test_download_file_returns_false_on_incomplete_read(monkeypatch, tmp_path):
    install_fake_urlopen(monkeypatch, http.client.IncompleteRead(b"half a zip"))
    dest = tmp_path / "asset.zip"
    assert update_fetch.download_file("http://example.com/asset.zip", dest) is False


def test_download_file_returns_false_on_any_unexpected_error(monkeypatch, tmp_path):
    install_fake_urlopen(monkeypatch, RuntimeError("something nobody predicted"))
    dest = tmp_path / "asset.zip"
    assert update_fetch.download_file("http://example.com/asset.zip", dest) is False
