"""
tier5/den_o.py
===============
Kamen Rider Den-O's Tier 5 gimmick: a "Timeline" tab. It shows one day's
focus blocks at a time, earliest first, with Prev / Next buttons to
walk through the days. The second of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-14-tier5-deno-timeline-design.md.

The little helpers that put blocks in order and write out times and day
names now live in tier5/_shared.py, because Zi-O's History tab needs
the very same ones (see
docs/superpowers/specs/2026-09-17-tier5-zi-o-history-editor-design.md).
So all that's left here is build(), which draws the tab. It remembers
which day you're looking at inside itself, so ui.py never has to know.
build() is checked by running the real app, like every other tab.
"""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from ._shared import format_day_heading, format_hm, format_time_range, resolve_task_name, sorted_blocks

# The same colors ui.py uses (COLOR_BREAK / COLOR_WARN / COLOR_IDLE):
# green = good, amber = careful, gray = quiet. They are copied here
# instead of imported, because ui.py already imports this package --
# importing back the other way would make the two files chase each
# other in a circle.
_COMPLETED_COLOR = "#2f9e5f"
_ENDED_EARLY_COLOR = "#e0a800"
_MUTED_COLOR = "#5a6472"


def build(parent, *, history, tasks, theme, appearance_mode, config=None) -> None:
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
