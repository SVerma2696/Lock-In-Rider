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
    # OOO's Combo tab: three fixed checkboxes, always in this order --
    # Plan, Work, Review. Checking all three never changes `status`; it
    # just shows a "Combo formed!" mark (see lock_in/tier5/ooo.py).
    phases: List[bool] = field(default_factory=lambda: [False, False, False])


def task_from_dict(item: object) -> Optional[Task]:
    """Turn one saved task (a dict) back into a Task. Returns None if
    it's broken, so one bad entry never costs you the others. Used by
    TaskStore.load() and by Revice's Pull History -- which matters more
    here than for most files, because a task pulled from another
    computer can hold anything at all. Every field is checked for the
    right type, not just the right shape: a task with the wrong type
    in `id`, `name`, `created_at`, or `completed_at` is rejected outright,
    since a bad `id` (e.g. a list, which can't go in a dict key) could
    otherwise crash the merge that calls this, not just show up wrong."""
    if not isinstance(item, dict):
        return None
    try:
        task_id = item.get("id")
        name = item.get("name")
        created_at = item.get("created_at", "")
        completed_at = item.get("completed_at")
        if not (isinstance(task_id, str) and task_id):
            return None
        if not (isinstance(name, str) and name):
            return None
        if not isinstance(created_at, str):
            return None
        if completed_at is not None and not isinstance(completed_at, str):
            return None

        # Build subtasks defensively, skipping any malformed entries.
        subtasks = []
        for s in item.get("subtasks", []):
            try:
                sub_id = s.get("id", "")
                text = s.get("text", "")
                done = s.get("done", False)
            except (TypeError, AttributeError):
                # Skip malformed subtask entries.
                continue
            # Only add valid subtasks: non-empty string id and text,
            # and a real bool for done (not just anything truthy).
            if (isinstance(sub_id, str) and sub_id
                    and isinstance(text, str) and text
                    and isinstance(done, bool)):
                subtasks.append(Subtask(id=sub_id, text=text, done=done))

        # phases: always exactly 3 booleans (Plan, Work, Review).
        # A hand-edited tasks.json could hold anything here --
        # anything that isn't a list of exactly 3 entries falls
        # back to all-unchecked rather than raising or guessing
        # which one was meant.
        raw_phases = item.get("phases", [False, False, False])
        if isinstance(raw_phases, list) and len(raw_phases) == 3:
            phases = [bool(p) for p in raw_phases]
        else:
            phases = [False, False, False]

        return Task(
            id=task_id,
            name=name,
            subtasks=subtasks,
            status=TaskStatus(item.get("status", "todo")),
            created_at=created_at,
            completed_at=completed_at,
            phases=phases,
        )
    except (KeyError, ValueError, TypeError):
        return None


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
            task = task_from_dict(item)
            if task is not None:
                self._tasks[task.id] = task

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

    def add_existing(self, task: Task) -> bool:
        """Add a whole task that already has its own id -- Revice's Pull
        History uses this for tasks copied from another computer. Saves
        straight away. Returns False, with nothing changed, if a task
        with that id is already here."""
        if task.id in self._tasks:
            return False
        self._tasks[task.id] = task
        self.save()
        return True

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

    def toggle_phase(self, task_id: str, index: int) -> bool:
        """Flip one of a task's three fixed phases (0=Plan, 1=Work,
        2=Review). Returns False, with nothing changed, for a missing
        task or an index that isn't 0, 1, or 2 -- the same
        bounds-checked posture as toggle_subtask()."""
        task = self._tasks.get(task_id)
        if task is None or index not in (0, 1, 2):
            return False
        task.phases[index] = not task.phases[index]
        self.save()
        return True

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

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def open(self) -> List[Task]:
        """Todo + in_progress tasks -- what the Tasks tab shows above the fold."""
        return [t for t in self._tasks.values() if t.status != TaskStatus.DONE]

    def done(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == TaskStatus.DONE]
