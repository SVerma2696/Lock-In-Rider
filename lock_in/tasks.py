"""
tasks.py
========
This file is the app's to-do list — separate from the timer, separate
from what it's watching your windows for. A Task is something you name
yourself ("Finish the report", "Study for the midterm"), optionally
broken into smaller checklist items (subtasks), that moves through
three states: todo, in_progress, done.

Nothing here ever changes on its own except one thing: picking a task
and pressing Start flips it to in_progress (see ui.py). Moving a task to
done is always something YOU click — a focus block ending, being
skipped, or being reset never touches a task's status. A real piece of
work often takes more than one Pomodoro block, so "a timer finished"
and "the task is actually finished" are two different facts, and mixing
them up would be the app deciding something for you that only you
actually know.

Where the file lives
---------------------
Same folder as config.json — see config.py's app_data_dir(). Saved as
one JSON file (not one-line-per-entry like observations.jsonl), because
tasks get renamed, reordered, and deleted in place, not just appended.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class TaskStatus(str, Enum):
    """Which of the three states a task is in right now."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Subtask:
    """One checklist item inside a Task."""

    id: str
    text: str
    done: bool = False


@dataclass
class Task:
    """
    One thing you're working on.

    No `notes` field on purpose — nothing reads or writes one yet, and
    there's no UI planned to edit it in this pass (see the design spec).
    """

    id: str
    name: str
    subtasks: List[Subtask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.TODO
    created_at: str = ""
    completed_at: Optional[str] = None


class TaskStore:
    """
    Loads, edits, and saves the whole task list.

    Unlike ObservationStore (which buffers changes and waits for an
    explicit save() call, because it's written from a fast polling
    loop), every mutating method here saves immediately. Task edits are
    infrequent, deliberate, human actions — add one, check one off,
    delete one — so there's no meaningful performance cost to writing
    the whole (small) file each time, and it means the Tasks tab can
    never lose an edit to a crash between "you clicked something" and
    "it got saved."
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._tasks: Dict[str, Task] = {}
        self.load()

    # ------------------------------------------------------------------ #
    # Reading and writing the file
    # ------------------------------------------------------------------ #
    def load(self) -> None:
        """Read tasks.json. A missing or broken file just means 'start empty'."""
        self._tasks.clear()
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        # Valid JSON of the wrong SHAPE is just as broken as invalid JSON,
        # and it used to be worse: a root of `[]` or `5` made raw.get()
        # raise AttributeError straight out of LockInApp.__init__, so the
        # app wouldn't open at all. Same for a `null` or `"hello"` sitting
        # in the tasks list. "A missing or broken file just means 'start
        # empty'" has to mean this too.
        if not isinstance(raw, dict):
            return
        entries = raw.get("tasks", [])
        if not isinstance(entries, list):
            return
        for item in entries:
            if not isinstance(item, dict):
                continue
            try:
                # Build subtasks defensively, skipping any malformed entries.
                subtasks = []
                for s in item.get("subtasks", []):
                    try:
                        subtask = Subtask(
                            id=s.get("id", ""),
                            text=s.get("text", ""),
                            done=s.get("done", False),
                        )
                        # Only add valid subtasks (with non-empty id and text).
                        if subtask.id and subtask.text:
                            subtasks.append(subtask)
                    except (TypeError, AttributeError):
                        # Skip malformed subtask entries.
                        continue

                task = Task(
                    id=item["id"],
                    name=item["name"],
                    subtasks=subtasks,
                    status=TaskStatus(item.get("status", "todo")),
                    created_at=item.get("created_at", ""),
                    completed_at=item.get("completed_at"),
                )
                self._tasks[task.id] = task
            except (KeyError, ValueError, TypeError):
                # One broken entry shouldn't cost you every other task.
                continue

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"tasks": [asdict(t) for t in self._tasks.values()]}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Editing
    # ------------------------------------------------------------------ #
    def add(self, name: str) -> Task:
        task = Task(
            id=uuid.uuid4().hex[:8],
            name=name.strip(),
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._tasks[task.id] = task
        self.save()
        return task

    def add_subtask(self, task_id: str, text: str) -> Optional[Subtask]:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        subtask = Subtask(id=uuid.uuid4().hex[:8], text=text.strip())
        task.subtasks.append(subtask)
        self.save()
        return subtask

    def toggle_subtask(self, task_id: str, subtask_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        for subtask in task.subtasks:
            if subtask.id == subtask_id:
                subtask.done = not subtask.done
                self.save()
                return True
        return False

    def set_status(self, task_id: str, status: TaskStatus) -> bool:
        """Plain status change -- does NOT touch completed_at. Use
        complete() instead when a task is genuinely finished."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.status = status
        self.save()
        return True

    def complete(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.status = TaskStatus.DONE
        task.completed_at = datetime.now().isoformat(timespec="seconds")
        self.save()
        return True

    def delete(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        self.save()
        return True

    # ------------------------------------------------------------------ #
    # Looking things up
    # ------------------------------------------------------------------ #
    def all(self) -> List[Task]:
        return list(self._tasks.values())

    def open(self) -> List[Task]:
        """Todo + in_progress tasks -- what the Tasks tab shows above the fold."""
        return [t for t in self._tasks.values() if t.status != TaskStatus.DONE]

    def done(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == TaskStatus.DONE]
