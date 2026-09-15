# Tier 5 Rider #3: Decade Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When Kamen Rider Decade (2009) is the picked Rider, an
"Analytics" tab appears with a 30-day version of V3's bar chart and a
"Top tasks" ranking (at most 10, by total time spent, descending).

**Architecture:** Three small generalizations to `tier5/_shared.py`
(`last_n_days` replacing V3's `last_14_days`, `resolve_task_name` moved
from Den-O), one new `HistoryStore.total_seconds_by_task()`, and one new
pure function (`ranked_tasks`, with the top-10 cap baked in) plus
`build()` in a new `tier5/decade.py`. No change to `ui.py`'s Tier 5 tab
mechanism beyond a one-line label addition — it's already fully generic.

**Tech Stack:** Python 3.11+, CustomTkinter, Pillow (via the already-
existing `make_hours_chart`), pytest.

## Global Constraints

- The ranking shows **at most 10 tasks**, sorted by total logged time
  descending. The cap is a hard `[:10]` inside `ranked_tasks()` itself —
  not a default page size, no "show more."
- A task with **zero** logged time never appears in the ranking at all.
- Two different tasks that were both deleted after being logged against
  show as **two separate `"Deleted task"` rows**, never merged.
- The 30-day chart reuses `visuals.make_hours_chart()` completely
  unchanged — no new rendering code, only a wider canvas (640×200) and a
  30-entry `last_n_days(..., n=30)` instead of V3's 14.
- No module in `lock_in/tier5/` may import from `lock_in/ui.py`, and
  nothing in `v3.py`/`den_o.py`/`decade.py` may import a name back out
  of `tier5/__init__.py` (the same circular-import shape already fixed
  twice in this tier — see Task 2 and Task 3).
- No new `HistoryStore` write method, no new config field.
- No git commit, tag, or push is executed as part of any task in this
  plan — every step stops at "write the file" / "run the tests". The
  final task hands the exact commands to the user to run themselves.

---

### Task 1: `HistoryStore.total_seconds_by_task()`

**Files:**
- Modify: `lock_in/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Produces: `HistoryStore.total_seconds_by_task() -> Dict[Optional[str], int]`.
  Task 4's `ranked_tasks()` consumes this.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_history.py` (after the `earliest_date` tests):

```python
def test_total_seconds_by_task_is_empty_for_an_empty_store(store):
    assert store.total_seconds_by_task() == {}


def test_total_seconds_by_task_sums_records_for_the_same_task(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123"))
    store.record(_record(datetime(2026, 9, 5, 9, 0, 0), 900, task_id="abc123"))
    assert store.total_seconds_by_task() == {"abc123": 2400}


def test_total_seconds_by_task_keeps_different_tasks_and_untagged_time_separate(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123"))
    store.record(_record(datetime(2026, 9, 4, 10, 0, 0), 600, task_id="other"))
    store.record(_record(datetime(2026, 9, 4, 11, 0, 0), 300, task_id=None))
    totals = store.total_seconds_by_task()
    assert totals == {"abc123": 1500, "other": 600, None: 300}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_history.py -k total_seconds_by_task -v`
Expected: FAIL — `AttributeError: 'HistoryStore' object has no attribute 'total_seconds_by_task'`

- [ ] **Step 3: Write the minimal implementation**

In `lock_in/history.py`, add this method to `HistoryStore` (right after
`total_seconds_by_day`):

```python
    def total_seconds_by_task(self) -> Dict[Optional[str], int]:
        """{'abc123': 1500, None: 900, ...} -- total focused seconds per
        task_id, with None holding every untagged block's time. The
        aggregate Decade's "Top tasks" ranking reads from."""
        totals: Dict[Optional[str], int] = {}
        for r in self._records:
            totals[r.task_id] = totals.get(r.task_id, 0) + r.duration_seconds
        return totals
```

