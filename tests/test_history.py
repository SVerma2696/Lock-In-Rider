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
