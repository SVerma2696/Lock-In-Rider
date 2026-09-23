# Tier 5 Rider #10 (MY-TH, the Priority tab) Implementation Plan

Spec: `docs/superpowers/specs/2026-09-22-tier5-myth-priority-design.md`.
Work through the tasks in order and tick each box as you go. This is the
second of two plans shipping together as one release — do the OOO plan
(`docs/superpowers/plans/2026-09-22-tier5-ooo-combo.md`) first, fold its
result in, then start this one.

**Goal:** When Kamen Rider MY-TH (2026) is the picked Rider, a "Priority" tab shows every open task, numbered, most-neglected first: a task you've never worked on ranks above every task you have, and among tasks you have worked on, the one you haven't touched in the longest comes first. This completes all 10 Tier 5 Riders.

**Architecture:** No new stored state — a new `lock_in/tier5/my_th.py` reads the existing `TaskStore` and `HistoryStore` fresh every time the tab is built. Two small pure functions (`last_worked_date`, `days_ago_phrase`) plus the sort itself (`neglect_order`), and one Tk-dependent `build()`. The tab plugs into the existing `TIER5_BUILDERS` registry and `_TIER5_TAB_LABELS`, the same way V3, Den-O, Decade, Zi-O, Blade, W, Geats, Gotchard, and OOO did.

**Tech Stack:** Python 3, CustomTkinter, pytest. No new dependency.

## Global Constraints

Copied from the spec. Every task below includes these.

- **Tab label:** `"Priority"`. **Effect name:** `"priority_order"`. **Rider:** `Kamen Rider MY-TH (2026)`.
- **The rule: most neglected first.** A task with no history at all ranks above every task that has one, no matter how stale. Among never-worked tasks, oldest `created_at` first. Among worked tasks, oldest last-worked date first; a tie (same last-worked day) is broken by `created_at`, oldest first.
- **A task's `status` (To Do vs. In Progress) plays no part in the order.**
- **Only open tasks show on the tab** (`tasks.open()`), numbered starting at 1.
- **Empty state (no open tasks):** the single line `"No open tasks yet. Add one on the Tasks tab."`, no list.
- **Caption (exact text):** `"Ranked by which task you've worked on least recently — nothing here is saved, it's worked out fresh every time you open this tab."`
- **The phrase under each task name (exact wording):** `"never started"` (no history), `"today"` (last worked today), `"yesterday"` (one day back), or `"{n} days ago"` (older). Never negative, even if a last-worked date somehow lands after "today".
- **The tab is read-only.** No buttons, no reordering, no "start this" action.
- **Colors:** the number and task name use `theme.primary_text_pair`; the phrase underneath uses `("gray40", "gray60")`, the same small-caption gray every other tab already uses.
- **No sentence says** "fail", "behind", "lost", "missed", or "broke".
- **Version:** `2.5.8` to `2.5.9` — this release ships both OOO and MY-TH together, completing Tier 5.
- **No commit, push, or tag is run while doing this plan.** The commands are in the Handoff section at the end, for the project owner to run.
- **Project files describe the software only** — nothing about who or what wrote it, in any file added or edited.
- **Line endings:** edit existing files in place and keep their current line-ending style (most are CRLF). New files may use LF (Git converts on commit).

## File Structure

| File | What it's for |
|---|---|
| `lock_in/tier5/my_th.py` *(new)* | `last_worked_date()`, `neglect_order()`, `days_ago_phrase()`, `build()` |
| `lock_in/tier5/__init__.py` *(edit)* | Register `"priority_order": my_th.build` |
| `lock_in/rider_themes.py` *(edit)* | `tier5_effect="priority_order"` on MY-TH; the comment's Rider list, now complete |
| `lock_in/ui.py` *(edit)* | `_TIER5_TAB_LABELS` entry; Help tab bullet and final wording |
| `lock_in/__init__.py` *(edit)* | Version `2.5.9` |
| `README.md` *(edit)* | MY-TH bullet, final "all ten" wording |
| `tests/test_tier5_myth.py` *(new)* | The pure functions and the wiring |
| `tests/test_rider_themes.py` *(edit)* | The tier5 completeness check grows to ten (final) |

