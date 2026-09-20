# Tier 5 Riders #4 and #5: Zi-O History Editor + Blade Kanban Board Implementation Plan

**Goal:** When Kamen Rider Zi-O (2018) is picked, a "History" tab shows
Den-O's day-by-day block list with the power to reassign a block's task
or delete it. When Kamen Rider Blade (2004) is picked, a "Board" tab
shows all tasks as three columns (To Do / In Progress / Done) with a
"→" button to advance a task one column. Both ship together as v2.5.4.

**Architecture:** Zi-O needs a real data-model change (`SessionRecord`
gains a stable `id`, with a one-time automatic migration for existing
`sessions.jsonl` files) plus two new `HistoryStore` methods
(`reassign_task`, `delete`). Three functions currently living in
`den_o.py` (`sorted_blocks`, `format_time_range`, `format_day_heading`)
generalize into `tier5/_shared.py` so Zi-O can reuse them without
importing from a sibling Rider module — the same move Decade already
made for `resolve_task_name`. Blade needs **no data-model change at
all**: it's a pure second view over the same `TaskStore` the Tasks tab
already reads and writes, plus one small pure function
(`group_by_status`). Both Riders slot into the existing
`tier5_effect` / `TIER5_BUILDERS` / `_TIER5_TAB_LABELS` mechanism
exactly as V3, Den-O, and Decade already did — no change to that
mechanism itself.

**Tech Stack:** Python 3.11+, CustomTkinter, pytest.

**Changes made while building (the code blocks below show the first
draft):**
- Zi-O's task menu is built by a new small plain function,
  `build_reassign_choices()`, instead of looking tasks up by name. Two
  tasks can have the same name, and a name lookup would move the block
  to the wrong one. Duplicates now show as "Name", "Name (2)", and so on.
  It has its own tests in `tests/test_tier5_zi_o.py`.
- If the diary file can't be re-saved while old blocks are getting their
  ids, the app just keeps going (as the spec says). Reassign and Delete
  do not hide a failed save.
- Blade's button shows an arrow (→), as in the spec, not "->".
- Code comments and help text were rewritten in plainer words.

## Global Constraints

- Zi-O's editor changes **only** a block's `task_id` (reassign) or
  removes the whole block (delete) — start time, end time, and
  duration are never editable in this pass.
- Deleting a block requires two clicks: "Delete" flips in place to
  "Really delete?" + "Cancel". No popup window anywhere in this plan —
  this codebase has no popup-confirm-dialog pattern today, and this
  plan doesn't introduce one.
- Blade moves a task forward exactly one column via a "→" button —
  no drag-and-drop, no backward moves, no reordering within a column.
- No module in `lock_in/tier5/` may import from `lock_in/ui.py`, and
  nothing in `v3.py`/`den_o.py`/`decade.py`/`zi_o.py`/`blade.py` may
  import a name back out of `tier5/__init__.py` (the same
  circular-import shape already avoided twice in this tier).
- No Rider module imports pure-logic functions directly from a sibling
  Rider module — shared logic lives in `tier5/_shared.py`.
- **No git command is run while building this.** No commit, no push, no
  tag. The changes stay in the working folder, and the last task hands
  the maintainer the exact commands to review, commit, tag and push
  them by hand.
- Everything written for this change (code comments, help text, README,
  docs) uses short, plain words that a young child could follow.

---

### Task 1: `SessionRecord.id` + one-time migration

**Files:**
- Modify: `lock_in/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Produces: `SessionRecord.id: str` (auto-generated via
  `default_factory` if not supplied). `HistoryStore._rewrite()` — a
  private helper that writes every in-memory record back to
  `sessions.jsonl`. Task 2's `reassign_task()`/`delete()` both use it.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_history.py` (after the existing imports, `_record`
stays as-is — it already builds `SessionRecord` via keyword args, so it
picks up an auto-generated `id` for free with no changes needed):

```python
def test_new_records_get_an_auto_generated_id(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    assert record.id != ""
    store.record(record)
    assert store.all()[0].id == record.id


def test_load_backfills_a_missing_id_and_persists_it(tmp_path):
    path = tmp_path / "sessions.jsonl"
    legacy = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    raw = dataclasses.asdict(legacy)
    del raw["id"]
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    store = HistoryStore(path)
    assert store.all()[0].id != ""
    first_id = store.all()[0].id

    # The id must be STABLE now that load() rewrote the file with it --
    # reloading again must not generate a second, different id.
    store2 = HistoryStore(path)
    assert store2.all()[0].id == first_id


def test_load_leaves_an_existing_id_unchanged(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store.record(record)
    original_id = record.id
    store.load()
    assert store.all()[0].id == original_id
```

