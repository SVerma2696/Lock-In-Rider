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


# --- classify_check / check_message: what the "Check for updates now" -----
# --- button needs to tell "up to date" apart from "couldn't check". ------

from lock_in.updater import (
    CHECK_AVAILABLE, CHECK_DOWNLOAD_FAILED, CHECK_FAILED, CHECK_NO_FILE,
    CHECK_UP_TO_DATE, CheckResult, check_message, classify_check,
)


def test_classify_check_failed_when_nothing_came_back():
    """fetch_latest_release() returns None for no internet, timeouts, etc."""
    assert classify_check("2.5.4", None, "win32") == CheckResult(CHECK_FAILED)


def test_classify_check_failed_when_response_has_no_readable_tag():
    """GitHub's rate-limit answer is valid JSON with no tag_name. That must
    read as "couldn't check", never as a false "you're up to date"."""
    result = classify_check("2.5.4", {"message": "API rate limit exceeded"}, "win32")
    assert result == CheckResult(CHECK_FAILED)


def test_classify_check_up_to_date_when_same_version():
    result = classify_check("2.5.4", _release("v2.5.4"), "win32")
    assert result == CheckResult(CHECK_UP_TO_DATE)


def test_classify_check_up_to_date_when_running_a_newer_build():
    assert classify_check("2.6.0", _release("v2.5.4"), "win32").status == CHECK_UP_TO_DATE


def test_classify_check_available_carries_info_and_version():
    result = classify_check("2.5.4", _release("v2.5.5"), "win32")
    assert result.status == CHECK_AVAILABLE
    assert result.latest == "2.5.5"
    assert result.info == UpdateInfo(
        version="2.5.5", asset_name="LockIn-Windows.zip",
        download_url="http://example.com/win.zip",
    )


def test_classify_check_no_file_when_newer_but_nothing_for_this_computer():
    result = classify_check("2.5.4", _release("v2.5.5", assets=[]), "win32")
    assert result == CheckResult(CHECK_NO_FILE, latest="2.5.5")


def test_check_message_is_plain_words_for_every_status():
    for result in (
        CheckResult(CHECK_FAILED),
        CheckResult(CHECK_UP_TO_DATE),
        CheckResult(CHECK_NO_FILE, latest="2.5.5"),
        CheckResult(CHECK_DOWNLOAD_FAILED, latest="2.5.5"),
        CheckResult(CHECK_AVAILABLE, latest="2.5.5"),
    ):
        assert check_message(result, "2.5.4", can_restart=True)


def test_check_message_up_to_date_names_the_current_version():
    assert "v2.5.4" in check_message(CheckResult(CHECK_UP_TO_DATE), "2.5.4", True)


def test_check_message_available_points_to_restart_button_when_it_can():
    result = CheckResult(CHECK_AVAILABLE, latest="2.5.5")
    text = check_message(result, "2.5.4", can_restart=True)
    assert "v2.5.5" in text and "Restart now" in text


def test_check_message_available_points_to_releases_page_from_source():
    """A source checkout has no file to swap, so no Restart button exists."""
    result = CheckResult(CHECK_AVAILABLE, latest="2.5.5")
    text = check_message(result, "2.5.4", can_restart=False)
    assert "v2.5.5" in text and "Releases" in text and "Restart now" not in text