---

### Task 1: `last_worked_date()`, `neglect_order()`, `days_ago_phrase()`

**Files:**
- Create: `lock_in/tier5/my_th.py`
- Create: `tests/test_tier5_myth.py`

**Interfaces:**
- Consumes: `HistoryStore.for_task()` (already exists, `lock_in/history.py`); `Task.id`, `Task.created_at` (already exist, `lock_in/tasks.py`).
- Produces: `last_worked_date(records: list[SessionRecord]) -> Optional[date]`; `neglect_order(open_tasks: list[Task], history: HistoryStore, today: date) -> list[Task]`; `days_ago_phrase(last: Optional[date], today: date) -> str`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tier5_myth.py`:

```python
"""Tests for MY-TH's Tier 5 gimmick: last_worked_date(), neglect_order(),
and days_ago_phrase(). No Tk, no display server -- see tier5/my_th.py."""

from datetime import date, timedelta

import pytest

from lock_in.history import HistoryStore, SessionRecord
from lock_in.tasks import Task, TaskStatus
from lock_in.tier5.my_th import days_ago_phrase, last_worked_date, neglect_order

TODAY = date(2026, 9, 22)


@pytest.fixture
def history(tmp_path) -> HistoryStore:
    return HistoryStore(tmp_path / "sessions.jsonl")


def _task(task_id: str, created_at: str) -> Task:
    return Task(id=task_id, name=task_id, created_at=created_at)


def _record(task_id: str, days_ago: int, today: date = TODAY) -> SessionRecord:
    day = today - timedelta(days=days_ago)
    start = f"{day.isoformat()}T09:00:00"
    end = f"{day.isoformat()}T09:25:00"
    return SessionRecord(start=start, end=end, duration_seconds=1500, task_id=task_id, completed=True)


# --- last_worked_date ------------------------------------------------------ #

def test_last_worked_date_with_no_records_is_none():
    assert last_worked_date([]) is None


def test_last_worked_date_returns_the_latest_records_day():
    early = SessionRecord(start="2026-09-17T09:00:00", end="2026-09-17T09:25:00",
                           duration_seconds=1500, task_id="t1", completed=True)
    late = SessionRecord(start="2026-09-21T09:00:00", end="2026-09-21T09:25:00",
                          duration_seconds=1500, task_id="t1", completed=True)
    assert last_worked_date([early, late]) == date(2026, 9, 21)
    assert last_worked_date([late, early]) == date(2026, 9, 21)


# --- neglect_order ----------------------------------------------------------- #

def test_never_worked_task_sorts_before_a_worked_one_no_matter_how_stale(history):
    never = _task("never", "2026-01-01T00:00:00")
    worked = _task("worked", "2020-01-01T00:00:00")
    history.record(_record("worked", 400))
    assert neglect_order([worked, never], history, TODAY) == [never, worked]


def test_never_worked_tasks_are_tie_broken_by_creation_date_oldest_first(history):
    newer = _task("newer", "2026-02-01T00:00:00")
    older = _task("older", "2026-01-01T00:00:00")
    assert neglect_order([newer, older], history, TODAY) == [older, newer]


def test_worked_tasks_sort_by_oldest_last_worked_date_first(history):
    stale = _task("stale", "2026-01-01T00:00:00")
    fresh = _task("fresh", "2026-01-01T00:00:00")
    history.record(_record("fresh", 1))
    history.record(_record("stale", 10))
    assert neglect_order([fresh, stale], history, TODAY) == [stale, fresh]


def test_worked_tasks_last_worked_the_same_day_are_tie_broken_by_created_at(history):
    newer = _task("newer", "2026-02-01T00:00:00")
    older = _task("older", "2026-01-01T00:00:00")
    history.record(_record("newer", 2))
    history.record(_record("older", 2))
    assert neglect_order([newer, older], history, TODAY) == [older, newer]


