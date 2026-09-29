"""
ui/pages/tasks.py
=================
The Tasks page: add a task, split it into small steps, and check things
off. Each task is its own little card.

The page only draws. Saving is done by TaskStore (lock_in/tasks.py),
exactly like before -- the tasks.json file looks the same as it always
did. Names can repeat; every task has its own hidden id, so two tasks
called "Reading" never get mixed up.

Filters (All / Active / Done) only change what's shown right now. They
aren't saved.
"""

from __future__ import annotations

import customtkinter as ctk

from ...tasks import Task, TaskStatus
from .. import theme as t
from ..components import ModernCard, PrimaryButton, StatusBadge
from ..components.box import Box
from .base import PAGE_PAD_X, Page, tasks_signature

FILTERS = ("All", "Active", "Done")

_STATUS_BADGE = {
    TaskStatus.TODO: ("To do", "neutral"),
    TaskStatus.IN_PROGRESS: ("In progress", "accent"),
    TaskStatus.DONE: ("Done", "success"),
}


def filter_tasks(open_tasks, done_tasks, which: str):
    """(tasks to show at the top, done tasks to show under them)."""
    if which == "Active":
        return list(open_tasks), []
    if which == "Done":
        return [], list(done_tasks)
    return list(open_tasks), list(done_tasks)


def step_progress(task: Task) -> str:
    """'2/3 steps', or '' when the task has no steps."""
    if not task.subtasks:
        return ""
    done = sum(1 for s in task.subtasks if s.done)
    word = "step" if len(task.subtasks) == 1 else "steps"
    return f"{done}/{len(task.subtasks)} {word}"


