"""
tier5/den_o.py
===============
Kamen Rider Den-O's Tier 5 gimmick: a new "Timeline" tab showing one
calendar day's focus blocks at a time, chronological, with Prev/Next
day navigation. The second of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-14-tier5-deno-timeline-design.md.

Three plain functions do the shaping (`sorted_blocks`,
`format_time_range`, `format_day_heading`) -- tested with no Tk, no
display server, same as every pure-logic module in this codebase.
(`resolve_task_name` moved to `tier5/_shared.py` once Decade also
needed it.) `build()` is the only Tk-dependent piece, including the one
bit of state (which day is currently shown) any Tier 5 Rider has needed
so far -- it lives entirely in build()'s own closure, never touching
ui.py. `build()` itself is screenshot-verified in the running app
instead, matching how every other tab is verified.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import customtkinter as ctk

from ..history import SessionRecord
from ..tasks import TaskStore
from ._shared import format_hm, resolve_task_name

# Same hex values as ui.py's COLOR_BREAK / COLOR_WARN / COLOR_IDLE --
# not imported from there, since ui.py imports TIER5_BUILDERS FROM the
# tier5 package, so a Rider module importing color constants back out
# of ui.py would be circular. Kept as local constants with this
# cross-reference so the app's "green = good, amber = caution" language
# stays visually consistent without a code dependency in either
# direction.
_COMPLETED_COLOR = "#2f9e5f"
_ENDED_EARLY_COLOR = "#e0a800"
_MUTED_COLOR = "#5a6472"


def sorted_blocks(records: list[SessionRecord]) -> list[SessionRecord]:
    """`records`, earliest-`start`-first. HistoryStore.for_date() filters
    but doesn't sort -- Den-O sorts explicitly rather than trusting
    JSONL append order."""
    return sorted(records, key=lambda r: r.start)


def format_time_range(start_iso: str, end_iso: str) -> str:
    """'2026-09-14T09:00:00', '2026-09-14T09:25:00' -> '09:00-09:25',
    the same 24-hour %H:%M format the Activity tab already uses."""
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    return f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"


def format_day_heading(day: date) -> str:
    """date(2026, 9, 12) -> 'Saturday, September 12'. Built from `.day`
    instead of a %-d/%#d strftime code -- those are platform-specific
    (glibc vs. MSVCRT) and this app runs on Windows, macOS, and Linux
    from one codebase."""
    return f"{day.strftime('%A, %B')} {day.day}"


def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` with Den-O's Timeline view: one calendar day's
    focus blocks at a time, earliest first, with Prev/Next day buttons.

    All of the day-navigation state (which day is currently shown)
    lives right here, in this function's own closure -- ui.py and
    TIER5_BUILDERS never see it and don't need to.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    header = ctk.CTkFrame(frame, fg_color="transparent")
    header.pack(fill="x", pady=(0, 10))
    prev_button = ctk.CTkButton(header, text="< Prev", width=90)
    prev_button.pack(side="left")
    heading_label = ctk.CTkLabel(
        header, text="", font=ctk.CTkFont(size=14, weight="bold"),
        text_color=theme.primary_text_pair,
    )
    heading_label.pack(side="left", expand=True)
    next_button = ctk.CTkButton(header, text="Next >", width=90)
    next_button.pack(side="right")

    rows_frame = ctk.CTkFrame(frame, fg_color="transparent")
    rows_frame.pack(fill="both", expand=True)

    state = {"day": date.today()}

    def render_day() -> None:
        day = state["day"]
        heading_label.configure(text=format_day_heading(day))

        earliest = history.earliest_date() or date.today()
        prev_button.configure(state="normal" if day > earliest else "disabled")
        next_button.configure(state="normal" if day < date.today() else "disabled")

        for child in rows_frame.winfo_children():
            child.destroy()

        blocks = sorted_blocks(history.for_date(day))
        if not blocks:
            ctk.CTkLabel(
                rows_frame, text="No focus blocks on this day.", text_color=_MUTED_COLOR,
            ).pack(anchor="w", pady=20)
            return

        for record in blocks:
            dot_color = _COMPLETED_COLOR if record.completed else _ENDED_EARLY_COLOR
            row = ctk.CTkFrame(rows_frame, border_width=1, border_color=dot_color)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(
                row, text="●", text_color=dot_color, width=20,
                font=ctk.CTkFont(size=14),
            ).pack(side="left", padx=(10, 0))

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            title = (
                f"{format_time_range(record.start, record.end)} · "
                f"{format_hm(record.duration_seconds)}"
            )
            ctk.CTkLabel(
                left, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w")
            ctk.CTkLabel(
                left, text=resolve_task_name(record.task_id, tasks), anchor="w",
                font=ctk.CTkFont(size=10), text_color=_MUTED_COLOR,
            ).pack(anchor="w")

    def go(delta: int) -> None:
        state["day"] += timedelta(days=delta)
        render_day()

    prev_button.configure(command=lambda: go(-1))
    next_button.configure(command=lambda: go(1))
    render_day()