Add `import dataclasses` alongside the existing `import json` at the
top of the file if it isn't already there (it already is — this file's
`test_corrupt_line_is_skipped_not_fatal` already uses
`dataclasses.asdict`).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_history.py -k "auto_generated_id or backfill or leaves_an_existing_id" -v`
Expected: FAIL — `TypeError: __init__() missing 1 required positional argument: 'id'` (or similar — `SessionRecord` has no `id` field yet).

- [ ] **Step 3: Add the `id` field and the `_rewrite()` helper**

In `lock_in/history.py`, change the imports:

```python
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
```

to:

```python
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
```

Then change the `SessionRecord` dataclass:

```python
@dataclass
class SessionRecord:
    """One completed (or cut-short) focus block."""

    start: str                     # ISO timestamp, when the block began
    end: str                       # ISO timestamp, when it ended/was cut short
    duration_seconds: int
    task_id: Optional[str]         # None if no task was picked -- still logged
    completed: bool                # False if skipped or reset before time ran out
```

to (adding `id` last, since it's the only field with a default — a
dataclass can't have a no-default field after one that has one):

```python
@dataclass
class SessionRecord:
    """One completed (or cut-short) focus block."""

    start: str                     # ISO timestamp, when the block began
    end: str                       # ISO timestamp, when it ended/was cut short
    duration_seconds: int
    task_id: Optional[str]         # None if no task was picked -- still logged
    completed: bool                # False if skipped or reset before time ran out
    # Auto-generated for every NEW record. Older sessions.jsonl lines
    # written before this field existed get one backfilled the first
    # time they're loaded -- see HistoryStore.load().
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
```

Then replace `HistoryStore.load()`:

```python
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
```

with:

```python
    def load(self) -> None:
        """Read every line, skipping any that's broken rather than
        failing. A line with no "id" key (written before ids existed)
        gets one backfilled here; if that happened at least once, the
        whole file is rewritten afterward so the same ids are stable on
        every later load, not regenerated fresh each time."""
        self._records.clear()
        if not self.path.exists():
            return
        backfilled = False
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        continue
                    if "id" not in raw:
                        backfilled = True
                    self._records.append(SessionRecord(**raw))
                except (json.JSONDecodeError, TypeError):
                    continue
        except OSError:
            return
        if backfilled:
            self._rewrite()

    def _rewrite(self) -> None:
        """Writes every in-memory record back to disk, in their current
        order. Used by load()'s one-time id-backfill migration and by
        reassign_task()/delete() -- the only three places this file's
        append-only shape is deliberately broken."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(asdict(r), ensure_ascii=False) for r in self._records]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_history.py -v`
Expected: PASS — all tests, including the 3 new ones. (Every existing
test still passes unchanged — `_record()` already builds via keyword
args, so it picks up the new `id` field automatically, and
`test_record_appends_and_is_readable_back`'s `store.all() == [record]`
still holds since it's the same object reference.)

- [ ] **Step 5: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 2: `HistoryStore.reassign_task()` and `HistoryStore.delete()`

**Files:**
- Modify: `lock_in/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: `HistoryStore._rewrite()` (Task 1).
- Produces: `HistoryStore.reassign_task(record_id: str, new_task_id: Optional[str]) -> bool`,
  `HistoryStore.delete(record_id: str) -> bool`. Task 5's `zi_o.py`
  `build()` calls both.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_history.py`:

```python
def test_reassign_task_changes_the_task_id(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123")
    store.record(record)
    assert store.reassign_task(record.id, "other") is True
    assert store.all()[0].task_id == "other"


def test_reassign_task_can_untag_to_none(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc123")
    store.record(record)
    store.reassign_task(record.id, None)
    assert store.all()[0].task_id is None


def test_reassign_task_returns_false_for_an_unknown_id(store):
    assert store.reassign_task("no-such-id", "abc123") is False


def test_reassign_task_leaves_other_records_untouched(store):
    a = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc")
    b = _record(datetime(2026, 9, 4, 10, 0, 0), 900, task_id="def")
    store.record(a)
    store.record(b)
    store.reassign_task(a.id, "changed")
    assert store.all()[1].task_id == "def"


def test_reassign_task_persists_across_a_reload(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store1 = HistoryStore(path)
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500, task_id="abc")
    store1.record(record)
    store1.reassign_task(record.id, "changed")
    store2 = HistoryStore(path)
    assert store2.all()[0].task_id == "changed"


def test_delete_removes_the_matching_record(store):
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store.record(record)
    assert store.delete(record.id) is True
    assert store.all() == []


def test_delete_returns_false_for_an_unknown_id(store):
    assert store.delete("no-such-id") is False


def test_delete_keeps_other_records_and_their_order(store):
    a = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    b = _record(datetime(2026, 9, 4, 10, 0, 0), 900)
    c = _record(datetime(2026, 9, 4, 11, 0, 0), 300)
    store.record(a)
    store.record(b)
    store.record(c)
    store.delete(b.id)
    assert [r.id for r in store.all()] == [a.id, c.id]


def test_delete_persists_across_a_reload(tmp_path):
    path = tmp_path / "sessions.jsonl"
    store1 = HistoryStore(path)
    record = _record(datetime(2026, 9, 4, 9, 0, 0), 1500)
    store1.record(record)
    store1.delete(record.id)
    store2 = HistoryStore(path)
    assert store2.all() == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_history.py -k "reassign_task or (delete and not corrupt)" -v`
Expected: FAIL — `AttributeError: 'HistoryStore' object has no attribute 'reassign_task'`.

- [ ] **Step 3: Write the minimal implementation**

In `lock_in/history.py`, add these two methods to `HistoryStore`, right
after `_rewrite()`:

```python
    def reassign_task(self, record_id: str, new_task_id: Optional[str]) -> bool:
        """Changes which task a past block is attributed to (None is a
        valid target -- "untag this block"). Never touches tasks.py --
        this is purely a history.py fact, matching the foundation
        spec's "the two stores never write to each other" rule."""
        for record in self._records:
            if record.id == record_id:
                record.task_id = new_task_id
                self._rewrite()
                return True
        return False

    def delete(self, record_id: str) -> bool:
        """Permanently removes one block. Returns whether a matching
        record was found."""
        for index, record in enumerate(self._records):
            if record.id == record_id:
                del self._records[index]
                self._rewrite()
                return True
        return False
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_history.py -v`
Expected: PASS — all tests, including the 9 new ones.

- [ ] **Step 5: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 3: Move `sorted_blocks`, `format_time_range`, `format_day_heading` to `_shared.py`

**Files:**
- Modify: `lock_in/tier5/_shared.py`
- Modify: `lock_in/tier5/den_o.py`
- Modify: `tests/test_tier5_shared.py`
- Modify: `tests/test_tier5_den_o.py`

**Interfaces:**
- Produces: `sorted_blocks(records: list[SessionRecord]) -> list[SessionRecord]`,
  `format_time_range(start_iso: str, end_iso: str) -> str`,
  `format_day_heading(day: date) -> str`, all in
  `lock_in.tier5._shared`. `den_o.py` (already exists) and Task 5's
  `zi_o.py` both consume them.

- [ ] **Step 1: Write the failing tests**

In `tests/test_tier5_shared.py`, change the import line:

```python
from lock_in.tasks import TaskStore
from lock_in.tier5._shared import format_hm, last_n_days, resolve_task_name
```

to:

```python
from lock_in.history import SessionRecord
from lock_in.tasks import TaskStore
from lock_in.tier5._shared import (
    format_day_heading, format_hm, format_time_range, last_n_days,
    resolve_task_name, sorted_blocks,
)
```

Then append (matching the assertions already in `tests/test_tier5_den_o.py`):

```python
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
    from datetime import date
    assert format_day_heading(date(2026, 9, 12)) == "Saturday, September 12"
