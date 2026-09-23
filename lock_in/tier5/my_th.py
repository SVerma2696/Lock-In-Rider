"""
tier5/my_th.py
===============
Kamen Rider MY-TH's Tier 5 gimmick: a "Priority" tab. Every open task,
numbered, most neglected first -- a task you've never worked on ranks
above every task you have, and among tasks you have worked on, the one
you haven't touched in the longest comes first. The tenth and last of
Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-22-tier5-myth-priority-design.md.

Nothing here is saved. The order is worked out fresh every time the tab
is built, reading only the existing task list and session history.

last_worked_date(), neglect_order(), and days_ago_phrase() are plain
logic, tested with no Tk and no display server. build() is the only
Tk-dependent piece; it's checked in the running app instead, matching
every other tab.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import customtkinter as ctk

from ..history import HistoryStore, SessionRecord
from ..tasks import Task


def last_worked_date(records: list[SessionRecord]) -> Optional[date]:
    """The calendar day of the most recent block in `records` (by start
    time), or None if `records` is empty."""
    if not records:
        return None
    latest = max(records, key=lambda r: r.start)
    return datetime.fromisoformat(latest.start).date()


def neglect_order(open_tasks: list[Task], history: HistoryStore, today: date) -> list[Task]:
    """`open_tasks` sorted most-neglected-first. A task with no history
    sorts before every task that has one, no matter how stale that date
    is (its sort date is a sentinel that never wins against a real
    date). Among tasks that share the same has-a-date standing, older
    sorts first; ties are broken by created_at, oldest first. `today`
    is accepted for a consistent signature with build()'s other calls,
    but the order itself is relative and doesn't need it."""
    def sort_key(task: Task):
        last = last_worked_date(history.for_task(task.id))
        has_date = last is not None
        return (has_date, last or date.min, task.created_at)

    return sorted(open_tasks, key=sort_key)


def days_ago_phrase(last: Optional[date], today: date) -> str:
    """None -> 'never started'; today -> 'today'; one day back ->
    'yesterday'; anything older -> '{n} days ago'. Never negative, even
    if `last` is somehow after `today`."""
    if last is None:
        return "never started"
    delta = max(0, (today - last).days)
    if delta == 0:
        return "today"
    if delta == 1:
        return "yesterday"
    return f"{delta} days ago"


def build(parent, *, history, tasks, theme, appearance_mode, config) -> None:
    """
    Populate `parent` with MY-TH's Priority view: every open task,
    numbered, most-neglected first, each with a short "last worked"
    phrase underneath.

    Nothing here is saved -- neglect_order() is called fresh every time
    this runs, the same as V3's chart or Decade's ranking already are.
    The tab is read-only, so there is nothing to wire up beyond this one
    pass.

    `appearance_mode` and `config` are part of every Tier 5 builder's
    signature for consistency -- MY-TH needs neither.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    open_tasks = tasks.open()
    if not open_tasks:
        ctk.CTkLabel(
            frame, text="No open tasks yet. Add one on the Tasks tab.",
            text_color=theme.primary_text_pair,
        ).pack(anchor="w", pady=(4, 0))
        return

    today = date.today()
    ordered = neglect_order(open_tasks, history, today)
    text_color = theme.primary_text_pair

    for index, task in enumerate(ordered, start=1):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8), anchor="w")
        ctk.CTkLabel(
            row, text=f"{index}. {task.name}", text_color=text_color,
            font=ctk.CTkFont(weight="bold"), anchor="w",
        ).pack(anchor="w")
        last = last_worked_date(history.for_task(task.id))
        ctk.CTkLabel(
            row, text=days_ago_phrase(last, today),
            text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11), anchor="w",
        ).pack(anchor="w")

    ctk.CTkLabel(
        frame,
        text="Ranked by which task you've worked on least recently — "
             "nothing here is saved, it's worked out fresh every time "
             "you open this tab.",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
        justify="left", wraplength=400,
    ).pack(anchor="w", pady=(6, 0))
