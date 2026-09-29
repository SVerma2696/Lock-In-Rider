"""
Tests for update_apply.py. extract_archive is tested against real, tiny
archives built on the fly in tmp_path -- no network needed. The
relaunch scripts are checked by their written text (the right paths and
PID show up in the right places) rather than by actually running them,
since a script that closes the real process isn't something pytest can
safely execute. launch_relauncher_and_quit itself (which really does
start a separate process) is checked with a stand-in for Popen, so no
real process is started.
"""

import io
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from lock_in import update_apply
from lock_in.update_apply import (
    clean_environment,
    current_app_path,
    extract_archive,
    write_relauncher_script,
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


def _make_exec_zip(path, entry_name: str, mode: int = 0o755) -> None:
    """A zip whose entry carries a real Unix mode in external_attr,
    exactly how Info-ZIP's `zip -r` (what release.yml uses) writes it."""
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo(entry_name)
        info.external_attr = mode << 16
        archive.writestr(info, b"app bytes")


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows chmod ignores exec bits entirely, so st_mode can never "
    "show them here; test_extract_archive_chmods_exec_entries_on_macos "
    "covers the same logic on this platform.",
)
def test_extract_archive_restores_exec_bit_on_macos(tmp_path):
    """zipfile.extractall() drops Unix mode bits, which left the macOS
    .app's executable at 0644 and made `open "Lock In.app"` fail
    silently. The mode IS in the entry's external_attr -- extract_archive
    has to put the exec bit back."""
    archive_path = tmp_path / "LockIn-macOS.zip"
    _make_exec_zip(archive_path, "Lock In.app")
    dest = tmp_path / "extracted"
    result = extract_archive(archive_path, dest, "darwin")
    assert result == dest / "Lock In.app"
    assert result.stat().st_mode & 0o111


def test_extract_archive_chmods_exec_entries_on_macos(tmp_path, monkeypatch):
    """Platform-independent half of the above: proves the darwin branch
    actually chmods the right file with the exec bits added, by watching
    the chmod calls rather than the resulting st_mode (which Windows
    refuses to record)."""
    archive_path = tmp_path / "LockIn-macOS.zip"
    _make_exec_zip(archive_path, "Lock In.app")
    dest = tmp_path / "extracted"

    calls = []
    real_chmod = Path.chmod

    def spy_chmod(self, mode, **kwargs):
        calls.append((Path(self).name, mode))
        return real_chmod(self, mode, **kwargs)

    monkeypatch.setattr(Path, "chmod", spy_chmod)

    assert extract_archive(archive_path, dest, "darwin") == dest / "Lock In.app"
    assert [name for name, _ in calls] == ["Lock In.app"]
    assert calls[0][1] & 0o111 == 0o111


def test_extract_archive_leaves_non_exec_entries_alone_on_macos(tmp_path, monkeypatch):
    """An entry that was never executable (0644) must not be made one."""
    archive_path = tmp_path / "LockIn-macOS.zip"
    _make_exec_zip(archive_path, "Lock In.app", mode=0o644)
    dest = tmp_path / "extracted"

    calls = []
    real_chmod = Path.chmod

    def spy_chmod(self, mode, **kwargs):
        calls.append(Path(self).name)
        return real_chmod(self, mode, **kwargs)

    monkeypatch.setattr(Path, "chmod", spy_chmod)

    assert extract_archive(archive_path, dest, "darwin") == dest / "Lock In.app"
    assert calls == []


def test_extract_archive_does_not_chmod_on_win32(tmp_path, monkeypatch):
    """The exec-bit restoration is darwin-only: Windows has no such
    concept, and Linux's tarfile.extractall already preserves modes."""
    archive_path = tmp_path / "LockIn-Windows.zip"
    _make_exec_zip(archive_path, "Lock In.exe")
    dest = tmp_path / "extracted"

    calls = []
    real_chmod = Path.chmod
    monkeypatch.setattr(
        Path,
        "chmod",
        lambda self, mode, **kw: (calls.append(mode), real_chmod(self, mode, **kw))[1],
    )
    assert extract_archive(archive_path, dest, "win32") == dest / "Lock In.exe"
    assert calls == []


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
        tmp_path,
        Path(r"C:\App\Lock In.exe"),
        Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242,
        platform="win32",
    )
    text = script.read_text()
    assert script.name == "update.bat"
    assert "4242" in text
    assert r"C:\App\Lock In.exe" in text
    assert r"C:\App\Lock In.exe.old" in text


