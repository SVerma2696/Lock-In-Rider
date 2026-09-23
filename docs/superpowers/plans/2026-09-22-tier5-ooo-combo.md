# Tier 5 Rider #9 (OOO, the Combo tab) Implementation Plan

Spec: `docs/superpowers/specs/2026-09-22-tier5-ooo-combo-design.md`.
Work through the tasks in order and tick each box as you go.

**Goal:** When Kamen Rider OOO (2010) is the picked Rider, a "Combo" tab shows every open task as a card with three fixed checkboxes — Plan, Work, Review — and checking all three shows a "Combo formed!" mark next to that task's name. The task itself is never finished by this tab; only your own click on the Tasks tab does that.

**Architecture:** One new field on the existing `Task` dataclass (`phases: List[bool]`, always exactly 3 entries) in `lock_in/tasks.py`, plus one new `TaskStore.toggle_phase()` method. A new `lock_in/tier5/ooo.py` holds one pure function (`combo_formed`) and the one Tk-dependent `build()`. The tab plugs into the existing `TIER5_BUILDERS` registry and `_TIER5_TAB_LABELS`, the same way V3, Den-O, Decade, Zi-O, Blade, W, Geats, and Gotchard did.

**Tech Stack:** Python 3, CustomTkinter, pytest. No new dependency.

## Global Constraints

Copied from the spec. Every task below includes these.

- **Tab label:** `"Combo"`. **Effect name:** `"phase_combo"`. **Rider:** `Kamen Rider OOO (2010)`.
- **Three fixed phases per task, in this order:** Plan, Work, Review. Every task, new or old, starts with all three unchecked (`[False, False, False]`).
- **Checking all three boxes never finishes the task.** The task's `status` is untouched by this feature.
- **Every box is a toggle** — checking and unchecking both just flip that one entry.
- **Only open tasks show on the tab** (`tasks.open()`: To Do + In Progress), in the same order the Tasks tab itself lists them.
- **Empty state (no open tasks):** the single line `"No open tasks yet. Add one on the Tasks tab."`, no cards.
- **Caption (exact text):** `"Plan, Work, Review — check them in any order. A full combo is just for fun; you still mark the task itself done on the Tasks tab."`
- **The "Combo formed!" text (exact):** `"⭐ Combo formed!"`, shown under the task name in `theme.secondary`, only once all three phases are checked; empty string otherwise.
- **Colors:** task name and phase-button labels use `theme.primary_text_pair`; a checked phase button uses `theme.secondary`; an unchecked one uses `("gray80", "gray30")`.
- **No sentence says** "fail", "behind", "lost", "missed", or "broke".
- **A hand-edited `tasks.json` with a broken `phases` value** (wrong type, wrong length, non-boolean entries) falls back to `[False, False, False]` for that one task, without dropping the task or any sibling task.
- **`toggle_phase(task_id, index)`** returns `False` and changes nothing for a missing task id or an `index` that is not `0`, `1`, or `2`.
- **Version:** not bumped by this plan — see the MY-TH plan's Task 4, which bumps `2.5.8` to `2.5.9` once both Riders are in.
- **No commit, push, or tag is run while doing this plan.** The commands are handed over once the MY-TH plan (which ships in the same release) is also done.
- **Project files describe the software only** — nothing about who or what wrote it, in any file added or edited.
- **Line endings:** edit existing files in place and keep their current line-ending style (most are CRLF). New files may use LF (Git converts on commit).

## File Structure

| File | What it's for |
|---|---|
| `lock_in/tasks.py` *(edit)* | `Task.phases`, defensive loading, `TaskStore.toggle_phase()` |
| `lock_in/tier5/ooo.py` *(new)* | `combo_formed()` and `build()` |
| `lock_in/tier5/__init__.py` *(edit)* | Register `"phase_combo": ooo.build` |
| `lock_in/rider_themes.py` *(edit)* | `tier5_effect="phase_combo"` on OOO; the comment's Rider list |
| `lock_in/ui.py` *(edit)* | `_TIER5_TAB_LABELS` entry; Help tab bullet and wording |
| `README.md` *(edit)* | OOO bullet, "nine of ten" wording |
| `tests/test_tasks.py` *(edit)* | `phases` field, `toggle_phase()`, defensive loading |
| `tests/test_tier5_ooo.py` *(new)* | `combo_formed()` and the wiring |
| `tests/test_rider_themes.py` *(edit)* | The tier5 completeness check grows to nine |

