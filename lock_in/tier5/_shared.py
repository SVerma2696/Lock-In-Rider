"""
tier5/_shared.py
=================
Little helpers that more than one Tier 5 Rider uses (like turning
seconds into "1h 5m", or a day into "Saturday, September 12").

Kept in its own leaf module with NO imports from anywhere else in
tier5/ (not even tier5/__init__.py) on purpose: __init__.py does
`from . import v3` / `from . import den_o` / `from . import decade` to
build TIER5_BUILDERS, so if a Rider module imported a shared helper
back out of __init__.py, that would be a circular import. Importing
from _shared.py instead means tier5/__init__.py's own import order
never matters to any Rider module -- see
docs/superpowers/specs/2026-09-14-tier5-deno-timeline-design.md and
docs/superpowers/specs/2026-09-14-tier5-decade-analytics-design.md.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from ..history import SessionRecord
from ..tasks import TaskStore


def format_hm(seconds: int) -> str:
    """3900 -> '1h 5m'; 600 -> '10m'; 0 -> '0m'. Hours are only shown at
    all once there's at least one -- an under-an-hour total never shows
    a redundant '0h'."""
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def last_n_days(totals: dict[str, int], today: date, n: int) -> list[tuple[date, int]]:
    """n entries, oldest -> newest, ending on `today`. A day absent
    from `totals` (no focus blocks that day) contributes 0 seconds --
    the chart always has exactly n bars, even on a brand new install."""
    return [
        (day, totals.get(day.isoformat(), 0))
        for day in (today - timedelta(days=offset) for offset in range(n - 1, -1, -1))
    ]


def resolve_task_name(task_id: Optional[str], tasks: TaskStore) -> str:
    """None -> 'No task'. A live task's id -> its real name. An id that
    doesn't match any task any more (the task was deleted after this
    block was logged) -> 'Deleted task', never a crash or a blank."""
    if task_id is None:
        return "No task"
    task = tasks.get(task_id)
    if task is None:
        return "Deleted task"
    return task.name


def sorted_blocks(records: list[SessionRecord]) -> list[SessionRecord]:
    """Put the blocks in order, earliest one first. HistoryStore.for_date()
    finds the right day but doesn't sort, so whoever shows a day sorts it."""
    return sorted(records, key=lambda r: r.start)


def format_time_range(start_iso: str, end_iso: str) -> str:
    """'2026-09-14T09:00:00', '2026-09-14T09:25:00' -> '09:00–09:25'.
    Same 24-hour clock the Activity tab uses."""
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    return f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"


def format_day_heading(day: date) -> str:
    """date(2026, 9, 12) -> 'Saturday, September 12'. The day number
    comes from `.day` on purpose: the strftime codes for "no leading
    zero" are different on Windows and on Mac/Linux, and this app runs
    on all three."""
    return f"{day.strftime('%A, %B')} {day.day}"