```

(`date` is already imported at the top of this file from the existing
`last_n_days` tests — you can drop the inline `from datetime import
date` inside the test above and rely on the top-level import instead.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tier5_shared.py -k "sorted_blocks or format_time_range or format_day_heading" -v`
Expected: FAIL — `ImportError: cannot import name 'sorted_blocks' from 'lock_in.tier5._shared'`.

- [ ] **Step 3: Write the minimal implementation**

In `lock_in/tier5/_shared.py`, change the imports:

```python
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from ..tasks import TaskStore
```

to:

```python
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from ..history import SessionRecord
from ..tasks import TaskStore
```

Then append, after `resolve_task_name`:

```python
def sorted_blocks(records: list[SessionRecord]) -> list[SessionRecord]:
    """`records`, earliest-`start`-first. HistoryStore.for_date() filters
    but doesn't sort -- callers sort explicitly rather than trusting
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

Run: `pytest tests/test_tier5_shared.py -v`
Expected: PASS — all tests, including the 4 new ones.

- [ ] **Step 5: Point `den_o.py` at the shared versions and drop its own copies**

Replace the whole top of `lock_in/tier5/den_o.py`, from the module
docstring through the `format_day_heading` function (i.e. everything
before `def build(...)`), with:

```python
"""
tier5/den_o.py
===============
Kamen Rider Den-O's Tier 5 gimmick: a new "Timeline" tab showing one
calendar day's focus blocks at a time, chronological, with Prev/Next
day navigation. The second of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-14-tier5-deno-timeline-design.md.

`sorted_blocks`, `format_time_range`, and `format_day_heading` (like
`resolve_task_name` before them) have since moved to `tier5/_shared.py`
-- Zi-O needed the exact same day-view shaping to build its own history
editor on top of, see
docs/superpowers/specs/2026-09-17-tier5-zi-o-history-editor-design.md.
Nothing Den-O-specific is left to unit-test; `build()` is the only
piece left here, including the one bit of state (which day is
currently shown) any Tier 5 Rider has needed so far -- it lives
entirely in build()'s own closure, never touching ui.py. `build()`
itself is screenshot-verified in the running app instead, matching how
every other tab is verified.
"""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from ._shared import format_day_heading, format_hm, format_time_range, resolve_task_name, sorted_blocks

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

