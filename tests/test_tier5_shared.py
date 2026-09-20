from datetime import date

from lock_in.history import SessionRecord
from lock_in.tasks import TaskStore
from lock_in.tier5._shared import (
    format_day_heading, format_hm, format_time_range, last_n_days,
    resolve_task_name, sorted_blocks,
)


def test_format_hm_zero_seconds():
    assert format_hm(0) == "0m"


def test_format_hm_minutes_only():
    assert format_hm(600) == "10m"


def test_format_hm_hours_and_minutes():
    assert format_hm(9000) == "2h 30m"


def test_format_hm_exact_hour_still_shows_minutes():
    assert format_hm(3600) == "1h 0m"


def test_last_n_days_returns_exactly_n_entries():
    result = last_n_days({}, date(2026, 9, 14), 14)
    assert len(result) == 14


def test_last_n_days_is_oldest_to_newest_ending_today():
    result = last_n_days({}, date(2026, 9, 14), 14)
    assert result[0][0] == date(2026, 9, 1)
    assert result[-1][0] == date(2026, 9, 14)


def test_last_n_days_fills_missing_days_with_zero():
    totals = {"2026-09-14": 1200}
    result = last_n_days(totals, date(2026, 9, 14), 14)
    assert result[-1] == (date(2026, 9, 14), 1200)
    assert result[0] == (date(2026, 9, 1), 0)


def test_last_n_days_crosses_a_month_boundary():
    result = last_n_days({}, date(2026, 3, 5), 14)
    assert result[0][0] == date(2026, 2, 20)
    assert result[-1][0] == date(2026, 3, 5)


def test_last_n_days_crosses_a_year_boundary():
    result = last_n_days({}, date(2026, 1, 3), 14)
    assert result[0][0] == date(2025, 12, 21)
    assert result[-1][0] == date(2026, 1, 3)


def test_last_n_days_returns_30_entries_for_decades_window():
    result = last_n_days({}, date(2026, 9, 14), 30)
    assert len(result) == 30
    assert result[0][0] == date(2026, 8, 16)
    assert result[-1][0] == date(2026, 9, 14)


def test_resolve_task_name_is_no_task_for_none(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    assert resolve_task_name(None, tasks) == "No task"


def test_resolve_task_name_returns_the_real_name(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    task = tasks.add("Write the Tier 5 spec")
    assert resolve_task_name(task.id, tasks) == "Write the Tier 5 spec"


def test_resolve_task_name_is_deleted_task_for_a_dangling_id(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    assert resolve_task_name("no-such-id", tasks) == "Deleted task"


def _rec(start, end):
    return SessionRecord(start=start, end=end, duration_seconds=1, task_id=None, completed=True)


def test_sorted_blocks_orders_earliest_first():
    late = _rec("2026-09-14T14:00:00", "2026-09-14T14:10:00")
    early = _rec("2026-09-14T09:00:00", "2026-09-14T09:10:00")
    assert sorted_blocks([late, early]) == [early, late]


def test_sorted_blocks_handles_an_empty_list():
    assert sorted_blocks([]) == []


def test_format_time_range_formats_hh_mm():
    result = format_time_range("2026-09-14T09:00:00", "2026-09-14T09:25:00")
    assert result == "09:00–09:25"


def test_format_day_heading_matches_expected_string():
    assert format_day_heading(date(2026, 9, 12)) == "Saturday, September 12"