---

### Task 1: The `phases` field and `toggle_phase()`

**Files:**
- Modify: `lock_in/tasks.py`
- Modify: `tests/test_tasks.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `Task.phases: List[bool]` (default `[False, False, False]`); `TaskStore.toggle_phase(task_id: str, index: int) -> bool`.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/test_tasks.py`, with two blank lines before them:

```python
def test_new_task_has_three_unchecked_phases(store):
    task = store.add("Task")
    assert task.phases == [False, False, False]


def test_toggle_phase_flips_the_given_index(store):
    task = store.add("Task")
    assert store.toggle_phase(task.id, 1) is True
    assert store.all()[0].phases == [False, True, False]
    store.toggle_phase(task.id, 1)
    assert store.all()[0].phases == [False, False, False]


def test_toggle_phase_on_missing_task_returns_false(store):
    assert store.toggle_phase("nope", 0) is False


def test_toggle_phase_with_an_out_of_range_index_returns_false(store):
    task = store.add("Task")
    assert store.toggle_phase(task.id, 3) is False
    assert store.toggle_phase(task.id, -1) is False
    assert store.all()[0].phases == [False, False, False]


def test_phases_round_trip_through_save_and_load(tmp_path):
    path = tmp_path / "tasks.json"
    store1 = TaskStore(path)
    task = store1.add("Task")
    store1.toggle_phase(task.id, 0)
    store1.toggle_phase(task.id, 2)
    store2 = TaskStore(path)
    assert store2.all()[0].phases == [True, False, True]


def test_missing_phases_field_defaults_to_all_unchecked(tmp_path):
    import json

    path = tmp_path / "tasks.json"
    payload = {"tasks": [{
        "id": "task1", "name": "Old task", "subtasks": [], "status": "todo",
        "created_at": "2024-01-01T10:00:00", "completed_at": None,
    }]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    store = TaskStore(path)
    assert store.all()[0].phases == [False, False, False]


@pytest.mark.parametrize("bad_phases", [
    "not a list", 5, None, True, [True, False], [True, False, True, False],
    {"0": True}, [],
])
def test_malformed_phases_falls_back_to_all_unchecked(tmp_path, bad_phases):
    import json

    path = tmp_path / "tasks.json"
    payload = {"tasks": [{
        "id": "task1", "name": "Task", "subtasks": [], "status": "todo",
        "created_at": "2024-01-01T10:00:00", "completed_at": None,
        "phases": bad_phases,
    }]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    store = TaskStore(path)
    tasks = store.all()
    assert len(tasks) == 1
    assert tasks[0].phases == [False, False, False]


def test_non_boolean_phase_entries_are_coerced_to_bool(tmp_path):
    import json

    path = tmp_path / "tasks.json"
    payload = {"tasks": [{
        "id": "task1", "name": "Task", "subtasks": [], "status": "todo",
        "created_at": "2024-01-01T10:00:00", "completed_at": None,
        "phases": [1, 0, "yes"],
    }]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    store = TaskStore(path)
    assert store.all()[0].phases == [True, False, True]
```