(This deletes `den_o.py`'s own `sorted_blocks`, `format_time_range`,
and `format_day_heading` definitions, and drops its now-unused
`from ..history import SessionRecord` / `from ..tasks import
TaskStore` / `from datetime import date, datetime, timedelta` imports
in favor of the trimmed set above — `build()` below still needs `date`
and `timedelta` directly, just not `datetime`, `SessionRecord`, or
`TaskStore`.)

Leave everything from `def build(parent, *, history, tasks, theme,
appearance_mode) -> None:` onward exactly as it is — `build()` itself
doesn't change at all, only the imports it relies on.

- [ ] **Step 6: Move `test_tier5_den_o.py`'s tests for the moved functions out**

Replace the whole contents of `tests/test_tier5_den_o.py` with:

```python
"""
sorted_blocks(), format_time_range(), and format_day_heading() moved to
tier5/_shared.py once Zi-O also needed them (see
docs/superpowers/specs/2026-09-17-tier5-zi-o-history-editor-design.md)
-- their tests moved to tests/test_tier5_shared.py along with them.
(resolve_task_name() made the same move earlier, for Decade.) Nothing
Den-O-specific is left to unit-test; build() is manually verified in
the running app, same as every other Tier 5 Rider's tab.
"""
```

(A docstring-only file, zero test functions — pytest collects it
without error and reports zero tests from it, matching how
`tests/test_tier5_v3.py` was left after its own function moved out.)

- [ ] **Step 7: Run the full test suite**

Run: `pytest -v`
Expected: PASS. `grep -n "def sorted_blocks\|def format_time_range\|def format_day_heading" lock_in/tier5/den_o.py`
should find nothing.

- [ ] **Step 8: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 4: `tier5_effect="history_editor"` on Zi-O

**Files:**
- Modify: `lock_in/rider_themes.py`
- Modify: `tests/test_rider_themes.py`

**Interfaces:**
- Produces: `RIDER_THEMES["Kamen Rider Zi-O (2018)"].tier5_effect ==
  "history_editor"`. Task 5's `TIER5_BUILDERS` and Task 6's `ui.py`
  wiring both key off this string.

- [ ] **Step 1: Update the failing test**

In `tests/test_rider_themes.py`, find `test_exactly_these_three_riders_have_a_tier5_effect`:

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

Replace it with:

```python
def test_exactly_these_four_riders_have_a_tier5_effect():
    from lock_in.rider_themes import RIDER_THEMES
    expected = {
        "Kamen Rider V3 (1973)": "hours_tab",
        "Kamen Rider Den-O (2007)": "timeline_view",
        "Kamen Rider Decade (2009)": "analytics_dashboard",
        "Kamen Rider Zi-O (2018)": "history_editor",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier5_effect == effect, name
    tier5_riders = {n for n, t in RIDER_THEMES.items() if t.tier5_effect != "none"}
    assert tier5_riders == set(expected)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_rider_themes.py -k tier5 -v`
Expected: FAIL — Zi-O's `tier5_effect` is still `"none"`.

- [ ] **Step 3: Assign the effect**

In `lock_in/rider_themes.py`, find:

```python
    "Kamen Rider Zi-O (2018)": RiderTheme(
        "Heisei", 2018, ("#1a1a1a", "#757575"), ("#9e1447", "#f06292"),
    ),
```

Replace it with:

```python
    "Kamen Rider Zi-O (2018)": RiderTheme(
        "Heisei", 2018, ("#1a1a1a", "#757575"), ("#9e1447", "#f06292"),
        tier5_effect="history_editor",
    ),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_rider_themes.py -v`
Expected: PASS — all tests.

- [ ] **Step 5: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 5: `zi_o.py` — the History tab, and registering it

**Files:**
- Create: `lock_in/tier5/zi_o.py`
- Modify: `lock_in/tier5/__init__.py`

**Interfaces:**
- Consumes: `format_day_heading`/`format_hm`/`format_time_range`/
  `resolve_task_name`/`sorted_blocks` (Task 3), `history.reassign_task()`/
  `.delete()` (Task 2), `history.for_date()`/`.earliest_date()`
  (already exist), `tasks.all()` (already exists).
- Produces: `build(parent, *, history, tasks, theme, appearance_mode) ->
  None` in `lock_in.tier5.zi_o`, registered in
  `TIER5_BUILDERS["history_editor"]`.

No automated test for this step — same reasoning as every other Tier 5
Rider's `build()`. Task 12 covers manual verification.

- [ ] **Step 1: Create `lock_in/tier5/zi_o.py`**

