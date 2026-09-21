# Tier 5 Rider #2: Den-O Timeline View Implementation Plan

**Goal:** When Kamen Rider Den-O (2007) is the picked Rider, a "Timeline"
tab appears showing one calendar day's focus blocks at a time,
chronological, with Prev/Next day navigation — reading only
`HistoryStore.for_date()`/`.all()` and a new `earliest_date()`.

**Architecture:** Two small, generically-useful store additions
(`HistoryStore.earliest_date()`, `TaskStore.get()`). A shared formatting
helper (`format_hm`, used by both V3 and Den-O) moves out of `v3.py` into
a new dependency-free leaf module, `tier5/_shared.py`, avoiding a
circular import with `tier5/__init__.py`. Den-O's own pure functions
(`resolve_task_name`, `sorted_blocks`, `format_time_range`,
`format_day_heading`) live in `tier5/den_o.py` next to its `build()`.
Day-navigation state (which day is currently shown) lives entirely
inside `build()`'s own closure — no change to `ui.py`'s Tier 5 tab
mechanism, which already generically supports any registered effect.

**Tech Stack:** Python 3.11+, CustomTkinter, pytest. No Pillow needed —
Den-O is a row list, not a rendered image.

## Global Constraints

- Den-O is **read-only** — no editing or deleting a logged block from
  this view (that's Zi-O's job later).
- **Plain calendar-flip navigation only** — Prev/Next always move
  exactly one day, whether or not that day has any blocks. No
  skip-to-nearest-day-with-data behavior.
- `SessionRecord.completed` is the *only* signal available — never
  present a block as "skipped" vs. "reset" specifically, only "finished"
  vs. "ended early."
- Time-of-day is always formatted `%H:%M` (24-hour), matching the
  Activity tab's existing convention — no new time format introduced.
- No `%-d`/`%#d` in any `strftime` call (platform-specific extensions) —
  use `date.day` for the un-padded day number instead.
- No module in `lock_in/tier5/` may import from `lock_in/ui.py`, and
  `tier5/__init__.py`'s own `from . import v3` / `from . import den_o`
  must not be relied upon by any Rider module for a name it needs (see
  Task 3 and Task 6 for the two places this already almost happened).
- No new `HistoryStore` write method, no new config field — this is a
  read-only view over data that already exists.
- No git commit, tag, or push is executed as part of any task in this
  plan — every step stops at "write the file" / "run the tests". The
  final task hands the exact commands to the user to run themselves.

---

### Task 1: `HistoryStore.earliest_date()`

**Files:**
- Modify: `lock_in/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Produces: `HistoryStore.earliest_date() -> Optional[date]`. Task 7's
  `den_o.py` calls this to bound `← Prev`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_history.py` (after `test_total_seconds_by_day_sums_same_day_records`):

```python
def test_earliest_date_is_none_for_an_empty_store(store):
    assert store.earliest_date() is None


def test_earliest_date_is_the_only_day_with_one_record(store):
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    assert store.earliest_date() == date(2026, 9, 4)


def test_earliest_date_is_the_minimum_across_out_of_order_records(store):
    store.record(_record(datetime(2026, 9, 10, 9, 0, 0), 1500))
    store.record(_record(datetime(2026, 9, 4, 9, 0, 0), 1500))
    store.record(_record(datetime(2026, 9, 7, 9, 0, 0), 1500))
    assert store.earliest_date() == date(2026, 9, 4)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_history.py -k earliest_date -v`
Expected: FAIL — `AttributeError: 'HistoryStore' object has no attribute 'earliest_date'`

- [ ] **Step 3: Write the minimal implementation**

In `lock_in/history.py`, add this method to `HistoryStore` (after
`total_seconds_by_day`):

```python
    def earliest_date(self) -> Optional[date]:
        """The calendar day of the very first record ever logged, or
        None if nothing has been logged yet -- backs how far back Den-O's
        Prev-day button can go."""
        if not self._records:
            return None
        return min(datetime.fromisoformat(r.start).date() for r in self._records)
```