(`Dict` and `Optional` are already imported at the top of this file —
no new imports needed.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_history.py -v`
Expected: PASS — all tests, including the 3 new ones.

- [ ] **Step 5: Commit**

(Per this plan's Global Constraints, no commit is run here — the final
task hands over the git steps.)

---

### Task 2: Generalize `last_14_days` into `last_n_days`

**Files:**
- Modify: `lock_in/tier5/_shared.py`
- Modify: `lock_in/tier5/v3.py`
- Modify: `tests/test_tier5_shared.py`
- Modify: `tests/test_tier5_v3.py`

**Interfaces:**
- Produces: `last_n_days(totals: dict[str, int], today: date, n: int) -> list[tuple[date, int]]`
  in `lock_in.tier5._shared`. V3's `build()` (already exists) and
  Task 6's `decade.py` both consume it.

- [ ] **Step 1: Write the failing tests**

In `tests/test_tier5_shared.py`, add (near the top, alongside the
existing `format_hm` tests):

```python
from datetime import date

from lock_in.tier5._shared import format_hm, last_n_days


def test_last_n_days_returns_exactly_n_entries():
    result = last_n_days({}, date(2026, 9, 14), 14)
    assert len(result) == 14


def test_last_n_days_is_oldest_to_newest_ending_today():
    result = last_n_days({}, date(2026, 9, 14), 14)
    assert result[0][0] == date(2026, 9, 1)
    assert result[-1][0] == date(2026, 9, 14)


def test_last_n_days_fills_missing_days_with_zero():
    totals = {"2026-09-14": 1200}
    result = last_n_days(totals, date(2026, 9, 14), 14)
    assert result[-1] == (date(2026, 9, 14), 1200)
    assert result[0] == (date(2026, 9, 1), 0)


def test_last_n_days_crosses_a_month_boundary():
    result = last_n_days({}, date(2026, 3, 5), 14)
    assert result[0][0] == date(2026, 2, 20)
    assert result[-1][0] == date(2026, 3, 5)


def test_last_n_days_crosses_a_year_boundary():
    result = last_n_days({}, date(2026, 1, 3), 14)
    assert result[0][0] == date(2025, 12, 21)
    assert result[-1][0] == date(2026, 1, 3)


def test_last_n_days_returns_30_entries_for_decades_window():
    result = last_n_days({}, date(2026, 9, 14), 30)
    assert len(result) == 30
    assert result[0][0] == date(2026, 8, 16)
    assert result[-1][0] == date(2026, 9, 14)
```

(This file already has `from lock_in.tier5._shared import format_hm` at
the top from the previous plan — change that line to the combined
import shown above instead of adding a second import line.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tier5_shared.py -k last_n_days -v`
Expected: FAIL — `ImportError: cannot import name 'last_n_days' from 'lock_in.tier5._shared'`

- [ ] **Step 3: Write the minimal implementation**

In `lock_in/tier5/_shared.py`, add `from datetime import date, timedelta`
to the imports, then add this function after `format_hm`:

```python
def last_n_days(totals: dict[str, int], today: date, n: int) -> list[tuple[date, int]]:
    """n entries, oldest -> newest, ending on `today`. A day absent
    from `totals` (no focus blocks that day) contributes 0 seconds --
    the chart always has exactly n bars, even on a brand new install."""
    return [
        (day, totals.get(day.isoformat(), 0))
        for day in (today - timedelta(days=offset) for offset in range(n - 1, -1, -1))
    ]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_tier5_shared.py -v`
Expected: PASS — all tests, including the 6 new ones.

- [ ] **Step 5: Point `v3.py` at `last_n_days` and remove `last_14_days`**

In `lock_in/tier5/v3.py`, replace:

```python
from .. import visuals
from ._shared import format_hm


def last_14_days(totals: dict[str, int], today: date) -> list[tuple[date, int]]:
    """14 entries, oldest -> newest, ending on `today`. A day absent
    from `totals` (no focus blocks that day) contributes 0 seconds --
    the chart always has 14 bars, even on a brand new install."""
    return [
        (day, totals.get(day.isoformat(), 0))
        for day in (today - timedelta(days=offset) for offset in range(13, -1, -1))
    ]
```

with:

```python
from .. import visuals
from ._shared import format_hm, last_n_days
```

Then find the one call site in `build()`:

```python
    day_values = [(day.isoformat(), secs) for day, secs in last_14_days(totals, today)]
```

Replace it with:

```python
    day_values = [(day.isoformat(), secs) for day, secs in last_n_days(totals, today, 14)]
```

`v3.py` no longer uses `timedelta` directly (only `last_n_days` inside
`_shared.py` does now) — remove `timedelta` from
`from datetime import date, timedelta` at the top of `v3.py`, leaving
just `from datetime import date`.

- [ ] **Step 6: Move `test_tier5_v3.py`'s `last_14_days` tests out**

`last_14_days` was V3's only pure function, and it just generalized away
into `_shared.py`'s `last_n_days` (tested in `tests/test_tier5_shared.py`
as of Step 1 above). Replace the entire contents of
`tests/test_tier5_v3.py` with:

```python
"""
V3's `last_14_days()` generalized into `tier5/_shared.py`'s
`last_n_days()` once Decade also needed a windowed day-list (see
docs/superpowers/specs/2026-09-14-tier5-decade-analytics-design.md) --
its tests moved to tests/test_tier5_shared.py along with it. Nothing
V3-specific is left to unit-test right now; build() is manually
verified in the running app, same as every other Tier 5 Rider's tab.
"""
```

(A docstring-only file, zero test functions — pytest collects it
without error and reports zero tests from it. Left in place rather than
deleted, so the next person who adds a V3-specific pure function has an
obvious home for its tests instead of wondering where V3's test file
went.)

- [ ] **Step 7: Run the full test suite**

Run: `pytest -v`
Expected: PASS — same total count as before this task (11 tests moved
files: 5 renamed/re-homed, 6 brand new for the `n=30` and `n=14`
combined coverage — check the exact delta matches what Step 1 added).
`grep last_14_days lock_in/tier5/v3.py tests/test_tier5_v3.py` should
find nothing.

- [ ] **Step 8: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 3: Move `resolve_task_name` to `_shared.py`

**Files:**
- Modify: `lock_in/tier5/_shared.py`
- Modify: `lock_in/tier5/den_o.py`
- Modify: `tests/test_tier5_shared.py`
- Modify: `tests/test_tier5_den_o.py`

**Interfaces:**
- Produces: `resolve_task_name(task_id: Optional[str], tasks: TaskStore) -> str`
  in `lock_in.tier5._shared`. `den_o.py` (already exists) and Task 4's
  `decade.py` both consume it.

- [ ] **Step 1: Write the failing tests**

In `tests/test_tier5_shared.py`, add:

```python
from lock_in.tasks import TaskStore
from lock_in.tier5._shared import format_hm, last_n_days, resolve_task_name


def test_resolve_task_name_is_no_task_for_none(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    assert resolve_task_name(None, tasks) == "No task"


def test_resolve_task_name_returns_the_real_name(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    task = tasks.add("Write the Tier 5 spec")
    assert resolve_task_name(task.id, tasks) == "Write the Tier 5 spec"


def test_resolve_task_name_is_deleted_task_for_a_dangling_id(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    assert resolve_task_name("no-such-id", tasks) == "Deleted task"
```