def test_write_relauncher_script_windows_waits_without_needing_a_console(tmp_path):
    """`timeout /t 1` exits immediately when it has no console it can
    read keys from, so the whole 15s wait silently collapsed. `ping`
    doesn't care."""
    script = write_relauncher_script(
        tmp_path,
        Path(r"C:\App\Lock In.exe"),
        Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242,
        platform="win32",
    )
    text = script.read_text()
    assert "ping -n 2 127.0.0.1" in text
    assert "timeout /t" not in text


def test_write_relauncher_script_windows_skips_swap_if_new_path_is_gone(tmp_path):
    """The temp folder can be swept between download and "Restart now";
    the script must bail out BEFORE renaming the installed app."""
    script = write_relauncher_script(
        tmp_path,
        Path(r"C:\App\Lock In.exe"),
        Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242,
        platform="win32",
    )
    text = script.read_text()
    assert 'if not exist "C:\\App\\tmp\\Lock In.exe" goto end' in text
    assert ":end" in text
    # The guard has to come before the first rename, or it's pointless.
    guard_line = text.index("if not exist")
    assert guard_line < text.index("move /y")


def test_write_relauncher_script_macos_contains_pid_and_open_command(tmp_path):
    script = write_relauncher_script(
        tmp_path,
        Path("/Apps/Lock In.app"),
        Path("/tmp/Lock In.app"),
        pid=99,
        platform="darwin",
    )
    text = script.read_text()
    assert script.name == "update.sh"
    assert "kill -0 99" in text
    assert 'open "/Apps/Lock In.app"' in text


def test_write_relauncher_script_macos_skips_swap_if_new_path_is_gone(tmp_path):
    script = write_relauncher_script(
        tmp_path,
        Path("/Apps/Lock In.app"),
        Path("/tmp/Lock In.app"),
        pid=99,
        platform="darwin",
    )
    text = script.read_text()
    assert '[ -e "/tmp/Lock In.app" ] || exit 0' in text
    assert text.index("[ -e ") < text.index("mv ")


def test_write_relauncher_script_linux_contains_chmod_and_nohup(tmp_path):
    script = write_relauncher_script(
        tmp_path,
        Path("/opt/Lock In"),
        Path("/tmp/Lock In"),
        pid=77,
        platform="linux",
    )
    text = script.read_text()
    assert "chmod +x" in text
    assert "nohup" in text


def test_write_relauncher_script_linux_skips_swap_if_new_path_is_gone(tmp_path):
    script = write_relauncher_script(
        tmp_path,
        Path("/opt/Lock In"),
        Path("/tmp/Lock In"),
        pid=77,
        platform="linux",
    )
    text = script.read_text()
    assert '[ -e "/tmp/Lock In" ] || exit 0' in text
    assert text.index("[ -e ") < text.index("mv ")


def test_write_relauncher_script_windows_uses_windows_own_tasklist_and_find(tmp_path):
    """Another "find" earlier on the PATH (Git for Windows has one) made
    the wait end at once, before the old app had closed."""
    script = write_relauncher_script(
        tmp_path,
        Path(r"C:\App\Lock In.exe"),
        Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242,
        platform="win32",
    )
    text = script.read_text()
    assert r"%SystemRoot%\System32\tasklist.exe" in text
    assert r"%SystemRoot%\System32\find.exe" in text