```python
"""
tier5/zi_o.py
==============
Kamen Rider Zi-O's Tier 5 gimmick: a "History" tab -- Den-O's exact
day-by-day Timeline view, with the one power Den-O deliberately didn't
have added on top: reassigning which task a past block belongs to, or
deleting it outright. Zi-O is the Time King, whose whole show is about
rewriting other Kamen Riders' history, so this is close to a literal
adaptation of its premise. The fourth of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-17-tier5-zi-o-history-editor-design.md.

All of the day-navigation state (which day is shown) lives in build()'s
own closure, the same pattern Den-O already established -- ui.py never
sees it. The delete-confirm state (whether a row is mid-"Really
delete?") is even more local: it lives in that one row's own nested
closure, so it can never leak into another row or survive a re-render.
build() is screenshot-verified in the running app, matching every
other Tier 5 tab.
"""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from ._shared import (
    format_day_heading, format_hm, format_time_range, resolve_task_name, sorted_blocks,
)

# Same hex values as den_o.py's own local color constants (which
# themselves cross-reference ui.py's COLOR_BREAK/COLOR_WARN/COLOR_IDLE)
# -- kept as its own local copy here rather than imported from
# den_o.py, for the same "keep every Tier 5 Rider module independent"
# reasoning den_o.py's own spec already gave for not importing colors
# out of ui.py.
_COMPLETED_COLOR = "#2f9e5f"
_ENDED_EARLY_COLOR = "#e0a800"
_MUTED_COLOR = "#5a6472"


def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` with Zi-O's History view: Den-O's day-by-day
    layout, plus a task-reassign dropdown and a delete control on every
    row.
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

        # Rebuilt fresh every render_day() call, so a task renamed or
        # deleted elsewhere is always reflected next time this day is
        # (re)drawn.
        task_names = {t.id: t.name for t in tasks.all()}

        for record in blocks:
            render_row(record, task_names)

    def render_row(record, task_names: dict) -> None:
        dot_color = _COMPLETED_COLOR if record.completed else _ENDED_EARLY_COLOR
        row = ctk.CTkFrame(rows_frame, border_width=1, border_color=dot_color)
        row.pack(fill="x", pady=3)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(
            top, text="●", text_color=dot_color, width=20,
            font=ctk.CTkFont(size=14),
        ).pack(side="left")
        title = (
            f"{format_time_range(record.start, record.end)} · "
            f"{format_hm(record.duration_seconds)}"
        )
        ctk.CTkLabel(
            top, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", fill="x", expand=True)

        controls = ctk.CTkFrame(row, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=(2, 8))

        def on_reassign(chosen: str) -> None:
            new_task_id = None
            if chosen != "No task":
                for task_id, name in task_names.items():
                    if name == chosen:
                        new_task_id = task_id
                        break
            history.reassign_task(record.id, new_task_id)
            render_day()

        names = ["No task"] + sorted(task_names.values())
        reassign_menu = ctk.CTkOptionMenu(
            controls, values=names, command=on_reassign, width=160,
        )
        # set() just changes the displayed text -- it works even for a
        # value like "Deleted task" that isn't in `values` at all, which
        # is exactly the dangling-task_id case.
        reassign_menu.set(resolve_task_name(record.task_id, tasks))
        reassign_menu.pack(side="left")

        delete_area = ctk.CTkFrame(controls, fg_color="transparent")
        delete_area.pack(side="right")

        def show_delete() -> None:
            for child in delete_area.winfo_children():
                child.destroy()
            ctk.CTkButton(
                delete_area, text="Delete", width=70, height=26, command=show_confirm,
            ).pack(side="left")

        def show_confirm() -> None:
            for child in delete_area.winfo_children():
                child.destroy()
            ctk.CTkButton(
                delete_area, text="Really delete?", width=110, height=26,
                fg_color=_ENDED_EARLY_COLOR,
                command=lambda: (history.delete(record.id), render_day()),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                delete_area, text="Cancel", width=70, height=26, command=show_delete,
            ).pack(side="left")

        show_delete()

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
from . import decade, den_o, v3

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
    "analytics_dashboard": decade.build,
}
```

to:

```python
from . import decade, den_o, v3, zi_o

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
    "analytics_dashboard": decade.build,
    "history_editor": zi_o.build,
}
```

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `pytest -v`
Expected: PASS — every test from Tasks 1-4 plus the whole pre-existing
suite.

- [ ] **Step 4: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 6: Wire Zi-O's tab label into `ui.py`

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `RIDER_THEMES["Kamen Rider Zi-O (2018)"].tier5_effect ==
  "history_editor"` (Task 4), `TIER5_BUILDERS["history_editor"]` (Task 5).

- [ ] **Step 1: Add the tab label**

In `lock_in/ui.py`, find:

```python
_TIER5_TAB_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
}
```

Replace it with:

```python
_TIER5_TAB_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
    "history_editor": "History",
}
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: PASS — same count as after Task 5.

