"""
application/update_service.py
=============================
One update check, start to finish, off the screen's thread:

    1. ask GitHub about the newest release
    2. fetch its fingerprint file (.sha256) and read it
    3. download the new version
    4. work out the download's own fingerprint and compare the two
    5. only if they match exactly, unpack it, ready for "Restart now"

A missing, garbled, or different fingerprint stops at that step and the
download is deleted. An unchecked update is never unpacked or installed.

The network and unpacking parts are passed in, so the tests can use
fakes and never touch the internet.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from .. import updater
from ..update_verify import MAX_CHECKSUM_BYTES, matches, parse_checksum

logger = logging.getLogger(__name__)


def prepare_update(
    current_version: str,
    platform: str,
    can_install: bool,
    fetch: ModuleType | None = None,
    apply: ModuleType | None = None,
    make_temp_dir: Callable[[], Path] = lambda: Path(tempfile.mkdtemp(prefix="lockin_update_")),
) -> tuple[updater.CheckResult, Path | None]:
    """Returns how the check ended, and the unpacked new version when one
    is ready to swap in (None otherwise). `can_install` is False when
    running from source: then only step 1 happens. Never raises."""
    try:
        if fetch is None:
            from .. import update_fetch

            fetch = update_fetch
        if apply is None:
            from .. import update_apply

            apply = update_apply
        result = updater.classify_check(current_version, fetch.fetch_latest_release(), platform)
        info = result.info
        if info is None or not can_install:
            return result, None
        return _download_and_check(result, info, platform, fetch, apply, make_temp_dir)
    except Exception:
        logger.warning("The update check failed", exc_info=True)
        return updater.CheckResult(updater.CHECK_FAILED), None


def _download_and_check(
    result: updater.CheckResult,
    info: updater.UpdateInfo,
    platform: str,
    fetch: ModuleType,
    apply: ModuleType,
    make_temp_dir: Callable[[], Path],
) -> tuple[updater.CheckResult, Path | None]:
    unverified = updater.CheckResult(updater.CHECK_UNVERIFIED, latest=result.latest)
    download_failed = updater.CheckResult(updater.CHECK_DOWNLOAD_FAILED, latest=result.latest)

    # Steps 2: no fingerprint means no install -- checked before downloading
    # anything, so nothing unchecked ever lands on the disk.
    if not info.checksum_url:
        logger.warning("Update %s has no fingerprint file; not installing it", info.version)
        return unverified, None
    text = fetch.fetch_text(info.checksum_url, MAX_CHECKSUM_BYTES)
    if text is None:
        return download_failed, None
    expected = parse_checksum(text, info.asset_name)
    if expected is None:
        logger.warning("Update %s has an unreadable fingerprint file", info.version)
        return unverified, None

    # Steps 3 and 4.
    temp_dir = make_temp_dir()
    archive_path = temp_dir / info.asset_name
    if not fetch.download_file(info.download_url, archive_path):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return download_failed, None
    if not matches(archive_path, expected):
        logger.warning("Update %s didn't match its fingerprint; deleted it", info.version)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return unverified, None

    # Step 5.
    extracted = apply.extract_archive(archive_path, temp_dir, platform)
    if extracted is None:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return download_failed, None
    # Only the unpacked app is needed from here on. temp_dir itself stays:
    # the unpacked app lives in it.
    archive_path.unlink(missing_ok=True)
    return result, extracted
