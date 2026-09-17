"""
updater.py
==========
Pure decision logic for the auto-update feature: does GitHub have a
newer version than this one, and if so, which release file matches
this computer's operating system? No network calls, no filesystem
access, no platform-specific behavior beyond a plain dictionary lookup
-- the same "stdlib only, fully unit-tested" rule config.py/session.py/
classifier.py already follow.

update_fetch.py does the actual GitHub request this module's functions
are fed from. update_apply.py does the actual file download/swap once
this module says one is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


ASSET_NAMES = {
    "win32": "LockIn-Windows.zip",
    "darwin": "LockIn-macOS.zip",
    "linux": "LockIn-Linux.tar.gz",
}


@dataclass
class UpdateInfo:
    """Everything ui.py needs to know about an update that's available."""

    version: str          # "2.5.3" -- no leading "v"
    asset_name: str        # "LockIn-Windows.zip"
    download_url: str      # straight from the release's asset list


def parse_version(tag: str) -> Optional[tuple]:
    """'v2.5.3' -> (2, 5, 3). None if it doesn't look like a version --
    an unparseable tag is treated as "nothing to offer", never as
    "obviously newer, update anyway"."""
    text = tag.strip()
    if text.startswith("v"):
        text = text[1:]
    parts = text.split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def is_newer(current: str, latest_tag: str) -> bool:
    """True only if latest_tag parses AND is strictly greater than
    current. Either side failing to parse means False, not True."""
    current_parsed = parse_version(current)
    latest_parsed = parse_version(latest_tag)
    if current_parsed is None or latest_parsed is None:
        return False
    return latest_parsed > current_parsed


def pick_asset(assets: list, platform: str) -> Optional[dict]:
    """assets is the GitHub API's raw list of {"name", "browser_download_url"}
    dicts for one release. None if this platform isn't in ASSET_NAMES,
    or none of the assets has the matching name."""
    wanted = ASSET_NAMES.get(platform)
    if wanted is None:
        return None
    for asset in assets:
        if asset.get("name") == wanted:
            return asset
    return None


def check_for_update(current_version: str, release_data: dict, platform: str) -> Optional[UpdateInfo]:
    """release_data is one GitHub 'latest release' API response, already
    parsed from JSON (a dict with at least "tag_name" and "assets").
    Returns None for: not newer, malformed tag, or no matching asset
    for this platform -- the single function ui.py's background thread
    calls right after fetching."""
    tag = release_data.get("tag_name", "")
    if not is_newer(current_version, tag):
        return None
    asset = pick_asset(release_data.get("assets", []), platform)
    if asset is None:
        return None
    # .get(), not [], to match pick_asset's own defensive style two lines
    # up: a release whose asset dict is missing a download URL is just
    # "nothing to offer", never a KeyError out of a background thread.
    asset_name = asset.get("name")
    download_url = asset.get("browser_download_url")
    if not asset_name or not download_url:
        return None
    version = parse_version(tag)
    return UpdateInfo(
        version=".".join(str(p) for p in version),
        asset_name=asset_name,
        download_url=download_url,
    )