- [ ] **Step 3: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 7: Blade's `group_by_status()`

**Files:**
- Create: `lock_in/tier5/blade.py` (pure function only in this task —
  `build()` comes in Task 9)
- Test: `tests/test_tier5_blade.py`

**Interfaces:**
- Produces: `group_by_status(tasks: list[Task]) -> dict[TaskStatus, list[Task]]`
  in `lock_in.tier5.blade`. Task 9's `build()` calls this.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tier5_blade.py`:

```python
from lock_in.tasks import Task, TaskStatus
from lock_in.tier5.blade import group_by_status


def _task(name: str, status: TaskStatus) -> Task:
    return Task(id=name, name=name, status=status)


def test_group_by_status_returns_all_three_keys_for_an_empty_list():
    result = group_by_status([])
    assert result == {TaskStatus.TODO: [], TaskStatus.IN_PROGRESS: [], TaskStatus.DONE: []}


def test_group_by_status_sorts_into_the_correct_buckets():
    todo = _task("a", TaskStatus.TODO)
    doing = _task("b", TaskStatus.IN_PROGRESS)
    done = _task("c", TaskStatus.DONE)
    result = group_by_status([todo, doing, done])
    assert result[TaskStatus.TODO] == [todo]
    assert result[TaskStatus.IN_PROGRESS] == [doing]
    assert result[TaskStatus.DONE] == [done]


def test_group_by_status_preserves_relative_order_within_a_bucket():
    first = _task("first", TaskStatus.TODO)
    second = _task("second", TaskStatus.TODO)
    result = group_by_status([first, second])
    assert result[TaskStatus.TODO] == [first, second]


def test_group_by_status_with_only_one_status_still_returns_all_three_keys():
    only = _task("only", TaskStatus.DONE)
    result = group_by_status([only])
    assert result[TaskStatus.TODO] == []
    assert result[TaskStatus.IN_PROGRESS] == []
    assert result[TaskStatus.DONE] == [only]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tier5_blade.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.tier5.blade'`.

- [ ] **Step 3: Write the minimal implementation**

Create `lock_in/tier5/blade.py`:

```python
"""
tier5/blade.py
===============
Kamen Rider Blade's Tier 5 gimmick: a "Board" tab -- your tasks laid
out as three columns (To Do / In Progress / Done), the "board/kanban
styling" the Tier 5 foundation spec named and deferred when it built
the plain-list Tasks tab. The fifth of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-17-tier5-blade-kanban-board-design.md.

`group_by_status()` is the one pure function this Rider needs -- tested
with no Tk, no display server. `build()` is the only Tk-dependent
piece, including the "->" column-advance buttons, which call the exact
same TaskStore.set_status()/complete() the Tasks tab's own "Done"
button already calls. Zero new data-model changes, unlike every other
Tier 5 Rider so far -- Blade is purely a second view of the same
TaskStore the Tasks tab already reads and writes. build() is
screenshot-verified in the running app, matching every other tab.
"""

from __future__ import annotations

from ..tasks import Task, TaskStatus


def group_by_status(tasks: list[Task]) -> dict[TaskStatus, list[Task]]:
    """Splits a flat task list into the three status buckets, in each
    bucket's original relative order. All three keys are always
    present, even with an empty bucket -- callers render three column
    headers every time, not just the ones with cards."""
    buckets: dict[TaskStatus, list[Task]] = {
        TaskStatus.TODO: [], TaskStatus.IN_PROGRESS: [], TaskStatus.DONE: [],
    }
    for task in tasks:
        buckets[task.status].append(task)
    return buckets
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_tier5_blade.py -v`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 8: `tier5_effect="kanban_board"` on Blade

**Files:**
- Modify: `lock_in/rider_themes.py`
- Modify: `tests/test_rider_themes.py`

**Interfaces:**
- Produces: `RIDER_THEMES["Kamen Rider Blade (2004)"].tier5_effect ==
  "kanban_board"`. Task 9's `TIER5_BUILDERS` and Task 10's `ui.py`
  wiring both key off this string.

- [ ] **Step 1: Update the failing test**

In `tests/test_rider_themes.py`, find the
`test_exactly_these_four_riders_have_a_tier5_effect` function added in
Task 4 and replace it with:

```python
def test_exactly_these_five_riders_have_a_tier5_effect():
    from lock_in.rider_themes import RIDER_THEMES
    expected = {
        "Kamen Rider V3 (1973)": "hours_tab",
        "Kamen Rider Den-O (2007)": "timeline_view",
        "Kamen Rider Decade (2009)": "analytics_dashboard",
        "Kamen Rider Zi-O (2018)": "history_editor",
        "Kamen Rider Blade (2004)": "kanban_board",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier5_effect == effect, name
    tier5_riders = {n for n, t in RIDER_THEMES.items() if t.tier5_effect != "none"}
    assert tier5_riders == set(expected)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_rider_themes.py -k tier5 -v`
