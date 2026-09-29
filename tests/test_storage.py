"""
Tests for lock_in/storage: saving can never leave a half-written file,
and broken files are read as safely as possible.
"""

import json
import os

import pytest

from lock_in import storage
from lock_in.classifier import NaiveBayesClassifier
from lock_in.history import HistoryStore, SessionRecord
from lock_in.observations import ObservationStore
from lock_in.storage import json_store
from lock_in.tasks import TaskStore


# ---------------------------------------------------------------------- #
# Whole files
# ---------------------------------------------------------------------- #
def test_atomic_write_json_writes_the_same_words_as_json_dumps(tmp_path):
    path = tmp_path / "a.json"
    data = {"name": "Kuuga — Mighty", "n": [1, 2]}
    storage.atomic_write_json(path, data, indent=2)
    assert path.read_text(encoding="utf-8") == json.dumps(data, indent=2, ensure_ascii=False)


def test_atomic_write_json_can_keep_ascii_escapes(tmp_path):
    path = tmp_path / "a.json"
    storage.atomic_write_json(path, {"a": "—"}, indent=1, ensure_ascii=True)
    assert path.read_text(encoding="utf-8") == json.dumps({"a": "—"}, indent=1)


def test_atomic_write_makes_missing_folders(tmp_path):
    path = tmp_path / "deep" / "er" / "a.json"
    storage.atomic_write_json(path, [1])
    assert json.loads(path.read_text(encoding="utf-8")) == [1]


def test_a_failed_save_leaves_the_old_file_untouched_and_no_spare_file(tmp_path, monkeypatch):
    """The crash-in-the-middle case: the swap never happens, so the real
    file is still the complete old copy."""
    path = tmp_path / "config.json"
    storage.atomic_write_json(path, {"version": "old"})

    def broken_replace(src, dst):
        raise OSError("power cut")

    monkeypatch.setattr(json_store.os, "replace", broken_replace)
    with pytest.raises(OSError):
        storage.atomic_write_json(path, {"version": "new"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"version": "old"}
    assert os.listdir(tmp_path) == ["config.json"]


def test_a_briefly_locked_file_is_retried(tmp_path, monkeypatch):
    """On Windows a virus scanner can hold the file for a moment."""
    path = tmp_path / "a.json"
    real_replace = os.replace
    calls = []

    def flaky_replace(src, dst):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("in use")
        real_replace(src, dst)

    monkeypatch.setattr(json_store.os, "replace", flaky_replace)
    monkeypatch.setattr(json_store, "_REPLACE_WAIT_SECONDS", 0)
    storage.atomic_write_json(path, {"ok": True})
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
    assert len(calls) == 3


@pytest.mark.parametrize("content", ["", "{not json", "\x00\x01"])
def test_read_json_gives_none_for_a_broken_file(tmp_path, content):
    path = tmp_path / "a.json"
    path.write_text(content, encoding="utf-8")
    assert storage.read_json(path) is None


def test_read_json_gives_none_for_a_missing_file(tmp_path):
    assert storage.read_json(tmp_path / "nope.json") is None


# ---------------------------------------------------------------------- #
# One-entry-per-line files
# ---------------------------------------------------------------------- #
def test_append_after_a_crash_cut_a_line_short_keeps_the_new_entry(tmp_path):
    """Before, the new entry was glued onto the broken half-line and both
    were lost."""
    path = tmp_path / "sessions.jsonl"
    path.write_text('{"a": 1}\n{"b": 2, "cut sho', encoding="utf-8")
    storage.append_jsonl(path, {"c": 3})
    assert list(storage.read_jsonl(path)) == [{"a": 1}, {"c": 3}]


def test_append_to_an_empty_or_missing_file(tmp_path):
    path = tmp_path / "new" / "sessions.jsonl"
    storage.append_jsonl(path, {"a": 1})
    storage.append_jsonl(path, {"b": 2})
    assert path.read_text(encoding="utf-8") == '{"a": 1}\n{"b": 2}\n'


def test_rewrite_jsonl_same_format_as_before(tmp_path):
    path = tmp_path / "h.jsonl"
    storage.rewrite_jsonl(path, [{"a": "é"}, {"b": 2}])
    assert path.read_text(encoding="utf-8") == '{"a": "é"}\n{"b": 2}\n'
    storage.rewrite_jsonl(path, [])
    assert path.read_text(encoding="utf-8") == ""


def test_read_jsonl_skips_blank_and_broken_lines(tmp_path):
    path = tmp_path / "h.jsonl"
    path.write_text('\n{"a": 1}\nnot json\n\n{"b": 2}\n', encoding="utf-8")
    assert list(storage.read_jsonl(path)) == [{"a": 1}, {"b": 2}]


# ---------------------------------------------------------------------- #
# The real stores use it
# ---------------------------------------------------------------------- #
def _record(minutes=25):
    return SessionRecord(
        start="2026-09-01T10:00:00",
        end="2026-09-01T10:25:00",
        duration_seconds=minutes * 60,
        task_id=None,
        completed=True,
    )


def test_history_survives_a_line_cut_short_by_a_crash(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store = HistoryStore(path)
    store.record(_record())
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"start": "2026-09-01T11:00')  # the crash
    store = HistoryStore(path)
    store.record(_record(10))
    assert [r.duration_seconds for r in HistoryStore(path).all()] == [1500, 600]


def test_tasks_save_is_atomic(tmp_path, monkeypatch):
    path = tmp_path / "tasks.json"
    store = TaskStore(path)
    store.add("Keep me")
    monkeypatch.setattr(json_store.os, "replace", lambda s, d: (_ for _ in ()).throw(OSError()))
    with pytest.raises(OSError):
        store.add("Never saved")
    assert [t.name for t in TaskStore(path).all()] == ["Keep me"]


@pytest.mark.parametrize("line", ["5", "[]", '"words"', "null", '{"text": 5}'])
def test_observations_skip_valid_json_that_is_not_an_entry(tmp_path, line):
    """These used to crash the app on opening."""
    path = tmp_path / "observations.jsonl"
    path.write_text(line + '\n{"text": "code.exe — main.py"}\n', encoding="utf-8")
    store = ObservationStore(path)
    assert [r.text for r in store.all()] == ["code.exe — main.py"]


@pytest.mark.parametrize("content", ["[]", "5", '"words"', "null", '{"label_counts": 7}'])
def test_model_file_of_the_wrong_shape_starts_fresh_instead_of_crashing(tmp_path, content):
    path = tmp_path / "model.json"
    path.write_text(content, encoding="utf-8")
    model = NaiveBayesClassifier.load(path)
    assert sum(model.label_counts.values()) > 0  # the starter examples


def test_model_round_trips(tmp_path):
    path = tmp_path / "model.json"
    model = NaiveBayesClassifier.load_seed()
    model.save(path)
    again = NaiveBayesClassifier.load(path)
    assert again.label_counts == model.label_counts
    assert again.vocabulary == model.vocabulary
