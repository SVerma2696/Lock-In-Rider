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

import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Mapping, Optional

EXPECTED_ENTRY = {
    "win32": "Lock In.exe",
    "darwin": "Lock In.app",
    "linux": "Lock In",
}

_WAIT_TRIES = 15   # ~15 seconds (Windows: 1s/try) / ~4.5s (macOS/Linux: 0.3s/try) before giving up


def _restore_zip_exec_bits(archive: zipfile.ZipFile, dest_dir: Path) -> None:
    """zipfile.extractall() throws away Unix permission bits, so a macOS
    .app extracted from LockIn-macOS.zip ends up with its inner
    executable at 0644 and `open "Lock In.app"` fails silently. The
    original mode IS in the zip (Info-ZIP's `zip -r`, used by
    release.yml, stores it in each entry's external_attr) -- this puts
    the executable bit back on every entry that had one.

    Best-effort by design: a chmod that fails must never turn a
    perfectly good extraction into "no update this time"."""
    for info in archive.infolist():
        if info.is_dir():
            continue
        original_mode = (info.external_attr >> 16) & 0o777
        if not original_mode & 0o111:
            continue
        extracted = dest_dir / info.filename
        try:
            if extracted.is_file():
                extracted.chmod(extracted.stat().st_mode | 0o111)
        except OSError:
            continue


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
                if platform == "darwin":
                    _restore_zip_exec_bits(archive, dest_dir)
        elif archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as archive:
                # filter= pinned explicitly: newer Pythons changed
                # extractall's default extraction filter, and release.yml
                # builds on 3.11 while this dev box may be on something
                # else -- without this the two could behave differently.
                # The fallback covers any Python old enough not to accept
                # the argument at all (pre-PEP-706 backport).
                try:
                    archive.extractall(dest_dir, filter="data")
                except TypeError:
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
    deleting anything.

    Before it renames anything, the script checks new_path still exists.
    The download sits in the OS temp folder from launch until you click
    "Restart now" -- which may be hours later -- so a temp-file cleaner
    can perfectly legitimately have swept it away in between. Without
    that check the app would rename itself to .old and then find nothing
    to move into its place, i.e. vanish."""
    script_dir.mkdir(parents=True, exist_ok=True)

    if platform == "win32":
        script_path = script_dir / "update.bat"
        # Windows' own tasklist and find, by full path. Another program
        # called "find" earlier on the PATH (Git for Windows has one) made
        # the wait below end at once, before the old app had closed.
        tasklist = r"%SystemRoot%\System32\tasklist.exe"
        find = r"%SystemRoot%\System32\find.exe"
        script_path.write_text(
            "@echo off\n"
            "set TRIES=0\n"
            ":wait\n"
            f"\"{tasklist}\" /nh /fi \"PID eq {pid}\" | \"{find}\" \"{pid}\" >nul\n"
            "if errorlevel 1 goto swap\n"
            "set /a TRIES+=1\n"
            f"if %TRIES% geq {_WAIT_TRIES} goto swap\n"
            # ping, not `timeout /t 1`: timeout.exe refuses to run
            # without a console it can read keys from, which would
            # collapse the whole wait to nothing.
            "ping -n 2 127.0.0.1 >nul\n"
            "goto wait\n"
            ":swap\n"
            # The extracted update has been sitting in the OS temp folder
            # since launch, and "Restart now" can be clicked much later --
            # if a temp-file cleaner swept it in between, bail out BEFORE
            # renaming anything, or the app renames itself to .old and then
            # has nothing to put in its place.
            f"if not exist \"{new_path}\" goto end\n"
            # Each move gets a few tries: a virus scanner or a cloud-sync
            # folder (OneDrive) can hold the file for a moment.
            "set TRIES=0\n"
            ":backup\n"
            f"move /y \"{current_path}\" \"{current_path}.old\" >nul 2>nul\n"
            "if not errorlevel 1 goto putnew\n"
            "set /a TRIES+=1\n"
            # Couldn't move the old app aside: leave it exactly as it was
            # and just open it again. No update this time, nothing lost.
            f"if %TRIES% geq {_WAIT_TRIES} goto reopen\n"
            "ping -n 2 127.0.0.1 >nul\n"
            "goto backup\n"
            ":putnew\n"
            "set TRIES=0\n"
            ":putnew_try\n"
            f"move /y \"{new_path}\" \"{current_path}\" >nul 2>nul\n"
            "if not errorlevel 1 goto reopen\n"
            "set /a TRIES+=1\n"
            f"if %TRIES% geq {_WAIT_TRIES} goto putback\n"
            "ping -n 2 127.0.0.1 >nul\n"
            "goto putnew_try\n"
            # The new one wouldn't go in: put the old one back, so the app
            # never disappears and leaves only a "Lock In.exe.old" behind.
            ":putback\n"
            f"move /y \"{current_path}.old\" \"{current_path}\" >nul 2>nul\n"
            ":reopen\n"
            f"start \"\" \"{current_path}\"\n"
            ":end\n"
            "del \"%~f0\"\n",
            encoding="utf-8",
        )
        return script_path

    script_path = script_dir / "update.sh"
    # Interpolated with as_posix() (not str()) so the shell script always
    # gets forward-slash paths, even when this is written on a Windows
    # dev box for a macOS/Linux target -- Path() on Windows would
    # otherwise render these with backslashes, which /bin/sh can't use.
    current_posix = current_path.as_posix()
    new_posix = new_path.as_posix()
    reopen = (f'open "{current_posix}"' if platform == "darwin"
              else f'chmod +x "{current_posix}" && nohup "{current_posix}" >/dev/null 2>&1 &')
    script_path.write_text(
        "#!/bin/sh\n"
        "TRIES=0\n"
        f"while kill -0 {pid} 2>/dev/null; do\n"
        "    TRIES=$((TRIES + 1))\n"
        f"    if [ \"$TRIES\" -ge {_WAIT_TRIES} ]; then break; fi\n"
        "    sleep 0.3\n"
        "done\n"
        # Same guard as the Windows branch: if the extracted update is
        # gone (temp-folder cleanup between download and "Restart now"),
        # leave the installed app completely alone rather than renaming
        # it to .old with nothing to replace it.
        f'[ -e "{new_posix}" ] || exit 0\n'
        # If the new one won't go in, put the old one back so the app
        # never disappears.
        f'if mv "{current_posix}" "{current_posix}.old"; then\n'
        f'    mv "{new_posix}" "{current_posix}" || mv "{current_posix}.old" "{current_posix}"\n'
        "fi\n"
        f"{reopen}\n"
        'rm -- "$0"\n',
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def clean_environment(environ: Mapping[str, str], bundle_dir: Optional[str]) -> dict:
    """A copy of environ that's safe to hand to a NEW copy of the app.

    The packaged app is one file that unpacks itself into a temp folder
    (bundle_dir) each time it opens, and it leaves notes for itself in
    its environment: "_PYI_..." values, plus paths into that folder
    (TCL_LIBRARY, TK_LIBRARY, entries on PATH). A program started from
    here inherits all of that. When the updated app started with those
    notes, it thought it was a helper of the old app, looked for the old
    app's temp folder (already deleted by then), and quit before
    showing anything -- the "it closed and never came back" bug.

    This removes every one of those notes and adds the switch the
    packager itself provides for "start fresh, like a double-click"."""
    folder = os.path.normcase(os.path.abspath(bundle_dir)) if bundle_dir else None

    def inside_bundle(value: str) -> bool:
        if folder is None or not value:
            return False
        try:
            path = os.path.normcase(os.path.abspath(value))
        except (TypeError, ValueError):
            return False
        return path == folder or path.startswith(folder + os.sep)

    clean = {}
    for key, value in environ.items():
        if key.upper().startswith(("_PYI_", "_MEIPASS")):
            continue
        if key.upper() == "PATH":
            value = os.pathsep.join(
                part for part in value.split(os.pathsep) if not inside_bundle(part))
        elif inside_bundle(value):
            continue
        clean[key] = value
    clean["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return clean


def app_process_id() -> int:
    """The process the update script should wait for.

    The packaged app is really two processes: a small starter, and the
    app itself running inside it. The starter keeps going for a moment
    after the app closes (it tidies up its temp folder), so waiting only
    for the app could start the swap too early. When the parent process
    is that starter (same program file), this returns the parent."""
    pid = os.getpid()
    if not getattr(sys, "frozen", False):
        return pid
    try:
        import psutil
        parent = psutil.Process(pid).parent()
        if parent is not None and os.path.normcase(parent.exe()) == os.path.normcase(sys.executable):
            return parent.pid
    except Exception:
        pass
    return pid


def launch_relauncher_and_quit(script_path: Path, platform: str) -> None:
    """Starts script_path as a fully detached process, so it keeps
    running after this one exits. Does NOT close the app itself --
    ui.py calls its normal _on_close() right after this returns, so
    settings/tasks/history are saved exactly like any other quit.

    The script (and so the reopened app) gets a clean environment, so
    the new version opens exactly as if it had been double-clicked."""
    env = clean_environment(os.environ, getattr(sys, "_MEIPASS", None))
    if platform == "win32":
        # CREATE_NO_WINDOW gives the script a hidden console window.
        # DETACHED_PROCESS (no console at all) made Windows' find.exe
        # wait forever, so the swap never happened and the app just
        # closed.
        subprocess.Popen(
            ["cmd", "/c", str(script_path)], env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
        )
    else:
        subprocess.Popen(["/bin/sh", str(script_path)], env=env, start_new_session=True)
