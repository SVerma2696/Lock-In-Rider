# Tier 5 Core: Tasks & Session History Implementation Plan

**Goal:** Add the task/session-history data model this codebase doesn't have at all yet, plus one plain "Tasks" tab to make it real and testable end to end — the shared foundation the later Tier 5 Riders (V3, Decade, W, OOO, Den-O, Zi-O, Gotchard, Geats, Blade, MY-TH) will each build on, one at a time, in their own future plans.

**Architecture:** Two new pure-logic modules, same tier as `config.py`/`session.py`/`observations.py` — `lock_in/tasks.py` (mutable, whole-file-JSON `TaskStore`) and `lock_in/history.py` (append-only JSONL `HistoryStore`, reusing the `LOG_PATH` constant already sitting unused in `config.py`). `ui.py` gets a new "Tasks" tab and a current-task picker on the Home header, wired into the existing `_on_phase_started`/`_on_phase_ended`/`_on_skip`/`_on_reset` call sites. `session.py` itself is not modified — it stays exactly as unaware that tasks exist as it already is of windows, blocking, or Claude.

**Tech Stack:** Python 3, customtkinter — no new pip dependencies, no new files under `lock_in/assets/`.

## Global Constraints

- `TaskStatus` values, verbatim: `"todo"`, `"in_progress"`, `"done"` (mirrors `Phase(str, Enum)`'s existing shape in `session.py`).
- New path: `TASKS_PATH = app_data_dir() / "tasks.json"`, added to `lock_in/config.py` alongside `CONFIG_PATH`/`MODEL_PATH`/`LOG_PATH`/`OBSERVATIONS_PATH`.
- Reused path: `LOG_PATH = app_data_dir() / "sessions.jsonl"` — this constant already exists in `lock_in/config.py` today but is used nowhere else in the codebase; `HistoryStore` is its first real consumer.
- **Session completion never changes task status.** The only automatic status change anywhere in this plan is todo → in_progress when a task is picked and Start is pressed. Moving a task to `done` is always a deliberate click on its own "done" checkbox — a focus block ending (naturally, skipped, or reset) never touches `Task.status`. This is a load-bearing rule from the approved spec, not an implementation detail — Task 5's tests include a regression test for it.
- A `SessionRecord.task_id` is a snapshot taken at `record()` time, never re-validated against `TaskStore` afterward. Deleting a task later leaves its past history entries with a dangling id rather than deleting, rewriting, or reassigning them.
- Each task ends with its own local `git commit`, exactly as that task's steps specify — these are normal checkpoints within this plan's own (isolated, unpublished) working branch, not a release action. What never happens anywhere in this plan is a `git push` or `git tag` to the shared remote — Task 7's final step only prints those commands for the user to run themselves.
- No version bump and no `README.md` edit in this plan — the approved spec (`docs/superpowers/specs/2026-09-04-tier5-tasks-history-design.md`) explicitly defers both until this slice is complete and the user decides on scope/versioning, matching this project's established convention of only bumping `__version__` once something actually ships.
- No Help tab section in this plan — not called for in the approved spec's file-by-file change list; can be added in a later pass if wanted.

---

### Task 1: `lock_in/tasks.py` — the task data model

**Files:**
- Create: `lock_in/tasks.py`
- Modify: `lock_in/config.py` (add `TASKS_PATH`)
- Test: `tests/test_tasks.py`

**Interfaces:**
- Produces: `TaskStatus` (str Enum: `TODO`, `IN_PROGRESS`, `DONE`), `Subtask` (dataclass: `id: str`, `text: str`, `done: bool`), `Task` (dataclass: `id: str`, `name: str`, `subtasks: List[Subtask]`, `status: TaskStatus`, `created_at: str`, `completed_at: Optional[str]`), `TaskStore` (methods: `add(name) -> Task`, `add_subtask(task_id, text) -> Optional[Subtask]`, `toggle_subtask(task_id, subtask_id) -> bool`, `set_status(task_id, status) -> bool`, `complete(task_id) -> bool`, `delete(task_id) -> bool`, `all() -> List[Task]`, `open() -> List[Task]`, `done() -> List[Task]`). Consumed by Tasks 3, 4, 5.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tasks.py`:

```python
"""Tests for the task list backing the Tasks tab and Tier 5's Riders."""

import pytest

from lock_in.tasks import Subtask, Task, TaskStatus, TaskStore


@pytest.fixture
def store(tmp_path) -> TaskStore:
    return TaskStore(tmp_path / "tasks.json")


def test_new_task_store_starts_empty(store):
    assert store.all() == []


def test_add_creates_a_todo_task(store):
    task = store.add("Write the Tier 5 spec")
    assert task.name == "Write the Tier 5 spec"
    assert task.status == TaskStatus.TODO
    assert task.id
    assert task.subtasks == []
    assert len(store.all()) == 1


def test_add_persists_across_a_reload(tmp_path):
    path = tmp_path / "tasks.json"
    store1 = TaskStore(path)
    store1.add("Ship it")
    store2 = TaskStore(path)
    assert len(store2.all()) == 1
    assert store2.all()[0].name == "Ship it"


def test_add_subtask_appends_to_the_task(store):
    task = store.add("Big task")
    subtask = store.add_subtask(task.id, "First step")
    assert subtask is not None
    assert subtask.done is False
    reloaded = store.all()[0]
    assert len(reloaded.subtasks) == 1
    assert reloaded.subtasks[0].text == "First step"


def test_add_subtask_on_missing_task_returns_none(store):
    assert store.add_subtask("nope", "text") is None


def test_toggle_subtask_flips_done(store):
    task = store.add("Task")
    subtask = store.add_subtask(task.id, "Step")
    assert store.toggle_subtask(task.id, subtask.id) is True
    assert store.all()[0].subtasks[0].done is True
    store.toggle_subtask(task.id, subtask.id)
    assert store.all()[0].subtasks[0].done is False


def test_toggle_subtask_on_missing_ids_returns_false(store):
    assert store.toggle_subtask("nope", "nope") is False


def test_set_status_changes_status(store):
    task = store.add("Task")
    assert store.set_status(task.id, TaskStatus.IN_PROGRESS) is True
    assert store.all()[0].status == TaskStatus.IN_PROGRESS


def test_set_status_on_missing_task_returns_false(store):
    assert store.set_status("nope", TaskStatus.DONE) is False


def test_set_status_never_touches_completed_at(store):
    """Regression test: only complete() should ever set completed_at.
    A plain status change (e.g. todo -> in_progress on Start) must not."""
    task = store.add("Task")
    store.set_status(task.id, TaskStatus.IN_PROGRESS)
    assert store.all()[0].completed_at is None


def test_complete_sets_status_and_completed_at(store):
    task = store.add("Task")
    assert store.complete(task.id) is True
    reloaded = store.all()[0]
    assert reloaded.status == TaskStatus.DONE
    assert reloaded.completed_at is not None


def test_complete_on_missing_task_returns_false(store):
    assert store.complete("nope") is False


def test_delete_removes_the_task(store):
    task = store.add("Task")
    assert store.delete(task.id) is True
    assert store.all() == []


def test_delete_missing_task_returns_false(store):
    assert store.delete("nope") is False


def test_open_returns_todo_and_in_progress_only(store):
    t1 = store.add("Todo task")
    t2 = store.add("In progress task")
    store.set_status(t2.id, TaskStatus.IN_PROGRESS)
    t3 = store.add("Done task")
    store.complete(t3.id)
    open_ids = {t.id for t in store.open()}
    assert open_ids == {t1.id, t2.id}


def test_done_returns_only_completed_tasks(store):
    t1 = store.add("Todo")
    t2 = store.add("Done")
    store.complete(t2.id)
    assert [t.id for t in store.done()] == [t2.id]


def test_corrupted_file_starts_fresh(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text("{ not valid json", encoding="utf-8")
    store = TaskStore(path)
    assert store.all() == []


def test_missing_file_starts_empty(tmp_path):
    store = TaskStore(tmp_path / "does_not_exist.json")
    assert store.all() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tasks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.tasks'`

- [ ] **Step 3: Add `TASKS_PATH` to config.py**

In `lock_in/config.py`, directly below the existing `OBSERVATIONS_PATH = app_data_dir() / "observations.jsonl"` line:

```python
TASKS_PATH = app_data_dir() / "tasks.json"
```

- [ ] **Step 4: Implement `lock_in/tasks.py`**

```python
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
        for item in raw.get("tasks", []):
            try:
                subtasks = [Subtask(**s) for s in item.get("subtasks", [])]
                task = Task(
                    id=item["id"],
                    name=item["name"],
                    subtasks=subtasks,
                    status=TaskStatus(item.get("status", "todo")),
                    created_at=item.get("created_at", ""),
                    completed_at=item.get("completed_at"),
                )
                self._tasks[task.id] = task
            except (KeyError, ValueError):
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_tasks.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add lock_in/tasks.py lock_in/config.py tests/test_tasks.py
git commit -m "Add Tier 5's task data model (tasks.py)"
```

---

### Task 2: `lock_in/history.py` — the session-history log

**Files:**
- Create: `lock_in/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: `Config.LOG_PATH` (already exists in `lock_in/config.py`, unused until now).
- Produces: `SessionRecord` (dataclass: `start: str`, `end: str`, `duration_seconds: int`, `task_id: Optional[str]`, `completed: bool`), `HistoryStore` (methods: `record(session_record) -> None`, `all() -> List[SessionRecord]`, `for_date(date) -> List[SessionRecord]`, `for_task(task_id) -> List[SessionRecord]`, `total_seconds_by_day() -> Dict[str, int]`). Consumed by Task 6.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_history.py`:

```python
"""Tests for the append-only session-history log."""

import dataclasses
import json
from datetime import date, datetime, timedelta

import pytest

from lock_in.history import HistoryStore, SessionRecord


@pytest.fixture
def store(tmp_path) -> HistoryStore:
    return HistoryStore(tmp_path / "sessions.jsonl")


def _record(start: datetime, duration: int, task_id=None, completed=True) -> SessionRecord:
    end = start + timedelta(seconds=duration)
    return SessionRecord(
        start=start.isoformat(timespec="seconds"),
        end=end.isoformat(timespec="seconds"),
        duration_seconds=duration,
        task_id=task_id,
        completed=completed,
    )


def test_new_history_store_starts_empty(store):
    assert store.all() == []


def test_record_appends_and_is_readable_back(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store.record(record)
    assert store.all() == [record]


def test_record_persists_across_a_reload(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store1 = HistoryStore(path)
    store1.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    store2 = HistoryStore(path)
    assert len(store2.all()) == 1


def test_for_date_filters_to_that_calendar_day(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    store.record(_record(datetime(2026, 9, 5, 9, 0, 0), 1500))
    matches = store.for_date(date(2026, 9, 4))
    assert len(matches) == 1


def test_for_task_filters_to_that_task_id(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123"))
    store.record(_record(datetime(2026, 9, 4, 10, 0, 0), 1500, task_id="other"))
    matches = store.for_task("abc123")
    assert len(matches) == 1
    assert matches[0].task_id == "abc123"


def test_total_seconds_by_day_sums_same_day_records(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    store.record(_record(datetime(2026, 9, 4, 14, 0, 0), 900))
    store.record(_record(datetime(2026, 9, 5, 9, 0, 0), 300))
    totals = store.total_seconds_by_day()
    assert totals["2026-09-04"] == 2400
    assert totals["2026-09-05"] == 300


def test_a_skipped_block_is_recorded_as_not_completed(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 400, completed=False)
    store.record(record)
    assert store.all()[0].completed is False


def test_corrupt_line_is_skipped_not_fatal(tmp_path):
    path = tmp_path / "sessions.jsonl"
    good = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    path.write_text(
        json.dumps(dataclasses.asdict(good)) + "\n" + "{ not valid json\n",
        encoding="utf-8",
    )
    store = HistoryStore(path)
    assert len(store.all()) == 1


def test_missing_file_starts_empty(tmp_path):
    store = HistoryStore(tmp_path / "does_not_exist.jsonl")
    assert store.all() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_history.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.history'`

- [ ] **Step 3: Implement `lock_in/history.py`**

```python
"""
history.py
==========
This file is the honest, append-only record of every focus block you've
actually run -- one line per block, written the moment it ends, never
edited afterward (editing past history is a later Rider's job, not
this file's).

Unlike tasks.py, nothing here is ever renamed or deleted in place, so
this is saved the same shape observations.jsonl already is: one JSON
object per line, safe to append, safe if the file gets cut off mid-save
(you'd lose at most one line, not everything).

A record's task_id is a snapshot of whichever task was current when
that block ended -- it is never looked up or re-validated against
tasks.py again after that. If you later delete that task, its past
history entries keep the old id rather than being changed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SessionRecord:
    """One completed (or cut-short) focus block."""

    start: str                     # ISO timestamp, when the block began
    end: str                       # ISO timestamp, when it ended/was cut short
    duration_seconds: int
    task_id: Optional[str]         # None if no task was picked -- still logged
    completed: bool                # False if skipped or reset before time ran out


class HistoryStore:
    """Appends, loads, and queries the session-history log."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: List[SessionRecord] = []
        self.load()

    def load(self) -> None:
        """Read every line, skipping any that's broken rather than failing."""
        self._records.clear()
        if not self.path.exists():
            return
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    self._records.append(SessionRecord(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    continue
        except OSError:
            pass

    def record(self, session_record: SessionRecord) -> None:
        """Append one completed block. Written and flushed immediately --
        there's no in-memory buffering to lose on a crash."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(session_record), ensure_ascii=False) + "\n")
        self._records.append(session_record)

    def all(self) -> List[SessionRecord]:
        return list(self._records)

    def for_date(self, day: date) -> List[SessionRecord]:
        return [r for r in self._records if datetime.fromisoformat(r.start).date() == day]

    def for_task(self, task_id: str) -> List[SessionRecord]:
        return [r for r in self._records if r.task_id == task_id]

    def total_seconds_by_day(self) -> Dict[str, int]:
        """{'2026-09-04': 2400, ...} -- the one aggregate every history-
        reading Rider downstream (V3, Decade, Den-O) will start from."""
        totals: Dict[str, int] = {}
        for r in self._records:
            day = datetime.fromisoformat(r.start).date().isoformat()
            totals[day] = totals.get(day, 0) + r.duration_seconds
        return totals
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_history.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add lock_in/history.py tests/test_history.py
git commit -m "Add Tier 5's append-only session-history log (history.py)"
```

---

### Task 3: `ui.py` — construct the two stores

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `TaskStore` (Task 1), `HistoryStore` (Task 2), `TASKS_PATH`/`LOG_PATH` (`lock_in/config.py`).
- Produces: `LockInApp.tasks: TaskStore`, `LockInApp.history: HistoryStore` — consumed by Tasks 4, 5, 6.

No dedicated automated test — two attribute assignments in `__init__`, matching how `self.observations`/`self.model` are constructed today; verified indirectly by every later task's own tests plus the final manual pass.

- [ ] **Step 1: Add the imports**

In `lock_in/ui.py`, near the existing `from .observations import ObservationStore` import:

```python
from .tasks import TaskStatus, TaskStore
from .history import HistoryStore, SessionRecord
```

In `lock_in/ui.py`, change the existing import line:

```python
from .config import Config, MODEL_PATH, OBSERVATIONS_PATH, app_data_dir
```

to:

```python
from .config import Config, MODEL_PATH, OBSERVATIONS_PATH, TASKS_PATH, LOG_PATH, app_data_dir
```

- [ ] **Step 2: Construct the stores**

In `lock_in/ui.py`, `__init__`, directly below the existing `self.observations = ObservationStore(OBSERVATIONS_PATH)` line:

```python
        self.tasks = TaskStore(TASKS_PATH)
        self.history = HistoryStore(LOG_PATH)
        # The task selected in the Home header's "current task" picker --
        # None means an untagged block, exactly like today's behavior
        # with no task system at all. Never saved to config.json; it's
        # meant to change often and doesn't need to survive a restart.
        self.current_task_id: Optional[str] = None
```

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `pytest -v`
Expected: all PASS (this task adds no new tests of its own; it must not break any existing one)

- [ ] **Step 4: Commit**

```bash
git add lock_in/ui.py
git commit -m "Construct TaskStore and HistoryStore in LockInApp.__init__"
```

---

### Task 4: `ui.py` — the "Tasks" tab

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `self.tasks` (Task 3), `TaskStatus` (Task 1).
- Produces: `LockInApp._build_tasks_tab(parent)`, `LockInApp._render_tasks()` — the render method is also called by Task 5 (whenever the current-task picker needs the task list refreshed after an add).

No dedicated automated test — widget-building code, matching the existing precedent that `_build_blocking_tab`/`_build_activity_tab`/`_render_activity` aren't unit-tested either; verified manually in the final task's screenshot pass.

- [ ] **Step 1: Add "Tasks" to the tab list**

In `lock_in/ui.py`, `_build_tabs()`, change:

```python
        for name in ("Blocking", "Activity", "Settings", "Help"):
            self.tabs.add(name)

        self._build_blocking_tab(self.tabs.tab("Blocking"))
        self._build_activity_tab(self.tabs.tab("Activity"))
        self._build_settings_tab(self.tabs.tab("Settings"))
        self._build_help_tab(self.tabs.tab("Help"))
```

to:

```python
        for name in ("Tasks", "Blocking", "Activity", "Settings", "Help"):
            self.tabs.add(name)

        self._build_tasks_tab(self.tabs.tab("Tasks"))
        self._build_blocking_tab(self.tabs.tab("Blocking"))
        self._build_activity_tab(self.tabs.tab("Activity"))
        self._build_settings_tab(self.tabs.tab("Settings"))
        self._build_help_tab(self.tabs.tab("Help"))
```

(Tasks goes first — it's the tab you'd want open before starting a block, the same reasoning Blocking already gets top billing over Settings.)

- [ ] **Step 2: Add `_build_tasks_tab` and `_render_tasks`**

Add these as new methods, directly after `_build_blocking_tab` (mirroring its `CTkScrollableFrame` shape) and before `_render_activity` (mirroring its clear-and-rebuild shape):

```python
    def _build_tasks_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._mpack(frame, fill="both", expand=True)

        add_row = ctk.CTkFrame(frame, fg_color="transparent")
        self._mpack(add_row, fill="x", pady=(0, 12))
        self.new_task_entry = ctk.CTkEntry(add_row, placeholder_text="Add a task...")
        self._mpack(self.new_task_entry, side="left", fill="x", expand=True, padx=(0, 8))
        self.new_task_entry.bind("<Return>", lambda e: self._on_add_task())
        self._mpack(ctk.CTkButton(add_row, text="Add", width=60, command=self._on_add_task), side="left")

        self.tasks_list_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._mpack(self.tasks_list_frame, fill="both", expand=True)

        self._render_tasks()

    def _on_add_task(self) -> None:
        name = self.new_task_entry.get().strip()
        if not name:
            return
        self.tasks.add(name)
        self.new_task_entry.delete(0, "end")
        self._render_tasks()
        self._refresh_current_task_picker()

    def _render_tasks(self) -> None:
        """Redraws the whole task list from scratch -- same pattern
        _render_activity() already uses for the Activity tab."""
        for child in self.tasks_list_frame.winfo_children():
            child.destroy()

        open_tasks = self.tasks.open()
        done_tasks = self.tasks.done()

        if not open_tasks and not done_tasks:
            self._mpack(ctk.CTkLabel(self.tasks_list_frame, text="No tasks yet.",
                         text_color=COLOR_IDLE), anchor="w", pady=20)
            return

        for task in open_tasks:
            self._render_one_task(task)

        if done_tasks:
            self._mpack(ctk.CTkLabel(
                self.tasks_list_frame, text=f"Done ({len(done_tasks)})",
                text_color=COLOR_IDLE, font=ctk.CTkFont(size=11, weight="bold"),
            ), anchor="w", pady=(14, 4))
            for task in done_tasks:
                self._render_one_task(task)

    def _render_one_task(self, task: Task) -> None:
        row = ctk.CTkFrame(self.tasks_list_frame, fg_color="transparent")
        self._mpack(row, fill="x", pady=4)

        header_row = ctk.CTkFrame(row, fg_color="transparent")
        self._mpack(header_row, fill="x")

        status_text = {"todo": "○", "in_progress": "◐", "done": "●"}[task.status.value]
        self._mpack(ctk.CTkLabel(header_row, text=status_text, width=20), side="left")
        self._mpack(ctk.CTkLabel(header_row, text=task.name, anchor="w"),
                     side="left", fill="x", expand=True)

        if task.status != TaskStatus.DONE:
            self._mpack(ctk.CTkButton(
                header_row, text="Done", width=50, height=24,
                command=lambda t=task: self._on_complete_task(t.id),
            ), side="right")

        for subtask in task.subtasks:
            sub_row = ctk.CTkFrame(row, fg_color="transparent")
            self._mpack(sub_row, fill="x", padx=(28, 0))
            var = ctk.BooleanVar(value=subtask.done)
            self._mpack(ctk.CTkCheckBox(
                sub_row, text=subtask.text, variable=var,
                command=lambda t=task, s=subtask: self._on_toggle_subtask(t.id, s.id),
            ), side="left", anchor="w", pady=2)

        add_sub_row = ctk.CTkFrame(row, fg_color="transparent")
        self._mpack(add_sub_row, fill="x", padx=(28, 0), pady=(2, 0))
        entry = ctk.CTkEntry(add_sub_row, placeholder_text="Add a step...", height=26)
        self._mpack(entry, side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e, t=task, ent=entry: self._on_add_subtask(t.id, ent))

    def _on_complete_task(self, task_id: str) -> None:
        self.tasks.complete(task_id)
        self._render_tasks()
        self._refresh_current_task_picker()

    def _on_toggle_subtask(self, task_id: str, subtask_id: str) -> None:
        self.tasks.toggle_subtask(task_id, subtask_id)
        self._render_tasks()

    def _on_add_subtask(self, task_id: str, entry) -> None:
        text = entry.get().strip()
        if not text:
            return
        self.tasks.add_subtask(task_id, text)
        self._render_tasks()
```

`_refresh_current_task_picker()` is defined in Task 5 — this task's `_on_add_task`/`_on_complete_task` calls to it will be dead references until Task 5 lands; that's expected and fine within this one plan (both tasks are implemented back-to-back before any release).

Add the `Task` import needed for the `_render_one_task` type hint, alongside the `TaskStatus, TaskStore` import already added in Task 3:

```python
from .tasks import Task, TaskStatus, TaskStore
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: all PASS (no new automated tests; must not break existing ones)

- [ ] **Step 4: Commit**

```bash
git add lock_in/ui.py
git commit -m "Add the Tasks tab: add/complete tasks, add/toggle subtasks"
```

---

### Task 5: `ui.py` — current-task picker + Start wiring

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `self.tasks` (Task 3), `self._render_tasks()` (Task 4), `TaskStatus` (Task 1).
- Produces: `LockInApp._refresh_current_task_picker()` (called by Task 4's `_on_add_task`/`_on_complete_task`), `LockInApp.current_task_id` updated on selection. Consumed by Task 6 (history logging reads `self.current_task_id`).

No dedicated automated test for the widget itself (same precedent as Task 4). The status-transition rule it triggers IS tested — see Step 3.

- [ ] **Step 1: Add the picker to the header**

In `lock_in/ui.py`, `_build_header()`, directly after the existing `self._mpack(self.driver_label, pady=(2, 0))` line (still inside `self.normal_header_content`, so it appears just above the progress bar and the Start/Skip/Reset row):

```python
        task_row = ctk.CTkFrame(self.normal_header_content, fg_color="transparent")
        self._mpack(task_row, pady=(6, 0))
        self.current_task_menu = ctk.CTkOptionMenu(
            task_row, values=["No task"], width=220,
            command=self._on_current_task_selected,
        )
        self._mpack(self.current_task_menu, side="left")
```

- [ ] **Step 2: Add the picker-refresh and selection-handler methods**

Add these near `_build_header` (or directly after it):

```python
    def _refresh_current_task_picker(self) -> None:
        """Rebuilds the dropdown's options from the current open-task
        list. Called after any add/complete in the Tasks tab (Task 4),
        so a newly-added task shows up here without restarting the app."""
        open_tasks = self.tasks.open()
        self._task_menu_ids = {t.name: t.id for t in open_tasks}
        values = ["No task"] + [t.name for t in open_tasks]
        self.current_task_menu.configure(values=values)

        if self.current_task_id not in {t.id for t in open_tasks}:
            # The selected task was completed or deleted out from under
            # the picker -- fall back to "No task" rather than pointing
            # at a task that's no longer open.
            self.current_task_id = None
            self.current_task_menu.set("No task")

    def _on_current_task_selected(self, name: str) -> None:
        self.current_task_id = self._task_menu_ids.get(name)  # None for "No task"
```

- [ ] **Step 3: Write the failing test for the Start-time status flip**

This one piece of logic (not the widget itself) is worth a real unit test, since it's the one automatic status change this whole plan makes and getting it wrong would be exactly the kind of silent surprise the spec called out. Add to `tests/test_tasks.py` (it only needs `TaskStore` directly, no `LockInApp`/Tk instance):

```python
def test_starting_a_focus_block_on_a_task_flips_it_to_in_progress(store):
    """Mirrors what ui.py's _on_toggle does: set_status(..., IN_PROGRESS)
    is called when a task is picked and Start is pressed. This test
    pins down the store-level contract that wiring depends on."""
    task = store.add("Write the report")
    store.set_status(task.id, TaskStatus.IN_PROGRESS)
    assert store.all()[0].status == TaskStatus.IN_PROGRESS


def test_a_completed_block_does_not_move_an_in_progress_task_to_done(store):
    """The other half of the same rule: nothing about a block finishing
    should ever call complete() on its own. This test simply asserts
    that calling set_status(IN_PROGRESS) alone -- with no complete()
    call -- leaves the task shy of done, documenting that ui.py's
    phase-ended code path (Task 6) must never call complete()."""
    task = store.add("Write the report")
    store.set_status(task.id, TaskStatus.IN_PROGRESS)
    assert store.all()[0].status != TaskStatus.DONE
```

- [ ] **Step 4: Run it to verify it fails, then confirm it already passes**

Run: `pytest tests/test_tasks.py -k "in_progress or does_not_move" -v`
Expected: both PASS immediately — `TaskStore.set_status` already exists from Task 1. (This step is a documentation/pinning test rather than driving new production code; running it here confirms the contract Task 6 must respect is already correctly in place.)

- [ ] **Step 5: Wire Start to flip the task's status**

**This must NOT be gated on `self.session.phase is Phase.IDLE`.** `auto_start_focus` defaults to `False`, so after a break ends, the next FOCUS phase is *entered* (phase is already `Phase.FOCUS`) but sits paused, waiting for you to press Start yourself — an IDLE-only check would miss exactly this (very common) case. The condition that's actually right is the one `_do_toggle()` already computes for deciding whether to resume window monitoring: "was not running before this toggle, is running now, and the phase is FOCUS." Reuse that existing block instead of adding a new, narrower check.

In `lock_in/ui.py`, `_do_toggle()`, change:

```python
        if not was_running and self.session.is_running:
            if self.session.phase is Phase.FOCUS:
                self.monitor.resume()
                if self.config_obj.camera_monitoring_enabled:
                    self.camera_watcher.resume()
```

to:

```python
        if not was_running and self.session.is_running:
            if self.session.phase is Phase.FOCUS:
                if self.current_task_id is not None:
                    self.tasks.set_status(self.current_task_id, TaskStatus.IN_PROGRESS)
                    self._render_tasks()
                self.monitor.resume()
                if self.config_obj.camera_monitoring_enabled:
                    self.camera_watcher.resume()
```

(This also fires on a plain mid-block pause → resume, re-setting an already-`in_progress` task to `in_progress` again — harmless, since `set_status` is idempotent and task edits are infrequent, human-paced actions; not worth extra bookkeeping to suppress.)

- [ ] **Step 6: Call the picker refresh once at startup**

In `lock_in/ui.py`, `__init__`, directly after `self._build_tabs()`:

```python
        self._refresh_current_task_picker()
```

- [ ] **Step 7: Run the full test suite**

Run: `pytest -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add lock_in/ui.py tests/test_tasks.py
git commit -m "Add current-task picker; starting a block sets it in_progress"
```

---

### Task 6: `ui.py` — log completed/skipped/reset blocks to history

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `self.history` (Task 3), `self.current_task_id` (Task 5), `SessionRecord` (Task 2).

No dedicated automated test in `ui.py` itself (matches every prior tier's precedent for phase-transition wiring) — the underlying `HistoryStore`/`SessionRecord` contract is already fully tested in Task 2; this task is pure wiring, verified in the final manual pass.

This is the one genuinely tricky piece in this plan: by the time `_on_phase_ended()` runs, `self.session.phase` has **already** advanced to the *next* phase (`session.py`'s `_advance()` mutates state before returning its events) — so `_on_phase_ended()` cannot ask "what phase just ended?" from `self.session.phase` directly. The fix is to snapshot the FOCUS phase's start time and planned duration the moment it *begins* (in `_on_phase_started()`), and consume that snapshot wherever the block ends.

- [ ] **Step 1: Add the snapshot fields**

In `lock_in/ui.py`, `__init__`, directly after the `self.current_task_id: Optional[str] = None` line added in Task 3:

```python
        # Set the instant a FOCUS phase begins, cleared once it's logged
        # to history (whether it finished naturally, was skipped, or was
        # reset). None means "no focus block is currently being timed" --
        # used to tell a FOCUS phase ending from a BREAK phase ending,
        # since by the time _on_phase_ended() runs, self.session.phase
        # has already moved on to whatever comes next.
        self._focus_block_start: Optional[datetime] = None
        self._focus_block_planned_seconds: int = 0
```

`datetime` is already imported at the top of `lock_in/ui.py` (`from datetime import datetime`, line 36) — no new import needed for this step.

- [ ] **Step 2: Take the snapshot when a focus block starts**

**This must NOT be gated on `self.session.is_running`.** `auto_start_focus` defaults to `False` (you must press Start yourself after a break), and `session.py`'s `_enter()` always fires `Event.PHASE_STARTED` — and therefore always calls `_on_phase_started()` — the instant a phase is *entered*, regardless of whether it's actually running yet or sitting paused waiting for you to press Start. Gating on `is_running` here would mean the snapshot silently never happens in that (default!) case, since resuming from that paused-and-not-yet-started state calls `session.py`'s `resume()`, which returns no events at all and never calls `_on_phase_started()` a second time. The fix is to snapshot on entering FOCUS, full stop — duration accuracy doesn't depend on exactly when Start was pressed anyway, since `remaining_seconds` (used below in Step 3) doesn't move while paused.

In `lock_in/ui.py`, `_on_phase_started()`, directly below the existing `phase = self.session.phase` line, add a new top-level block (not nested inside the existing `if phase is Phase.FOCUS and self.session.is_running:` block below it):

```python
        phase = self.session.phase

        if phase is Phase.FOCUS:
            self._focus_block_start = datetime.now()
            self._focus_block_planned_seconds = self.session.total_seconds
```

- [ ] **Step 3: Add the shared logging helper**

Add this method near `_on_phase_started`/`_on_phase_ended`:

```python
    def _log_focus_block_if_any(self, completed: bool) -> None:
        """Writes one history entry for the focus block currently being
        timed, if there is one -- called from _on_phase_ended (natural
        completion), _on_skip, and _on_reset (both cut it short).
        A no-op when no focus block is in progress (e.g. a break just
        ended, or Reset was pressed while idle)."""
        if self._focus_block_start is None:
            return
        now = datetime.now()
        if completed:
            duration = self._focus_block_planned_seconds
        else:
            elapsed = self._focus_block_planned_seconds - self.session.remaining_seconds
            duration = max(0, elapsed)
        self.history.record(SessionRecord(
            start=self._focus_block_start.isoformat(timespec="seconds"),
            end=now.isoformat(timespec="seconds"),
            duration_seconds=duration,
            task_id=self.current_task_id,
            completed=completed,
        ))
        self._focus_block_start = None
```

- [ ] **Step 4: Call it on natural completion**

In `lock_in/ui.py`, `_on_phase_ended()`, as the very first line of the method (before `self.monitor.pause()`):

```python
        self._log_focus_block_if_any(completed=True)
```

- [ ] **Step 5: Call it on skip**

In `lock_in/ui.py`, `_on_skip()`, change:

```python
    def _on_skip(self) -> None:
        for event in self.session.skip():
            if event is Event.PHASE_STARTED:
                self._on_phase_started()
        self._refresh_timer_widgets()
```

to:

```python
    def _on_skip(self) -> None:
        was_focus = self.session.phase is Phase.FOCUS
        if was_focus:
            self._log_focus_block_if_any(completed=False)
        for event in self.session.skip():
            if event is Event.PHASE_STARTED:
                self._on_phase_started()
        self._refresh_timer_widgets()
```

(`self._log_focus_block_if_any` is called *before* `self.session.skip()` runs, while `self.session.remaining_seconds` still reflects the FOCUS phase being cut short -- calling it after would read the new phase's remaining time instead. The `was_focus` check avoids a redundant no-op call when skip is pressed during a break, where `_focus_block_start` is already `None` anyway and the helper would no-op regardless -- kept explicit here for readability, matching this method's existing small, explicit style.)

- [ ] **Step 6: Call it on reset**

In `lock_in/ui.py`, `_on_reset()`, change:

```python
    def _on_reset(self) -> None:
        self.session.reset()
```

to:

```python
    def _on_reset(self) -> None:
        self._log_focus_block_if_any(completed=False)
        self.session.reset()
```

(Same ordering requirement as Step 5 -- must run before `self.session.reset()` clears the session's timing state.)

- [ ] **Step 7: Run the full test suite**

Run: `pytest -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add lock_in/ui.py
git commit -m "Log completed, skipped, and reset focus blocks to session history"
```

---

### Task 7: Manual verification, then hand off to the user

**Files:** none (verification only).

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: all tests pass, including everything added in Tasks 1, 2, and 5.

- [ ] **Step 2: Launch the real app and verify by hand**

Run: `python main.py`

1. **Tasks tab exists and works:** open the new "Tasks" tab (first in the list). Add a task, confirm it appears immediately. Add a subtask to it, check it off, confirm the checkbox state persists after switching tabs and back. Click "Done" on a task, confirm it moves into the collapsed "Done (N)" section.
2. **Data survives a restart:** with at least one open task and one done task present, close the app entirely and relaunch it. Confirm both are still there in the same state (this exercises `TaskStore.load()`/`save()` for real, not just under `pytest`'s `tmp_path`).
3. **Current-task picker:** confirm the dropdown above the Start button lists every open (non-done) task plus "No task", and that a newly-added task appears in it without restarting the app. Select a task, confirm it stays selected.
4. **Starting flips status, ending does not:** pick a task in the dropdown, press Start. Switch to the Tasks tab — confirm that task's status marker changed to in-progress (`◐`). Let the block finish naturally (or use a very short `focus_minutes` in Settings to speed this up). Immediately check the Tasks tab again — **confirm the task is still in-progress, NOT done.** This is the one behavior most worth double-checking by hand, since it's the exact rule the spec called out explicitly.
5. **History is being logged:** after that same completed block, confirm a new line was written to `sessions.jsonl` in the app's data folder (Settings tab → check the app's data folder path, or just inspect `%APPDATA%\Lock In\sessions.jsonl` directly on Windows) with `"completed": true` and a `task_id` matching the task you picked.
6. **Skip and Reset log a cut-short block:** start a new focus block with a task picked, let a few seconds pass, then press Skip. Confirm a new `sessions.jsonl` line was written with `"completed": false` and a `duration_seconds` well under the phase's full length. Repeat once more using Reset instead of Skip.
7. **Untagged blocks still work:** set the picker to "No task" and run a full block. Confirm the app behaves exactly as it did before this plan (no crash, no missing UI), and that the resulting history line has `"task_id": null`.
8. **Nothing else regressed:** spot-check that Ryuki's mirror, the Blocking/Settings/Help tabs, and a normal Rider switch all still work — the Tasks tab and picker are new additions, not replacements, so everything from Tiers 0-4 should look and behave exactly as before.

- [ ] **Step 3: Give the user the commands to review and push**

Do not run any of these — print them for the user to run themselves:

```bash
git log --oneline main..HEAD
git push origin main
```

No version bump and no tag here — this plan ships an internal foundation, not a user-facing release on its own. Versioning and the README update are a separate decision once the user is ready to fold this (and however many of the 10 Tier 5 Riders they want alongside it) into an actual release.
