"""
tier5/geats.py
==============
Kamen Rider Geats' Tier 5 gimmick: a "Goal" tab. You pick how many
minutes you want to focus each day, a bar fills up as you focus, and a
streak counts the days in a row you reached your goal. The seventh of
Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-21-tier5-geats-daily-goal-design.md.

The six small functions below are plain logic, tested with no Tk and no
display server. `build()` is the only Tk-dependent piece; it's checked in
the running app instead, matching every other tab.
"""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from .. import visuals
from ..config import (
    DAILY_GOAL_MAX_MINUTES,
    DAILY_GOAL_MIN_MINUTES,
    DAILY_GOAL_STEP_MINUTES,
)
from ._shared import format_hm, last_n_days

# What an empty (goal not reached) box looks like -- CustomTkinter's own
# gray, picked for light and dark mode.
_EMPTY_BOX = ("gray80", "gray30")


def streak_days(totals: dict[str, int], today: date, goal_seconds: int) -> int:
    """How many days in a row reached the goal. A day is done when its
    total is at least the goal. If today is done, today counts. If today
    is NOT done yet, it is still in play until midnight, so the streak is
    counted back from yesterday instead -- being part-way through the day
    never breaks it. The walk also stops at the first day in `totals`, as
    a second safety net."""
    if not totals:
        return 0
    earliest = date.fromisoformat(min(totals))
    day = today
    if totals.get(day.isoformat(), 0) < goal_seconds:
        day = today - timedelta(days=1)
    count = 0
    while day >= earliest and totals.get(day.isoformat(), 0) >= goal_seconds:
        count += 1
        day -= timedelta(days=1)
    return count


def week_dots(totals: dict[str, int], today: date, goal_seconds: int) -> list[tuple[date, bool]]:
    """Exactly 7 tuples of (day, done), oldest to newest, ending on today.
    Uses last_n_days(), so a day with no focus blocks counts as 0 seconds
    and is not done."""
    return [
        (day, seconds >= goal_seconds)
        for day, seconds in last_n_days(totals, today, 7)
    ]