`pytest` is already imported at the top of `tests/test_tasks.py`, and `TaskStore` is already imported from `lock_in.tasks` — both are used above without any new import line.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tasks.py -v`
Expected: the 9 new tests FAIL (`Task` has no `phases` yet, `TaskStore` has no `toggle_phase`). The older tests still PASS.

- [ ] **Step 3: Add the `phases` field**

In `lock_in/tasks.py`, replace:

```python
    id: str
    name: str
    subtasks: List[Subtask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.TODO
    created_at: str = ""
    completed_at: Optional[str] = None
```

with:

```python
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
```

- [ ] **Step 4: Load `phases` defensively**

In `lock_in/tasks.py`, replace:

```python
                task = Task(
                    id=item["id"],
                    name=item["name"],
                    subtasks=subtasks,
                    status=TaskStatus(item.get("status", "todo")),
                    created_at=item.get("created_at", ""),
                    completed_at=item.get("completed_at"),
                )
```

with:

```python
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

                task = Task(
                    id=item["id"],
                    name=item["name"],
                    subtasks=subtasks,
                    status=TaskStatus(item.get("status", "todo")),
                    created_at=item.get("created_at", ""),
                    completed_at=item.get("completed_at"),
                    phases=phases,
                )
```

This exact 7-line `task = Task(...)` block appears once in the file, right after the subtask-building loop, so the replace is unambiguous.

- [ ] **Step 5: Add `toggle_phase()`**

In `lock_in/tasks.py`, replace:

```python
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
```

with:

```python
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
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tasks.py -v`
Expected: all PASS.

- [ ] **Step 7: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 2: `combo_formed()`

**Files:**
- Create: `lock_in/tier5/ooo.py`
- Create: `tests/test_tier5_ooo.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (`combo_formed` takes a plain `list[bool]`, not a `Task`).
- Produces: `combo_formed(phases: list[bool]) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tier5_ooo.py`:

```python
from lock_in.tier5.ooo import combo_formed


def test_combo_formed_when_all_three_are_true():
    assert combo_formed([True, True, True]) is True


def test_combo_formed_false_when_any_one_is_false():
    assert combo_formed([False, True, True]) is False
    assert combo_formed([True, False, True]) is False
    assert combo_formed([True, True, False]) is False


def test_combo_formed_false_when_all_are_false():
    assert combo_formed([False, False, False]) is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_ooo.py -v`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'lock_in.tier5.ooo'`.

- [ ] **Step 3: Write the minimal implementation**

Create `lock_in/tier5/ooo.py`:

```python
"""
tier5/ooo.py
============
Kamen Rider OOO's Tier 5 gimmick: a "Combo" tab. Every open task gets
three fixed checkboxes -- Plan, Work, Review -- and checking all three
shows a "Combo formed!" mark next to that task's name. The ninth of
Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-22-tier5-ooo-combo-design.md.

Checking all three boxes never finishes the task -- that's still always
your own click on the Tasks tab. See build() below.

combo_formed() is plain logic, tested with no Tk and no display server.
build() is the only Tk-dependent piece; it's checked in the running app
instead, matching every other tab.
"""

from __future__ import annotations


def combo_formed(phases: list[bool]) -> bool:
    """True once all three of a task's phases are checked."""
    return all(phases)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_ooo.py -v`
Expected: all PASS.

- [ ] **Step 5: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 3: The "Combo" tab, plus the wiring

**Files:**
- Modify: `lock_in/tier5/ooo.py` (add `build()`)
- Modify: `lock_in/tier5/__init__.py`
- Modify: `lock_in/rider_themes.py` (the `Kamen Rider OOO (2010)` entry, and one comment)
- Modify: `lock_in/ui.py` (`_TIER5_TAB_LABELS`)
- Modify: `tests/test_tier5_ooo.py` (wiring tests)
- Modify: `tests/test_rider_themes.py`

**Interfaces:**
- Consumes: `combo_formed()` (Task 2); `tasks.open()`, `tasks.get()`, `tasks.toggle_phase()` (Task 1 and `lock_in/tasks.py`); the theme's `secondary`, `primary_text_pair`.
- Produces: `build(parent, *, history, tasks, theme, appearance_mode, config) -> None`, registered as `TIER5_BUILDERS["phase_combo"]`; the tab label `"Combo"`.

Every one of the other eight Tier 5 builders already accepts `history=`, `tasks=`, `theme=`, `appearance_mode=`, and `config=`, so this task needs no change to any sibling Rider module.

- [ ] **Step 1: Write the failing wiring tests**

Append to `tests/test_tier5_ooo.py`, with two blank lines before them:

```python
# --- wiring --------------------------------------------------------------- #

def test_phase_combo_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, ooo
    assert TIER5_BUILDERS["phase_combo"] is ooo.build


def test_phase_combo_has_the_combo_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["phase_combo"] == "Combo"


def test_ooo_builder_accepts_the_standard_tier5_signature():
    import inspect
    from lock_in.tier5 import ooo
    params = inspect.signature(ooo.build).parameters
    for name in ("parent", "history", "tasks", "theme", "appearance_mode", "config"):
        assert name in params
```

In `tests/test_rider_themes.py`, the completeness check grows from eight Riders to nine. Two edits:

In `tests/test_rider_themes.py`, replace:

```python
def test_exactly_these_eight_riders_have_a_tier5_effect():
```

with:

```python
def test_exactly_these_nine_riders_have_a_tier5_effect():
```

In `tests/test_rider_themes.py`, replace:

```python
        "Kamen Rider Gotchard (2023)": "badge_cards",
    }
