"""Tests for MY-TH's Tier 5 gimmick: last_worked_date(), neglect_order(),
and days_ago_phrase(). No Tk, no display server -- see tier5/my_th.py."""

from datetime import date, timedelta

import pytest

from lock_in.history import HistoryStore, SessionRecord
from lock_in.tasks import Task, TaskStatus
from lock_in.tier5.my_th import days_ago_phrase, last_worked_date, neglect_order

TODAY = date(2026, 9, 22)


@pytest.fixture
def history(tmp_path) -> HistoryStore:
    return HistoryStore(tmp_path / "sessions.jsonl")


def _task(task_id: str, created_at: str) -> Task:
    return Task(id=task_id, name=task_id, created_at=created_at)


def _record(task_id: str, days_ago: int, today: date = TODAY) -> SessionRecord:
    day = today - timedelta(days=days_ago)
    start = f"{day.isoformat()}T09:00:00"
    end = f"{day.isoformat()}T09:25:00"
    return SessionRecord(start=start, end=end, duration_seconds=1500, task_id=task_id, completed=True)


# --- last_worked_date ------------------------------------------------------ #

def test_last_worked_date_with_no_records_is_none():
    assert last_worked_date([]) is None


def test_last_worked_date_returns_the_latest_records_day():
    early = SessionRecord(start="2026-09-17T09:00:00", end="2026-09-17T09:25:00",
                           duration_seconds=1500, task_id="t1", completed=True)
    late = SessionRecord(start="2026-09-21T09:00:00", end="2026-09-21T09:25:00",
                          duration_seconds=1500, task_id="t1", completed=True)
    assert last_worked_date([early, late]) == date(2026, 9, 21)
    assert last_worked_date([late, early]) == date(2026, 9, 21)


# --- neglect_order ----------------------------------------------------------- #

def test_never_worked_task_sorts_before_a_worked_one_no_matter_how_stale(history):
    never = _task("never", "2026-01-01T00:00:00")
    worked = _task("worked", "2020-01-01T00:00:00")
    history.record(_record("worked", 400))
    assert neglect_order([worked, never], history, TODAY) == [never, worked]


def test_never_worked_tasks_are_tie_broken_by_creation_date_oldest_first(history):
    newer = _task("newer", "2026-02-01T00:00:00")
    older = _task("older", "2026-01-01T00:00:00")
    assert neglect_order([newer, older], history, TODAY) == [older, newer]


def test_worked_tasks_sort_by_oldest_last_worked_date_first(history):
    stale = _task("stale", "2026-01-01T00:00:00")
    fresh = _task("fresh", "2026-01-01T00:00:00")
    history.record(_record("fresh", 1))
    history.record(_record("stale", 10))
    assert neglect_order([fresh, stale], history, TODAY) == [stale, fresh]


def test_worked_tasks_last_worked_the_same_day_are_tie_broken_by_created_at(history):
    newer = _task("newer", "2026-02-01T00:00:00")
    older = _task("older", "2026-01-01T00:00:00")
    history.record(_record("newer", 2))
    history.record(_record("older", 2))
    assert neglect_order([newer, older], history, TODAY) == [older, newer]


def test_neglect_order_with_no_open_tasks_is_empty(history):
    assert neglect_order([], history, TODAY) == []


def test_task_status_has_no_effect_on_the_order(history):
    todo = Task(id="todo", name="todo", created_at="2026-01-01T00:00:00", status=TaskStatus.TODO)
    in_progress = Task(id="in_progress", name="in_progress", created_at="2026-01-02T00:00:00",
                        status=TaskStatus.IN_PROGRESS)
    assert neglect_order([in_progress, todo], history, TODAY) == [todo, in_progress]


# --- days_ago_phrase ---------------------------------------------------------- #

def test_days_ago_phrase_for_never_started():
    assert days_ago_phrase(None, TODAY) == "never started"


def test_days_ago_phrase_for_today():
    assert days_ago_phrase(TODAY, TODAY) == "today"


def test_days_ago_phrase_for_yesterday():
    assert days_ago_phrase(TODAY - timedelta(days=1), TODAY) == "yesterday"


def test_days_ago_phrase_for_several_days_ago():
    assert days_ago_phrase(TODAY - timedelta(days=5), TODAY) == "5 days ago"


def test_days_ago_phrase_across_a_month_boundary():
    today = date(2026, 10, 2)
    assert days_ago_phrase(date(2026, 9, 28), today) == "4 days ago"


def test_days_ago_phrase_across_a_year_boundary():
    today = date(2027, 1, 2)
    assert days_ago_phrase(date(2026, 12, 29), today) == "4 days ago"


def test_days_ago_phrase_never_goes_negative():
    """Defensive: a last-worked date somehow after 'today' (e.g. the
    system clock moved backward) reads as 'today', never a nonsensical
    negative count."""
    assert days_ago_phrase(TODAY + timedelta(days=1), TODAY) == "today"


# --- wiring --------------------------------------------------------------- #

def test_priority_order_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, my_th
    assert TIER5_BUILDERS["priority_order"] is my_th.build


def test_priority_order_has_the_priority_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["priority_order"] == "Priority"


def test_my_th_builder_accepts_the_standard_tier5_signature():
    import inspect
    from lock_in.tier5 import my_th
    params = inspect.signature(my_th.build).parameters
    for name in ("parent", "history", "tasks", "theme", "appearance_mode", "config"):
        assert name in params
