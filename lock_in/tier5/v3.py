"""
tier5/v3.py
===========
Kamen Rider V3's Tier 5 gimmick: a new "Hours" tab showing how long
you've focused today, plus a 14-day bar chart. The first, and smallest,
of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md.

Two plain functions do the shaping (`last_14_days`, `_format_hm`) --
tested with no Tk, no display server, same as every pure-logic module
in this codebase. `build()` is the only Tk-dependent piece; it's
screenshot-verified in the running app instead, matching how every
other tab in ui.py is verified.
"""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from .. import visuals


def last_14_days(totals: dict[str, int], today: date) -> list[tuple[date, int]]:
    """14 entries, oldest -> newest, ending on `today`. A day absent
    from `totals` (no focus blocks that day) contributes 0 seconds --
    the chart always has 14 bars, even on a brand new install."""
    return [
        (day, totals.get(day.isoformat(), 0))
        for day in (today - timedelta(days=offset) for offset in range(13, -1, -1))
    ]


def _format_hm(seconds: int) -> str:
    """3900 -> '1h 5m'; 600 -> '10m'; 0 -> '0m'. Hours are only shown at
    all once there's at least one -- an under-an-hour total never shows
    a redundant '0h'."""
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` (an empty Tier 5 tab frame) with V3's Hours view:
    a headline number for today, and a 14-day bar chart below it.

    `tasks` and `appearance_mode` are part of every Tier 5 builder's
    signature for consistency across the 10 Riders -- V3 doesn't need
    either. CustomTkinter's own `(light, dark)` color-tuple support and
    `CTkImage(light_image=, dark_image=)` already handle V3's light/dark
    switching without checking `appearance_mode` by hand.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    totals = history.total_seconds_by_day()
    today = date.today()
    headline_seconds = totals.get(today.isoformat(), 0)

    ctk.CTkLabel(
        frame, text=_format_hm(headline_seconds), text_color=theme.primary_text_pair,
        font=ctk.CTkFont(family=visuals.display_font_family(), size=32, weight="bold"),
    ).pack(anchor="w", pady=(4, 0))
    ctk.CTkLabel(
        frame, text="focused today", text_color=theme.primary_text_pair,
    ).pack(anchor="w", pady=(0, 12))

    if not history.all():
        ctk.CTkLabel(
            frame, text="No focus blocks yet. Finish one and it shows up here.",
            justify="left", wraplength=400,
        ).pack(anchor="w", pady=8)
        return

    day_values = [(day.isoformat(), secs) for day, secs in last_14_days(totals, today)]
    light_image = visuals.make_hours_chart(
        440, 200, day_values, theme.primary[0], theme.secondary[0],
        dark=False, era=theme.era,
    )
    dark_image = visuals.make_hours_chart(
        440, 200, day_values, theme.primary[1], theme.secondary[1],
        dark=True, era=theme.era,
    )
    chart_image = ctk.CTkImage(light_image=light_image, dark_image=dark_image, size=(440, 200))
    chart_label = ctk.CTkLabel(frame, text="", image=chart_image)
    # CTkImage is garbage-collected the moment nothing references it,
    # which would blank the label the next time Tk redraws -- stashing
    # it as a plain attribute on the label itself keeps it alive for as
    # long as the label is.
    chart_label._v3_chart_image = chart_image
    chart_label.pack(anchor="w")

    ctk.CTkLabel(
        frame, text="Last 14 days · every focus block counts, finished or not",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(6, 0))
