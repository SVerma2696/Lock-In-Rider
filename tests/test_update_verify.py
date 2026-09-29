"""
Tests for update safety: an update is only installed when its download
matches the fingerprint (SHA-256) the release published. A valid,
wrong, missing, or garbled fingerprint, and a download that doesn't
match, are all covered. Nothing here touches the internet.
"""

import hashlib
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from lock_in import update_apply, updater
from lock_in.application.update_service import prepare_update
from lock_in.update_verify import (
    checksum_asset_name,
    matches,
    parse_checksum,
    sha256_of,
)

ASSET = "LockIn-Windows.zip"
GOOD = "a" * 64


# ---------------------------------------------------------------------- #
# Reading a fingerprint file
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text",
    [
        GOOD,
        GOOD + "\n",
        f"{GOOD}  {ASSET}\n",
        f"{GOOD} *{ASSET}",
        GOOD.upper(),
    ],
)
def test_valid_fingerprint_files_are_read(text):
    assert parse_checksum(text, ASSET) == GOOD


@pytest.mark.parametrize(
    "text",
    [
        "",  # missing
        "   \n",
        "abc123",  # too short
        "g" * 64,  # not hex
        "a" * 63,
        "a" * 65,
        f"{GOOD}  LockIn-macOS.zip",  # another file's fingerprint
        f"{GOOD}\n{GOOD}",  # two lines
        f"{GOOD}  {ASSET} extra",
        "<html>Not Found</html>",
    ],
)
def test_malformed_fingerprint_files_are_rejected(text):
    assert parse_checksum(text, ASSET) is None


def test_checksum_file_name():
    assert checksum_asset_name(ASSET) == "LockIn-Windows.zip.sha256"


# ---------------------------------------------------------------------- #
# Comparing a file with its fingerprint
# ---------------------------------------------------------------------- #
def test_sha256_matches_hashlib(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"lock in" * 1000)
    assert sha256_of(path) == hashlib.sha256(b"lock in" * 1000).hexdigest()


def test_a_matching_file_passes_and_capitals_dont_matter(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"new version")
    digest = hashlib.sha256(b"new version").hexdigest()
    assert matches(path, digest)
    assert matches(path, digest.upper())


@pytest.mark.parametrize("expected", [None, "", "zz", GOOD])
def test_a_wrong_or_missing_fingerprint_fails(tmp_path, expected):
    path = tmp_path / "f.bin"
    path.write_bytes(b"new version")
    assert not matches(path, expected)


def test_one_changed_byte_fails(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"new version")
    digest = hashlib.sha256(b"new version").hexdigest()
    path.write_bytes(b"new versioN")
    assert not matches(path, digest)


def test_a_missing_file_fails(tmp_path):
    assert not matches(tmp_path / "gone.bin", GOOD)


# ---------------------------------------------------------------------- #
# The whole update check, with fake network parts
# ---------------------------------------------------------------------- #
def make_zip_bytes(tmp_path) -> bytes:
    path = tmp_path / "build.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Lock In.exe", b"brand new app")
    return path.read_bytes()


class FakeFetch:
    """Stands in for update_fetch.py."""

    def __init__(self, archive: bytes, checksum_text: str | None, with_checksum_asset=True):
        self.archive = archive
        self.checksum_text = checksum_text
        self.downloads = 0
        assets = [{"name": ASSET, "browser_download_url": "https://x/zip"}]
        if with_checksum_asset:
            assets.append(
                {"name": ASSET + ".sha256", "browser_download_url": "https://x/zip.sha256"}
            )
        self.release = {"tag_name": "v9.9.9", "assets": assets}

    def fetch_latest_release(self):
        return self.release

    def fetch_text(self, url, max_bytes):
        return self.checksum_text

    def download_file(self, url, dest: Path):
        self.downloads += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.archive)
        return True


def run(tmp_path, fetch):
    folder = tmp_path / "update"
    folder.mkdir(exist_ok=True)
    return prepare_update(
        "3.0.2",
        "win32",
        can_install=True,
        fetch=fetch,
        apply=update_apply,
        make_temp_dir=lambda: folder,
    )


def test_a_valid_fingerprint_installs(tmp_path):
    archive = make_zip_bytes(tmp_path)
    digest = hashlib.sha256(archive).hexdigest()
    result, extracted = run(tmp_path, FakeFetch(archive, f"{digest}  {ASSET}\n"))
    assert result.status == updater.CHECK_AVAILABLE
    assert extracted is not None and extracted.read_bytes() == b"brand new app"


def test_a_wrong_fingerprint_is_never_installed(tmp_path):
    archive = make_zip_bytes(tmp_path)
    result, extracted = run(tmp_path, FakeFetch(archive, GOOD))
    assert result.status == updater.CHECK_UNVERIFIED
    assert extracted is None
    assert not (tmp_path / "update").exists() or not any((tmp_path / "update").iterdir())


def test_a_release_without_a_fingerprint_is_never_downloaded(tmp_path):
    fetch = FakeFetch(make_zip_bytes(tmp_path), None, with_checksum_asset=False)
    result, extracted = run(tmp_path, fetch)
    assert result.status == updater.CHECK_UNVERIFIED
    assert extracted is None and fetch.downloads == 0


def test_a_garbled_fingerprint_is_never_downloaded(tmp_path):
    fetch = FakeFetch(make_zip_bytes(tmp_path), "<html>404</html>")
    result, extracted = run(tmp_path, fetch)
    assert result.status == updater.CHECK_UNVERIFIED
    assert extracted is None and fetch.downloads == 0


def test_a_fingerprint_that_couldnt_be_fetched_is_a_download_problem(tmp_path):
    fetch = FakeFetch(make_zip_bytes(tmp_path), None)
    result, extracted = run(tmp_path, fetch)
    assert result.status == updater.CHECK_DOWNLOAD_FAILED
    assert extracted is None and fetch.downloads == 0


def test_running_from_source_never_downloads(tmp_path):
    fetch = FakeFetch(make_zip_bytes(tmp_path), GOOD)
    result, extracted = prepare_update("3.0.2", "win32", can_install=False, fetch=fetch)
    assert result.status == updater.CHECK_AVAILABLE
    assert extracted is None and fetch.downloads == 0


def test_a_crash_inside_the_check_just_means_failed():
    broken = SimpleNamespace(fetch_latest_release=lambda: 1 / 0)
    result, extracted = prepare_update("3.0.2", "win32", can_install=True, fetch=broken)
    assert result.status == updater.CHECK_FAILED and extracted is None


def test_the_unverified_message_is_plain():
    text = updater.check_message(
        updater.CheckResult(updater.CHECK_UNVERIFIED, latest="9.9.9"), "3.0.2", True
    )
    assert "safety check" in text and "wasn't installed" in text


def test_update_info_picks_up_the_fingerprint_link():
    info = updater.check_for_update(
        "3.0.2",
        {
            "tag_name": "v3.1.0",
            "assets": [
                {"name": ASSET, "browser_download_url": "u1"},
                {"name": ASSET + ".sha256", "browser_download_url": "u2"},
            ],
        },
        "win32",
    )
    assert info.checksum_url == "u2"
