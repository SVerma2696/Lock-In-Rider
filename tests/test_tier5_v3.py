from datetime import date

from lock_in.tier5.v3 import _format_hm, last_14_days


def test_last_14_days_returns_exactly_14_entries():
    result = last_14_days({}, date(2026, 9, 14))
    assert len(result) == 14


def test_last_14_days_is_oldest_to_newest_ending_today():
    result = last_14_days({}, date(2026, 9, 14))
    assert result[0][0] == date(2026, 9, 1)
    assert result[-1][0] == date(2026, 9, 14)


def test_last_14_days_fills_missing_days_with_zero():
    totals = {"2026-09-14": 1200}
    result = last_14_days(totals, date(2026, 9, 14))
    assert result[-1] == (date(2026, 9, 14), 1200)
    assert result[0] == (date(2026, 9, 1), 0)


def test_last_14_days_crosses_a_month_boundary():
    result = last_14_days({}, date(2026, 3, 5))
    assert result[0][0] == date(2026, 2, 20)
    assert result[-1][0] == date(2026, 3, 5)


def test_last_14_days_crosses_a_year_boundary():
    result = last_14_days({}, date(2026, 1, 3))
    assert result[0][0] == date(2025, 12, 21)
    assert result[-1][0] == date(2026, 1, 3)


def test_format_hm_zero_seconds():
    assert _format_hm(0) == "0m"


def test_format_hm_minutes_only():
    assert _format_hm(600) == "10m"


def test_format_hm_hours_and_minutes():
    assert _format_hm(9000) == "2h 30m"


def test_format_hm_exact_hour_still_shows_minutes():
    assert _format_hm(3600) == "1h 0m"
