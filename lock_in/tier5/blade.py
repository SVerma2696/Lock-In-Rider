"""
tier5/blade.py
===============
Kamen Rider Blade's Tier 5 gimmick: a "Board" tab. It shows your tasks
in three columns side by side -- To Do, In Progress and Done -- like
sticky notes on a wall. The Tasks tab has a "board" idea it never got
around to; this is it. The fifth of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-17-tier5-blade-kanban-board-design.md.

group_by_status() is a plain function (no windows, no Tk) so it can be
tested by itself. build() draws the tab. Each note has a little arrow
button that pushes it ONE column to the right. It uses the very same
TaskStore calls the Tasks tab's own buttons use, so the Board makes no
new kind of data at all -- it is just a second way to look at the same
tasks. build() is checked by running the real app, like every other
Tier 5 tab.
"""

from __future__ import annotations

import customtkinter as ctk

from ..tasks import Task, TaskStatus


def group_by_status(tasks: list[Task]) -> dict[TaskStatus, list[Task]]:
    """Sort the tasks into three piles: to do, in progress and done.

    Inside each pile the tasks stay in the same order they came in. All
    three piles are ALWAYS there, even an empty one, so the board can
    always draw all three columns.
    """
    buckets: dict[TaskStatus, list[Task]] = {
        TaskStatus.TODO: [], TaskStatus.IN_PROGRESS: [], TaskStatus.DONE: [],
    }
    for task in tasks:
        buckets[task.status].append(task)
    return buckets


def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Fill `parent` with Blade's Board tab: three columns, one note per
    task, and (except in Done) an arrow button to move a note one column
    to the right.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    if not tasks.all():
        ctk.CTkLabel(
            frame, text="No tasks yet. Add one on the Tasks tab.",
            justify="left", wraplength=400,
        ).pack(anchor="w", pady=8)
        return

    columns_row = ctk.CTkFrame(frame, fg_color="transparent")
    columns_row.pack(fill="both", expand=True)

    columns = (
        (TaskStatus.TODO, "To Do"),
        (TaskStatus.IN_PROGRESS, "In Progress"),
        (TaskStatus.DONE, "Done"),
    )
    # Where an arrow sends a note. Done has nowhere to go, so a note in
    # Done gets no arrow at all.
    next_status = {
        TaskStatus.TODO: TaskStatus.IN_PROGRESS,
        TaskStatus.IN_PROGRESS: TaskStatus.DONE,
    }

    def render_board() -> None:
        for child in columns_row.winfo_children():
            child.destroy()
        buckets = group_by_status(tasks.all())
        for status, label in columns:
            column = ctk.CTkFrame(columns_row, fg_color="transparent")
            column.pack(side="left", fill="both", expand=True, padx=6)

            bucket_tasks = buckets[status]
            ctk.CTkLabel(
                column, text=f"{label} ({len(bucket_tasks)})",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=theme.primary_text_pair,
            ).pack(anchor="w", pady=(0, 8))

            for task in bucket_tasks:
                render_card(column, task, status)

    def render_card(column, task, status) -> None:
        card = ctk.CTkFrame(column, border_width=1)
        card.pack(fill="x", pady=4)

        ctk.CTkLabel(card, text=task.name, anchor="w", wraplength=140).pack(
            anchor="w", padx=8, pady=(8, 0),
        )
        # "2/5" = 2 small steps finished out of 5. A task with no small
        # steps shows nothing here, instead of an empty line.
        if task.subtasks:
            done_count = sum(1 for s in task.subtasks if s.done)
            ctk.CTkLabel(
                card, text=f"{done_count}/{len(task.subtasks)}", anchor="w",
                font=ctk.CTkFont(size=10), text_color=("gray40", "gray60"),
            ).pack(anchor="w", padx=8)

        target = next_status.get(status)
        if target is not None:
            ctk.CTkButton(
                card, text="→", width=40, height=24,
                command=lambda t=task, s=target: advance(t, s),
            ).pack(anchor="e", padx=8, pady=(4, 8))
        else:
            # Same gap at the bottom as a note with a button has.
            ctk.CTkFrame(card, fg_color="transparent", height=8).pack()

    def advance(task, new_status: TaskStatus) -> None:
        if new_status == TaskStatus.DONE:
            tasks.complete(task.id)
        else:
            tasks.set_status(task.id, new_status)
        render_board()

    render_board()
