# Auto-Update (v2.5.3) Implementation Plan

**Goal:** Add a background check that notices when a newer Lock In release exists, downloads and unpacks it quietly, and offers a one-click "Restart now" that swaps the old app for the new one and reopens it — without ever interrupting a focus block or the lockdown screen, and without ever breaking the app if anything along the way goes wrong.

**Architecture:** Three new pure-to-thin modules, same tier system the rest of the codebase already uses — `lock_in/updater.py` (pure version-compare/asset-pick logic, stdlib only, fully unit-tested, no network), `lock_in/update_fetch.py` (the one network shell, parallel to `claude_fallback.py`, tested with a fake `urlopen`), and `lock_in/update_apply.py` (the platform shell that unpacks the archive and writes/launches the per-OS relaunch script, parallel to `monitor.py`/`notifier.py`). `ui.py` wires a background thread into the existing `_pump()`/`queue.Queue` cross-thread pattern already used for window/camera/Claude/banner messages, and adds one persistent header notice plus one Settings switch.

**Tech Stack:** Python 3, stdlib only (`urllib`, `zipfile`, `tarfile`, `tempfile`, `subprocess`, `threading`) — no new entry in `requirements.txt`.

## Global Constraints

- Repo constant, verbatim: `REPO = "SVerma2696/Lock-In-Rider"` in `update_fetch.py`.
- Release asset names, verbatim, must match `release.yml`'s `matrix.asset_name` values exactly: `"LockIn-Windows.zip"` (`win32`), `"LockIn-macOS.zip"` (`darwin`), `"LockIn-Linux.tar.gz"` (`linux`).
- Expected file/bundle inside each archive, verbatim: `"Lock In.exe"` (`win32`), `"Lock In.app"` (`darwin`), `"Lock In"` (`linux`) — these come from exactly how `release.yml` packages each platform's build.
- **Fail-silent contract.** Every failure path — no internet, GitHub down, malformed JSON, unparseable version tag, no matching asset, a download that fails partway, a corrupt or unexpected archive, a file-swap that can't complete — results in "nothing happens, the app keeps running exactly as it was." Never a raised exception reaching `ui.py`, never a crash, never a dialog.
- **The restart button must never act during a focus block or lockdown.** Re-checked at click time (`self.session.phase is Phase.FOCUS or self._lockdown_window is not None`), not just when the notice was first shown — a focus block could start after the notice appeared.
- `Config.check_for_updates: bool = True` — on by default. This is the approved design decision (every other network-touching feature in this app is opt-in; this one isn't, because it sends nothing personal), not an oversight to "fix" during implementation.
- Running from source (`getattr(sys, "frozen", False)` is falsy) still runs the check, but skips the download/extract steps and shows a plain notice with no restart button instead.
- Each task ends with its own local `git commit` — a normal checkpoint on this plan's own working branch. Nothing in this plan ever runs `git push` or `git tag`; the final task only prints those commands for the user to run themselves.
- `__version__` (`lock_in/__init__.py`, currently `"2.5.2"`) is bumped to `"2.5.3"` only in the final task, immediately before the git commands are handed to the user — not any earlier.

---

### Task 1: `lock_in/updater.py` — pure version-compare and asset-pick logic

**Files:**
- Create: `lock_in/updater.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Produces: `UpdateInfo` (dataclass: `version: str`, `asset_name: str`, `download_url: str`), `ASSET_NAMES` (dict), `parse_version(tag: str) -> Optional[tuple]`, `is_newer(current: str, latest_tag: str) -> bool`, `pick_asset(assets: list, platform: str) -> Optional[dict]`, `check_for_update(current_version: str, release_data: dict, platform: str) -> Optional[UpdateInfo]`. Consumed by Task 4 (`ui.py`'s background thread).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_updater.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_updater.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.updater'`

- [ ] **Step 3: Implement `lock_in/updater.py`**

```python
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
    version = parse_version(tag)
    return UpdateInfo(
        version=".".join(str(p) for p in version),
        asset_name=asset["name"],
        download_url=asset["browser_download_url"],
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_updater.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add lock_in/updater.py tests/test_updater.py
git commit -m "Add pure version-compare/asset-pick logic for auto-update (updater.py)"
```

---

### Task 2: `lock_in/update_fetch.py` — the network shell

**Files:**
- Create: `lock_in/update_fetch.py`
- Test: `tests/test_update_fetch.py`

**Interfaces:**
- Produces: `REPO` (str constant), `fetch_latest_release(timeout: float = 5.0) -> Optional[dict]`, `download_file(url: str, dest_path: Path, timeout: float = 30.0) -> bool`. Consumed by Task 4 (`ui.py`'s background thread).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_update_fetch.py`:

```python
"""
Tests for update_fetch.py. Nothing here ever opens a real socket --
urllib.request.urlopen is swapped out for a small fake context manager,
the same "fake stands in for the one network call site" idea
test_claude_fallback.py uses for the Claude SDK client.
"""

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_update_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.update_fetch'`

- [ ] **Step 3: Implement `lock_in/update_fetch.py`**

```python
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
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except (urllib.error.URLError, OSError):
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
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
    except (urllib.error.URLError, OSError):
        return False
```

(`TimeoutError` is a subclass of `OSError` in Python 3, so `except (urllib.error.URLError, OSError)` already covers a timed-out request — no separate `TimeoutError` clause needed.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_update_fetch.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add lock_in/update_fetch.py tests/test_update_fetch.py
git commit -m "Add the GitHub-release network shell for auto-update (update_fetch.py)"
```

---

### Task 3: `lock_in/update_apply.py` — the platform shell

**Files:**
- Create: `lock_in/update_apply.py`
- Test: `tests/test_update_apply.py`

**Interfaces:**
- Produces: `EXPECTED_ENTRY` (dict), `extract_archive(archive_path: Path, dest_dir: Path, platform: str) -> Optional[Path]`, `current_app_path(platform: str) -> Path`, `write_relauncher_script(script_dir: Path, current_path: Path, new_path: Path, pid: int, platform: str) -> Path`, `launch_relauncher_and_quit(script_path: Path, platform: str) -> None`. Consumed by Task 4 (`extract_archive`) and Task 5 (`current_app_path`, `write_relauncher_script`, `launch_relauncher_and_quit`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_update_apply.py`:

```python
"""
Tests for update_apply.py. extract_archive is tested against real, tiny
archives built on the fly in tmp_path -- no network needed. The
relaunch scripts are checked by their written text (the right paths and
PID show up in the right places) rather than by actually running them,
since a script that closes the real process isn't something pytest can
safely execute. launch_relauncher_and_quit itself (which really does
start a detached process) is exercised only by the manual verification
pass in the final task of this plan.
"""

import io
import tarfile
import zipfile
from pathlib import Path

from lock_in.update_apply import (
    current_app_path, extract_archive, write_relauncher_script,
)


def _make_zip(path, entry_name: str, content: bytes = b"exe bytes") -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(entry_name, content)


def _make_tar_gz(path, entry_name: str, content: bytes = b"binary bytes") -> None:
    with tarfile.open(path, "w:gz") as archive:
        data = io.BytesIO(content)
        info = tarfile.TarInfo(name=entry_name)
        info.size = len(content)
        archive.addfile(info, data)


def test_extract_archive_zip_finds_the_expected_exe(tmp_path):
    archive_path = tmp_path / "LockIn-Windows.zip"
    _make_zip(archive_path, "Lock In.exe")
    dest = tmp_path / "extracted"
    result = extract_archive(archive_path, dest, "win32")
    assert result == dest / "Lock In.exe"
    assert result.read_bytes() == b"exe bytes"


def test_extract_archive_tar_gz_finds_the_expected_binary(tmp_path):
    archive_path = tmp_path / "LockIn-Linux.tar.gz"
    _make_tar_gz(archive_path, "Lock In")
    dest = tmp_path / "extracted"
    result = extract_archive(archive_path, dest, "linux")
    assert result == dest / "Lock In"


def test_extract_archive_returns_none_when_expected_entry_missing(tmp_path):
    archive_path = tmp_path / "LockIn-Windows.zip"
    _make_zip(archive_path, "some_other_file.txt")
    dest = tmp_path / "extracted"
    assert extract_archive(archive_path, dest, "win32") is None


def test_extract_archive_returns_none_for_corrupt_archive(tmp_path):
    archive_path = tmp_path / "LockIn-Windows.zip"
    archive_path.write_bytes(b"not a real zip file")
    dest = tmp_path / "extracted"
    assert extract_archive(archive_path, dest, "win32") is None


def test_extract_archive_returns_none_for_unknown_platform(tmp_path):
    archive_path = tmp_path / "LockIn-Windows.zip"
    _make_zip(archive_path, "Lock In.exe")
    dest = tmp_path / "extracted"
    assert extract_archive(archive_path, dest, "freebsd") is None


def test_current_app_path_on_windows_is_the_executable(monkeypatch):
    monkeypatch.setattr("sys.executable", r"C:\Users\me\Downloads\Lock In.exe")
    assert current_app_path("win32") == Path(r"C:\Users\me\Downloads\Lock In.exe")


def test_current_app_path_on_macos_is_the_app_bundle_root(monkeypatch):
    monkeypatch.setattr(
        "sys.executable",
        "/Users/me/Downloads/Lock In.app/Contents/MacOS/Lock In",
    )
    assert current_app_path("darwin") == Path("/Users/me/Downloads/Lock In.app")


def test_write_relauncher_script_windows_contains_pid_and_paths(tmp_path):
    script = write_relauncher_script(
        tmp_path, Path(r"C:\App\Lock In.exe"), Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242, platform="win32",
    )
    text = script.read_text()
    assert script.name == "update.bat"
    assert "4242" in text
    assert r"C:\App\Lock In.exe" in text
    assert r"C:\App\Lock In.exe.old" in text


def test_write_relauncher_script_macos_contains_pid_and_open_command(tmp_path):
    script = write_relauncher_script(
        tmp_path, Path("/Apps/Lock In.app"), Path("/tmp/Lock In.app"),
        pid=99, platform="darwin",
    )
    text = script.read_text()
    assert script.name == "update.sh"
    assert "kill -0 99" in text
    assert 'open "/Apps/Lock In.app"' in text


def test_write_relauncher_script_linux_contains_chmod_and_nohup(tmp_path):
    script = write_relauncher_script(
        tmp_path, Path("/opt/Lock In"), Path("/tmp/Lock In"),
        pid=77, platform="linux",
    )
    text = script.read_text()
    assert "chmod +x" in text
    assert "nohup" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_update_apply.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.update_apply'`

- [ ] **Step 3: Implement `lock_in/update_apply.py`**

```python
"""
update_apply.py
================
The one platform-specific shell in the auto-update feature: unpacking
the downloaded release archive, and -- once you click "Restart now" --
writing and launching the small script that swaps the old app for the
new one and reopens it. Same "thin, per-OS, orchestration only" shape
as monitor.py and notifier.py.

Nothing here ever runs the actual swap itself; that only happens inside
the detached script this module writes, after this process has already
quit -- a running program can't safely delete or replace its own file.
"""

from __future__ import annotations

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Optional

EXPECTED_ENTRY = {
    "win32": "Lock In.exe",
    "darwin": "Lock In.app",
    "linux": "Lock In",
}

_WAIT_TRIES = 15   # ~15 seconds (Windows: 1s/try) / ~4.5s (macOS/Linux: 0.3s/try) before giving up


def extract_archive(archive_path: Path, dest_dir: Path, platform: str) -> Optional[Path]:
    """Unzips or untars archive_path into dest_dir, then checks
    EXPECTED_ENTRY[platform] actually exists inside. Returns that path,
    or None if extraction failed, platform is unrecognized, or the
    expected file/bundle isn't there -- the sanity check that keeps a
    half-downloaded or unexpected archive from ever reaching the swap
    step."""
    expected_name = EXPECTED_ENTRY.get(platform)
    if expected_name is None:
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        if archive_path.name.endswith(".zip"):
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(dest_dir)
        elif archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as archive:
                archive.extractall(dest_dir)
        else:
            return None
    except (zipfile.BadZipFile, tarfile.TarError, OSError):
        return None

    extracted = dest_dir / expected_name
    return extracted if extracted.exists() else None


def current_app_path(platform: str) -> Path:
    """Windows/Linux: the running executable itself. macOS: the whole
    .app bundle three levels up from the executable inside it
    (Lock In.app/Contents/MacOS/Lock In) -- the whole bundle is what
    gets swapped, not just the inner binary."""
    exe_path = Path(sys.executable)
    if platform == "darwin":
        return exe_path.parents[2]
    return exe_path


def write_relauncher_script(script_dir: Path, current_path: Path, new_path: Path,
                             pid: int, platform: str) -> Path:
    """Writes update.bat (Windows) or update.sh (macOS/Linux) into
    script_dir. In plain words, the script: waits for this process
    (pid) to actually exit, renames current_path to '<name>.old' as a
    backup, moves new_path into current_path's place, reopens it, then
    deletes itself. The wait loop is capped at _WAIT_TRIES so a process
    that never exits can't leave it spinning forever -- it just gives up
    and leaves the .old backup sitting there, untouched, rather than
    deleting anything."""
    script_dir.mkdir(parents=True, exist_ok=True)

    if platform == "win32":
        script_path = script_dir / "update.bat"
        script_path.write_text(
            "@echo off\n"
            "set TRIES=0\n"
            ":wait\n"
            f"tasklist /fi \"PID eq {pid}\" | find \"{pid}\" >nul\n"
            "if errorlevel 1 goto swap\n"
            "set /a TRIES+=1\n"
            f"if %TRIES% geq {_WAIT_TRIES} goto swap\n"
            "timeout /t 1 >nul\n"
            "goto wait\n"
            ":swap\n"
            f"move /y \"{current_path}\" \"{current_path}.old\" >nul\n"
            f"move /y \"{new_path}\" \"{current_path}\" >nul\n"
            f"start \"\" \"{current_path}\"\n"
            "del \"%~f0\"\n",
            encoding="utf-8",
        )
        return script_path

    script_path = script_dir / "update.sh"
    reopen = (f'open "{current_path}"' if platform == "darwin"
              else f'chmod +x "{current_path}" && nohup "{current_path}" >/dev/null 2>&1 &')
    script_path.write_text(
        "#!/bin/sh\n"
        "TRIES=0\n"
        f"while kill -0 {pid} 2>/dev/null; do\n"
        "    TRIES=$((TRIES + 1))\n"
        f"    if [ \"$TRIES\" -ge {_WAIT_TRIES} ]; then break; fi\n"
        "    sleep 0.3\n"
        "done\n"
        f'mv "{current_path}" "{current_path}.old"\n'
        f'mv "{new_path}" "{current_path}"\n'
        f"{reopen}\n"
        'rm -- "$0"\n',
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def launch_relauncher_and_quit(script_path: Path, platform: str) -> None:
    """Starts script_path as a fully detached process, so it keeps
    running after this one exits. Does NOT close the app itself --
    ui.py calls its normal _on_close() right after this returns, so
    settings/tasks/history are saved exactly like any other quit."""
    if platform == "win32":
        subprocess.Popen(
            ["cmd", "/c", str(script_path)],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )
    else:
        subprocess.Popen(["/bin/sh", str(script_path)], start_new_session=True)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_update_apply.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add lock_in/update_apply.py tests/test_update_apply.py
git commit -m "Add the archive-extraction and relaunch-script platform shell (update_apply.py)"
```

---

### Task 4: `config.py` + `ui.py` — the background check, on by default

**Files:**
- Modify: `lock_in/config.py`
- Modify: `lock_in/ui.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `updater.check_for_update` (Task 1), `update_fetch.fetch_latest_release`/`download_file` (Task 2), `update_apply.extract_archive` (Task 3), `lock_in.__version__`.
- Produces: `Config.check_for_updates: bool` field. `LockInApp._update_queue`, `LockInApp._pending_update`, `LockInApp.update_frame`/`update_label`/`update_restart_button` (built in `_build_header`), `LockInApp._start_update_check()`, `LockInApp._drain_update_queue()`, `LockInApp._show_update_ready_frame(info, extracted_path)`. Consumed by Task 5 (`_on_restart_update_clicked`, which this task wires the button to but does not yet define — same forward-reference pattern the tier5 plan used between its Tasks 4 and 5).

- [ ] **Step 1: Write the failing config test**

Add to `tests/test_config.py`:

```python
def test_check_for_updates_defaults_to_on():
    assert Config().check_for_updates is True
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_config.py -k check_for_updates -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'check_for_updates'`

- [ ] **Step 3: Add the field to `Config`**

In `lock_in/config.py`, directly below the existing `record_observations: bool = True` field (in the "Write down EVERY window seen during focus..." comment block):

```python
    # Auto-update: on by default. When it's on, the app quietly asks
    # GitHub once per launch whether a newer release exists -- nothing
    # about you or your machine is sent, just "what's your latest
    # version?". Turning this off stops that check from ever happening.
    check_for_updates: bool = True
```

- [ ] **Step 4: Run the config test to verify it passes**

Run: `pytest tests/test_config.py -k check_for_updates -v`
Expected: PASS

- [ ] **Step 5: Add the new imports to `ui.py`**

In `lock_in/ui.py`, change the top-of-file import block. Change:

```python
import dataclasses
import queue
import sys
import time
from datetime import datetime
from typing import List, Optional
```

to:

```python
import dataclasses
import os
import queue
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
```

Directly below the existing `from .history import HistoryStore, SessionRecord` line, add:

```python
from . import __version__, update_apply, update_fetch, updater
from .updater import UpdateInfo
```

- [ ] **Step 6: Add the update-check state in `__init__`**

In `lock_in/ui.py`, `__init__`, directly below the existing `self._banner_after_id: Optional[str] = None` line:

```python
        self._update_queue: "queue.Queue[tuple]" = queue.Queue()
        # (UpdateInfo, Optional[Path]) once the background check finds
        # something -- Path is None exactly when running from source
        # (see _start_update_check), which has no file to swap.
        self._pending_update: Optional[tuple] = None
```

- [ ] **Step 7: Add the persistent header notice (built hidden)**

In `lock_in/ui.py`, `_build_header()`, directly below the existing:

```python
        # A short pop-up message banner. Starts hidden; _show_banner reveals it.
        self.banner = ctk.CTkLabel(
            header, text="", corner_radius=8, height=44,
            font=ctk.CTkFont(size=13), wraplength=480, justify="left",
        )
```

add:

```python
        # A persistent "a new version is ready" notice -- unlike self.banner
        # above, this stays up until you act on it (or the app restarts
        # itself), since a one-time toast could easily be missed and
        # staying visible is the whole point. Starts hidden;
        # _show_update_ready_frame reveals it.
        self.update_frame = ctk.CTkFrame(header, fg_color=self.color_surface, corner_radius=8)
        self.update_label = ctk.CTkLabel(
            self.update_frame, text="", font=ctk.CTkFont(size=12), anchor="w",
        )
        self._mpack(self.update_label, side="left", padx=(10, 6), pady=8, fill="x", expand=True)
        self.update_restart_button = ctk.CTkButton(
            self.update_frame, text="Restart now", width=110,
            command=self._on_restart_update_clicked,
        )
        self._mpack(self.update_restart_button, side="right", padx=(0, 10), pady=8)
```

(`_on_restart_update_clicked` is defined in Task 5 — this button's `command` is a dead reference until then, exactly like `_refresh_current_task_picker`'s forward reference in the tier5-tasks-history plan's Task 4. Both tasks land in the same implementation pass, so this is expected and harmless.)

- [ ] **Step 8: Add the background-check method and its queue drain**

Add these methods near `_warn_if_app_detection_unavailable`:

```python
    def _start_update_check(self) -> None:
        """Kicks off the one-per-launch background check for a newer
        release. Runs entirely off the main thread -- fetching from
        GitHub, and (only for the packaged app) downloading and
        unpacking the update -- so it can never freeze the window."""
        if not self.config_obj.check_for_updates:
            return

        def run() -> None:
            release_data = update_fetch.fetch_latest_release()
            if release_data is None:
                return
            info = updater.check_for_update(__version__, release_data, sys.platform)
            if info is None:
                return

            extracted_path: Optional[Path] = None
            if getattr(sys, "frozen", False):
                temp_dir = Path(tempfile.mkdtemp(prefix="lockin_update_"))
                archive_path = temp_dir / info.asset_name
                if not update_fetch.download_file(info.download_url, archive_path):
                    return
                extracted_path = update_apply.extract_archive(archive_path, temp_dir, sys.platform)
                if extracted_path is None:
                    return

            self._update_queue.put((info, extracted_path))

        threading.Thread(target=run, daemon=True, name="update-check").start()

    def _drain_update_queue(self) -> None:
        """The background update check (started once at launch) reports
        back here, on the main thread."""
        try:
            info, extracted_path = self._update_queue.get_nowait()
        except queue.Empty:
            return
        self._show_update_ready_frame(info, extracted_path)

    def _show_update_ready_frame(self, info: UpdateInfo, extracted_path: Optional[Path]) -> None:
        """Reveals the persistent header notice built in _build_header().
        extracted_path is None exactly when running from source (see
        _start_update_check) -- there's no file to swap in that case,
        so the restart button is hidden and the text points at the
        Releases page instead."""
        self._pending_update = (info, extracted_path)
        if extracted_path is None:
            self.update_label.configure(
                text=f"Lock In v{info.version} is available \u2014 see the Releases page.")
            self.update_restart_button.pack_forget()
        else:
            self.update_label.configure(text=f"Update ready \u2014 v{info.version}")
            self._mpack(self.update_restart_button, side="right", padx=(0, 10), pady=8)
        self._mpack(self.update_frame, fill="x", pady=(0, 10), before=self.phase_label)
```

- [ ] **Step 9: Wire the check into startup and the drain into the heartbeat**

In `lock_in/ui.py`, `__init__`, directly below the existing:

```python
        self.after(400, self._warn_if_app_detection_unavailable)
```

add:

```python
        self.after(2000, self._start_update_check)
```

In `lock_in/ui.py`, `_pump()`, change:

```python
            self._drain_window_queue()
            self._drain_camera_queue()
            self._drain_claude_queue()
            self._drain_banner_queue()
            self._refresh_timer_widgets()
```

to:

```python
            self._drain_window_queue()
            self._drain_camera_queue()
            self._drain_claude_queue()
            self._drain_banner_queue()
            self._drain_update_queue()
            self._refresh_timer_widgets()
```

- [ ] **Step 10: Add the Settings tab switch**

In `lock_in/ui.py`, `_build_settings_tab()`, directly below the existing:

```python
        self.toast_var = ctk.BooleanVar(value=self.config_obj.toast_enabled)
        self._mpack(ctk.CTkSwitch(frame, text="Desktop notifications", variable=self.toast_var,
                      progress_color=COLOR_LOOK_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=4)
```

add:

```python
        self.check_updates_var = ctk.BooleanVar(value=self.config_obj.check_for_updates)
        self._mpack(ctk.CTkSwitch(frame, text="Automatically check for updates",
                      variable=self.check_updates_var, progress_color=COLOR_LOOK_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=4)
```

In `lock_in/ui.py`, `_save_from_widgets()`, change:

```python
        if hasattr(self, "autobreak_var"):
            c.auto_start_breaks = self.autobreak_var.get()
            c.auto_start_focus = self.autofocus_var.get()
            c.sound_enabled = self.sound_var.get()
            c.toast_enabled = self.toast_var.get()
        c.save()
```

to:

```python
        if hasattr(self, "autobreak_var"):
            c.auto_start_breaks = self.autobreak_var.get()
            c.auto_start_focus = self.autofocus_var.get()
            c.sound_enabled = self.sound_var.get()
            c.toast_enabled = self.toast_var.get()
            c.check_for_updates = self.check_updates_var.get()
        c.save()
```

- [ ] **Step 11: Run the full test suite**

Run: `pytest -v`
Expected: all PASS (this step's `ui.py` changes add no new automated tests of their own beyond Step 1's config test — widget/thread wiring, matching the precedent set by every prior tier's UI-wiring tasks; verified manually in Task 7)

- [ ] **Step 12: Commit**

```bash
git add lock_in/config.py lock_in/ui.py tests/test_config.py
git commit -m "Wire the background update check into ui.py, on by default"
```

---

### Task 5: `ui.py` — the "Restart now" button and the version line

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `self._pending_update` (Task 4), `update_apply.current_app_path`/`write_relauncher_script`/`launch_relauncher_and_quit` (Task 3), `self.session.phase`, `self._lockdown_window`, `self._on_close()` (all pre-existing), `__version__` (Task 4's import).
- Produces: `LockInApp._on_restart_update_clicked()` (fulfills Task 4's forward reference). Help tab gains a version line — no new symbol.

No dedicated automated test for the click handler itself — it starts a real detached process and closes the real app, neither of which pytest can safely exercise (same category as `launch_relauncher_and_quit` in Task 3). Verified manually in Task 7.

- [ ] **Step 1: Add the click handler**

Add this method near `_on_restart_update_clicked`'s sibling handlers (e.g. directly after `_drain_update_queue`/`_show_update_ready_frame` from Task 4):

```python
    def _on_restart_update_clicked(self) -> None:
        """Runs the file swap and reopens the app -- but only when doing
        so can't cut off an active focus block or the lockdown screen.
        Clicking during either of those is a no-op with an explanation,
        never a forced interruption. Re-checked here, at click time, not
        just when the notice first appeared -- a focus block could have
        started in between."""
        if self._pending_update is None:
            return
        info, extracted_path = self._pending_update
        if extracted_path is None:
            return  # no button should be visible in this case; guard anyway

        if self.session.phase is Phase.FOCUS or self._lockdown_window is not None:
            self._show_banner("Finish your focus block first.", "normal")
            return

        current_path = update_apply.current_app_path(sys.platform)
        script_path = update_apply.write_relauncher_script(
            extracted_path.parent, current_path, extracted_path,
            pid=os.getpid(), platform=sys.platform,
        )
        update_apply.launch_relauncher_and_quit(script_path, sys.platform)
        self._on_close()
```

- [ ] **Step 2: Add the version line to the Help tab**

In `lock_in/ui.py`, `_build_help_tab()`, directly below the existing final block:

```python
        body(
            "A separate extra, nothing to do with heroes: turn it on in "
            "the Blocking tab, and Lock In peeks at your webcam every "
            "few seconds during a focus block to check for a phone. If "
            "it sees one, you get warned the same way you would for a "
            "blocked app. It's off unless you turn it on. It only "
            "watches during an actual focus block -- the second a "
            "break starts, or you flip the switch back off, the camera "
            "turns off too. Watch for the little \"Camera monitoring "
            "active\" words under the timer: the camera is only ever "
            "on when those words are showing."
        )
```

add:

```python

        # --- Version ------------------------------------------------ #
        heading("7. Version", COLOR_IDLE)
        body(f"You're running Lock In v{__version__}.")
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add lock_in/ui.py
git commit -m "Add the update-restart click handler and the Help tab version line"
```

---

### Task 6: README.md and .gitignore

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`

No automated test — documentation only.

- [ ] **Step 1: Add the Auto-Update section to README.md**

In `README.md`, directly below the closing `---` of the "🚀 Releases" section (right before `## ⚙️ Features`), insert:

```markdown
## 🔄 Auto-Update

**In plain words:** the app quietly checks once when it opens whether a
newer version exists. If it does, a small button appears saying
"Update ready — restart now." Click it whenever you're ready — never
while you're mid-focus-block, the button simply won't do anything until
you finish — and it closes, swaps itself for the new version, and
reopens, same as if you'd downloaded it by hand.

- Only checks when you're online; if it can't reach GitHub, nothing
  happens and the app works exactly as it did before.
- Only sends one anonymous thing to GitHub: "what's your newest
  release?" — nothing about you or your machine.
- Turn it off anytime: Settings tab → "Automatically check for
  updates."
- Only works for the app downloaded from Releases. Running it from
  source (`python main.py`)? Use `git pull` instead — you'll still see
  a small "update available" note, just without the restart button.

---
```

- [ ] **Step 2: Add one line each to Requirements and Known limits**

In `README.md`, in the `## 🔧 Requirements` section, directly below the existing:

```markdown
* Optional: the `anthropic` SDK + an API key, only if you turn on the
  [Claude fallback](#claude-fallback-optional-off-by-default)
```

add:

```markdown
* Auto-update needs no new dependency — it's built entirely from the
  standard library already required to run Python at all.
```

In `README.md`, in the `## Known limits` section, directly below the existing:

```markdown
- **Tasks can't be deleted or un-marked done from the app yet** — once
  something is checked off, hiding it again means editing `tasks.json`
  by hand. Past entries in the session diary (`sessions.jsonl`) can't be
  edited from the app either. Both are on the list for later.
```

add:

```markdown
- **Auto-update only replaces the downloaded app** — a source checkout
  (`python main.py`) shows the same "update available" note but needs
  `git pull` instead of a restart button.
```

- [ ] **Step 3: Add the three new files to the Project Structure tree**

In `README.md`, in the Project Structure ASCII tree (the fenced block starting with `Lock In/`), directly below the existing `visuals.py` line:

```
│   ├── visuals.py               Display font pick, plus Pillow-generated glow,
│   │                           background art, and app-icon loading.
```

add:

```
│   ├── updater.py               Pure version-compare/asset-pick logic for
│   │                           auto-update (no network, no filesystem).
```

and directly below the existing `notifier.py` line:

```
│   └── notifier.py              Toasts and sounds: winotify/winsound (Windows),
│                               osascript/afplay (macOS), notify-send/paplay (Linux).
```

change the `└──` to `├──` and add two new lines after it:

```
│   ├── notifier.py              Toasts and sounds: winotify/winsound (Windows),
│   │                           osascript/afplay (macOS), notify-send/paplay (Linux).
│   ├── update_fetch.py          The one network call in auto-update: asks GitHub
│   │                           for the latest release, downloads the matching file.
│   └── update_apply.py          Unpacks the downloaded release and writes/launches
│                               the per-OS relaunch script that swaps files.
```

- [ ] **Step 4: Add the .gitignore safety net**

In `.gitignore`, directly below the existing:

```
# App data (settings, trained model, training data) — this lives in
# %APPDATA%\Lock In\ on Windows, not in this project folder, so it
# normally won't show up here. This is just a safety net in case any
# of it ever gets created locally.
config.json
model.json
observations.jsonl
tasks.json
sessions.jsonl
lockin_training_data.csv
app_icon.ico
app_icon_square.png
```

add:

```

# Safety net for the auto-updater's temp files, in case anything ever
# runs from inside this folder during manual testing -- the real thing
# always downloads and unpacks in the OS temp folder, never this one.
*.old
lockin_update_tmp/
```

- [ ] **Step 5: Commit**

```bash
git add README.md .gitignore
git commit -m "Document auto-update in README.md; add its .gitignore safety net"
```

---

### Task 7: Manual verification, version bump, and handoff to the user

**Files:**
- Modify: `lock_in/__init__.py` (`__version__` bump — the only code change in this task)

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: all tests pass, including everything added in Tasks 1–4.

- [ ] **Step 2: Verify by hand with a forced fake update**

Since a real newer GitHub release doesn't exist yet, temporarily prove the pipeline end-to-end with a fake one. In a Python shell (or a scratch script) with the app's virtualenv active:

```python
from lock_in import updater
info = updater.check_for_update(
    "2.5.2",
    {"tag_name": "v99.0.0", "assets": [{"name": "LockIn-Windows.zip", "browser_download_url": "http://example.com/fake.zip"}]},
    "win32",
)
print(info)  # should print an UpdateInfo, confirming Task 1's logic end-to-end
```

Then, with `python main.py` running (source, not frozen — `getattr(sys, "frozen", False)` is `False`), temporarily call `app._show_update_ready_frame(info, None)` from a debugger or a one-off `self.after(3000, lambda: self._show_update_ready_frame(info, None))` line added and then removed from `__init__` — confirm:
1. The persistent notice appears above the phase label, reading `"Lock In v99.0.0 is available — see the Releases page."` with no button (the `extracted_path=None` / running-from-source branch).
2. Toggling Settings → "Automatically check for updates" off, restarting the app, and confirming no notice appears and no network call is attempted (the switch's `False` value is what `_start_update_check` reads).

- [ ] **Step 3: Verify the restart guard by hand**

With the same temporary `_show_update_ready_frame(info, Path("some/fake/path"))` call (a non-`None` path so the button appears): start a focus block, click "Restart now" — confirm you see the "Finish your focus block first." toast and the app does *not* close. Then let the block end (or Skip/Reset it) and click again — confirm this time it proceeds to `_on_close()` (it's fine if the fake path makes `write_relauncher_script`/`launch_relauncher_and_quit` themselves error in this contrived test — the point of this step is confirming the *guard*, not a full real swap; a full real swap is Step 4).

Remove the temporary debug call/line once this and Step 2 are confirmed — nothing from this manual step should remain in the committed code.

- [ ] **Step 4: One real dry-run swap-and-relaunch, before this ships**

Build the app with `build.bat` (or the real `pyinstaller` command from `release.yml`), producing a real `Lock In.exe`. Publish a throwaway tag on GitHub — it must be a **normal release, NOT marked "pre-release"**, and the tag must be exactly 3 numeric dot-separated parts (e.g. `v99.0.0`, never `v99.0.0-test`). Both constraints are real: GitHub's `/repos/.../releases/latest` endpoint never returns pre-releases, so a pre-release would simply never be seen; and `parse_version()` rejects anything that isn't 3 numeric parts, so a suffixed tag would be treated as "nothing to offer" even if it were returned. Attach that build zipped as `LockIn-Windows.zip`, run the built exe, let the real background check find it, click "Restart now" for real, and confirm the app actually closes, swaps files, and reopens as the "new" version. Delete the throwaway tag/release afterward. This is the one step in this plan that exercises `launch_relauncher_and_quit` and the real `.bat`/`.sh` script for real — everything else about them is covered by Task 3's content-based tests plus this one manual pass, exactly as flagged as a requirement in the approved spec's Testing section.

- [ ] **Step 5: Confirm nothing else regressed**

Spot-check that a normal Rider switch, the Tasks/Blocking/Activity/Settings/Help tabs, and Ryuki's mirror all still work exactly as before — this plan only adds to the header and Settings tab, it doesn't touch any existing tab's content.

- [ ] **Step 6: Bump the version**

In `lock_in/__init__.py`, change:

```python
__version__ = "2.5.2"
```

to:

```python
__version__ = "2.5.3"
```

- [ ] **Step 7: Commit the version bump**

```bash
git add lock_in/__init__.py
git commit -m "Bump version to 2.5.3"
```

- [ ] **Step 8: Give the user the commands to review, tag, and push**

Do not run any of these — print them for the user to run themselves:

```bash
git log --oneline main..HEAD
git tag v2.5.3
git push origin main
git push origin v2.5.3
```

Pushing the `v2.5.3` tag is what triggers `release.yml` to build and publish the Windows/macOS/Linux downloads — exactly the moment this whole feature starts being useful, since v2.5.2 users' apps will now be able to notice v2.5.3 exists.
