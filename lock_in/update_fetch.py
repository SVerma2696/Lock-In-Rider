"""
update_fetch.py
================
The only part of the auto-update feature that touches the network --
one GET to ask GitHub what its latest release is, and one streamed
download of the matching file. Exactly the same "thin shell around a
single network call, tested with a fake standing in for it" shape as
claude_fallback.py: nothing in tests/test_update_fetch.py ever opens a
real socket.

Every function here reports failure by returning None/False -- it never
raises. That's the fail-silent contract the whole feature depends on:
no internet, GitHub down, a bad response, a network drop mid-download --
all of it just means "no update this time," never a crash.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

REPO = "SVerma2696/Lock-In-Rider"
_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
_USER_AGENT = "Lock-In-Auto-Updater"


def fetch_latest_release(timeout: float = 5.0) -> Optional[dict]:
    """GET the GitHub API's 'latest release' endpoint. Returns the
    parsed JSON dict, or None on ANY failure -- timeout, non-200, a
    response that isn't valid JSON, no internet at all."""
    request = urllib.request.Request(_API_URL, headers={"User-Agent": _USER_AGENT})
    # Deliberately broad. Named exception classes kept letting real
    # failures through: http.client.IncompleteRead (server closes the
    # connection mid-body) isn't an OSError, and json.loads on non-UTF-8
    # bytes raises UnicodeDecodeError, not JSONDecodeError. This module's
    # entire job is "never raise, report failure by return value," so the
    # catch-all IS the contract here, not laziness.
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except Exception:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None


def download_file(url: str, dest_path: Path, timeout: float = 30.0) -> bool:
    """Streams url to dest_path. Returns whether it succeeded."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with dest_path.open("wb") as handle:
                handle.write(response.read())
        return True
    except Exception:  # broad on purpose -- see fetch_latest_release above
        return False
