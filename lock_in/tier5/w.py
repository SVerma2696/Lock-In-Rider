"""
tier5/w.py
==========
Kamen Rider W's Tier 5 gimmick: a "Week" tab that puts two weeks side by
side -- the last 7 days against the 7 days right before them -- W being
two Riders sharing one body. The sixth of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-21-tier5-w-week-compare-design.md.

`week_pairs()` and `compare_sentence()` are plain logic, tested with no
Tk and no display server. `build()` is the only Tk-dependent piece; it's
checked in the running app instead, matching every other tab.
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from .. import visuals
from ._shared import format_hm, last_n_days


def week_pairs(totals: dict[str, int], today: date) -> list[tuple[date, int, int]]:
    """Exactly 7 tuples of (day, last_week_seconds, this_week_seconds),
    oldest to newest, where `day` is the THIS-week date. Each this-week day
    is paired with the same day 7 days earlier. Built from the 14-day list
    last_n_days() already makes: its first 7 entries are last week, its
    last 7 are this week, and entry i of one pairs with entry i of the
    other. A day with no focus blocks counts as 0 seconds."""
    days = last_n_days(totals, today, 14)
    last_week, this_week = days[:7], days[7:]
    return [
        (this_day, last_seconds, this_seconds)
        for (_, last_seconds), (this_day, this_seconds) in zip(last_week, this_week)
    ]


def compare_sentence(this_seconds: int, last_seconds: int) -> str:
    """One short, kind sentence about how this week went next to last
    week. A gap under a minute counts as "the same", so it never says
    something like "0m MORE"."""
    if this_seconds == 0 and last_seconds == 0:
        return "No focus blocks in the last 14 days. Start one and it shows up here."
    gap = this_seconds - last_seconds
    if abs(gap) < 60:
        return "Same as last week. Nice and steady!"
    if gap > 0:
        return f"You did {format_hm(gap)} MORE than last week. Yay!"
    return f"That's {format_hm(-gap)} less than last week. You can do it!"


def build(parent, *, history, tasks, theme, appearance_mode, config=None) -> None:
    """
    Populate `parent` with W's Week view: two total lines (this week and
    last week, colored to match their bars), one short sentence, and a
    paired bar chart of the last 7 days against the 7 days before.

    `tasks` and `appearance_mode` are part of every Tier 5 builder's
    signature for consistency -- W needs neither. CustomTkinter's own
    (light, dark) color pairs and CTkImage(light_image=, dark_image=)
    already handle light and dark switching.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    if not history.all():
        ctk.CTkLabel(
            frame, text="No focus blocks yet. Finish one and it shows up here.",
            justify="left", wraplength=400,
        ).pack(anchor="w", pady=8)
        return

    pairs = week_pairs(history.total_seconds_by_day(), date.today())
    this_total = sum(this for _, _, this in pairs)
    last_total = sum(last for _, last, _ in pairs)

    # The colored words below double as the chart's legend: "This week"
    # is in the same green as this week's bars, "Last week" in the same
    # dark/grey as last week's bars.
    for name, seconds, color in (
        ("This week", this_total, theme.primary_text_pair),
        ("Last week", last_total, theme.secondary_text_pair),
    ):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(row, text=name, text_color=color, anchor="w").pack(
            side="left", fill="x", expand=True)
        ctk.CTkLabel(
            row, text=format_hm(seconds), text_color=color, anchor="e",
            font=ctk.CTkFont(family=visuals.display_font_family(), size=20, weight="bold"),
        ).pack(side="right")

    ctk.CTkLabel(
        frame, text=compare_sentence(this_total, last_total),
        justify="left", wraplength=400, anchor="w",
    ).pack(anchor="w", pady=(10, 12))

    chart_pairs = [(day.isoformat(), last, this) for day, last, this in pairs]
    light_image = visuals.make_week_compare_chart(
        440, 200, chart_pairs, theme.primary[0], theme.secondary[0],
        dark=False, era=theme.era,
    )
    dark_image = visuals.make_week_compare_chart(
        440, 200, chart_pairs, theme.primary[1], theme.secondary[1],
        dark=True, era=theme.era,
    )
    chart_image = ctk.CTkImage(light_image=light_image, dark_image=dark_image, size=(440, 200))
    chart_label = ctk.CTkLabel(frame, text="", image=chart_image)
    # CTkImage is garbage-collected the moment nothing references it,
    # which would blank the label the next time Tk redraws -- stashing it
    # as an attribute on the label keeps it alive as long as the label is.
    chart_label._w_chart_image = chart_image
    chart_label.pack(anchor="w")

    ctk.CTkLabel(
        frame, text="Last 7 days vs the 7 days before · every focus block counts, finished or not",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(6, 0))