def test_neglect_order_with_no_open_tasks_is_empty(history):
    assert neglect_order([], history, TODAY) == []


def test_task_status_has_no_effect_on_the_order(history):
    todo = Task(id="todo", name="todo", created_at="2026-01-01T00:00:00", status=TaskStatus.TODO)
    in_progress = Task(id="in_progress", name="in_progress", created_at="2026-01-02T00:00:00",
                        status=TaskStatus.IN_PROGRESS)
    assert neglect_order([in_progress, todo], history, TODAY) == [todo, in_progress]


# --- days_ago_phrase ---------------------------------------------------------- #

def test_days_ago_phrase_for_never_started():
    assert days_ago_phrase(None, TODAY) == "never started"


def test_days_ago_phrase_for_today():
    assert days_ago_phrase(TODAY, TODAY) == "today"


def test_days_ago_phrase_for_yesterday():
    assert days_ago_phrase(TODAY - timedelta(days=1), TODAY) == "yesterday"


def test_days_ago_phrase_for_several_days_ago():
    assert days_ago_phrase(TODAY - timedelta(days=5), TODAY) == "5 days ago"


def test_days_ago_phrase_across_a_month_boundary():
    today = date(2026, 10, 2)
    assert days_ago_phrase(date(2026, 9, 28), today) == "4 days ago"


def test_days_ago_phrase_across_a_year_boundary():
    today = date(2027, 1, 2)
    assert days_ago_phrase(date(2026, 12, 29), today) == "4 days ago"


def test_days_ago_phrase_never_goes_negative():
    """Defensive: a last-worked date somehow after 'today' (e.g. the
    system clock moved backward) reads as 'today', never a nonsensical
    negative count."""
    assert days_ago_phrase(TODAY + timedelta(days=1), TODAY) == "today"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_myth.py -v`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'lock_in.tier5.my_th'`.

- [ ] **Step 3: Write the implementation**

Create `lock_in/tier5/my_th.py`:

```python
"""
tier5/my_th.py
===============
Kamen Rider MY-TH's Tier 5 gimmick: a "Priority" tab. Every open task,
numbered, most neglected first -- a task you've never worked on ranks
above every task you have, and among tasks you have worked on, the one
you haven't touched in the longest comes first. The tenth and last of
Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-22-tier5-myth-priority-design.md.

Nothing here is saved. The order is worked out fresh every time the tab
is built, reading only the existing task list and session history.

last_worked_date(), neglect_order(), and days_ago_phrase() are plain
logic, tested with no Tk and no display server. build() is the only
Tk-dependent piece; it's checked in the running app instead, matching
every other tab.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from ..history import HistoryStore, SessionRecord
from ..tasks import Task


def last_worked_date(records: list[SessionRecord]) -> Optional[date]:
    """The calendar day of the most recent block in `records` (by start
    time), or None if `records` is empty."""
    if not records:
        return None
    latest = max(records, key=lambda r: r.start)
    return datetime.fromisoformat(latest.start).date()


def neglect_order(open_tasks: list[Task], history: HistoryStore, today: date) -> list[Task]:
    """`open_tasks` sorted most-neglected-first. A task with no history
    sorts before every task that has one, no matter how stale that date
    is (its sort date is a sentinel that never wins against a real
    date). Among tasks that share the same has-a-date standing, older
    sorts first; ties are broken by created_at, oldest first. `today`
    is accepted for a consistent signature with build()'s other calls,
    but the order itself is relative and doesn't need it."""
    def sort_key(task: Task):
        last = last_worked_date(history.for_task(task.id))
        has_date = last is not None
        return (has_date, last or date.min, task.created_at)

    return sorted(open_tasks, key=sort_key)


def days_ago_phrase(last: Optional[date], today: date) -> str:
    """None -> 'never started'; today -> 'today'; one day back ->
    'yesterday'; anything older -> '{n} days ago'. Never negative, even
    if `last` is somehow after `today`."""
    if last is None:
        return "never started"
    delta = max(0, (today - last).days)
    if delta == 0:
        return "today"
    if delta == 1:
        return "yesterday"
    return f"{delta} days ago"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_myth.py -v`