Expected: FAIL — Blade's `tier5_effect` is still `"none"`.

- [ ] **Step 3: Assign the effect**

In `lock_in/rider_themes.py`, find:

```python
    "Kamen Rider Blade (2004)": RiderTheme(
        "Heisei", 2004, ("#0f4a8f", "#42a5f5"), ("#78909c", "#b0bec5"),
    ),
```

Replace it with:

```python
    "Kamen Rider Blade (2004)": RiderTheme(
        "Heisei", 2004, ("#0f4a8f", "#42a5f5"), ("#78909c", "#b0bec5"),
        tier5_effect="kanban_board",
    ),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_rider_themes.py -v`
Expected: PASS — all tests.

- [ ] **Step 5: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 9: `blade.py`'s `build()` — the Board tab, and registering it

**Files:**
- Modify: `lock_in/tier5/blade.py` (add `build()`)
- Modify: `lock_in/tier5/__init__.py`

**Interfaces:**
- Consumes: `group_by_status()` (Task 7), `tasks.all()`/
  `.set_status()`/`.complete()` (already exist), `theme.primary_text_pair`
  (already exists).
- Produces: `build(parent, *, history, tasks, theme, appearance_mode) ->
  None` in `lock_in.tier5.blade`, registered in
  `TIER5_BUILDERS["kanban_board"]`.

No automated test for this step — same reasoning as every other Tier 5
Rider's `build()`. Task 12 covers manual verification.

- [ ] **Step 1: Add the needed import and `build()` to `lock_in/tier5/blade.py`**

Replace:

```python
from __future__ import annotations

from ..tasks import Task, TaskStatus
```

with:

```python
from __future__ import annotations

import customtkinter as ctk

from ..tasks import Task, TaskStatus
```

Append to the end of the file:

```python
def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` with Blade's Board view: three columns (To Do /
    In Progress / Done), one card per task, each (except Done) with a
    "->" button that advances it one column.
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
    # A card in the To Do column advances to In Progress; one in In
    # Progress advances to Done; Done has nowhere further to go (no
    # button shown for it).
    next_status = {TaskStatus.TODO: TaskStatus.IN_PROGRESS, TaskStatus.IN_PROGRESS: TaskStatus.DONE}

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
        if task.subtasks:
            done_count = sum(1 for s in task.subtasks if s.done)
            ctk.CTkLabel(
                card, text=f"{done_count}/{len(task.subtasks)}", anchor="w",
                font=ctk.CTkFont(size=10), text_color=("gray40", "gray60"),
            ).pack(anchor="w", padx=8)

        target = next_status.get(status)
        if target is not None:
            ctk.CTkButton(
                card, text="->", width=40, height=24,
                command=lambda t=task, s=target: advance(t, s),
            ).pack(anchor="e", padx=8, pady=(4, 8))
        else:
            ctk.CTkFrame(card, fg_color="transparent", height=8).pack()

    def advance(task, new_status: TaskStatus) -> None:
        if new_status == TaskStatus.DONE:
            tasks.complete(task.id)
        else:
            tasks.set_status(task.id, new_status)
        render_board()

    render_board()
```

- [ ] **Step 2: Register it in `TIER5_BUILDERS`**

In `lock_in/tier5/__init__.py`, change:

```python
from . import decade, den_o, v3, zi_o

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
    "analytics_dashboard": decade.build,
    "history_editor": zi_o.build,
}
```

to:

```python
from . import blade, decade, den_o, v3, zi_o

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
    "analytics_dashboard": decade.build,
    "history_editor": zi_o.build,
    "kanban_board": blade.build,
}
```

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `pytest -v`
Expected: PASS — every test from Tasks 1-8 plus the whole pre-existing
suite.

- [ ] **Step 4: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 10: Wire Blade's tab label into `ui.py`

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `RIDER_THEMES["Kamen Rider Blade (2004)"].tier5_effect ==
  "kanban_board"` (Task 8), `TIER5_BUILDERS["kanban_board"]` (Task 9).

- [ ] **Step 1: Add the tab label**

In `lock_in/ui.py`, find:

```python
_TIER5_TAB_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
    "history_editor": "History",
}
```

Replace it with:

```python
_TIER5_TAB_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
    "history_editor": "History", "kanban_board": "Board",
}
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: PASS — same count as after Task 9.

- [ ] **Step 3: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 11: Docs — Help tab, README, and the version bump to v2.5.4

**Files:**
- Modify: `lock_in/ui.py` (`_build_help_tab`)
- Modify: `README.md`
- Modify: `lock_in/__init__.py`

- [ ] **Step 1: Add Zi-O and Blade to the Help tab's Tier 5 section**

In `_build_help_tab()`, find:

