"""
tier5/v3.py
===========
Kamen Rider V3's Tier 5 gimmick: a new "Hours" tab showing how long
you've focused today, plus a 14-day bar chart. The first, and smallest,
of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md.

V3's own pure function, `last_14_days()`, generalized into
`tier5/_shared.py`'s `last_n_days()` once Decade also needed a windowed
day-list, the same way duration formatting (`format_hm()`) moved there
once Den-O needed it. Nothing V3-specific is left to unit-test right
now -- see `tests/test_tier5_v3.py`. `build()` is the only Tk-dependent
piece; it's screenshot-verified in the running app instead, matching
how every other tab in ui.py is verified.
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from .. import visuals
from ._shared import format_hm, last_n_days


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
        frame, text=format_hm(headline_seconds), text_color=theme.primary_text_pair,
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

    day_values = [(day.isoformat(), secs) for day, secs in last_n_days(totals, today, 14)]
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