def goal_sentence(today_seconds: int, goal_seconds: int) -> str:
    """One short, kind sentence about today. The time left is rounded UP
    to a whole minute, so 30 seconds short reads "1m to go", never
    "0m to go"."""
    if today_seconds >= goal_seconds:
        return "You did it! Goal done for today. Yay!"
    if today_seconds == 0:
        return "Start a focus block to fill the bar."
    left_seconds = -(-(goal_seconds - today_seconds) // 60) * 60
    return f"{format_hm(left_seconds)} to go. You can do it!"


def days_in_a_row(streak: int) -> str:
    """'5 days in a row', '1 day in a row', '0 days in a row'. The one
    place the word "day" is made singular."""
    unit = "day" if streak == 1 else "days"
    return f"{streak} {unit} in a row"


def streak_sentence(streak: int, today_done: bool) -> str:
    """One short, kind sentence about the streak."""
    if streak == 0:
        return "No streak yet. Reach your goal today to start one!"
    if today_done:
        return f"{days_in_a_row(streak)}. Wow!"
    return f"{days_in_a_row(streak)}. Do your goal today to keep it going!"


def stepped_goal(minutes: int, direction: int) -> int:
    """What one press of the minus (direction -1) or plus (direction +1)
    button does: 15 minutes up or down, never below 15 minutes or above
    12 hours."""
    stepped = minutes + DAILY_GOAL_STEP_MINUTES * direction
    return max(DAILY_GOAL_MIN_MINUTES, min(DAILY_GOAL_MAX_MINUTES, stepped))


def build(parent, *, history, tasks, theme, appearance_mode, config) -> None:
    """
    Populate `parent` with Geats' Goal view: today's bar against the daily
    goal, the goal's minus and plus buttons, the streak, and seven boxes
    for the last 7 days.

    Every widget is built once, and refresh() then re-configures them. The
    buttons never destroy and rebuild the tab from inside their own click,
    which is what makes them safe to press.

    `tasks` and `appearance_mode` are part of every Tier 5 builder's
    signature for consistency -- Geats needs neither. CustomTkinter's own
    (light, dark) color pairs already handle light and dark switching.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    totals = history.total_seconds_by_day()
    today = date.today()
    today_seconds = totals.get(today.isoformat(), 0)
    week = last_n_days(totals, today, 7)
    text_color = theme.primary_text_pair
    big_font = ctk.CTkFont(family=visuals.display_font_family(), size=20, weight="bold")

    def line(name: str) -> ctk.CTkLabel:
        """A row with `name` on the left and a big value on the right.
        Returns the value label so refresh() can change it."""
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(row, text=name, text_color=text_color, anchor="w").pack(
            side="left", fill="x", expand=True)
        value = ctk.CTkLabel(row, text="", text_color=text_color, anchor="e", font=big_font)
        value.pack(side="right")
        return value

    def sentence() -> ctk.CTkLabel:
        label = ctk.CTkLabel(frame, text="", justify="left", wraplength=400, anchor="w")
        label.pack(anchor="w", pady=(6, 12))
        return label

    # --- today's bar ------------------------------------------------------ #
    today_value = line("Today")
    bar = ctk.CTkProgressBar(frame, progress_color=theme.secondary)
    bar.pack(fill="x", pady=(6, 0))
    today_sentence = sentence()

    # --- the goal row: Daily goal ........ [-] 1h [+] --------------------- #
    goal_row = ctk.CTkFrame(frame, fg_color="transparent")
    goal_row.pack(fill="x", pady=(0, 12))
    ctk.CTkLabel(goal_row, text="Daily goal", text_color=text_color, anchor="w").pack(
        side="left", fill="x", expand=True)
    # Packed from the right edge inward: plus first, then the number, then
    # minus, so they read minus, number, plus from left to right.
    plus_button = ctk.CTkButton(goal_row, text="+", width=36, command=lambda: change_goal(+1))
    plus_button.pack(side="right")
    goal_value = ctk.CTkLabel(goal_row, text="", text_color=text_color, width=80)
    goal_value.pack(side="right", padx=6)
    minus_button = ctk.CTkButton(goal_row, text="-", width=36, command=lambda: change_goal(-1))
    minus_button.pack(side="right")

    # --- the streak ------------------------------------------------------- #
    streak_value = line("Streak")
    streak_text = sentence()

    # --- seven boxes, today last ------------------------------------------ #
    boxes_row = ctk.CTkFrame(frame, fg_color="transparent")
    boxes_row.pack(anchor="w")
    boxes = []
    for day, _ in week:
        cell = ctk.CTkFrame(boxes_row, fg_color="transparent")
        cell.pack(side="left", padx=4)
        box = ctk.CTkFrame(cell, width=28, height=28, corner_radius=6, fg_color=_EMPTY_BOX)
        box.pack()
        ctk.CTkLabel(
            cell, text=day.strftime("%a")[0],
            text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
        ).pack()
        boxes.append(box)

    ctk.CTkLabel(
        frame, text="Every focus block counts, finished or not · every day is judged by today's goal",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(10, 0))

    def refresh() -> None:
        """Re-configure every widget that depends on the goal."""
        goal_minutes = config.effective_daily_goal_minutes()
        goal_seconds = goal_minutes * 60
        streak = streak_days(totals, today, goal_seconds)

        today_value.configure(text=f"{format_hm(today_seconds)} of {format_hm(goal_seconds)}")
        bar.set(min(1.0, today_seconds / goal_seconds))
        today_sentence.configure(text=goal_sentence(today_seconds, goal_seconds))

        goal_value.configure(text=format_hm(goal_seconds))
        minus_button.configure(state="normal" if goal_minutes > DAILY_GOAL_MIN_MINUTES else "disabled")
        plus_button.configure(state="normal" if goal_minutes < DAILY_GOAL_MAX_MINUTES else "disabled")

        streak_value.configure(text=days_in_a_row(streak))
        streak_text.configure(text=streak_sentence(streak, today_seconds >= goal_seconds))
        for box, (_, done) in zip(boxes, week_dots(totals, today, goal_seconds)):
            box.configure(fg_color=theme.secondary if done else _EMPTY_BOX)

    def change_goal(direction: int) -> None:
        config.daily_goal_minutes = stepped_goal(config.effective_daily_goal_minutes(), direction)
        try:
            config.save()
        except OSError:
            # For example, the file is locked. The new goal still works for
            # the rest of this session, and the next press tries the save again.
            pass
        refresh()

    refresh()
