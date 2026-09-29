"""
ui/insights_data.py
===================
The numbers on the Insights page, worked out from what the app already
saves: your focus blocks (sessions.jsonl) and your tasks (tasks.json).
Nothing new is saved anywhere.

The Insights page shows plain totals only. The fancy views -- V3's bar
chart, Decade's ranking, W's week-vs-week, Geats' streak -- stay on
those Riders' own pages, so picking one of them still feels special.

No window code here, so it's tested by itself
(tests/test_ui_insights_data.py).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from ..tasks import TaskStatus


@dataclass(frozen=True)
class InsightNumbers:
    today_seconds: int
    week_seconds: int  # today and the 6 days before it
    all_time_seconds: int
    blocks_logged: int
    blocks_finished: int  # ran all the way to the end
    average_block_seconds: int
    active_days: int  # days with any focus at all
    tasks_open: int
    tasks_in_progress: int
    tasks_done: int

    @property
    def finish_rate(self) -> float:
        """How many blocks ran to the end, from 0.0 to 1.0."""
        if not self.blocks_logged:
            return 0.0
        return self.blocks_finished / self.blocks_logged


def summarize(records: Iterable, tasks: Iterable, today: date) -> InsightNumbers:
    """Add everything up. `records` are SessionRecords, `tasks` are Tasks."""
    records = list(records)
    tasks = list(tasks)
    week_start = today - timedelta(days=6)

    today_seconds = week_seconds = all_time = finished = 0
    days = set()
    for record in records:
        try:
            day = datetime.fromisoformat(record.start).date()
        except (TypeError, ValueError):
            continue
        seconds = max(0, int(record.duration_seconds))
        all_time += seconds
        if seconds > 0:
            days.add(day)
        if day == today:
            today_seconds += seconds
        if week_start <= day <= today:
            week_seconds += seconds
        if record.completed:
            finished += 1

    logged = len(records)
    return InsightNumbers(
        today_seconds=today_seconds,
        week_seconds=week_seconds,
        all_time_seconds=all_time,
        blocks_logged=logged,
        blocks_finished=finished,
        average_block_seconds=all_time // logged if logged else 0,
        active_days=len(days),
        tasks_open=sum(1 for t in tasks if t.status == TaskStatus.TODO),
        tasks_in_progress=sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
        tasks_done=sum(1 for t in tasks if t.status == TaskStatus.DONE),
    )


def format_duration(seconds: int) -> str:
    """3900 -> '1h 5m', 600 -> '10m', 0 -> '0m'."""
    hours, rest = divmod(max(0, int(seconds)), 3600)
    minutes = rest // 60
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"