Expected: all PASS.

- [ ] **Step 5: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 2: The "Priority" tab, plus the wiring

**Files:**
- Modify: `lock_in/tier5/my_th.py` (add `build()`)
- Modify: `lock_in/tier5/__init__.py`
- Modify: `lock_in/rider_themes.py` (the `Kamen Rider MY-TH (2026)` entry, and one comment)
- Modify: `lock_in/ui.py` (`_TIER5_TAB_LABELS`)
- Modify: `tests/test_tier5_myth.py` (wiring tests)
- Modify: `tests/test_rider_themes.py`

**Interfaces:**
- Consumes: `last_worked_date()`, `neglect_order()`, `days_ago_phrase()` (Task 1); `tasks.open()`; `history.for_task()`; the theme's `primary_text_pair`.
- Produces: `build(parent, *, history, tasks, theme, appearance_mode, config) -> None`, registered as `TIER5_BUILDERS["priority_order"]`; the tab label `"Priority"`.

Every one of the other nine Tier 5 builders already accepts `history=`, `tasks=`, `theme=`, `appearance_mode=`, and `config=`, so this task needs no change to any sibling Rider module.

- [ ] **Step 1: Write the failing wiring tests**

Append to `tests/test_tier5_myth.py`, with two blank lines before them:

```python
# --- wiring --------------------------------------------------------------- #

def test_priority_order_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, my_th
    assert TIER5_BUILDERS["priority_order"] is my_th.build


def test_priority_order_has_the_priority_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["priority_order"] == "Priority"


def test_my_th_builder_accepts_the_standard_tier5_signature():
    import inspect
    from lock_in.tier5 import my_th
    params = inspect.signature(my_th.build).parameters
    for name in ("parent", "history", "tasks", "theme", "appearance_mode", "config"):
        assert name in params
```

In `tests/test_rider_themes.py`, the completeness check grows from nine Riders to ten — its final value for Tier 5. Two edits:

In `tests/test_rider_themes.py`, replace:

```python
def test_exactly_these_nine_riders_have_a_tier5_effect():
```

with:

```python
def test_exactly_these_ten_riders_have_a_tier5_effect():
```

In `tests/test_rider_themes.py`, replace:

```python
        "Kamen Rider OOO (2010)": "phase_combo",
    }
```

with:

```python
        "Kamen Rider OOO (2010)": "phase_combo",
        "Kamen Rider MY-TH (2026)": "priority_order",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_myth.py tests/test_rider_themes.py -v`
Expected: 4 FAIL (the registry check, the tab-label check, the builder-signature check, and the ten-Riders check). Everything else PASSES.

- [ ] **Step 3: Add `build()` to `my_th.py`**

In `lock_in/tier5/my_th.py`, replace the import block at the top:

Replace:

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from ..history import HistoryStore, SessionRecord
from ..tasks import Task
```

with:

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import customtkinter as ctk

from ..history import HistoryStore, SessionRecord
from ..tasks import Task
```

Then add this to the very end of the file, with two blank lines before it:

```python
def build(parent, *, history, tasks, theme, appearance_mode, config) -> None:
    """
    Populate `parent` with MY-TH's Priority view: every open task,
    numbered, most-neglected first, each with a short "last worked"
    phrase underneath.

    Nothing here is saved -- neglect_order() is called fresh every time
    this runs, the same as V3's chart or Decade's ranking already are.
    The tab is read-only, so there is nothing to wire up beyond this one
    pass.

    `appearance_mode` and `config` are part of every Tier 5 builder's
    signature for consistency -- MY-TH needs neither.
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

    today = date.today()
    ordered = neglect_order(open_tasks, history, today)
    text_color = theme.primary_text_pair

    for index, task in enumerate(ordered, start=1):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8), anchor="w")
        ctk.CTkLabel(
            row, text=f"{index}. {task.name}", text_color=text_color,
            font=ctk.CTkFont(weight="bold"), anchor="w",
        ).pack(anchor="w")
        last = last_worked_date(history.for_task(task.id))
        ctk.CTkLabel(
            row, text=days_ago_phrase(last, today),
            text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11), anchor="w",
        ).pack(anchor="w")

    ctk.CTkLabel(
        frame,
        text="Ranked by which task you've worked on least recently — "
             "nothing here is saved, it's worked out fresh every time "
             "you open this tab.",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
        justify="left", wraplength=400,
    ).pack(anchor="w", pady=(6, 0))
```

- [ ] **Step 4: Register the builder**

In `lock_in/tier5/__init__.py`, replace:

```python
from . import blade, decade, den_o, geats, gotchard, ooo, v3, w, zi_o
```

with:

```python
from . import blade, decade, den_o, geats, gotchard, my_th, ooo, v3, w, zi_o
```

In `lock_in/tier5/__init__.py`, replace:

```python
    "badge_cards": gotchard.build,
    "phase_combo": ooo.build,
}
```

with:

```python
    "badge_cards": gotchard.build,
    "phase_combo": ooo.build,
    "priority_order": my_th.build,
}
```

- [ ] **Step 5: Give MY-TH its effect**

In `lock_in/rider_themes.py`, replace:

```python
    "Kamen Rider MY-TH (2026)": RiderTheme(
        "Reiwa", 2026, ("#0f4a8f", "#42a5f5"), ("#78909c", "#b0bec5"),
    ),
```

with:

```python
    "Kamen Rider MY-TH (2026)": RiderTheme(
        "Reiwa", 2026, ("#0f4a8f", "#42a5f5"), ("#78909c", "#b0bec5"),
        tier5_effect="priority_order",
    ),
```

This plan runs after the OOO plan has already been folded in, so the comment above `tier5_effect` at this point reads the version OOO's plan left it in. Replace it with its final, complete wording:

In `lock_in/rider_themes.py`, replace:

```python
    # "none" for every Rider except the ones that read your tasks and
    # history (V3, Den-O, Decade, Zi-O, Blade, W, Geats, Gotchard and
    # OOO so far, out of 10
    # planned -- see
    # docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md).
```

with:

```python
    # "none" for every Rider except the ones that read your tasks and
    # history -- all 10 planned Riders are now built: V3, Den-O, Decade,
    # Zi-O, Blade, W, Geats, Gotchard, OOO, and MY-TH. See
    # docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md).
```

If OOO's plan was not folded in with exactly this wording, match on the `tier5_effect: str = "none"` field's comment block instead — it is the only comment directly above that field.

- [ ] **Step 6: Give the tab its name**

In `lock_in/ui.py`, replace:

```python
    "goal_streak": "Goal", "badge_cards": "Badges", "phase_combo": "Combo",
}
```

with:

```python
    "goal_streak": "Goal", "badge_cards": "Badges", "phase_combo": "Combo",
    "priority_order": "Priority",
}
```

Nothing else in `ui.py` changes for the tab itself: building it, refreshing it after a finished block, and hiding it for Standard Mode all already work for any registered effect.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_myth.py tests/test_rider_themes.py -v`
Expected: all PASS.

- [ ] **Step 8: Drive the real tab in the real app**

Save the script below as `myth_drive.py` in any scratch folder OUTSIDE the project (for example your temp folder). It points the app at a throwaway data folder, so your real settings, tasks, and history are not touched. It seeds three tasks — one never worked on, one worked on recently, one worked on a while ago — and reads the real tab:

```python
"""Drives the real Lock In window with fake tasks and history, and
reads the real Priority tab. Run from the PROJECT folder so `lock_in`
can be imported:

  Git Bash:    PYTHONPATH=. python /path/to/myth_drive.py
  PowerShell:  $env:PYTHONPATH="."; python C:\\path\\to\\myth_drive.py

Optional switches (environment variables):
  EMPTY=1                          fresh install, no tasks at all
  RIDER="Kamen Rider (1971)"       a Rider other than MY-TH (the Priority tab must be absent)
  SHOT=C:\\some\\folder\\priority  also saves priority-dark.png and priority-light.png
"""
import ctypes, dataclasses, json, os, sys, tempfile, time
from datetime import datetime, timedelta
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="lockin_fake_appdata_")

