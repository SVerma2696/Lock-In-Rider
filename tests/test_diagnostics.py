"""Tests for diagnostics.py: the log file is small, private by default,
and never breaks the app."""

import logging

import pytest

from lock_in import diagnostics


@pytest.fixture(autouse=True)
def clean_logging():
    diagnostics.stop_logging()
    diagnostics._logged_once.clear()
    yield
    diagnostics.stop_logging()


def test_private_hides_personal_words_unless_debug_is_on(monkeypatch):
    monkeypatch.delenv(diagnostics.DEBUG_SWITCH, raising=False)
    assert diagnostics.private("Secret Essay.docx") == diagnostics.HIDDEN
    monkeypatch.setenv(diagnostics.DEBUG_SWITCH, "1")
    assert diagnostics.private("Secret Essay.docx") == "Secret Essay.docx"


def test_setup_writes_a_log_file_and_is_safe_to_call_twice(tmp_path):
    path = diagnostics.setup_logging(tmp_path)
    assert path == tmp_path / diagnostics.LOG_FILE_NAME
    diagnostics.setup_logging(tmp_path)
    logging.getLogger("lock_in.test").warning("hello from the test")
    diagnostics.stop_logging()
    text = path.read_text(encoding="utf-8")
    assert "hello from the test" in text
    assert text.count("started on") == 1


def test_log_file_stays_small(tmp_path):
    assert diagnostics.MAX_BYTES <= 512 * 1024
    assert diagnostics.BACKUP_COUNT <= 3


def test_log_once_only_logs_the_first_time(tmp_path, caplog):
    log = logging.getLogger("lock_in.test_once")
    with caplog.at_level(logging.WARNING, logger="lock_in.test_once"):
        for _ in range(5):
            try:
                raise OSError("camera busy")
            except OSError:
                diagnostics.log_once(log, "key", "Camera failed")
    assert [r.message for r in caplog.records] == ["Camera failed"]


def test_an_unwritable_folder_just_means_no_log(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(diagnostics.Path, "mkdir", refuse)
    assert diagnostics.setup_logging(tmp_path / "nope") is None
