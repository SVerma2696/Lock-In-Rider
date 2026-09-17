# Lock In: Auto-Update (v2.5.3)

Date: 2026-09-16
Status: Approved, ready for implementation plan

## Goal

Right now, finding out about a new release means remembering to check the
GitHub Releases page by hand. This adds a quiet background check: when the
downloaded app opens, it asks GitHub once whether a newer version exists,
and if so, offers a one-click "restart to update" — no manual download,
no unzip, no re-running the installer warnings.

Three properties drive every decision below:

1. **Never surprises you.** No popup, no forced restart, and the restart
   button flatly does not work while a focus block is running or the
   lockdown screen is up.
2. **Fails silent, not broken** — the exact contract `claude_fallback.py`
   already uses. No internet, GitHub down, a corrupt download, a missing
   file inside the archive, a permissions error during the file swap —
   every one of these just means "nothing happens," never a crash or an
   error dialog.
3. **Only touches the downloaded app.** Running from source
   (`python main.py`) has no single file to replace, so it only shows a
   plain notice pointing at the Releases page — no self-replace attempted.

## Where the version number lives

`lock_in/__init__.py` already has `__version__` (currently `"2.5.2"`) —
nothing new to add here, it becomes this feature's single source of
truth. It gets bumped to `"2.5.3"` as the last code edit of this
implementation, immediately before the release is tagged.

The Help tab gains one line showing it, e.g. `"You're running Lock In
v2.5.3."` — without this, nothing in the UI would ever tell you what
you're currently on, which is the number the update check is comparing
against.

## Three new modules

Following the same split the codebase already uses everywhere else
(pure logic vs. thin platform/network shells — see the Project Structure
table in README.md):

### `lock_in/updater.py` — pure logic, stdlib only, fully unit-tested

No network, no filesystem, no `sys.platform` branching beyond a plain
string lookup. Everything here takes plain data in and hands plain data
back, so it's tested the same way `classifier.py` and `session.py` are.

```python
@dataclass
class UpdateInfo:
    version: str          # "2.5.3" (no leading "v")
    asset_name: str        # "LockIn-Windows.zip"
    download_url: str      # from the release's asset list

def parse_version(tag: str) -> Optional[tuple[int, int, int]]:
    """'v2.5.3' -> (2, 5, 3). None if it doesn't look like a version."""

def is_newer(current: str, latest_tag: str) -> bool:
    """False (not True) if either string fails to parse — an
    unparseable tag is treated as 'nothing to offer', never as
    'obviously newer, update anyway'."""

ASSET_NAMES = {
    "win32": "LockIn-Windows.zip",
    "darwin": "LockIn-macOS.zip",
    "linux": "LockIn-Linux.tar.gz",
}

def pick_asset(assets: list[dict], platform: str) -> Optional[dict]:
    """assets is the GitHub API's raw list of {"name", "browser_download_url"}
    dicts. None if this platform has no matching asset name, or platform
    isn't a key in ASSET_NAMES at all."""

def check_for_update(current_version: str, release_data: dict, platform: str) -> Optional[UpdateInfo]:
    """release_data is one GitHub 'latest release' API response, already
    parsed from JSON. Returns None for: not newer, malformed tag, no
    matching asset for this platform. This is the single function
    ui.py's background thread calls after fetching."""
```

### `lock_in/update_fetch.py` — the network shell (parallel to `claude_fallback.py`)

```python
REPO = "SVerma2696/Lock-In-Rider"

def fetch_latest_release(timeout: float = 5.0) -> Optional[dict]:
    """GET https://api.github.com/repos/{REPO}/releases/latest with a
    User-Agent header (GitHub's API 403s without one). Returns the
    parsed JSON dict, or None on ANY failure — timeout, non-200, bad
    JSON, no internet. Never raises."""

def download_file(url: str, dest_path: Path, timeout: float = 30.0) -> bool:
    """Streams url to dest_path. Returns whether it succeeded — same
    'never raises, just reports success' shape."""
```

Built on `urllib.request` — stdlib, no new entry in `requirements.txt`.
Tested exactly like `test_claude_fallback.py` tests `ClaudeFallback`: a
fake object swapped in for the one network call site (here,
`urllib.request.urlopen`), so no test ever touches a real socket.

### `lock_in/update_apply.py` — the platform shell (parallel to `monitor.py` / `notifier.py`)

```python
EXPECTED_ENTRY = {
    "win32": "Lock In.exe",
    "darwin": "Lock In.app",
    "linux": "Lock In",
}

def extract_archive(archive_path: Path, dest_dir: Path, platform: str) -> Optional[Path]:
    """Unzips (.zip, via zipfile) or untars (.tar.gz, via tarfile) into
    dest_dir, then checks EXPECTED_ENTRY[platform] actually exists inside.
    Returns that path, or None if extraction failed or the expected file/
    bundle isn't there — the sanity check that stops a half-downloaded or
    unexpected archive from ever reaching the swap step."""

def current_app_path(platform: str) -> Path:
    """Windows/Linux: Path(sys.executable) (the running exe itself).
    macOS: walks up from sys.executable (.../Lock In.app/Contents/MacOS/Lock In)
    three parents to the .app bundle root, since the whole bundle is what
    gets swapped, not just the inner binary."""

def write_relauncher_script(script_dir: Path, current_path: Path, new_path: Path, pid: int, platform: str) -> Path:
    """Writes update.bat (Windows) or update.sh (macOS/Linux) into
    script_dir. See 'The relaunch script' below for exactly what it does."""

def launch_relauncher_and_quit(script_path: Path, platform: str) -> None:
    """Starts the script as a fully detached process (Windows:
    subprocess.Popen with CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS;
    macOS/Linux: subprocess.Popen with start_new_session=True) so it
    keeps running after this process exits. Does not itself close the
    app — ui.py calls its normal _on_close() right after this returns,
    so settings/tasks/history are saved exactly like any other quit."""
```