(Combine this with the existing `from lock_in.tier5._shared import
format_hm, last_n_days` line from Task 2 into one import line, as shown.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tier5_shared.py -k resolve_task_name -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_task_name' from 'lock_in.tier5._shared'`

- [ ] **Step 3: Write the minimal implementation**

In `lock_in/tier5/_shared.py`, add `from typing import Optional` to the
imports and `from ..tasks import TaskStore` (this imports from
`lock_in.tasks`, outside the `tier5` package — not the circular shape
this file exists to avoid; only imports from `v3`/`den_o`/`decade`/
`tier5/__init__` would be). Then add:

```python
def resolve_task_name(task_id: Optional[str], tasks: TaskStore) -> str:
    """None -> 'No task'. A live task's id -> its real name. An id that
    doesn't match any task any more (the task was deleted after this
    block was logged) -> 'Deleted task', never a crash or a blank."""
    if task_id is None:
        return "No task"
    task = tasks.get(task_id)
    if task is None:
        return "Deleted task"
    return task.name
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_tier5_shared.py -v`
Expected: PASS — all tests, including the 3 new ones.

- [ ] **Step 5: Point `den_o.py` at the shared version**

In `lock_in/tier5/den_o.py`, replace:

```python
from ..history import SessionRecord
from ..tasks import TaskStore
from ._shared import format_hm
```

with:

```python
from ..history import SessionRecord
from ..tasks import TaskStore
from ._shared import format_hm, resolve_task_name
```

Then delete the whole `resolve_task_name` function definition (the
block starting `def resolve_task_name(task_id: Optional[str], tasks:
TaskStore) -> str:` and ending `return task.name`) — it's the same code,
now imported instead of defined locally.

Update this file's own module docstring line:

```
Four plain functions do the shaping (`resolve_task_name`,
`sorted_blocks`, `format_time_range`, `format_day_heading`) -- tested
```

to:

```
Three plain functions do the shaping (`sorted_blocks`,
`format_time_range`, `format_day_heading`) -- tested
```

- [ ] **Step 6: Move `test_tier5_den_o.py`'s `resolve_task_name` tests out**

In `tests/test_tier5_den_o.py`, remove `resolve_task_name` from the
`from lock_in.tier5.den_o import (...)` block (it's no longer defined
there — it now lives in, and is tested by, `tests/test_tier5_shared.py`
as added in Step 1 above), and delete these 3 test functions:
`test_resolve_task_name_is_no_task_for_none`,
`test_resolve_task_name_returns_the_real_name`,
`test_resolve_task_name_is_deleted_task_for_a_dangling_id`.

- [ ] **Step 7: Run the full test suite**

Run: `pytest -v`
Expected: PASS. `grep "def resolve_task_name" lock_in/tier5/den_o.py`
should find nothing.

- [ ] **Step 8: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 4: Decade's `ranked_tasks()`

**Files:**
- Create: `lock_in/tier5/decade.py` (pure function only in this task —
  `build()` comes in Task 6)
- Test: `tests/test_tier5_decade.py`

**Interfaces:**
- Consumes: `resolve_task_name` (Task 3), `TaskStore.get()` (already
  exists, used transitively).
- Produces: `ranked_tasks(totals_by_task: dict, tasks: TaskStore) -> list[tuple[str, int]]`
  in `lock_in.tier5.decade`. Task 6's `build()` calls this.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tier5_decade.py`:

```python
from lock_in.tasks import TaskStore
from lock_in.tier5.decade import ranked_tasks


def test_ranked_tasks_sorts_by_seconds_descending(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    t1 = tasks.add("Small task")
    t2 = tasks.add("Big task")
    totals = {t1.id: 300, t2.id: 1500}
    assert ranked_tasks(totals, tasks) == [("Big task", 1500), ("Small task", 300)]


def test_ranked_tasks_resolves_untagged_time_as_no_task(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    totals = {None: 600}
    assert ranked_tasks(totals, tasks) == [("No task", 600)]


def test_ranked_tasks_empty_input_returns_empty_list(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    assert ranked_tasks({}, tasks) == []


def test_ranked_tasks_keeps_two_deleted_tasks_as_separate_rows(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    totals = {"gone-1": 400, "gone-2": 900}
    result = ranked_tasks(totals, tasks)
    assert result == [("Deleted task", 900), ("Deleted task", 400)]


def test_ranked_tasks_caps_at_ten(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    totals = {f"task-{i}": (20 - i) * 60 for i in range(15)}
    result = ranked_tasks(totals, tasks)
    assert len(result) == 10
    # The 11th-highest (task-10, 10*60=600s) and everything smaller must
    # not appear -- only the top 10 by seconds do.
    assert all(seconds >= 11 * 60 for _, seconds in result)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tier5_decade.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.tier5.decade'`

- [ ] **Step 3: Write the minimal implementation**

Create `lock_in/tier5/decade.py`:

```python
"""
tier5/decade.py
================
Kamen Rider Decade's Tier 5 gimmick: an "Analytics" tab combining a
30-day version of V3's bar chart with a "Top tasks" ranking. The third
of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-14-tier5-decade-analytics-design.md.

`ranked_tasks()` does the one piece of shaping this Rider needs beyond
what V3 and Den-O already built and shared -- tested with no Tk, no
display server. `build()` is the only Tk-dependent piece; it's
screenshot-verified in the running app instead, matching every other
tab.
"""

from __future__ import annotations

from typing import Optional

from ..tasks import TaskStore
from ._shared import resolve_task_name


def ranked_tasks(
    totals_by_task: dict[Optional[str], int], tasks: TaskStore,
) -> list[tuple[str, int]]:
    """[(name, seconds), ...] sorted by seconds descending, capped at
    the top 10. Every task_id (including None, for untagged time) is
    resolved through resolve_task_name() -- two different tasks that
    were both later deleted show as two separate 'Deleted task' rows,
    never merged, since there's no way left to tell them apart by name."""
    resolved = [
        (resolve_task_name(task_id, tasks), seconds)
        for task_id, seconds in totals_by_task.items()
    ]
    resolved.sort(key=lambda pair: pair[1], reverse=True)
    return resolved[:10]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_tier5_decade.py -v`
Expected: PASS — all 5 tests.

- [ ] **Step 5: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 5: `tier5_effect="analytics_dashboard"` on Decade

**Files:**
- Modify: `lock_in/rider_themes.py`
- Test: `tests/test_rider_themes.py`

**Interfaces:**
- Produces: `RIDER_THEMES["Kamen Rider Decade (2009)"].tier5_effect ==
  "analytics_dashboard"`. Task 6's `TIER5_BUILDERS` and Task 7's `ui.py`
  wiring both key off this string.

- [ ] **Step 1: Update the failing test**

In `tests/test_rider_themes.py`, find:

```python
def test_exactly_these_two_riders_have_a_tier5_effect():
    from lock_in.rider_themes import RIDER_THEMES
    expected = {
        "Kamen Rider V3 (1973)": "hours_tab",
        "Kamen Rider Den-O (2007)": "timeline_view",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier5_effect == effect, name
    tier5_riders = {n for n, t in RIDER_THEMES.items() if t.tier5_effect != "none"}
    assert tier5_riders == set(expected)
```

Replace it with:

```python
def test_exactly_these_three_riders_have_a_tier5_effect():
    from lock_in.rider_themes import RIDER_THEMES
    expected = {
        "Kamen Rider V3 (1973)": "hours_tab",
        "Kamen Rider Den-O (2007)": "timeline_view",
        "Kamen Rider Decade (2009)": "analytics_dashboard",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier5_effect == effect, name
    tier5_riders = {n for n, t in RIDER_THEMES.items() if t.tier5_effect != "none"}
    assert tier5_riders == set(expected)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_rider_themes.py -k tier5 -v`
Expected: FAIL — Decade's `tier5_effect` is still `"none"`.

- [ ] **Step 3: Assign the effect**

In `lock_in/rider_themes.py`, find:

```python
    "Kamen Rider Decade (2009)": RiderTheme(
        "Heisei", 2009, ("#9e1447", "#f06292"), ("#1a1a1a", "#757575"),
    ),
```

Replace it with:

```python
    "Kamen Rider Decade (2009)": RiderTheme(
        "Heisei", 2009, ("#9e1447", "#f06292"), ("#1a1a1a", "#757575"),
        tier5_effect="analytics_dashboard",
    ),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_rider_themes.py -v`
Expected: PASS — all tests.

- [ ] **Step 5: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 6: `build()` — the Analytics tab, and registering it

**Files:**
- Modify: `lock_in/tier5/decade.py` (add `build()`)
- Modify: `lock_in/tier5/__init__.py` (register it)

**Interfaces:**
- Consumes: `ranked_tasks()` (Task 4), `last_n_days`/`format_hm` (Tasks
  2 and already-existing), `history.total_seconds_by_day()`/
  `.total_seconds_by_task()`/`.all()`, `visuals.make_hours_chart()`
  (already exists), `theme.primary`/`.secondary`/`.era`/
  `.primary_text_pair` (already exist).
- Produces: `build(parent, *, history, tasks, theme, appearance_mode) ->
  None` in `lock_in.tier5.decade`, registered in
  `TIER5_BUILDERS["analytics_dashboard"]`.

No automated test for this step — same reasoning as V3's and Den-O's
`build()`. Task 8 covers manual verification.

- [ ] **Step 1: Add the needed imports and `build()` to `lock_in/tier5/decade.py`**

Replace:

```python
from ..tasks import TaskStore
from ._shared import resolve_task_name
```

with:

```python
from datetime import date

import customtkinter as ctk

from .. import visuals
from ..tasks import TaskStore
from ._shared import format_hm, last_n_days, resolve_task_name
```

Append to the end of the file:

```python
def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` with Decade's Analytics view: a 30-day bar chart
    (V3's renderer, a wider window), then a "Top tasks" ranking below
    it.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    if not history.all():
        ctk.CTkLabel(
            frame, text="No focus blocks yet. Finish one and it shows up here.",
            justify="left", wraplength=400,
        ).pack(anchor="w", pady=8)
        return

    totals_by_day = history.total_seconds_by_day()
    today = date.today()
    day_values = [(day.isoformat(), secs) for day, secs in last_n_days(totals_by_day, today, 30)]
    light_image = visuals.make_hours_chart(
        640, 200, day_values, theme.primary[0], theme.secondary[0],
        dark=False, era=theme.era,
    )
    dark_image = visuals.make_hours_chart(
        640, 200, day_values, theme.primary[1], theme.secondary[1],
        dark=True, era=theme.era,
    )
    chart_image = ctk.CTkImage(light_image=light_image, dark_image=dark_image, size=(640, 200))
    chart_label = ctk.CTkLabel(frame, text="", image=chart_image)
    # Same CTkImage-garbage-collection guard V3 uses -- see its build().
    chart_label._decade_chart_image = chart_image
    chart_label.pack(anchor="w")

    ctk.CTkLabel(
        frame, text="Last 30 days", text_color=("gray40", "gray60"),
        font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(6, 14))

    ctk.CTkLabel(
        frame, text="Top tasks", font=ctk.CTkFont(size=13, weight="bold"),
        text_color=theme.primary_text_pair,
    ).pack(anchor="w", pady=(0, 6))

    for name, seconds in ranked_tasks(history.total_seconds_by_task(), tasks):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=name, anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(row, text=format_hm(seconds), anchor="e").pack(side="right")
```

- [ ] **Step 2: Register it in `TIER5_BUILDERS`**

In `lock_in/tier5/__init__.py`, change:

```python
from . import den_o, v3

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
}
```

to:

```python
from . import decade, den_o, v3

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
    "analytics_dashboard": decade.build,
}
```

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `pytest -v`
Expected: PASS — every test from Tasks 1-5 plus the whole pre-existing
suite.

- [ ] **Step 4: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 7: Wire the tab label into `ui.py`

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `RIDER_THEMES["Kamen Rider Decade (2009)"].tier5_effect ==
  "analytics_dashboard"` (Task 5), `TIER5_BUILDERS["analytics_dashboard"]`
  (Task 6).

- [ ] **Step 1: Add the tab label**

In `lock_in/ui.py`, find:

```python
_TIER5_TAB_LABELS = {"hours_tab": "Hours", "timeline_view": "Timeline"}
```

Replace it with:

```python
_TIER5_TAB_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
}
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: PASS — same count as after Task 6.