class TasksPage(Page):
    route_id = "tasks"

    def build(self) -> None:
        p = self.palette
        self.page_header(
            "Tasks",
            "Write down what you're working on. Break big things "
            "into small steps. Pick one on the Focus page to track "
            "your time.",
        )

        add_card = ModernCard(self.body, p, layout=self.layout, padding=t.SPACE_3)
        self.pack(add_card, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_3))
        self.new_task_entry = ctk.CTkEntry(
            add_card.body,
            placeholder_text="Add a task…",
            height=36,
            border_width=1,
            fg_color=p.control_bg,
            border_color=p.card_border,
            text_color=p.text_primary,
            corner_radius=t.CONTROL_RADIUS,
            font=t.font(),
        )
        self.pack(self.new_task_entry, side="left", fill="x", expand=True, padx=(0, t.SPACE_2))
        self.new_task_entry.bind("<Return>", lambda e: self._on_add_task())
        self.pack(
            PrimaryButton(
                add_card.body,
                p,
                text="+  Add task",
                height=36,
                width=120,
                font_size=13,
                command=self._on_add_task,
            ),
            side="left",
        )

        bar = self.section(pady=(0, t.SPACE_3))
        self.filter_buttons = self.segmented(bar, FILTERS, self._on_filter)
        self.filter_buttons.set(self.app._task_filter)
        self.pack(self.filter_buttons, side="left")
        self.count_label = self.label(bar, "", size=t.FONT_SMALL + 1, color=p.text_muted)
        self.pack(self.count_label, side="right")

        self.tasks_list_frame = Box(self.body)
        self.pack(
            self.tasks_list_frame, fill="both", expand=True, padx=PAGE_PAD_X, pady=(0, t.SPACE_6)
        )
        self.render()

    def on_show(self) -> None:
        # Tasks can change on other pages (Blade's board, OOO's combo,
        # a buddy's pulled history) -- redraw only if something did.
        if self._signature() != getattr(self, "_drawn", None):
            self.render()

    def _signature(self) -> tuple:
        return (
            tasks_signature(self.app.tasks.all()),
            self.app._task_filter,
            tuple(sorted(self.app._expanded_tasks.items())),
        )

    # ------------------------------------------------------------------ #
    def _on_filter(self, value: str) -> None:
        self.app._task_filter = value
        self.render()

    def _on_add_task(self) -> None:
        name = self.new_task_entry.get().strip()
        if not name:
            return
        self.app.tasks.add(name)
        self.new_task_entry.delete(0, "end")
        self.render()
        self.app._refresh_current_task_picker()

    def _on_complete_task(self, task_id: str) -> None:
        self.app.tasks.complete(task_id)
        self.render()
        self.app._refresh_current_task_picker()

    def _on_toggle_subtask(self, task_id: str, subtask_id: str) -> None:
        self.app.tasks.toggle_subtask(task_id, subtask_id)
        self.render()

    def _on_add_subtask(self, task_id: str, entry) -> None:
        text = entry.get().strip()
        if not text:
            return
        self.app.tasks.add_subtask(task_id, text)
        self.app._expanded_tasks[task_id] = True
        self.render()

    def _on_toggle_expand(self, task: Task) -> None:
        self.app._expanded_tasks[task.id] = not self._is_expanded(task)
        self.render()

    def _is_expanded(self, task: Task) -> bool:
        # Open tasks start opened up; finished ones start folded away.
        return self.app._expanded_tasks.get(task.id, task.status != TaskStatus.DONE)

    # ------------------------------------------------------------------ #
    def render(self) -> None:
        """Redraw the whole list from scratch -- there are never so many
        tasks that this is slow."""
        try:
            if not self.tasks_list_frame.winfo_exists():
                return
        except Exception:
            return
        for child in self.tasks_list_frame.winfo_children():
            child.destroy()
        self._drawn = self._signature()

        store = self.app.tasks
        open_tasks, done_tasks = store.open(), store.done()
        self.count_label.configure(text=f"{len(open_tasks)} open · {len(done_tasks)} done")
        shown_open, shown_done = filter_tasks(open_tasks, done_tasks, self.app._task_filter)

        if not shown_open and not shown_done:
            empty = ModernCard(
                self.tasks_list_frame, self.palette, layout=self.layout, padding=t.SPACE_6
            )
            self.pack(empty, fill="x")
            words = (
                "No tasks yet. Type one above and press Add task."
                if not open_tasks and not done_tasks
                else "Nothing here right now."
            )
            self.pack(
                self.label(empty.body, words, color=self.palette.text_secondary, anchor="center"),
                fill="x",
            )
            return

        for task in shown_open:
            self._render_one(task)
        if shown_done:
            if shown_open:
                self.pack(
                    self.label(
                        self.tasks_list_frame,
                        f"Done ({len(shown_done)})",
                        size=t.FONT_SMALL + 1,
                        color=self.palette.text_muted,
                        bold=True,
                    ),
                    anchor="w",
                    pady=(t.SPACE_4, t.SPACE_2),
                )
            for task in shown_done:
                self._render_one(task)

    def _render_one(self, task: Task) -> None:
        p = self.palette
        done = task.status == TaskStatus.DONE
        card = ModernCard(self.tasks_list_frame, p, layout=self.layout, padding=t.SPACE_3)
        self.pack(card, fill="x", pady=(0, t.SPACE_2))

        top = Box(card.body)
        self.pack(top, fill="x")
        # Ticking the box finishes the task. A finished task stays ticked.
        box = ctk.CTkCheckBox(
            top,
            text="",
            width=24,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=6,
            fg_color=t.SUCCESS,
            hover_color=p.control_hover,
            border_color=p.text_muted,
            command=lambda: self._on_complete_task(task.id),
            font=t.font(),
        )
        if done:
            box.select()
            box.configure(state="disabled")
        self.pack(box, side="left", padx=(0, t.SPACE_2))

        expanded = self._is_expanded(task)
        toggle = ctk.CTkButton(
            top,
            text="",
            width=28,
            height=28,
            corner_radius=6,
            image=self.icon("chevron_down" if expanded else "chevron_right"),
            fg_color="transparent",
            hover_color=p.control_hover,
            command=lambda: self._on_toggle_expand(task),
            font=t.font(),
        )
        self.pack(toggle, side="right")
        badge_text, badge_kind = _STATUS_BADGE[task.status]
        self.pack(
            StatusBadge(top, p, text=badge_text, kind=badge_kind, dot=False),
            side="right",
            padx=(t.SPACE_2, t.SPACE_1),
        )
        progress = step_progress(task)
        if progress:
            self.pack(
                self.label(top, progress, size=t.FONT_SMALL + 1, color=p.text_muted),
                side="right",
                padx=(t.SPACE_2, 0),
            )
        name = self.label(
            top,
            task.name,
            size=t.FONT_BODY + 1,
            color=p.text_muted if done else p.text_primary,
            wrap=420,
        )
        self.pack(name, side="left", fill="x", expand=True)

        if not expanded:
            return
        steps = Box(card.body)
        self.pack(steps, fill="x", padx=(34, 0), pady=(t.SPACE_2, 0))
        for subtask in task.subtasks:
            var = ctk.BooleanVar(value=subtask.done)
            check = ctk.CTkCheckBox(
                steps,
                text=subtask.text,
                variable=var,
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=5,
                fg_color=p.accent,
                hover_color=p.control_hover,
                border_color=p.text_muted,
                text_color=p.text_muted if subtask.done else p.text_primary,
                font=t.font(size=t.FONT_BODY),
                command=lambda s=subtask: self._on_toggle_subtask(task.id, s.id),
            )
            self.pack(check, anchor="w", pady=2)
        entry = ctk.CTkEntry(
            steps,
            placeholder_text="Add a step… (press Enter)",
            height=30,
            border_width=1,
            fg_color=p.control_bg,
            border_color=p.card_border,
            text_color=p.text_primary,
            corner_radius=t.CONTROL_RADIUS,
            font=t.font(),
        )
        self.pack(entry, fill="x", pady=(t.SPACE_1, 0))
        entry.bind("<Return>", lambda e: self._on_add_subtask(task.id, entry))