from lock_in.config import Config, LOG_PATH, app_data_dir
from lock_in.history import SessionRecord
from lock_in.tasks import TaskStore

MYTH = "Kamen Rider MY-TH (2026)"
RIDER = os.environ.get("RIDER", MYTH)
EMPTY = bool(os.environ.get("EMPTY"))
SHOT = os.environ.get("SHOT")
CAPTION = ("Ranked by which task you've worked on least recently — "
           "nothing here is saved, it's worked out fresh every time "
           "you open this tab.")

config = Config()
config.rider_theme = RIDER
config.save()


def make_record(days_ago, task_id):
    start = (datetime.now() - timedelta(days=days_ago)).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=25)
    return SessionRecord(start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds"),
                          1500, task_id, True)


if not EMPTY:
    seed_tasks = TaskStore(app_data_dir() / "tasks.json")
    never = seed_tasks.add("Never touched")
    recent = seed_tasks.add("Worked on yesterday")
    stale = seed_tasks.add("Worked on 10 days ago")
    lines = [
        json.dumps(dataclasses.asdict(make_record(1, recent.id))),
        json.dumps(dataclasses.asdict(make_record(10, stale.id))),
    ]
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

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
has_tab = "Priority" in app.tabs._tab_dict

if RIDER != MYTH:
    check("no Priority tab for a Rider that isn't MY-TH", not has_tab)
else:
    check("Priority tab exists for MY-TH", has_tab)
    app.tabs.set("Priority")
    app.update()
    tab = app.tabs.tab("Priority")
    texts = label_texts(tab)

    if EMPTY:
        print("fresh install:")
        check("shows the empty state", "No open tasks yet. Add one on the Tasks tab." in texts)
    else:
        print("with three seeded tasks:")
        for expected in [
            "1. Never touched", "never started",
            "2. Worked on 10 days ago", "10 days ago",
            "3. Worked on yesterday", "yesterday",
            CAPTION,
        ]:
            check(f"shows {expected!r}", expected in texts)

        if SHOT:
            app.geometry("620x1000+40+0")
            app.attributes("-topmost", True)
            for mode in ("dark", "light"):
                app._on_appearance_change(mode)
                app.tabs.set("Priority")
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
1. Default (three seeded tasks): every line prints PASS and `FAILURES: none` — confirming the never-touched task is #1, the 10-days-ago task is #2, and the worked-yesterday task is #3.
2. `EMPTY=1`: the empty-state line passes.
3. `RIDER="Kamen Rider (1971)"`: the "no Priority tab" line passes.

Then run it once more with `SHOT` set and open the two PNGs. Expected in both light and dark: a numbered list reading "1. Never touched / never started", "2. Worked on 10 days ago / 10 days ago", "3. Worked on yesterday / yesterday", and the caption underneath.

- [ ] **Step 9: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 3: Docs, version, and final checks

**Files:**
- Modify: `lock_in/__init__.py`
- Modify: `lock_in/ui.py` (Help tab)
- Modify: `README.md`

**Interfaces:**
- Consumes: the finished feature from Tasks 1 and 2, plus OOO's already-folded-in changes.
- Produces: version `2.5.9`; the MY-TH bullet and the final "all ten" wording in the Help tab and README.

- [ ] **Step 1: Bump the version**

In `lock_in/__init__.py`, replace:

```python
__version__ = "2.5.8"
```

with:

```python
__version__ = "2.5.9"
```