- [ ] **Step 3: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 8: Docs — Help tab entry and README

**Files:**
- Modify: `lock_in/ui.py` (`_build_help_tab`)
- Modify: `README.md`

- [ ] **Step 1: Add Decade to the Help tab's Tier 5 section**

In `_build_help_tab()`, find:

```python
        bullet(
            "Den-O — a \"Timeline\" tab appears, listing one day's focus "
            "blocks at a time (earliest first), with buttons to flip a "
            "day forward or back. Each one shows its time, how long it "
            "ran, and which task it was for."
        )
        body(
            "More heroes will get a tab like this over time -- these two "
            "are just the first."
        )
```

Replace it with:

```python
        bullet(
            "Den-O — a \"Timeline\" tab appears, listing one day's focus "
            "blocks at a time (earliest first), with buttons to flip a "
            "day forward or back. Each one shows its time, how long it "
            "ran, and which task it was for."
        )
        bullet(
            "Decade — an \"Analytics\" tab appears: a 30-day version of "
            "V3's bar chart, plus your top 10 tasks by total time spent."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "three are just the first."
        )
```

- [ ] **Step 2: Add Decade to README's Tier 5 subsection**

In `README.md`, find:

```markdown
- **Den-O** — adds a "Timeline" tab: one day's focus blocks at a time,
  earliest first, with buttons to flip a day forward or back. Each block
  shows its time, how long it ran, whether it finished naturally or got
  cut short, and which task (if any) it was for.

More Riders will read your tasks and history this way over time — these
two are just the first of ten planned.
```

