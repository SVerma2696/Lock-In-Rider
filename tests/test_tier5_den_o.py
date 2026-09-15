from datetime import date

from lock_in.history import SessionRecord
from lock_in.tier5.den_o import format_day_heading, format_time_range, sorted_blocks


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
