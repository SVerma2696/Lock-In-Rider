"""
update_verify.py
================
Making sure a downloaded update is exactly the file the release
published, before anything is installed.

Every release publishes two files per computer type:

    LockIn-Windows.zip          the new version
    LockIn-Windows.zip.sha256   its fingerprint (a SHA-256 hash)

A fingerprint is a long code worked out from every single byte of a
file. Change even one byte -- a download cut short, a file swapped along
the way -- and the fingerprint comes out completely different.

So after downloading, the app works out the fingerprint of what it got
and compares it with the published one. Only an exact match is
installed. A missing, garbled, or different fingerprint means the update
is thrown away. An unchecked update is never installed.

The comparison uses hmac.compare_digest, which takes the same time
whether the codes differ early or late, so the check can't be probed.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from pathlib import Path

CHECKSUM_SUFFIX = ".sha256"
# A fingerprint file is one short line; anything bigger isn't one.
MAX_CHECKSUM_BYTES = 4096
_HEX_64 = re.compile(r"^[0-9a-fA-F]{64}$")
_CHUNK = 1024 * 1024


def checksum_asset_name(asset_name: str) -> str:
    """The fingerprint file's name: LockIn-Windows.zip -> LockIn-Windows.zip.sha256."""
    return asset_name + CHECKSUM_SUFFIX


def parse_checksum(text: str, asset_name: str) -> str | None:
    """The fingerprint written in a .sha256 file, in small letters, or
    None if the file isn't a proper one.

    Accepts the two usual layouts, as written by `sha256sum` and friends:
        <64 hex digits>
        <64 hex digits>  LockIn-Windows.zip     (or " *LockIn-Windows.zip")
    When a file name is given, it must be this update's file."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) != 1:
        return None
    parts = lines[0].split()
    digest = parts[0]
    if not _HEX_64.match(digest):
        return None
    if len(parts) > 2:
        return None
    if len(parts) == 2 and parts[1].lstrip("*") != asset_name:
        return None
    return digest.lower()


def sha256_of(path: Path) -> str:
    """The fingerprint of a file, read in pieces so a big file never has
    to fit in memory at once."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def matches(path: Path, expected: str | None) -> bool:
    """True only if the file's fingerprint is exactly `expected`. No
    expected fingerprint, or a file that can't be read, is always False."""
    if not expected or not _HEX_64.match(expected):
        return False
    try:
        actual = sha256_of(path)
    except OSError:
        return False
    return hmac.compare_digest(actual.encode("ascii"), expected.lower().encode("ascii"))