```python
        bullet(
            "Decade — an \"Analytics\" tab appears: a 30-day version of "
            "V3's bar chart, plus your top 10 tasks by total time spent."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "three are just the first."
        )
```

Replace it with:

```python
        bullet(
            "Decade — an \"Analytics\" tab appears: a 30-day version of "
            "V3's bar chart, plus your top 10 tasks by total time spent."
        )
        bullet(
            "Zi-O — a \"History\" tab appears: the same day-by-day list "
            "Den-O shows, but now you can fix a block's task from a "
            "dropdown on each row, or delete one entirely (tap Delete, "
            "then tap Really delete? to confirm)."
        )
        bullet(
            "Blade — a \"Board\" tab appears: your tasks laid out in "
            "three columns (To Do, In Progress, Done), each with a "
            "small arrow button to move it forward one column."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "five are just the first."
        )
```

- [ ] **Step 2: Add Zi-O and Blade to README's Tier 5 subsection**

In `README.md`, find:

```markdown
- **Decade** — adds an "Analytics" tab: a 30-day version of V3's bar
  chart, plus your top 10 tasks ranked by how much total time you've
  spent on each.

More Riders will read your tasks and history this way over time — these
three are just the first of ten planned.
```

Replace it with:

```markdown
- **Decade** — adds an "Analytics" tab: a 30-day version of V3's bar
  chart, plus your top 10 tasks ranked by how much total time you've
  spent on each.
- **Zi-O** — adds a "History" tab: Den-O's same day-by-day list, but
  editable. Reassign which task a block belongs to from a dropdown, or
  delete a block entirely (a two-click "Delete" / "Really delete?"
  confirm, no popup).
- **Blade** — adds a "Board" tab: your tasks as three columns (To Do,
  In Progress, Done), each card with a small arrow button that moves it
  one column forward.

More Riders will read your tasks and history this way over time — these
five are just the first of ten planned.
```

- [ ] **Step 3: Bump the version**

In `lock_in/__init__.py`, change:

```python
__version__ = "2.5.3"
```

to:

```python
__version__ = "2.5.4"
```

- [ ] **Step 4: Run the full test suite**

Run: `pytest -v`
Expected: PASS — documentation and version-string changes only.

- [ ] **Step 5: Checkpoint** — no commit here. Everything is committed together at the end by the maintainer (see Task 12).

---

### Task 12: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire automated test suite**

Run: `pytest -v`
Expected: PASS — every test in the suite, old and new.

- [ ] **Step 2: Manually verify Zi-O, in the running app**

Run the app with `python main.py`:

1. Settings → Kamen Rider theme → pick "Kamen Rider Zi-O (2018)". A
   "History" tab appears after Help.
2. With history logged across at least two tasks (plus one untagged
   block, and ideally one whose task has since been deleted): each row
   shows its time/duration, a reassign dropdown pre-set to the correct
   current task ("No task" or "Deleted task" where applicable), and a
   "Delete" button.
3. Reassigning a block via the dropdown updates that row immediately
   and survives closing and reopening the app.
4. Reassigning to "No task" clears the block's task.
5. Clicking "Delete" flips it to "Really delete?" + "Cancel" in place
   (no popup window). Clicking "Cancel" reverts to plain "Delete" with
   no data changed. Clicking "Really delete?" removes the block from
   the day's list and from `sessions.jsonl` permanently.
6. Prev/Next day navigation still works exactly as it does for Den-O.
7. If you have a `sessions.jsonl` from before this version, it still
   loads correctly, and every old record now has a stable id (delete
   one, reopen the app, confirm it's still gone and nothing else
   changed).
8. Light and dark mode both render correctly. Switching to a
   non-Tier-5 Rider, or turning on Standard Mode, hides the tab.

- [ ] **Step 3: Manually verify Blade, in the running app**

1. Settings → Kamen Rider theme → pick "Kamen Rider Blade (2004)". A
   "Board" tab appears after Help.
2. On a fresh install (no tasks yet), it shows only
   "No tasks yet. Add one on the Tasks tab." — no columns.
3. Add a task on the Tasks tab; it appears in the To Do column on
   Board without restarting the app.
4. Click "→" on a To Do card: it moves to In Progress, and the Tasks
   tab (reopen it) shows the same status change.
5. Click "→" again: it moves to Done, and also now appears in the
   Tasks tab's collapsed "Done" section. Done cards show no "→" button.
6. A task with subtasks shows its `done/total` count; a task with none
   shows no extra line.
7. Light and dark mode both render correctly. Switching to a
   non-Tier-5 Rider, or turning on Standard Mode, hides the tab.

- [ ] **Step 4: Report results**

Report the full test count and pass/fail, and the outcome of each
manual check above for both Riders. Do not run any git command — list
the exact `git add` / `git commit` / `git tag` / `git push` commands
for the maintainer to run by hand.