Replace it with:

```markdown
- **Den-O** — adds a "Timeline" tab: one day's focus blocks at a time,
  earliest first, with buttons to flip a day forward or back. Each block
  shows its time, how long it ran, whether it finished naturally or got
  cut short, and which task (if any) it was for.
- **Decade** — adds an "Analytics" tab: a 30-day version of V3's bar
  chart, plus your top 10 tasks ranked by how much total time you've
  spent on each.

More Riders will read your tasks and history this way over time — these
three are just the first of ten planned.
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: PASS — documentation-only changes.

- [ ] **Step 4: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 9: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire automated test suite**

Run: `pytest -v`
Expected: PASS — every test in the suite, old and new.

- [ ] **Step 2: Manually verify the running app**

Using the `run` skill (or `python main.py` directly), check:

1. Settings → Kamen Rider theme → pick "Kamen Rider Decade (2009)". An
   "Analytics" tab appears after Help.
2. On a fresh install, it shows only the empty-state message — no
   chart, no "Top tasks" heading.
3. With history logged across several tasks (including one untagged
   block and, ideally, one whose task has since been deleted), the
   chart renders at the wider 640×200 size with today's bar in
   `secondary`, and "Top tasks" lists them ranked correctly, "No task"
   and "Deleted task" included where they rank.
4. Log time against 11+ distinct tasks (or fake it via the same
   approach used for V3/Den-O's own verification) — exactly 10 rows
   show, the smallest omitted.
5. Both light and dark appearance modes render correctly.
6. Switching to a non-Tier-5 Rider, or turning on Standard Mode with
   Decade still selected, hides the tab; turning Standard Mode back off
   restores it.

- [ ] **Step 3: Report results**

Confirm to the user: full test count and pass/fail, and the outcome of
each manual check above. Do not run any git command.