If this file already reads `2.5.9` (for example because it was bumped as part of an earlier, separate change in this same working tree), leave it as `2.5.9` and skip this step — the end state either way is the same.

- [ ] **Step 2: Help tab**

In `lock_in/ui.py`, in the Tier 5 section of the Help tab, directly after the OOO bullet that the OOO plan added:

In `lock_in/ui.py`, replace:

```python
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

with:

```python
        bullet(
            "OOO — a \"Combo\" tab appears: every open task gets three "
            "boxes, Plan, Work, and Review. Check all three and the task "
            "shows a \"Combo formed!\" mark -- but only your own click on "
            "the Tasks tab actually finishes it."
        )
        bullet(
            "MY-TH — a \"Priority\" tab appears: your open tasks, "
            "numbered, the one you've gone the longest without working "
            "on at the top. Nothing is saved -- it's worked out fresh "
            "every time you open the tab."
        )
        body(
            "All ten Tier 5 heroes are built now -- every one of them "
            "reads your tasks and history this way."
        )
```

If the OOO bullet was folded in with slightly different wording, match on the `body(...)` call that says "these nine are just the first" instead — it is the only such line in the Help tab.

- [ ] **Step 3: README, the MY-TH bullet and the final count**

In `README.md`, in the "Tier 5" section, directly after the OOO bullet the OOO plan added:

In `README.md`, replace:

```
- **OOO** — adds a "Combo" tab: every open task gets three boxes, Plan,
  Work, and Review, that you can check in any order. Check all three
  and the task shows a small "Combo formed!" mark. It's just for fun —
  you still mark the task itself done on the Tasks tab, the same as
  always.

More Riders will read your tasks and history this way over time — these
nine are just the first of ten planned.
```

with:

```
- **OOO** — adds a "Combo" tab: every open task gets three boxes, Plan,
  Work, and Review, that you can check in any order. Check all three
  and the task shows a small "Combo formed!" mark. It's just for fun —
  you still mark the task itself done on the Tasks tab, the same as
  always.
- **MY-TH** — adds a "Priority" tab: your open tasks, numbered, with the
  one you've gone the longest without working on at the top. A task
  you've never started outranks every task you have, no matter how
  stale. Nothing is saved here — the order is worked out fresh every
  time you open the tab.