```

with:

```python
        "Kamen Rider Gotchard (2023)": "badge_cards",
        "Kamen Rider OOO (2010)": "phase_combo",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_ooo.py tests/test_rider_themes.py -v`
Expected: 4 FAIL (the registry check, the tab-label check, the builder-signature check, and the nine-Riders check). Everything else PASSES.

- [ ] **Step 3: Add `build()` to `ooo.py`**

First, in `lock_in/tier5/ooo.py`, replace the import block at the top:

Replace:

```python
from __future__ import annotations
```

with:

```python
from __future__ import annotations

import customtkinter as ctk

PHASE_LABELS = ("Plan", "Work", "Review")

# What an unchecked phase button looks like -- CustomTkinter's own gray,
# picked for light and dark mode. A checked one uses theme.secondary.
_EMPTY_BOX = ("gray80", "gray30")
```

Then add this to the very end of the file, with two blank lines before it:

```python
def build(parent, *, history, tasks, theme, appearance_mode, config) -> None:
    """
    Populate `parent` with OOO's Combo view: one card per open task,
    each with three Plan/Work/Review buttons.

    Every card and its three buttons are built once. Clicking a button
    calls tasks.toggle_phase(...) and then re-configures just that one
    card in place -- it never destroys and rebuilds the whole tab from
    inside a click, the same safety rule Geats' and Gotchard's widgets
    already follow.

    `history`, `appearance_mode`, and `config` are part of every Tier 5
    builder's signature for consistency -- OOO needs none of them.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    open_tasks = tasks.open()
    if not open_tasks:
        ctk.CTkLabel(
            frame, text="No open tasks yet. Add one on the Tasks tab.",
            text_color=theme.primary_text_pair,
        ).pack(anchor="w", pady=(4, 0))
        return

    text_color = theme.primary_text_pair

    for task in open_tasks:
        card = ctk.CTkFrame(frame, fg_color="transparent")
        card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            card, text=task.name, text_color=text_color,
            font=ctk.CTkFont(weight="bold"), anchor="w",
        ).pack(anchor="w")

        combo_label = ctk.CTkLabel(
            card, text="", text_color=theme.secondary,
            font=ctk.CTkFont(size=11, weight="bold"), anchor="w",
        )
        combo_label.pack(anchor="w")

        buttons_row = ctk.CTkFrame(card, fg_color="transparent")
        buttons_row.pack(anchor="w", pady=(4, 0))

        buttons: list = []

        def refresh_card(task_id=task.id, combo_label=combo_label, buttons=buttons) -> None:
            current = tasks.get(task_id)
            if current is None:
                return
            for button, checked in zip(buttons, current.phases):
                button.configure(fg_color=theme.secondary if checked else _EMPTY_BOX)
            combo_label.configure(text="⭐ Combo formed!" if combo_formed(current.phases) else "")

        def make_toggle(task_id, index, refresh):
            def toggle() -> None:
                tasks.toggle_phase(task_id, index)
                refresh()
            return toggle

        for index, label in enumerate(PHASE_LABELS):
            button = ctk.CTkButton(
                buttons_row, text=label, width=80,
                fg_color=_EMPTY_BOX, text_color=text_color,
                command=make_toggle(task.id, index, refresh_card),
            )
            button.pack(side="left", padx=(0, 6))
            buttons.append(button)

        refresh_card()

    ctk.CTkLabel(
        frame,
        text="Plan, Work, Review — check them in any order. A full combo "
             "is just for fun; you still mark the task itself done on the "
             "Tasks tab.",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
        justify="left", wraplength=400,
    ).pack(anchor="w", pady=(6, 0))
```

`refresh_card` binds `task_id`, `combo_label`, and `buttons` as default-argument values (evaluated once, at `def` time, each time round the `for task in open_tasks` loop) rather than as free variables looked up at call time — this is what stops every card from ending up wired to the *last* task in the list, a classic closure-in-a-loop bug. `make_toggle` takes `refresh` as an explicit parameter for the same reason: it is bound to that iteration's own `refresh_card` the moment `make_toggle(...)` runs (inside the loop, building the button), not looked up later when the button is actually clicked.

- [ ] **Step 4: Register the builder**

In `lock_in/tier5/__init__.py`, replace:

```python
from . import blade, decade, den_o, geats, gotchard, v3, w, zi_o
```

with:

```python
from . import blade, decade, den_o, geats, gotchard, ooo, v3, w, zi_o
```

In `lock_in/tier5/__init__.py`, replace:

```python
    "goal_streak": geats.build,
    "badge_cards": gotchard.build,
}
```

with:

```python
    "goal_streak": geats.build,
    "badge_cards": gotchard.build,
    "phase_combo": ooo.build,
}
```

- [ ] **Step 5: Give OOO its effect**

In `lock_in/rider_themes.py`, replace:

```python
    "Kamen Rider OOO (2010)": RiderTheme(
        "Heisei", 2010, ("#111111", "#616161"), ("#9c1e1e", "#ef5350"),
    ),
```

with:

```python
    "Kamen Rider OOO (2010)": RiderTheme(
        "Heisei", 2010, ("#111111", "#616161"), ("#9c1e1e", "#ef5350"),
        tier5_effect="phase_combo",
    ),
```

And the comment above `tier5_effect` lists the Riders "so far". Update it:

In `lock_in/rider_themes.py`, replace:

```python
    # "none" for every Rider except the ones that read your tasks and
    # history (V3, Den-O, Decade, Zi-O, Blade, W, Geats and Gotchard so
    # far, out of 10
    # planned -- see
```

with:

```python
    # "none" for every Rider except the ones that read your tasks and
    # history (V3, Den-O, Decade, Zi-O, Blade, W, Geats, Gotchard and
    # OOO so far, out of 10
    # planned -- see
```

- [ ] **Step 6: Give the tab its name**

In `lock_in/ui.py`, replace:

```python
    "goal_streak": "Goal", "badge_cards": "Badges",
}
```

with:

```python
    "goal_streak": "Goal", "badge_cards": "Badges", "phase_combo": "Combo",
}
```

Nothing else in `ui.py` changes for the tab itself: building it, refreshing it after a finished block, and hiding it for Standard Mode all already work for any registered effect.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_ooo.py tests/test_rider_themes.py -v`
Expected: all PASS.

- [ ] **Step 8: Drive the real tab in the real app**

Save the script below as `ooo_drive.py` in any scratch folder OUTSIDE the project (for example your temp folder). It points the app at a throwaway data folder, so your real settings and tasks are not touched. It seeds three fake tasks (one untouched, one with two of three phases checked, one with a full combo) and reads the real tab:

```python
"""Drives the real Lock In window with fake tasks and reads the real
Combo tab. Run from the PROJECT folder so `lock_in` can be imported:

  Git Bash:    PYTHONPATH=. python /path/to/ooo_drive.py
  PowerShell:  $env:PYTHONPATH="."; python C:\\path\\to\\ooo_drive.py

