"""
application/task_controller.py
==============================
Which task the next focus block is for.

The Focus page has a menu of your open tasks. Picking one means "the
focus blocks I do now count toward this task". This keeps track of that
pick, and turns the menu's words back into the right task -- even when
two tasks have the same name. It never draws anything; the Focus page
asks it what to show.
"""

from __future__ import annotations

from ..task_picker import NO_TASK_LABEL, build_task_picker_entries
from ..tasks import Task, TaskStatus, TaskStore


class TaskController:
    def __init__(self, tasks: TaskStore) -> None:
        self.tasks = tasks
        # The task picked on the Focus page. None means "no task".
        # Never saved -- it's meant to change often.
        self.current_task_id: str | None = None
        # Menu words -> task id, from the last time the menu was built.
        self._menu_ids: dict[str, str | None] = {}

    def menu(self) -> tuple[list[str], str]:
        """The menu's choices, and which one should be showing.

        If the picked task was finished or deleted, the pick falls back
        to "No task" instead of pointing at a task that's gone."""
        open_tasks = self.tasks.open()
        values, self._menu_ids = build_task_picker_entries(open_tasks)
        if self.current_task_id not in {task.id for task in open_tasks}:
            self.current_task_id = None
            return values, NO_TASK_LABEL
        label = next(
            (k for k, v in self._menu_ids.items() if v == self.current_task_id), NO_TASK_LABEL
        )
        return values, label

    def select(self, label: str) -> None:
        """The menu choice with these words was picked."""
        self.current_task_id = self._menu_ids.get(label)  # None for "No task"

    def current_task(self) -> Task | None:
        return self.tasks.get(self.current_task_id) if self.current_task_id else None

    def mark_started(self) -> bool:
        """Work began on the picked task: it's now In progress. Returns
        True if a task was changed (so the Tasks page needs redrawing).
        A disk problem is ignored here -- it must never stop the focus
        block from starting."""
        if self.current_task_id is None:
            return False
        try:
            self.tasks.set_status(self.current_task_id, TaskStatus.IN_PROGRESS)
        except OSError:
            pass
        return True