### The relaunch script

The one piece that can't run inside the app that's about to close. In
plain words: *"wait for the old program to actually finish closing, keep
a backup of it just in case, put the new one in its place, open it back
up, then clean up after yourself."* Concretely, per platform:

**Windows (`update.bat`)**
```bat
:wait
tasklist /fi "PID eq <pid>" | find "<pid>" >nul
if not errorlevel 1 (timeout /t 1 >nul & goto wait)
move /y "<current>" "<current>.old"
move /y "<new>" "<current>"
start "" "<current>"
del "%~f0"
```

**macOS / Linux (`update.sh`)**
```sh
while kill -0 <pid> 2>/dev/null; do sleep 0.3; done
mv "<current>" "<current>.old"
mv "<new>" "<current>"
# macOS: open "<current>"   |   Linux: chmod +x "<current>" && nohup "<current>" >/dev/null 2>&1 &
rm -- "$0"
```

Both loops are capped (≈15 tries) so a process that somehow never exits
can't leave the script spinning forever — it just gives up and leaves
the `.old` backup sitting there, untouched, rather than forcing anything.

**Why the `.old` rename instead of deleting outright:** if the `move`/`mv`
of the new file ever fails partway (permissions, disk full), the old
file is never destroyed — worst case, you have both files sitting there
and can rename `.old` back by hand. This is the one safety net standing
between "an update went wrong" and "the app won't open anymore."

## Wiring into `ui.py`

- **`Config.check_for_updates: bool = True`** — new field in
  `config.py`, same JSON-persisted pattern as every other switch, same
  "missing key in an old config.json just falls back to the default"
  behavior `Config.load()` already gives every field for free.
- **Settings tab** gets one new switch: `"Automatically check for
  updates"`, right alongside the other on/off switches (plain wording,
  not Rider-flavored — this is a technical setting, not a gimmick).
- **On startup**, after the main window is built and only if
  `self.config_obj.check_for_updates`:
  `self.after(2000, self._start_update_check)` — a short delay so this
  never competes with the window's first paint. `_start_update_check`
  spawns one daemon thread that does, entirely off the main thread:
  1. `update_fetch.fetch_latest_release()` — `None` means stop here,
     silently.
  2. `updater.check_for_update(__version__, release_data, sys.platform)`
     — `None` means stop here too (already current, unparseable tag, or
     no asset for this OS).
  3. **Only if `getattr(sys, "frozen", False)`** (a packaged download,
     not `python main.py` from source):
     `update_fetch.download_file(...)` into a fresh
     `tempfile.mkdtemp(prefix="lockin_update_")` — failure stops
     silently; then `update_apply.extract_archive(...)` — failure stops
     silently and removes the temp directory. Running from source skips
     straight to step 4 with no path to extract.
  4. Puts `(update_info, extracted_path_or_None)` on a new
     `self._update_queue: queue.Queue`, mirroring `_banner_queue`.
     `extracted_path` is `None` exactly when running from source, and
     `_drain_update_queue()` uses that to decide which of the two
     notices below to show.
- **A new `_drain_update_queue()`**, polled from the same `after()` loop
  that already calls `_drain_banner_queue()`. On a message, it builds a
  small persistent frame (not the auto-hiding toast `_show_banner` — this
  one stays up until acted on) packed in the same spot as the toast
  banner: a label reading `"Update ready — vX.Y.Z"` plus a `"Restart
  now"` button. Stored as `self._update_ready_frame` so it's easy to
  tear down after a successful click, and so `_build_tabs()` rebuilds
  never duplicate it (it lives outside the tab view, like the toast
  banner and the phase label).
- **Clicking "Restart now"** calls a handler that re-checks, right at
  click time: if `self.session.phase is Phase.FOCUS or self._lockdown_window
  is not None`, it does nothing to the app itself and instead shows the
  ordinary toast (`_show_banner("Finish your focus block first.",
  "normal")`) — so a click during a focus block is a no-op with an
  explanation, never a forced interruption. Otherwise: writes and
  launches the relaunch script via `update_apply.write_relauncher_script`
  + `launch_relauncher_and_quit`, then calls `self._on_close()` exactly
  as if the window's own close button had been pressed (same save path
  for settings/tasks/history, same monitor/ambient/camera shutdown).
