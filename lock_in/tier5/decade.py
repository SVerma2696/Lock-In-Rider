"""
tier5/decade.py
================
Kamen Rider Decade's Tier 5 gimmick: an "Analytics" tab combining a
30-day version of V3's bar chart with a "Top tasks" ranking. The third
of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-14-tier5-decade-analytics-design.md.

`ranked_tasks()` does the one piece of shaping this Rider needs beyond
what V3 and Den-O already built and shared -- tested with no Tk, no
display server. `build()` is the only Tk-dependent piece; it's
screenshot-verified in the running app instead, matching every other
tab.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import customtkinter as ctk

from .. import visuals
from ..tasks import TaskStore
from ._shared import format_hm, last_n_days, resolve_task_name


def ranked_tasks(
    totals_by_task: dict[Optional[str], int], tasks: TaskStore,
) -> list[tuple[str, int]]:
    """[(name, seconds), ...] sorted by seconds descending, capped at
    the top 10. Every task_id (including None, for untagged time) is
    resolved through resolve_task_name() -- two different tasks that
    were both later deleted show as two separate 'Deleted task' rows,
    never merged, since there's no way left to tell them apart by name."""
    resolved = [
        (resolve_task_name(task_id, tasks), seconds)
        for task_id, seconds in totals_by_task.items()
    ]
    resolved.sort(key=lambda pair: pair[1], reverse=True)
    return resolved[:10]


def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` with Decade's Analytics view: a 30-day bar chart
    (V3's renderer, a wider window), then a "Top tasks" ranking below
    it.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    if not history.all():
        ctk.CTkLabel(
            frame, text="No focus blocks yet. Finish one and it shows up here.",
            justify="left", wraplength=400,
        ).pack(anchor="w", pady=8)
        return

    totals_by_day = history.total_seconds_by_day()
    today = date.today()
    day_values = [(day.isoformat(), secs) for day, secs in last_n_days(totals_by_day, today, 30)]
    light_image = visuals.make_hours_chart(
        640, 200, day_values, theme.primary[0], theme.secondary[0],
        dark=False, era=theme.era,
    )
    dark_image = visuals.make_hours_chart(
        640, 200, day_values, theme.primary[1], theme.secondary[1],
        dark=True, era=theme.era,
    )
    chart_image = ctk.CTkImage(light_image=light_image, dark_image=dark_image, size=(640, 200))
    chart_label = ctk.CTkLabel(frame, text="", image=chart_image)
    # Same CTkImage-garbage-collection guard V3 uses -- see its build().
    chart_label._decade_chart_image = chart_image
    chart_label.pack(anchor="w")

    ctk.CTkLabel(
        frame, text="Last 30 days", text_color=("gray40", "gray60"),
        font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(6, 14))

    ctk.CTkLabel(
        frame, text="Top tasks", font=ctk.CTkFont(size=13, weight="bold"),
        text_color=theme.primary_text_pair,
    ).pack(anchor="w", pady=(0, 6))

    for name, seconds in ranked_tasks(history.total_seconds_by_task(), tasks):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=name, anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(row, text=format_hm(seconds), anchor="e").pack(side="right")