All ten Tier 5 Riders now read your tasks and history this way.
```

If the OOO bullet was folded in with slightly different wording, match on the "More Riders will read your tasks and history this way over time" paragraph instead — it is the only such line in the README.

- [ ] **Step 4: Run everything**

Run: `python -m pytest`
Expected: 0 failed, 1 skipped (the same skip as before).

Run the existing real-window smoke test in a throwaway data folder. Git Bash: `APPDATA="$(mktemp -d)" PYTHONPATH=. python tests/smoke_ui.py`. PowerShell: `$env:APPDATA=(New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([guid]::NewGuid()))).FullName; $env:PYTHONPATH="."; python tests/smoke_ui.py`.
Expected: ends with `smoke test passed`.

Re-run `myth_drive.py` (Task 2, Step 8) with the default seeded tasks, and re-run `ooo_drive.py` from the OOO plan too, to confirm neither Rider's tab broke the other. Then open the real app once with a Rider that is neither OOO nor MY-TH and open Help: it should now say v2.5.9 and list all ten Tier 5 Riders.

- [ ] **Step 5: Repo hygiene checks**

Run: `git status --short`
Expected: exactly these paths, and nothing else (in particular nothing generated):
`README.md`, `lock_in/__init__.py`, `lock_in/rider_themes.py`, `lock_in/tasks.py`, `lock_in/tier5/__init__.py`, `lock_in/tier5/ooo.py` (new), `lock_in/tier5/my_th.py` (new), `lock_in/ui.py`, `tests/test_rider_themes.py`, `tests/test_tasks.py`, `tests/test_tier5_ooo.py` (new), `tests/test_tier5_myth.py` (new), plus the two specs and the two plans under `docs/superpowers/`.
If anything else shows up (a picture, a data file, a folder), add a matching line to `.gitignore`. If nothing does, `.gitignore` needs no change. Neither Rider makes a new data file — OOO's `phases` lives in the existing `tasks.json`, and MY-TH saves nothing at all — so none is expected.

Now check that the changes describe the software only. This looks at the lines added across both plans and at the four new source/test files, and prints any line that names a helper tool or a co-writer, or that has a credit line. The square brackets are on purpose: they stop the check from matching its own words.

```bash
git diff -U0 | grep '^+' | grep -inE "cl[a]ude|anthrop[i]c|co-[a]uthor|generated [w]ith|[a]ssistant|sub[a]gent|[a]gentic" ; grep -inE "cl[a]ude|anthrop[i]c|co-[a]uthor|generated [w]ith|[a]ssistant|sub[a]gent|[a]gentic" lock_in/tier5/ooo.py lock_in/tier5/my_th.py tests/test_tier5_ooo.py tests/test_tier5_myth.py docs/superpowers/specs/2026-09-22-tier5-ooo-combo-design.md docs/superpowers/specs/2026-09-22-tier5-myth-priority-design.md docs/superpowers/plans/2026-09-22-tier5-ooo-combo.md docs/superpowers/plans/2026-09-22-tier5-myth-priority.md
```

Expected: nothing printed.

---

## Handoff: git steps for the project owner

Nothing above runs any of these. Run them yourself once you have looked at the result. The commit message is plain, with **one** `-m` and no extra lines under it, so no trailer or credit line can end up in it.

```bash
git status
git add -A
git commit -m "v2.5.9: add OOO and MY-TH (Tier 5 Riders 9 and 10) -- Tier 5 complete"
git log -1 --format=%B
git shortlog -sne
git push origin main
git tag v2.5.9
git push origin v2.5.9
```

Two safety looks after the commit and before the pushes:
- `git log -1 --format=%B` should print only the one-line message above, and nothing under it.
- `git shortlog -sne` should list only you, with your own name and email, and nobody else. Anyone listed there would show up as a contributor on GitHub.

Pushing the tag starts the release build (`.github/workflows/release.yml`), so push it last, after you are happy with the result. Git may print harmless "LF will be replaced by CRLF" warnings.

If the `.gitignore` hardening from earlier this session (the `.claude/`, `.superpowers/`, `graphify-out/` entries) is still sitting uncommitted alongside this, `git status` will show it too — it's unrelated to Tier 5 but harmless to include in the same commit, or split out first with its own `git add .gitignore && git commit -m "..."` if you'd rather keep it separate.

## Spec coverage check

| Spec section | Where it's covered |
|---|---|
| `last_worked_date()`, most-recent-wins | Task 1 (`last_worked_date` + its tests) |
| The ranking rule (never-worked first, then oldest-last-worked, tie-broken by `created_at`) | Task 1 (`neglect_order` + its tests) |
| `days_ago_phrase()` wording, including the never-negative guard | Task 1 (`days_ago_phrase` + its tests, including the clock-skew test) |
| The tab (numbered list, phrase, empty state, caption, read-only) | Task 2, Step 3 (`build()`) and Step 8 (checked in the real app) |
| Colors | Task 2, Step 3, and the screenshots in Step 8 |
| Wiring (registry, theme, tab label, theme comment) | Task 2, Steps 4 to 6, with wiring tests in Steps 1 and 7 |
| Error handling (no history, deleted blocks, blank `created_at`, midnight rollover) | Task 1 (the tie-break and never-worked tests cover the data side); Task 2's `build()` reads `date.today()` fresh on every rebuild |
| Testing list | Tasks 1 and 2; manual checks in Task 2 Step 8 and Task 3 Step 4 |
| Docs, version, repo hygiene | Task 3 and the Handoff section |
| Out of scope (pinning/snoozing, blending in OOO's combos or subtask count, a start button, real scheduling, notifications) | Nothing in this plan builds any of it |