Optional switches (environment variables):
  EMPTY=1                          fresh install, no tasks at all
  RIDER="Kamen Rider (1971)"       a Rider other than OOO (the Combo tab must be absent)
  SHOT=C:\\some\\folder\\combo     also saves combo-dark.png and combo-light.png
"""
import ctypes, os, sys, tempfile, time
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="lockin_fake_appdata_")

from lock_in.config import Config, app_data_dir
from lock_in.tasks import TaskStore

OOO = "Kamen Rider OOO (2010)"
RIDER = os.environ.get("RIDER", OOO)
EMPTY = bool(os.environ.get("EMPTY"))
SHOT = os.environ.get("SHOT")
CAPTION = ("Plan, Work, Review — check them in any order. A full combo "
           "is just for fun; you still mark the task itself done on the "
           "Tasks tab.")

config = Config()
config.rider_theme = RIDER
config.save()

if not EMPTY:
    seed_tasks = TaskStore(app_data_dir() / "tasks.json")
    seed_tasks.add("Untouched task")
    two_of_three = seed_tasks.add("Two of three")
    seed_tasks.toggle_phase(two_of_three.id, 0)
    seed_tasks.toggle_phase(two_of_three.id, 1)
    full_combo = seed_tasks.add("Full combo")
    seed_tasks.toggle_phase(full_combo.id, 0)
    seed_tasks.toggle_phase(full_combo.id, 1)
    seed_tasks.toggle_phase(full_combo.id, 2)

import customtkinter as ctk
from lock_in.ui import LockInApp

failures = []
def check(label, condition):
    print(("  PASS  " if condition else "  FAIL  ") + label)
    if not condition:
        failures.append(label)

def walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from walk(child)

def label_texts(widget):
    return [w.cget("text") for w in walk(widget) if isinstance(w, ctk.CTkLabel) and w.cget("text")]

app = LockInApp()
app.update()
has_tab = "Combo" in app.tabs._tab_dict

if RIDER != OOO:
    check("no Combo tab for a Rider that isn't OOO", not has_tab)
else:
    check("Combo tab exists for OOO", has_tab)
    app.tabs.set("Combo")
    app.update()
    tab = app.tabs.tab("Combo")
    texts = label_texts(tab)

    if EMPTY:
        print("fresh install:")
        check("shows the empty state", "No open tasks yet. Add one on the Tasks tab." in texts)
    else:
        print("with three seeded tasks:")
        for expected in ["Untouched task", "Two of three", "Full combo", CAPTION]:
            check(f"shows {expected!r}", expected in texts)
        check("exactly one combo formed so far", texts.count("⭐ Combo formed!") == 1)

        if SHOT:
            app.geometry("620x1000+40+0")
            app.attributes("-topmost", True)
            for mode in ("dark", "light"):
                app._on_appearance_change(mode)
                app.tabs.set("Combo")
                app.lift(); app.update(); time.sleep(0.6); app.update()
                x, y = app.winfo_rootx(), app.winfo_rooty()
                from PIL import ImageGrab
                ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(f"{SHOT}-{mode}.png")
                print("  saved", f"{SHOT}-{mode}.png")

app.destroy()
print("\nFAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
```

Run it three ways, from the project folder:
1. Default (three seeded tasks): every line prints PASS and `FAILURES: none`.
2. `EMPTY=1`: the empty-state line passes.
3. `RIDER="Kamen Rider (1971)"`: the "no Combo tab" line passes.

Then run it once more with `SHOT` set and open the two PNGs, and separately click the app itself once by hand: pick OOO, open the Combo tab, click a phase button on "Untouched task" and confirm its color changes immediately (no flicker, no other card changing), click the remaining phase on "Two of three" and confirm its "⭐ Combo formed!" line appears right away, then un-check one of "Full combo"'s phases and confirm its line disappears.

- [ ] **Step 9: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 4: Docs and hygiene checks

**Files:**
- Modify: `lock_in/ui.py` (Help tab)
- Modify: `README.md`

**Interfaces:**
- Consumes: the finished feature from Tasks 1 to 3.
- Produces: the OOO bullet in the Help tab and README; the "nine" wording.

No version bump here — see the MY-TH plan's Task 4, which bumps `2.5.8` to `2.5.9` once both Riders are in and does the final "ten of ten" wording pass.

- [ ] **Step 1: Help tab**

In `lock_in/ui.py`, replace:

```python
        bullet(
            "Gotchard — a \"Badges\" tab appears: 9 cards to collect, "
            "for things like your first focus block, a 3-hour day, or a "
            "7-day streak of reaching your daily goal. A badge you win "
            "is yours to keep."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "eight are just the first."
        )
```

with:

```python
        bullet(
            "Gotchard — a \"Badges\" tab appears: 9 cards to collect, "
            "for things like your first focus block, a 3-hour day, or a "
            "7-day streak of reaching your daily goal. A badge you win "
            "is yours to keep."
        )
        bullet(
            "OOO — a \"Combo\" tab appears: every open task gets three "
            "boxes, Plan, Work, and Review. Check all three and the task "
            "shows a \"Combo formed!\" mark -- but only your own click on "
            "the Tasks tab actually finishes it."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "nine are just the first."
        )
```

- [ ] **Step 2: README, the OOO bullet and the count**

In `README.md`, in the "Tier 5" section, directly after the Gotchard bullet (which ends "...once you win a badge, it's yours to keep."):

In `README.md`, replace:

```
- **Gotchard** — adds a "Badges" tab: 9 cards to collect, for things
  like your first focus block, doing 10 blocks, a 1-hour day, a 3-hour
  day, 10 hours in all, checking off a task, and reaching your daily
  goal once, 3 days in a row, or 7 days in a row. A card you haven't
  won yet shows a gray hint so you know what to aim for; once you win a
  badge, it's yours to keep.

More Riders will read your tasks and history this way over time — these
eight are just the first of ten planned.
```

with:

```
- **Gotchard** — adds a "Badges" tab: 9 cards to collect, for things
  like your first focus block, doing 10 blocks, a 1-hour day, a 3-hour
  day, 10 hours in all, checking off a task, and reaching your daily
  goal once, 3 days in a row, or 7 days in a row. A card you haven't
  won yet shows a gray hint so you know what to aim for; once you win a
  badge, it's yours to keep.
- **OOO** — adds a "Combo" tab: every open task gets three boxes, Plan,
  Work, and Review, that you can check in any order. Check all three
  and the task shows a small "Combo formed!" mark. It's just for fun —
  you still mark the task itself done on the Tasks tab, the same as
  always.

More Riders will read your tasks and history this way over time — these
nine are just the first of ten planned.
```

Keep one blank line between the OOO bullet and the "More Riders..." paragraph.

- [ ] **Step 3: Run everything**

Run: `python -m pytest`
Expected: 0 failed, 1 skipped (the same skip as before).

Run the existing real-window smoke test in a throwaway data folder. Git Bash: `APPDATA="$(mktemp -d)" PYTHONPATH=. python tests/smoke_ui.py`. PowerShell: `$env:APPDATA=(New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([guid]::NewGuid()))).FullName; $env:PYTHONPATH="."; python tests/smoke_ui.py`.
Expected: ends with `smoke test passed`.

Re-run `ooo_drive.py` (Task 3, Step 8) with the default seeded tasks. Expected: `FAILURES: none`.

- [ ] **Step 4: Repo hygiene checks**

Run: `git status --short`
Expected: exactly these paths, and nothing else (in particular nothing generated):
`README.md`, `lock_in/rider_themes.py`, `lock_in/tasks.py`, `lock_in/tier5/__init__.py`, `lock_in/tier5/ooo.py` (new), `lock_in/ui.py`, `tests/test_rider_themes.py`, `tests/test_tasks.py`, `tests/test_tier5_ooo.py` (new), plus the spec and this plan under `docs/superpowers/`.
If anything else shows up (a picture, a data file, a folder), add a matching line to `.gitignore`. If nothing does, `.gitignore` needs no change. OOO makes no new file, because `phases` is saved inside the existing `tasks.json`, which is already ignored, so none is expected.

Now check that the changes describe the software only. This looks at the lines you added and at the two new files, and prints any line that names a helper tool or a co-writer, or that has a credit line. The square brackets are on purpose: they stop the check from matching its own words.

```bash
git diff -U0 | grep '^+' | grep -inE "cl[a]ude|anthrop[i]c|co-[a]uthor|generated [w]ith|[a]ssistant|sub[a]gent|[a]gentic" ; grep -inE "cl[a]ude|anthrop[i]c|co-[a]uthor|generated [w]ith|[a]ssistant|sub[a]gent|[a]gentic" lock_in/tier5/ooo.py tests/test_tier5_ooo.py docs/superpowers/specs/2026-09-22-tier5-ooo-combo-design.md docs/superpowers/plans/2026-09-22-tier5-ooo-combo.md
```

Expected: nothing printed.

- [ ] **Step 5: Hand off to the MY-TH plan**

This plan does not commit, push, tag, or bump the version — OOO and MY-TH ship together as one v2.5.9 release. Continue with `docs/superpowers/plans/2026-09-22-tier5-myth-priority.md`, whose Task 4 bumps the version, finishes the "ten of ten" wording, and hands over the combined git steps for both Riders.

## Spec coverage check

| Spec section | Where it's covered |
|---|---|
| The `phases` field, always exactly 3 entries | Task 1 (`Task.phases` + its tests) |
| `toggle_phase()`, checking never finishes the task | Task 1 (`toggle_phase()` + its tests) |
| The tab (cards, three buttons, combo mark, empty state, caption) | Task 3, Step 3 (`build()`) and Step 8 (checked in the real app) |
| Colors | Task 3, Step 3, and the screenshots in Step 8 |
| Wiring (registry, theme, tab label, theme comment) | Task 3, Steps 4 to 6, with wiring tests in Steps 1 and 7 |
| Error handling (malformed `phases`, bad `toggle_phase` args, a task completed/deleted while the tab is open) | Task 1 (malformed-value tests); Task 3 (`build()` reads `tasks.open()` fresh on every rebuild) |
| Testing list | Tasks 1 to 3; manual checks in Task 3 Step 8 and Task 4 Step 3 |
| Docs, version, repo hygiene | Task 4 (docs); version and final hygiene pass deferred to the MY-TH plan, as the spec says |
| Out of scope (custom phase names, sounds/animations, un-combo, Gotchard-style badges) | Nothing in this plan builds any of it |
