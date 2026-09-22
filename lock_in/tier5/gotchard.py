"""
tier5/gotchard.py
==================
Kamen Rider Gotchard's Tier 5 gimmick: a "Badges" tab. Nine collectible
badges reward real progress -- blocks done, a big day, total hours, a
checked-off task, and streaks of days that reached the daily goal
Geats' "Goal" tab controls. The eighth of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-21-tier5-gotchard-badges-design.md.

Once a badge is won it is saved to Config.badges_earned and never taken
away by this module, even if the history changes or the goal is edited
later -- see build() below.

Everything except build() is plain logic, tested with no Tk and no
display server. build() is the only Tk-dependent piece; it's checked in
the running app instead, matching every other tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import customtkinter as ctk

from .. import visuals
from ._shared import format_hm

# What a not-yet-won card and its text look like -- CustomTkinter's own
# grays, picked for light and dark mode.
_EMPTY_CARD = ("gray80", "gray30")
_EMPTY_NAME = ("gray20", "gray80")
_EMPTY_BODY = ("gray30", "gray70")


@dataclass(frozen=True)
class Badge:
    """One badge's fixed description. `metric` names which number in a
    Progress it looks at; `target` is the smallest value that wins it."""

    id: str
    name: str
    hint: str
    metric: str
    target: int


# The nine badges, in the fixed order they're shown and checked. Adding a
# badge later is one new row here -- nothing else needs to change shape.
BADGES: list[Badge] = [
    Badge("first_step", "First Step", "Do your first focus block.", "blocks", 1),
    Badge("ten_blocks", "Ten Blocks", "Do 10 focus blocks.", "blocks", 10),
    Badge("hour_day", "One Hour Day", "Focus for 1 hour in one day.", "best_day_seconds", 3600),
    Badge("big_day", "Big Day", "Focus for 3 hours in one day.", "best_day_seconds", 10800),
    Badge("ten_hours", "Ten Hours", "Focus for 10 hours in all.", "total_seconds", 36000),
    Badge("task_done", "Task Done", "Check off a task.", "tasks_done", 1),
    Badge("goal_done", "Goal Done", "Reach your daily goal once.", "longest_run", 1),
    Badge("three_days", "Three in a Row", "Reach your daily goal 3 days in a row.", "longest_run", 3),
    Badge("seven_days", "Seven in a Row", "Reach your daily goal 7 days in a row.", "longest_run", 7),
]


@dataclass(frozen=True)
class Progress:
    """The five numbers the badges look at."""

    blocks: int
    best_day_seconds: int
    total_seconds: int
    longest_run: int
    tasks_done: int


def longest_goal_run(totals: dict[str, int], goal_seconds: int) -> int:
    """The longest stretch of days in a row that each reached the goal,
    found anywhere in the history -- not just a streak ending today.
    0 for empty `totals`. Works from the calendar dates of the days that
    reached the goal, so a run across a month or year boundary counts
    right, and a long history is sorted once instead of walked one day
    at a time, so it never loops forever."""
    goal_days = sorted(
        date.fromisoformat(day) for day, seconds in totals.items()
        if seconds >= goal_seconds
    )
    if not goal_days:
        return 0
    longest = current = 1
    for previous, day in zip(goal_days, goal_days[1:]):
        current = current + 1 if day == previous + timedelta(days=1) else 1
        longest = max(longest, current)
    return longest


def progress(totals: dict[str, int], block_count: int, goal_seconds: int, tasks_done: int) -> Progress:
    """Turn the raw history into the five numbers the badges compare
    against their targets. `totals` is history.total_seconds_by_day()
    and `block_count` is len(history.all())."""
    return Progress(
        blocks=block_count,
        best_day_seconds=max(totals.values(), default=0),
        total_seconds=sum(totals.values()),
        longest_run=longest_goal_run(totals, goal_seconds),
        tasks_done=tasks_done,
    )


def earned_ids(p: Progress) -> list[str]:
    """The ids of every badge `p` has won, in badge order."""
    values = {
        "blocks": p.blocks,
        "best_day_seconds": p.best_day_seconds,
        "total_seconds": p.total_seconds,
        "tasks_done": p.tasks_done,
        "longest_run": p.longest_run,
    }
    return [badge.id for badge in BADGES if values[badge.metric] >= badge.target]


def saved_badges(raw) -> list[str]:
    """The safe reader for Config.badges_earned. A hand-edited
    config.json could hold anything, so this never raises: anything that
    isn't a list becomes an empty list. Entries that aren't text are
    dropped, and repeats are dropped, keeping the first. Names this app
    doesn't recognize are KEPT as-is (so a list saved by a newer app is
    never shortened here), but the tab never counts or shows them."""
    if not isinstance(raw, list):
        return []
    kept: list[str] = []
    for item in raw:
        if isinstance(item, str) and item not in kept:
            kept.append(item)
    return kept


def newly_won(earned: list[str], saved: list[str]) -> list[str]:
    """The ids in `earned` that aren't in `saved` yet, in badge order --
    what build() needs to add to Config.badges_earned this time."""
    return [badge_id for badge_id in earned if badge_id not in saved]


def badge_sentence(have: int, total: int, new_names: list[str]) -> str:
    """One short, kind sentence about the collection. A badge just won
    this build always gets its own sentence, even on the build where you
    also complete the whole set."""
    if len(new_names) == 1:
        return f"New! You won {new_names[0]}!"
    if len(new_names) > 1:
        return f"New! You won {len(new_names)} badges!"
    if have == 0:
        return "Do a focus block to win your first badge."
    if have == total:
        return "You got them all! Wow!"
    return f"You have {have} of {total}. Keep going!"


def build(parent, *, history, tasks, theme, appearance_mode, config) -> None:
    """
    Populate `parent` with Gotchard's Badges view: how many of the 9
    badges are won, one sentence about the collection, and a 3-by-3 grid
    of cards.

    Every widget is built once -- there are no buttons on this tab, so
    nothing is ever destroyed and rebuilt from inside a click.

    `tasks` is used for tasks.done() (the Task Done badge). `appearance_
    mode` is part of every Tier 5 builder's signature for consistency --
    Gotchard doesn't need it, since CustomTkinter's own (light, dark)
    color pairs already handle light and dark switching.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    totals = history.total_seconds_by_day()
    goal_seconds = config.effective_daily_goal_minutes() * 60
    current = progress(totals, len(history.all()), goal_seconds, len(tasks.done()))
    earned = earned_ids(current)

    saved = saved_badges(config.badges_earned)
    new_ids = newly_won(earned, saved)
    if new_ids:
        config.badges_earned = saved + new_ids
        try:
            config.save()
        except OSError:
            # For example, the file is locked. Roll back so the next
            # build tries the save again -- the new badges still show
            # for the rest of THIS session (`won` below is built from
            # the local `new_ids`, not re-read from config), they just
            # aren't durably saved yet.
            config.badges_earned = saved

    won = set(saved) | set(new_ids)
    have = sum(1 for badge in BADGES if badge.id in won)
    new_names = [badge.name for badge in BADGES if badge.id in new_ids]

    text_color = theme.primary_text_pair
    big_font = ctk.CTkFont(family=visuals.display_font_family(), size=20, weight="bold")

    # --- the count line ----------------------------------------------- #
    header = ctk.CTkFrame(frame, fg_color="transparent")
    header.pack(fill="x", pady=(4, 0))
    ctk.CTkLabel(header, text="Badges", text_color=text_color, anchor="w").pack(
        side="left", fill="x", expand=True)
    ctk.CTkLabel(
        header, text=f"{have} of {len(BADGES)}", text_color=text_color,
        anchor="e", font=big_font,
    ).pack(side="right")

    ctk.CTkLabel(
        frame, text=badge_sentence(have, len(BADGES), new_names),
        text_color=text_color, justify="left", wraplength=400, anchor="w",
    ).pack(anchor="w", pady=(6, 12))

    # --- the 3-by-3 grid ------------------------------------------------ #
    grid = ctk.CTkFrame(frame, fg_color="transparent")
    grid.pack(fill="x")
    for column in range(3):
        grid.grid_columnconfigure(column, weight=1, uniform="badge")

    won_text_color = theme.button_text_pair
    for index, badge in enumerate(BADGES):
        row, column = divmod(index, 3)
        is_won = badge.id in won
        card = ctk.CTkFrame(
            grid, corner_radius=8,
            fg_color=theme.secondary if is_won else _EMPTY_CARD,
        )
        card.grid(row=row, column=column, padx=4, pady=4, sticky="nsew")
        name_color = won_text_color if is_won else _EMPTY_NAME
        body_color = won_text_color if is_won else _EMPTY_BODY
        ctk.CTkLabel(
            card, text=badge.name, text_color=name_color,
            font=ctk.CTkFont(weight="bold"), wraplength=120, justify="left",
        ).pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(
            card, text=badge.hint, text_color=body_color,
            font=ctk.CTkFont(size=11), wraplength=120, justify="left",
        ).pack(anchor="w", padx=10)
        ctk.CTkLabel(
            card, text="Got it!" if is_won else "Not yet", text_color=body_color,
            font=ctk.CTkFont(size=11, weight="bold"), wraplength=120, justify="left",
        ).pack(anchor="w", padx=10, pady=(2, 10))

    # --- captions --------------------------------------------------------- #
    ctk.CTkLabel(
        frame, text="Every focus block counts, finished or not · a badge is yours to keep",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(10, 0))
    ctk.CTkLabel(
        frame,
        text=f"Goal badges use your daily goal of {format_hm(goal_seconds)}. Pick Geats to change it.",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
        justify="left", wraplength=400,
    ).pack(anchor="w")