(`date`, `datetime`, and `Optional` are already imported at the top of
this file — no new imports needed.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_history.py -v`
Expected: PASS — all tests, including the 3 new ones.

- [ ] **Step 5: Commit**

(Per this plan's Global Constraints, no commit is run here — the final
task hands over the git steps.)

---

### Task 2: `TaskStore.get()`

**Files:**
- Modify: `lock_in/tasks.py`
- Test: `tests/test_tasks.py`

**Interfaces:**
- Produces: `TaskStore.get(task_id: str) -> Optional[Task]`. Task 5's
  `resolve_task_name()` calls this.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tasks.py` (near the other `all()`/`open()`/`done()`
tests):

```python
def test_get_returns_the_matching_task(store):
    task = store.add("Write the Tier 5 spec")
    assert store.get(task.id) is task


def test_get_returns_none_for_an_unknown_id(store):
    assert store.get("does-not-exist") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tasks.py -k "test_get_returns" -v`
Expected: FAIL — `AttributeError: 'TaskStore' object has no attribute 'get'`

- [ ] **Step 3: Write the minimal implementation**

In `lock_in/tasks.py`, add this method to `TaskStore` (next to `all()`):

```python
    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_tasks.py -v`
Expected: PASS — all tests, including the 2 new ones.

- [ ] **Step 5: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 3: Move `format_hm` to its own leaf module

**Files:**
- Create: `lock_in/tier5/_shared.py`
- Modify: `lock_in/tier5/v3.py`
- Create: `tests/test_tier5_shared.py`
- Modify: `tests/test_tier5_v3.py`

**Interfaces:**
- Produces: `format_hm(seconds: int) -> str` in `lock_in.tier5._shared`.
  Task 7's `den_o.py` and the already-existing `v3.py` both consume it.

This has to happen *before* Den-O is built (Task 7), so both Riders read
from the same place from day one instead of Den-O briefly importing a
private name out of `v3.py`.

- [ ] **Step 1: Write the failing test for the new home**

Create `tests/test_tier5_shared.py`:

```python
from lock_in.tier5._shared import format_hm


def test_format_hm_zero_seconds():
    assert format_hm(0) == "0m"


def test_format_hm_minutes_only():
    assert format_hm(600) == "10m"


def test_format_hm_hours_and_minutes():
    assert format_hm(9000) == "2h 30m"


def test_format_hm_exact_hour_still_shows_minutes():
    assert format_hm(3600) == "1h 0m"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_tier5_shared.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.tier5._shared'`

- [ ] **Step 3: Create `_shared.py`**

Create `lock_in/tier5/_shared.py`:

```python
"""
tier5/_shared.py
=================
Small formatting helpers shared by more than one Tier 5 Rider module.

Kept in its own leaf module with NO imports from anywhere else in
tier5/ (not even tier5/__init__.py) on purpose: __init__.py does
`from . import v3` / `from . import den_o` to build TIER5_BUILDERS, so
if a Rider module imported a shared helper back out of __init__.py,
that would be a circular import. Importing from _shared.py instead
means tier5/__init__.py's own import order never matters to any Rider
module -- see
docs/superpowers/specs/2026-09-14-tier5-deno-timeline-design.md.
"""

from __future__ import annotations


def format_hm(seconds: int) -> str:
    """3900 -> '1h 5m'; 600 -> '10m'; 0 -> '0m'. Hours are only shown at
    all once there's at least one -- an under-an-hour total never shows
    a redundant '0h'."""
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
```

- [ ] **Step 4: Run the new test to verify it passes**

Run: `pytest tests/test_tier5_shared.py -v`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Point `v3.py` at the new home and remove the old one**

In `lock_in/tier5/v3.py`, replace this:

```python
from .. import visuals


def last_14_days(totals: dict[str, int], today: date) -> list[tuple[date, int]]:
```

with:

```python
from .. import visuals
from ._shared import format_hm


def last_14_days(totals: dict[str, int], today: date) -> list[tuple[date, int]]:
```

Then delete the whole `_format_hm` function (the block starting
`def _format_hm(seconds: int) -> str:` and ending at `return f"{minutes}m"`,
right after `last_14_days`).

Finally, in `build()`, change the one call site:

```python
        frame, text=_format_hm(headline_seconds), text_color=theme.primary_text_pair,
```

to:

```python
        frame, text=format_hm(headline_seconds), text_color=theme.primary_text_pair,
```

- [ ] **Step 6: Remove the now-duplicate tests from `test_tier5_v3.py`**

In `tests/test_tier5_v3.py`, change the import line from:

```python
from lock_in.tier5.v3 import _format_hm, last_14_days
```

to:

```python
from lock_in.tier5.v3 import last_14_days
```

Then delete these 4 test functions (they now live in
`tests/test_tier5_shared.py`, Step 1 above):
`test_format_hm_zero_seconds`, `test_format_hm_minutes_only`,
`test_format_hm_hours_and_minutes`, `test_format_hm_exact_hour_still_shows_minutes`.

- [ ] **Step 7: Run the full test suite**

Run: `pytest -v`
Expected: PASS — same total count as before this task (4 tests moved
files, none were added or lost), and `lock_in/tier5/v3.py` still has no
`_format_hm` left in it (`grep _format_hm lock_in/tier5/v3.py` should
find nothing).

- [ ] **Step 8: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 4: Den-O's pure functions

**Files:**
- Create: `lock_in/tier5/den_o.py` (pure functions only in this task —
  `build()` comes in Task 7)
- Test: `tests/test_tier5_den_o.py`

**Interfaces:**
- Consumes: `TaskStore.get()` (Task 2), `SessionRecord` (already exists
  in `lock_in.history`).
- Produces: `resolve_task_name(task_id, tasks) -> str`,
  `sorted_blocks(records) -> list[SessionRecord]`,
  `format_time_range(start_iso, end_iso) -> str`,
  `format_day_heading(day) -> str`, all in `lock_in.tier5.den_o`. Task 7's
  `build()` calls all four.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tier5_den_o.py`:

```python
from datetime import date

from lock_in.history import SessionRecord
from lock_in.tasks import TaskStore
from lock_in.tier5.den_o import (
    format_day_heading,
    format_time_range,
    resolve_task_name,
    sorted_blocks,
)


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


def _rec(start, end):
    return SessionRecord(start=start, end=end, duration_seconds=1, task_id=None, completed=True)


def test_sorted_blocks_orders_earliest_first():
    late = _rec("2026-09-14T14:00:00", "2026-09-14T14:10:00")
    early = _rec("2026-09-14T09:00:00", "2026-09-14T09:10:00")
    assert sorted_blocks([late, early]) == [early, late]


def test_sorted_blocks_handles_an_empty_list():
    assert sorted_blocks([]) == []


def test_format_time_range_formats_hh_mm():
    result = format_time_range("2026-09-14T09:00:00", "2026-09-14T09:25:00")
    assert result == "09:00–09:25"


def test_format_day_heading_matches_expected_string():
    assert format_day_heading(date(2026, 9, 12)) == "Saturday, September 12"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tier5_den_o.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.tier5.den_o'`

- [ ] **Step 3: Write the minimal implementation**

Create `lock_in/tier5/den_o.py`:

```python
"""
tier5/den_o.py
===============
Kamen Rider Den-O's Tier 5 gimmick: a new "Timeline" tab showing one
calendar day's focus blocks at a time, chronological, with Prev/Next
day navigation. The second of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-14-tier5-deno-timeline-design.md.

Four plain functions do the shaping (`resolve_task_name`,
`sorted_blocks`, `format_time_range`, `format_day_heading`) -- tested
with no Tk, no display server, same as every pure-logic module in this
codebase. `build()` is the only Tk-dependent piece, including the one
bit of state (which day is currently shown) any Tier 5 Rider has needed
so far -- it lives entirely in build()'s own closure, never touching
ui.py. `build()` itself is screenshot-verified in the running app
instead, matching how every other tab is verified.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from ..history import SessionRecord
from ..tasks import TaskStore


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


def sorted_blocks(records: list[SessionRecord]) -> list[SessionRecord]:
    """`records`, earliest-`start`-first. HistoryStore.for_date() filters
    but doesn't sort -- Den-O sorts explicitly rather than trusting
    JSONL append order."""
    return sorted(records, key=lambda r: r.start)


def format_time_range(start_iso: str, end_iso: str) -> str:
    """'2026-09-14T09:00:00', '2026-09-14T09:25:00' -> '09:00-09:25',
    the same 24-hour %H:%M format the Activity tab already uses."""
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    return f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"


def format_day_heading(day: date) -> str:
    """date(2026, 9, 12) -> 'Saturday, September 12'. Built from `.day`
    instead of a %-d/%#d strftime code -- those are platform-specific
    (glibc vs. MSVCRT) and this app runs on Windows, macOS, and Linux
    from one codebase."""
    return f"{day.strftime('%A, %B')} {day.day}"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_tier5_den_o.py -v`
Expected: PASS — all 7 tests.

- [ ] **Step 5: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 5: `tier5_effect="timeline_view"` on Den-O

**Files:**
- Modify: `lock_in/rider_themes.py`
- Test: `tests/test_rider_themes.py`

**Interfaces:**
- Produces: `RIDER_THEMES["Kamen Rider Den-O (2007)"].tier5_effect ==
  "timeline_view"`. Task 6's `TIER5_BUILDERS` and Task 7's `ui.py`
  wiring both key off this string.

- [ ] **Step 1: Update the failing test**

In `tests/test_rider_themes.py`, find:

```python
def test_v3_has_the_hours_tab_tier5_effect():
    from lock_in.rider_themes import RIDER_THEMES
    assert RIDER_THEMES["Kamen Rider V3 (1973)"].tier5_effect == "hours_tab"
    tier5_riders = {n for n, t in RIDER_THEMES.items() if t.tier5_effect != "none"}
    assert tier5_riders == {"Kamen Rider V3 (1973)"}
```

Replace it with:

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

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_rider_themes.py -k tier5 -v`
Expected: FAIL — `assert RIDER_THEMES["Kamen Rider Den-O (2007)"].tier5_effect == "timeline_view"` fails because it's still `"none"`.

- [ ] **Step 3: Assign the effect**

In `lock_in/rider_themes.py`, find:

```python
    "Kamen Rider Den-O (2007)": RiderTheme(
        "Heisei", 2007, ("#9c1e1e", "#ef5350"), ("#90a4ae", "#eceff1"),
    ),
```

Replace it with:

```python
    "Kamen Rider Den-O (2007)": RiderTheme(
        "Heisei", 2007, ("#9c1e1e", "#ef5350"), ("#90a4ae", "#eceff1"),
        tier5_effect="timeline_view",
    ),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_rider_themes.py -v`
Expected: PASS — all tests.

- [ ] **Step 5: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 6: `build()` — the Timeline tab, and registering it

**Files:**
- Modify: `lock_in/tier5/den_o.py` (add `build()`)
- Modify: `lock_in/tier5/__init__.py` (register it)

**Interfaces:**
- Consumes: everything from Task 4 (`resolve_task_name`, `sorted_blocks`,
  `format_time_range`, `format_day_heading`), `format_hm` (Task 3),
  `history.earliest_date()` (Task 1), `history.for_date()`/`.all()`
  (already exist), `theme.primary_text_pair` (already exists).
- Produces: `build(parent, *, history, tasks, theme, appearance_mode) ->
  None` in `lock_in.tier5.den_o`, registered in
  `TIER5_BUILDERS["timeline_view"]`. Task 7's `ui.py` wiring calls
  `TIER5_BUILDERS[effect](...)` exactly as it already does for V3 — no
  change needed there.

No automated test for this step — same reasoning as V3's `build()`: it
only builds Tk widgets, and this codebase verifies tab-building methods
by running the real app. Task 8 covers manual verification.

- [ ] **Step 1: Add the three color constants and `build()` to `lock_in/tier5/den_o.py`**

Add these two things: three module-level constants right after the
imports, and `build()` at the end of the file.

After the `from ..tasks import TaskStore` line, add:

```python
import customtkinter as ctk

from ._shared import format_hm

# Same hex values as ui.py's COLOR_BREAK / COLOR_WARN / COLOR_IDLE --
# not imported from there, since ui.py imports TIER5_BUILDERS FROM the
# tier5 package, so a Rider module importing color constants back out
# of ui.py would be circular. Kept as local constants with this
# cross-reference so the app's "green = good, amber = caution" language
# stays visually consistent without a code dependency in either
# direction.
_COMPLETED_COLOR = "#2f9e5f"
_ENDED_EARLY_COLOR = "#e0a800"
_MUTED_COLOR = "#5a6472"
```

Append to the end of the file:

```python
def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` with Den-O's Timeline view: one calendar day's
    focus blocks at a time, earliest first, with Prev/Next day buttons.

    All of the day-navigation state (which day is currently shown)
    lives right here, in this function's own closure -- ui.py and
    TIER5_BUILDERS never see it and don't need to.
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

        for record in blocks:
            dot_color = _COMPLETED_COLOR if record.completed else _ENDED_EARLY_COLOR
            row = ctk.CTkFrame(rows_frame, border_width=1, border_color=dot_color)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(
                row, text="●", text_color=dot_color, width=20,
                font=ctk.CTkFont(size=14),
            ).pack(side="left", padx=(10, 0))

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            title = (
                f"{format_time_range(record.start, record.end)} · "
                f"{format_hm(record.duration_seconds)}"
            )
            ctk.CTkLabel(
                left, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w")
            ctk.CTkLabel(
                left, text=resolve_task_name(record.task_id, tasks), anchor="w",
                font=ctk.CTkFont(size=10), text_color=_MUTED_COLOR,
            ).pack(anchor="w")

    def go(delta: int) -> None:
        state["day"] += timedelta(days=delta)
        render_day()

    prev_button.configure(command=lambda: go(-1))
    next_button.configure(command=lambda: go(1))
    render_day()
```

- [ ] **Step 2: Register it in `TIER5_BUILDERS`**

In `lock_in/tier5/__init__.py`, change:

```python
from . import v3

TIER5_BUILDERS = {
    "hours_tab": v3.build,
}
```

to:

```python
from . import den_o, v3

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
}
```

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `pytest -v`
Expected: PASS — every test from Tasks 1-5 plus the whole pre-existing
suite. (No new automated tests in this task; `build()` is manually
verified in Task 8.)

- [ ] **Step 4: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 7: Wire the tab label into `ui.py`

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `RIDER_THEMES["Kamen Rider Den-O (2007)"].tier5_effect ==
  "timeline_view"` (Task 5), `TIER5_BUILDERS["timeline_view"]` (Task 6).
- Produces: nothing new consumed by a later task — this is the only
  `ui.py` change this Rider needs, since `_build_tabs()` /
  `_build_tier5_tab()` (built for V3) are already fully generic over
  whatever `_TIER5_TAB_LABELS` and `TIER5_BUILDERS` contain.

- [ ] **Step 1: Add the tab label**

In `lock_in/ui.py`, find:

```python
_TIER5_TAB_LABELS = {"hours_tab": "Hours"}
```

Replace it with:

```python
_TIER5_TAB_LABELS = {"hours_tab": "Hours", "timeline_view": "Timeline"}
```

That's the entire `ui.py` change for this Rider — `_build_tabs()`,
`_build_tier5_tab()`, and the `_on_phase_ended()` refresh hook already
read `self.current_tier5_effect` and `_TIER5_TAB_LABELS` generically; none
of them hardcode `"hours_tab"`.

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: PASS — same count as after Task 6 (this is a one-line change
with no new automated test; Task 8 covers manual verification).

- [ ] **Step 3: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 8: Docs — Help tab entry and README

**Files:**
- Modify: `lock_in/ui.py` (`_build_help_tab`)
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing (pure documentation, no behavior change).
- Produces: nothing consumed by a later task.

- [ ] **Step 1: Add Den-O to the Help tab's Tier 5 section**

In `_build_help_tab()`, find the Tier 5 block added for V3:

```python
        # --- Tier 5 -------------------------------------------------------- #
        heading("5. One hero reads your own history", COLOR_ENFORCE_ACCENT)
        body(
            "Something new, separate from the display tricks above: pick "
            "this hero and an extra tab appears next to Help, built from "
            "your own past focus blocks instead of just changing colors "
            "or sounds."
        )
        bullet(
            "V3 — an \"Hours\" tab appears, showing how long you've "
            "focused today plus a bar chart of the last 14 days. Every "
            "block counts toward it, finished or not."
        )
        body(
            "More heroes will get a tab like this over time -- V3 is "
            "just the first."
        )
```

Replace the heading text and the closing `body(...)`, and add a Den-O
bullet after V3's:

```python
        # --- Tier 5 -------------------------------------------------------- #
        heading("5. Some heroes read your own history", COLOR_ENFORCE_ACCENT)
        body(
            "Something new, separate from the display tricks above: pick "
            "one of these heroes and an extra tab appears next to Help, "
            "built from your own past focus blocks instead of just "
            "changing colors or sounds."
        )
        bullet(
            "V3 — an \"Hours\" tab appears, showing how long you've "
            "focused today plus a bar chart of the last 14 days. Every "
            "block counts toward it, finished or not."
        )
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

- [ ] **Step 2: Add Den-O to README's Tier 5 subsection**

In `README.md`, find:

```markdown
### Tier 5: Riders that read your own history

A new kind of Rider gimmick, separate from every tier above: picking one
of these Riders adds a whole new tab next to Help, built from your own
tasks and past focus blocks instead of just changing colors, sounds, or
behavior.

- **V3** — adds an "Hours" tab: a big number showing how long you've
  focused today, plus a simple bar chart of the last 14 days. Every
  block counts toward it, whether you finished it, skipped it, or reset
  it early.

More Riders will read your tasks and history this way over time — V3 is
the first of ten planned.
```

Replace it with:

```markdown
### Tier 5: Riders that read your own history

A new kind of Rider gimmick, separate from every tier above: picking one
of these Riders adds a whole new tab next to Help, built from your own
tasks and past focus blocks instead of just changing colors, sounds, or
behavior.

- **V3** — adds an "Hours" tab: a big number showing how long you've
  focused today, plus a simple bar chart of the last 14 days. Every
  block counts toward it, whether you finished it, skipped it, or reset
  it early.
- **Den-O** — adds a "Timeline" tab: one day's focus blocks at a time,
  earliest first, with buttons to flip a day forward or back. Each block
  shows its time, how long it ran, whether it finished naturally or got
  cut short, and which task (if any) it was for.

More Riders will read your tasks and history this way over time — these
two are just the first of ten planned.
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: PASS — documentation-only changes, no test should be affected.

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

1. Settings → Kamen Rider theme → pick "Kamen Rider Den-O (2007)". A
   "Timeline" tab appears after Help (and after Hours, if a Tier 5 Rider
   was already selected — only one Tier 5 tab exists at a time).
2. On a day with several logged blocks, they show earliest-first, each
   with the right time range, duration, task name (or "No task" /
   "Deleted task" for a block whose task was later removed), and a
   green dot for a finished block vs. an amber dot for one that ended
   early.
3. Click `< Prev` repeatedly back to the very first day you ever logged
   anything — the button disables exactly there, not one day earlier or
   later.
4. Click `Next >` forward back up to today — it disables at today, and
   clicking it never shows a future day.
5. Navigate to an ordinary day in the middle of your history with zero
   blocks (a real day off) — see "No focus blocks on this day.", with
   both Prev and Next still correctly enabled/disabled by date, not by
   whether that day has data.
6. Finish a focus block while the Timeline tab is open on a past day —
   the tab resets to show today (matching V3's same refresh behavior),
   not silently update the day you were browsing.
7. Switch to a Rider with no Tier 5 gimmick — the Timeline tab
   disappears. Turn on Standard Mode with Den-O still selected
   underneath — it stays gone. Turn Standard Mode back off — it's back.
8. Both light and dark appearance modes render correctly.

- [ ] **Step 3: Report results**

Confirm to the user: full test count and pass/fail, and the outcome of
each manual check above. Do not run any git command — hand over the
commit/tag/push steps as its own message, per this plan's Global
Constraints.