- **Running from source** (`sys.frozen` is falsy): the same check still
  runs (still worth knowing a newer version exists), but on finding one,
  it skips the download/extract steps entirely and the persistent frame
  reads `"A new version (vX.Y.Z) is available — see the Releases page."`
  with no button, since there's no single file here to replace.

## Error handling

Every one of these results in exactly one outcome — the app keeps
running precisely as it was, with no dialog, no crash, no half-updated
state:

- No internet connection, or GitHub unreachable.
- GitHub API rate limit or a non-200 response.
- Malformed or unexpected JSON in the response.
- A release tag that doesn't parse as a version.
- No release asset matching the current OS.
- Download fails partway (network drop, disk full).
- A downloaded archive that's corrupt, or that doesn't contain the
  expected file/bundle once extracted.
- The relaunch script's file-swap step fails (permissions, file in use
  longer than the wait loop's cap) — the `.old` backup is left in place,
  nothing is deleted, the old app just doesn't reopen automatically and
  you can still run the backed-up file by hand.

## Testing

- **`tests/test_updater.py`** *(new)* — `parse_version`: valid tags,
  malformed tags (missing parts, non-numeric, no leading "v"). `is_newer`:
  strictly newer, equal, older, one side unparseable. `pick_asset`:
  matching name present, absent, empty asset list, unknown platform key.
  `check_for_update`: end-to-end over hand-built fake `release_data`
  dicts covering every `None`-returning branch above plus the success
  case. All pure, no network, no filesystem.
- **`tests/test_update_fetch.py`** *(new)* — `fetch_latest_release` and
  `download_file` with `urllib.request.urlopen` swapped for a fake
  (mirrors `test_claude_fallback.py`'s `install_fake_client` pattern):
  success, HTTP error, timeout/exception, malformed JSON body.
- **`tests/test_update_apply.py`** *(new)* — `extract_archive` against
  real small `.zip`/`.tar.gz` fixtures built in a `tmp_path` (no network
  needed): expected file present, expected file missing, corrupt archive
  bytes. `write_relauncher_script`: asserts the written script's text
  contains the right paths and PID for each of the three platform
  branches (string-content assertions — actually executing a script that
  closes the real process isn't something pytest can safely do).
- **Manual, in the running app** (same category as every prior tier — no
  automated GUI test covers this): force a fake newer version to confirm
  the persistent frame appears and the Settings switch turning off
  actually skips the check; confirm the restart button is a no-op with
  the explanatory toast during an active focus block and during
  lockdown; confirm the Help tab's version line matches `__version__`. A
  full dry-run swap-and-relaunch against a real throwaway pre-release tag
  before this ships, so the very first genuine auto-update in the wild
  isn't also the first time the relaunch script has ever executed for
  real.

## Out of scope for this pass

- Any rollback beyond the `.old` rename (e.g. auto-restoring the backup
  if the new version crashes on its first launch) — noted as a real gap,
  left for later if it ever actually bites someone.
- A manual "Check for updates now" button — the automatic startup check
  plus the Settings switch covers the need; can be added later without
  touching anything designed here.
- Code-signing / notarizing the app to remove the OS warnings on a fresh
  download — unrelated to this feature and unchanged either way.
- Auto-updating a source checkout via `git pull` — intentionally left as
  a manual `git pull`, not automated.
- Delta/incremental downloads — every update re-downloads the full
  release asset, same size as downloading it from the Releases page by
  hand today.

## File-by-file change list

**New**
- `lock_in/updater.py` — `UpdateInfo`, `parse_version`, `is_newer`,
  `ASSET_NAMES`, `pick_asset`, `check_for_update`.
- `lock_in/update_fetch.py` — `REPO`, `fetch_latest_release`,
  `download_file`.
- `lock_in/update_apply.py` — `EXPECTED_ENTRY`, `extract_archive`,
  `current_app_path`, `write_relauncher_script`,
  `launch_relauncher_and_quit`.
- `tests/test_updater.py`, `tests/test_update_fetch.py`,
  `tests/test_update_apply.py`.

**Edit**
- `lock_in/__init__.py` — `__version__` bumped to `"2.5.3"` (last edit,
  right before tagging).
- `lock_in/config.py` — `check_for_updates: bool = True`.
- `lock_in/ui.py` — `self._update_queue`; `_start_update_check()`;
  `_drain_update_queue()` wired into the existing `after()` poll loop
  alongside `_drain_banner_queue()`; the persistent update-ready frame
  and its "Restart now" handler; one new Settings-tab switch; one new
  Help-tab line showing `__version__`.
- `README.md` — new "Auto-Update" section (plain language: it checks
  quietly, never interrupts a focus block, here's the switch to turn it
  off, source checkouts use `git pull` instead); one line each in
  Requirements (no new dependency — stdlib only) and Known limits (only
  updates the downloaded app, not a source checkout); Project Structure
  tree gains the three new files.
- `.gitignore` — `*.old` and a `lockin_update_tmp/` entry, defensive only
  (the real download/extract always happens in the OS temp folder, never
  inside the project).

**Git — deferred, as always**
- `__version__` bump and the `v2.5.3` tag are the very last steps, handed
  to the user as commands at the end — nothing committed, tagged, or
  pushed here.
