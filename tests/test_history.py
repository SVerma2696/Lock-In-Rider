"""Tests for the append-only session-history log."""

import dataclasses
import json
from datetime import date, datetime, timedelta

import pytest

from lock_in.history import HistoryStore, SessionRecord


@pytest.fixture
def store(tmp_path) -> HistoryStore:
    return HistoryStore(tmp_path / "sessions.jsonl")


def _record(start: datetime, duration: int, task_id=None, completed=True) -> SessionRecord:
    end = start + timedelta(seconds=duration)
    return SessionRecord(
        start=start.isoformat(timespec="seconds"),
        end=end.isoformat(timespec="seconds"),
        duration_seconds=duration,
        task_id=task_id,
        completed=completed,
    )


def test_new_history_store_starts_empty(store):
    assert store.all() == []


def test_record_appends_and_is_readable_back(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store.record(record)
    assert store.all() == [record]


def test_record_persists_across_a_reload(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store1 = HistoryStore(path)
    store1.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    store2 = HistoryStore(path)
    assert len(store2.all()) == 1


def test_for_date_filters_to_that_calendar_day(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    store.record(_record(datetime(2026, 9, 5, 9, 0, 0), 1500))
    matches = store.for_date(date(2026, 9, 4))
    assert len(matches) == 1


def test_for_task_filters_to_that_task_id(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123"))
    store.record(_record(datetime(2026, 9, 4, 10, 0, 0), 1500, task_id="other"))
    matches = store.for_task("abc123")
    assert len(matches) == 1
    assert matches[0].task_id == "abc123"


def test_total_seconds_by_day_sums_same_day_records(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    store.record(_record(datetime(2026, 9, 4, 14, 0, 0), 900))
    store.record(_record(datetime(2026, 9, 5, 9, 0, 0), 300))
    totals = store.total_seconds_by_day()
    assert totals["2026-09-04"] == 2400
    assert totals["2026-09-05"] == 300


def test_earliest_date_is_none_for_an_empty_store(store):
    assert store.earliest_date() is None


def test_earliest_date_is_the_only_day_with_one_record(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    assert store.earliest_date() == date(2026, 9, 4)


def test_earliest_date_is_the_minimum_across_out_of_order_records(store):
    store.record(_record(datetime(2026, 9, 10, 9, 0, 0), 1500))
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    store.record(_record(datetime(2026, 9, 7, 9, 0, 0), 1500))
    assert store.earliest_date() == date(2026, 9, 4)


def test_total_seconds_by_task_is_empty_for_an_empty_store(store):
    assert store.total_seconds_by_task() == {}


def test_total_seconds_by_task_sums_records_for_the_same_task(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123"))
    store.record(_record(datetime(2026, 9, 5, 9, 0, 0), 900, task_id="abc123"))
    assert store.total_seconds_by_task() == {"abc123": 2400}


def test_total_seconds_by_task_keeps_different_tasks_and_untagged_time_separate(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123"))
    store.record(_record(datetime(2026, 9, 4, 10, 0, 0), 600, task_id="other"))
    store.record(_record(datetime(2026, 9, 4, 11, 0, 0), 300, task_id=None))
    totals = store.total_seconds_by_task()
    assert totals == {"abc123": 1500, "other": 600, None: 300}


def test_a_skipped_block_is_recorded_as_not_completed(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 400, completed=False)
    store.record(record)
    assert store.all()[0].completed is False


def test_corrupt_line_is_skipped_not_fatal(tmp_path):
    path = tmp_path / "sessions.jsonl"
    good = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    path.write_text(
        json.dumps(dataclasses.asdict(good)) + "\n" + "{ not valid json\n",
        encoding="utf-8",
    )
    store = HistoryStore(path)
    assert len(store.all()) == 1


def test_missing_file_starts_empty(tmp_path):
    store = HistoryStore(tmp_path / "does_not_exist.jsonl")
    assert store.all() == []


# ---- Every block gets its own name tag (an id) ----------------------------

def test_new_records_get_an_auto_generated_id(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    assert record.id != ""
    store.record(record)
    assert store.all()[0].id == record.id


def test_two_new_records_get_different_ids():
    a = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    b = _record(datetime(2026, 9, 4, 10, 0, 0), 1500)
    assert a.id != b.id


def test_load_backfills_a_missing_id_and_persists_it(tmp_path):
    path = tmp_path / "sessions.jsonl"
    legacy = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    raw = dataclasses.asdict(legacy)
    del raw["id"]
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    store = HistoryStore(path)
    assert store.all()[0].id != ""
    first_id = store.all()[0].id

    # The name tag must STAY the same. load() saved it to the file, so
    # opening the file again must not make up a second, different one.
    store2 = HistoryStore(path)
    assert store2.all()[0].id == first_id


def test_load_leaves_an_existing_id_unchanged(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store.record(record)
    original_id = record.id
    store.load()
    assert store.all()[0].id == original_id


def test_load_only_rewrites_the_file_when_an_id_was_missing(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store1 = HistoryStore(path)
    store1.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    before = path.stat().st_mtime_ns
    HistoryStore(path)
    assert path.stat().st_mtime_ns == before


# ---- Fixing a past block: change its task, or delete it -------------------

def test_reassign_task_changes_the_task_id(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123")
    store.record(record)
    assert store.reassign_task(record.id, "other") is True
    assert store.all()[0].task_id == "other"


def test_reassign_task_can_untag_to_none(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123")
    store.record(record)
    store.reassign_task(record.id, None)
    assert store.all()[0].task_id is None


def test_reassign_task_returns_false_for_an_unknown_id(store):
    assert store.reassign_task("no-such-id", "abc123") is False


def test_reassign_task_leaves_other_records_untouched(store):
    a = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc")
    b = _record(datetime(2026, 9, 4, 10, 0, 0), 900, task_id="def")
    store.record(a)
    store.record(b)
    store.reassign_task(a.id, "changed")
    assert store.all()[1].task_id == "def"


def test_reassign_task_never_changes_the_times(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc")
    store.record(record)
    start, end, seconds = record.start, record.end, record.duration_seconds
    store.reassign_task(record.id, "changed")
    kept = store.all()[0]
    assert (kept.start, kept.end, kept.duration_seconds) == (start, end, seconds)


def test_reassign_task_persists_across_a_reload(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store1 = HistoryStore(path)
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc")
    store1.record(record)
    store1.reassign_task(record.id, "changed")
    store2 = HistoryStore(path)
    assert store2.all()[0].task_id == "changed"


def test_delete_removes_the_matching_record(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store.record(record)
    assert store.delete(record.id) is True
    assert store.all() == []


def test_delete_returns_false_for_an_unknown_id(store):
    assert store.delete("no-such-id") is False


def test_delete_keeps_other_records_and_their_order(store):
    a = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    b = _record(datetime(2026, 9, 4, 10, 0, 0), 900)
    c = _record(datetime(2026, 9, 4, 11, 0, 0), 300)
    store.record(a)
    store.record(b)
    store.record(c)
    store.delete(b.id)
    assert [r.id for r in store.all()] == [a.id, c.id]


def test_delete_persists_across_a_reload(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store1 = HistoryStore(path)
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store1.record(record)
    store1.delete(record.id)
    store2 = HistoryStore(path)
    assert store2.all() == []


def test_deleting_the_last_record_leaves_an_empty_file_that_still_loads(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store1 = HistoryStore(path)
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store1.record(record)
    store1.delete(record.id)
    assert path.read_text(encoding="utf-8") == ""
    assert HistoryStore(path).all() == []


def test_a_failed_id_save_on_load_does_not_crash_the_app(tmp_path, monkeypatch):
    path = tmp_path / "sessions.jsonl"
    legacy = dataclasses.asdict(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    del legacy["id"]
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    def locked(self):
        raise OSError("file is locked")

    monkeypatch.setattr(HistoryStore, "_rewrite", locked)
    store = HistoryStore(path)
    # The block still loads, and still has an id to use this time.
    assert len(store.all()) == 1
    assert store.all()[0].id != ""