def test_write_relauncher_script_windows_puts_the_old_app_back_if_the_new_one_wont_go_in(tmp_path):
    """If the new file can't be moved in, the app must never be left as
    only "Lock In.exe.old" (which Windows can't open)."""
    script = write_relauncher_script(
        tmp_path,
        Path(r"C:\App\Lock In.exe"),
        Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242,
        platform="win32",
    )
    text = script.read_text()
    put_back = r'move /y "C:\App\Lock In.exe.old" "C:\App\Lock In.exe"'
    assert put_back in text
    assert text.index(":putback") < text.index(put_back) < text.index(":reopen")
    # Every way through the swap ends by opening the app again.
    assert text.count(r'start "" "C:\App\Lock In.exe"') == 1
    assert text.index(":reopen") < text.index('start ""')


def test_write_relauncher_script_unix_puts_the_old_app_back_if_the_new_one_wont_go_in(tmp_path):
    script = write_relauncher_script(
        tmp_path,
        Path("/opt/Lock In"),
        Path("/tmp/Lock In"),
        pid=77,
        platform="linux",
    )
    text = script.read_text()
    assert '|| mv "/opt/Lock In.old" "/opt/Lock In"' in text


def test_clean_environment_removes_the_old_apps_notes():
    """The new app was started with the old app's leftover notes, thought
    it was the old app's helper, and quit without a window."""
    bundle = r"C:\Temp\_MEI12345" if sys.platform == "win32" else "/tmp/_MEI12345"
    sep = ";" if sys.platform == "win32" else ":"
    other = r"C:\Windows\System32" if sys.platform == "win32" else "/usr/bin"
    inside = bundle + (r"\_tcl_data" if sys.platform == "win32" else "/_tcl_data")
    env = {
        "_PYI_ARCHIVE_FILE": "Lock In.exe",
        "_PYI_APPLICATION_HOME_DIR": bundle,
        "_PYI_PARENT_PROCESS_LEVEL": "1",
        "_MEIPASS2": bundle,
        "TCL_LIBRARY": inside,
        "PATH": sep.join([bundle, other]),
        "HOME": "/home/me",
    }
    clean = clean_environment(env, bundle)
    assert not any(key.startswith(("_PYI_", "_MEIPASS")) for key in clean)
    assert "TCL_LIBRARY" not in clean
    assert clean["PATH"] == other
    assert clean["HOME"] == "/home/me"
    assert clean["PYINSTALLER_RESET_ENVIRONMENT"] == "1"


def test_clean_environment_leaves_normal_values_alone_when_not_packaged():
    env = {"PATH": "a", "TCL_LIBRARY": "/usr/share/tcl"}
    clean = clean_environment(env, None)
    assert clean["PATH"] == "a"
    assert clean["TCL_LIBRARY"] == "/usr/share/tcl"
    assert env == {"PATH": "a", "TCL_LIBRARY": "/usr/share/tcl"}  # the original isn't changed


def test_app_process_id_is_this_process_when_running_from_source(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    import os

    assert update_apply.app_process_id() == os.getpid()


def test_launch_relauncher_windows_uses_a_hidden_window_and_a_clean_environment(
    tmp_path, monkeypatch
):
    """With no window at all (DETACHED_PROCESS), Windows' find.exe waited
    forever, so the swap never happened and the app just closed."""
    calls = []
    monkeypatch.setattr(
        update_apply.subprocess, "Popen", lambda args, **kwargs: calls.append((args, kwargs))
    )
    monkeypatch.setenv("_PYI_ARCHIVE_FILE", "old")
    no_window = getattr(update_apply.subprocess, "CREATE_NO_WINDOW", 0x08000000)
    detached = getattr(update_apply.subprocess, "DETACHED_PROCESS", 0x00000008)
    monkeypatch.setattr(update_apply.subprocess, "CREATE_NO_WINDOW", no_window, raising=False)
    monkeypatch.setattr(update_apply.subprocess, "DETACHED_PROCESS", detached, raising=False)
    monkeypatch.setattr(update_apply.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)

    update_apply.launch_relauncher_and_quit(tmp_path / "update.bat", "win32")

    ((args, kwargs),) = calls
    assert args[:2] == ["cmd", "/c"]
    assert kwargs["creationflags"] & no_window
    assert not kwargs["creationflags"] & detached
    assert "_PYI_ARCHIVE_FILE" not in kwargs["env"]
    assert kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
