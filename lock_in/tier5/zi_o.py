"""
tier5/zi_o.py
==============
Kamen Rider Zi-O's Tier 5 gimmick: a "History" tab. It looks just like
Den-O's Timeline -- one day at a time, with Prev / Next buttons -- but
here you can FIX the past. Every block has a little menu to pick a
different task for it, and a Delete button to throw it away.

Why Zi-O? He's the Time King, and his whole show is about changing
history. The fourth of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-17-tier5-zi-o-history-editor-design.md.

Only two things can change: which task a block belongs to, and whether
the block exists at all. When it started, when it ended and how long it
was never change -- those are the true facts the timer measured.

build_reassign_choices() is a plain function (no windows, no Tk) so it
can be tested by itself. build() draws the tab. It remembers which day
you're looking at inside itself, so ui.py never has to know. A Delete
button's "Really delete?" state lives only inside that one row, so it
can never spill into another row. build() is checked by running the
real app, like every other Tier 5 tab.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import customtkinter as ctk

from ..tasks import Task
from ._shared import (
    format_day_heading, format_hm, format_time_range, resolve_task_name, sorted_blocks,
)

# The same colors ui.py uses (green = good, amber = careful, gray =
# quiet), copied here so this file doesn't need to import ui.py. Den-O
# keeps its own copy too, so no Rider file has to import another
# Rider's file just for three colors.
_COMPLETED_COLOR = "#2f9e5f"
_ENDED_EARLY_COLOR = "#e0a800"
_MUTED_COLOR = "#5a6472"

_NO_TASK_LABEL = "No task"


def build_reassign_choices(all_tasks: list[Task]) -> tuple[list[str], dict[str, Optional[str]]]:
    """Get the words for the "pick a task" menu.

    Returns (menu words, word -> task id). "No task" is always first and
    means "no task" (None). Two tasks can have the same name, so if a
    word is already taken the next one gets " (2)", " (3)" and so on --
    that way every word points at exactly ONE task.
    """
    words = [_NO_TASK_LABEL]
    ids: dict[str, Optional[str]] = {_NO_TASK_LABEL: None}
    for task in sorted(all_tasks, key=lambda t: t.name.lower()):
        word = task.name
        counter = 1
        while word in ids:
            counter += 1
            word = f"{task.name} ({counter})"
        words.append(word)
        ids[word] = task.id
    return words, ids


def build(parent, *, history, tasks, theme, appearance_mode, config=None) -> None:
    """
    Fill `parent` with Zi-O's History tab: Den-O's day-by-day list, plus
    a task menu and a Delete button on every block.
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

        # Made fresh every time the day is drawn, so a task that was
        # renamed or deleted on the Tasks tab shows up right.
        words, word_to_id = build_reassign_choices(tasks.all())
        id_to_word = {task_id: word for word, task_id in word_to_id.items() if task_id is not None}

        for record in blocks:
            render_row(record, words, word_to_id, id_to_word)

    def render_row(record, words, word_to_id, id_to_word) -> None:
        dot_color = _COMPLETED_COLOR if record.completed else _ENDED_EARLY_COLOR
        row = ctk.CTkFrame(rows_frame, border_width=1, border_color=dot_color)
        row.pack(fill="x", pady=3)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(
            top, text="●", text_color=dot_color, width=20,
            font=ctk.CTkFont(size=14),
        ).pack(side="left")
        title = (
            f"{format_time_range(record.start, record.end)} · "
            f"{format_hm(record.duration_seconds)}"
        )
        ctk.CTkLabel(
            top, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", fill="x", expand=True)

        controls = ctk.CTkFrame(row, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=(2, 8))

        def on_reassign(chosen_word: str) -> None:
            history.reassign_task(record.id, word_to_id.get(chosen_word))
            render_day()

        reassign_menu = ctk.CTkOptionMenu(
            controls, values=words, command=on_reassign, width=160,
        )
        # .set() only changes the words showing on the menu, so it can
        # show "Deleted task" even though that isn't one of the choices.
        # (That's a block whose task was deleted -- you can still pick
        # a new task for it.)
        shown = id_to_word.get(record.task_id) or resolve_task_name(record.task_id, tasks)
        reassign_menu.set(shown)
        reassign_menu.pack(side="left")

        delete_area = ctk.CTkFrame(controls, fg_color="transparent")
        delete_area.pack(side="right")

        def show_delete() -> None:
            for child in delete_area.winfo_children():
                child.destroy()
            ctk.CTkButton(
                delete_area, text="Delete", width=70, height=26, command=show_confirm,
            ).pack(side="left")

        def show_confirm() -> None:
            for child in delete_area.winfo_children():
                child.destroy()
            ctk.CTkButton(
                delete_area, text="Really delete?", width=110, height=26,
                fg_color=_ENDED_EARLY_COLOR, command=confirm_delete,
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                delete_area, text="Cancel", width=70, height=26, command=show_delete,
            ).pack(side="left")

        def confirm_delete() -> None:
            history.delete(record.id)
            render_day()

        show_delete()

    def go(delta: int) -> None:
        state["day"] += timedelta(days=delta)
        render_day()

    prev_button.configure(command=lambda: go(-1))
    next_button.configure(command=lambda: go(1))
    render_day()
