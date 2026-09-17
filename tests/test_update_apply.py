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
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

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
        Path, "chmod",
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
        tmp_path, Path(r"C:\App\Lock In.exe"), Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242, platform="win32",
    )
    text = script.read_text()
    assert script.name == "update.bat"
    assert "4242" in text
    assert r"C:\App\Lock In.exe" in text
    assert r"C:\App\Lock In.exe.old" in text


def test_write_relauncher_script_windows_waits_without_needing_a_console(tmp_path):
    """`timeout /t 1` exits immediately when it has no console to read
    from, and launch_relauncher_and_quit starts this script with
    DETACHED_PROCESS -- so the whole 15s wait silently collapsed. `ping`
    needs no console."""
    script = write_relauncher_script(
        tmp_path, Path(r"C:\App\Lock In.exe"), Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242, platform="win32",
    )
    text = script.read_text()
    assert "ping -n 2 127.0.0.1" in text
    assert "timeout /t" not in text


def test_write_relauncher_script_windows_skips_swap_if_new_path_is_gone(tmp_path):
    """The temp folder can be swept between download and "Restart now";
    the script must bail out BEFORE renaming the installed app."""
    script = write_relauncher_script(
        tmp_path, Path(r"C:\App\Lock In.exe"), Path(r"C:\App\tmp\Lock In.exe"),
        pid=4242, platform="win32",
    )
    text = script.read_text()
    assert 'if not exist "C:\\App\\tmp\\Lock In.exe" goto end' in text
    assert ":end" in text
    # The guard has to come before the first rename, or it's pointless.
    guard_line = text.index("if not exist")
    assert guard_line < text.index("move /y")


def test_write_relauncher_script_macos_contains_pid_and_open_command(tmp_path):
    script = write_relauncher_script(
        tmp_path, Path("/Apps/Lock In.app"), Path("/tmp/Lock In.app"),
        pid=99, platform="darwin",
    )
    text = script.read_text()
    assert script.name == "update.sh"
    assert "kill -0 99" in text
    assert 'open "/Apps/Lock In.app"' in text


def test_write_relauncher_script_macos_skips_swap_if_new_path_is_gone(tmp_path):
    script = write_relauncher_script(
        tmp_path, Path("/Apps/Lock In.app"), Path("/tmp/Lock In.app"),
        pid=99, platform="darwin",
    )
    text = script.read_text()
    assert '[ -e "/tmp/Lock In.app" ] || exit 0' in text
    assert text.index("[ -e ") < text.index("mv ")


def test_write_relauncher_script_linux_contains_chmod_and_nohup(tmp_path):
    script = write_relauncher_script(
        tmp_path, Path("/opt/Lock In"), Path("/tmp/Lock In"),
        pid=77, platform="linux",
    )
    text = script.read_text()
    assert "chmod +x" in text
    assert "nohup" in text


def test_write_relauncher_script_linux_skips_swap_if_new_path_is_gone(tmp_path):
    script = write_relauncher_script(
        tmp_path, Path("/opt/Lock In"), Path("/tmp/Lock In"),
        pid=77, platform="linux",
    )
    text = script.read_text()
    assert '[ -e "/tmp/Lock In" ] || exit 0' in text
    assert text.index("[ -e ") < text.index("mv ")
