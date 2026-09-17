"""Tests for updater.py -- pure version-compare and asset-picking logic.
No network, no filesystem; see test_update_fetch.py and
test_update_apply.py for the modules that actually touch either."""

from lock_in.updater import UpdateInfo, check_for_update, is_newer, parse_version, pick_asset


def test_parse_version_strips_leading_v():
    assert parse_version("v2.5.3") == (2, 5, 3)


def test_parse_version_without_leading_v():
    assert parse_version("2.5.3") == (2, 5, 3)


def test_parse_version_rejects_wrong_part_count():
    assert parse_version("v2.5") is None
    assert parse_version("v2.5.3.1") is None


def test_parse_version_rejects_non_numeric_parts():
    assert parse_version("v2.x.3") is None


def test_is_newer_true_when_strictly_greater():
    assert is_newer("2.5.2", "v2.5.3") is True


def test_is_newer_false_when_equal():
    assert is_newer("2.5.3", "v2.5.3") is False


def test_is_newer_false_when_older():
    assert is_newer("2.5.3", "v2.5.2") is False


def test_is_newer_false_when_latest_tag_is_unparseable():
    assert is_newer("2.5.2", "not-a-version") is False


def test_is_newer_false_when_current_is_unparseable():
    assert is_newer("not-a-version", "v2.5.3") is False


def test_pick_asset_finds_matching_name():
    assets = [
        {"name": "LockIn-Windows.zip", "browser_download_url": "http://example.com/win.zip"},
        {"name": "LockIn-macOS.zip", "browser_download_url": "http://example.com/mac.zip"},
    ]
    found = pick_asset(assets, "win32")
    assert found["browser_download_url"] == "http://example.com/win.zip"


def test_pick_asset_returns_none_when_no_match():
    assets = [{"name": "LockIn-macOS.zip", "browser_download_url": "http://example.com/mac.zip"}]
    assert pick_asset(assets, "win32") is None


def test_pick_asset_returns_none_for_empty_list():
    assert pick_asset([], "win32") is None


def test_pick_asset_returns_none_for_unknown_platform():
    assets = [{"name": "LockIn-Windows.zip", "browser_download_url": "http://example.com/win.zip"}]
    assert pick_asset(assets, "freebsd") is None


def _release(tag: str, assets=None) -> dict:
    if assets is None:
        assets = [{"name": "LockIn-Windows.zip", "browser_download_url": "http://example.com/win.zip"}]
    return {"tag_name": tag, "assets": assets}


def test_check_for_update_returns_info_when_newer_and_asset_matches():
    info = check_for_update("2.5.2", _release("v2.5.3"), "win32")
    assert info == UpdateInfo(
        version="2.5.3", asset_name="LockIn-Windows.zip",
        download_url="http://example.com/win.zip",
    )


def test_check_for_update_returns_none_when_not_newer():
    assert check_for_update("2.5.3", _release("v2.5.3"), "win32") is None


def test_check_for_update_returns_none_for_malformed_tag():
    assert check_for_update("2.5.2", _release("not-a-version"), "win32") is None


def test_check_for_update_returns_none_when_no_asset_for_platform():
    assert check_for_update("2.5.2", _release("v2.5.3", assets=[]), "win32") is None


def test_check_for_update_returns_none_when_asset_has_no_download_url():
    """A malformed asset dict must be "nothing to offer", not a KeyError
    escaping the background thread."""
    release = _release("v2.5.3", assets=[{"name": "LockIn-Windows.zip"}])
    assert check_for_update("2.5.2", release, "win32") is None


def test_check_for_update_returns_none_when_asset_download_url_is_empty():
    release = _release("v2.5.3", assets=[
        {"name": "LockIn-Windows.zip", "browser_download_url": ""},
    ])
    assert check_for_update("2.5.2", release, "win32") is None
