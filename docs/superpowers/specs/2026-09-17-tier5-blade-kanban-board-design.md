# Lock In: Tier 5 Rider #5 — Blade, the Kanban board

Date: 2026-09-17
Status: Approved, ready for implementation plan

## Goal

The fifth of Tier 5's 10 Riders, built on the shared `tier5_effect` /
`lock_in/tier5/` plumbing V3, Den-O, Decade, and Zi-O already
established. This is the "board/kanban styling" the Tier 5 foundation
spec explicitly named and deferred when it built the plain-list Tasks
tab (`docs/superpowers/specs/2026-09-04-tier5-tasks-history-design.md`).
Blade's whole show is built around category battles between suits of
"Undead" (Spade/Heart/Diamond/Club) — categories laid out side by side
maps directly onto a Kanban board of task statuses. When Kamen Rider
Blade (2004) is the picked Rider, a "Board" tab shows your tasks as
three columns: **To Do / In Progress / Done.**

This is purely a second *view* of the same `TaskStore` the Tasks tab
already reads and writes — Blade needs **zero new data-model changes**,
unlike every other Tier 5 Rider so far. Adding tasks, adding subtasks,
and checking off individual subtask items all stay Tasks-tab-only; the
Board only shows tasks and lets you advance one between columns.

## Column moves: buttons, not drag-and-drop

Decided during brainstorming: this codebase has never implemented
drag-and-drop (the original Tasks-tab spec explicitly deferred
"drag-reorder" as YAGNI), and CustomTkinter has no built-in support for
it. Rather than build new mouse-tracking/drop-target interaction code
from scratch for one Rider, each card gets a **"→" button** that
advances its task exactly one column, reusing the exact `TaskStore`
calls the Tasks tab's own "Done" button already makes:

- To Do → In Progress: `tasks.set_status(task_id, TaskStatus.IN_PROGRESS)`.
- In Progress → Done: `tasks.complete(task_id)`.
- Done: no button shown — nothing to advance to, and moving a task
  backward out of Done is out of scope for this pass.

## One pure function, in `lock_in/tier5/blade.py`

- **`group_by_status(tasks: list[Task]) -> dict[TaskStatus, list[Task]]`**
  — splits a flat task list into the three status buckets, preserving
  each bucket's original relative order (whatever order `TaskStore.all()`
  returns, which is insertion order — same order the Tasks tab's list
  already implies, just re-grouped instead of split into
  open-vs-done). Every one of the three keys is always present, even
  if its list is empty — `build()` renders all three column headers
  every time, not just the columns that currently have cards, so a
  fresh install with zero tasks still shows the board's shape rather
  than looking broken.

No other pure logic is needed — "which column comes after this one" is
two `if`/`elif` branches inline in `build()`, not worth its own tested
function given there's exactly one linear order and no branching logic
to get wrong.

## The tab

Tab label **"Board"**; `Kamen Rider Blade (2004)` gets
`tier5_effect="kanban_board"`.

Layout, top to bottom, inside a `CTkScrollableFrame` (matching every
other tab): three columns laid out side by side in one horizontal
`CTkFrame` row, each column its own vertical `CTkFrame` with:

1. A heading label (`"To Do"` / `"In Progress"` / `"Done"`) plus a
   count, e.g. `"To Do (3)"` — free from `len()` on that column's list,
   no extra state.
2. One card per task in that column, top to bottom, in
   `group_by_status()`'s order: the task's name, a small
   `"{done}/{total}"` subtask-progress label underneath if it has any
   subtasks (nothing shown if it has none — an empty line for every
   subtask-less task would be visual noise for what's likely the common
   case), and the "→" button (except in the Done column).
3. **Empty state**: if `tasks.all()` is empty entirely, one centered
   line above the three columns, `"No tasks yet. Add one on the Tasks
   tab."` — Blade's board can't create tasks itself, so its empty state
   points at the tab that can, unlike Den-O/Zi-O's empty-state lines
   (which don't need to point anywhere, since focus blocks are created
   by using the timer, not a specific tab).
   When at least one task exists anywhere, all three column headers
   still render even if a particular column is empty (e.g., "Done (0)"
   with no cards under it) — the three-column *shape* is the point of a
   board, so a column never disappears just because it's temporarily
   empty.

Clicking a card's "→" button calls the appropriate `TaskStore` method,
then re-renders the Board tab from scratch (same "tear down and
rebuild" pattern every other Tier 5 tab already uses after a data
change). It does **not** call `_render_tasks()` on the Tasks tab
directly — the Tasks tab already re-reads `self.tasks` fresh every time
`_build_tasks_tab()`/`_render_tasks()` runs, same as it does today after
any of its own buttons, so the two tabs naturally agree without one
needing to know the other exists.

## Wiring summary

- No new config field, no new store method, no new write path beyond
  the two existing `TaskStore` calls this reuses verbatim.
- `_build_tier5_tab()` in `ui.py` needs no change beyond the existing
  one-line `TIER5_BUILDERS` / `_TIER5_TAB_LABELS` additions every prior
  Rider has needed.
- `_on_phase_ended()` is unaffected — Blade has nothing to do with
  focus-block completion, only with tasks, and tasks already don't
  change on block completion (per the foundation spec).

## Error handling

Same posture as every other Rider in this codebase. `group_by_status([])`
returns all three keys mapped to empty lists, not a missing-key error —
`build()` never needs a `.get(status, [])` guard. Clicking "→" always
operates on a `task_id` captured from a task that was just rendered, so
there's no id-not-found path to handle in the UI layer (`TaskStore`'s
own methods already return `False` harmlessly if a task vanished
between render and click, e.g. deleted from the Tasks tab in another
moment — the board's next render simply won't show it).

## Testing

- `tests/test_tier5_blade.py` *(new)* — `group_by_status()`: an empty
  list returns all three keys with empty lists; a mix of statuses sorts
  into the correct buckets; relative order within a bucket matches
  input order; a list with only one status still returns all three
  keys, the other two empty.
- `tests/test_rider_themes.py` — the tier5 completeness check grows to
  expect five Riders now (V3, Den-O, Decade, Zi-O, Blade).
- Manual, in the running app (same as every prior Tier 5 Rider — no
  automated GUI test): the Board tab appears only for Blade; a fresh
  install shows the empty state and no columns; adding a task on the
  Tasks tab makes it appear in the To Do column on Board without
  restarting; clicking "→" on a To Do card moves it to In Progress and
  the Tasks tab reflects the same status change; clicking "→" again
  moves it to Done, and it now also appears in the Tasks tab's
  collapsed Done section; Done cards show no "→" button; a task with
  subtasks shows its progress count, a task with none shows no extra
  line; light and dark mode both render; switching to a non-Tier-5
  Rider or turning on Standard Mode hides the tab.

## Out of scope for this pass

- Drag-and-drop.
- Moving a task backward (Done → In Progress, etc.).
- Reordering cards within a column.
- Adding, renaming, or deleting tasks, or editing subtasks, from the
  Board tab — Tasks-tab-only, unchanged.
- The other 5 Tier 5 Riders (W, OOO, Gotchard, Geats, MY-TH) — each gets
  its own spec.
- Any git/GitHub step — the maintainer does those by hand.

## File-by-file change list

**New**
- `lock_in/tier5/blade.py` — `group_by_status()`, `build()`.
- `tests/test_tier5_blade.py`.

**Edit**
- `lock_in/tier5/__init__.py` — `TIER5_BUILDERS["kanban_board"] = blade.build`.
- `lock_in/rider_themes.py` — `tier5_effect="kanban_board"` on
  `Kamen Rider Blade (2004)`.
- `lock_in/ui.py` — one line: `_TIER5_TAB_LABELS` gains
  `"kanban_board": "Board"`.
- `tests/test_rider_themes.py` — the tier5 completeness check grows to
  five Riders.

**Docs — same pattern as every prior Rider, added once this ships**
- `README.md`'s Tier 5 subsection gains a Blade bullet.
- `lock_in/ui.py` Help tab's Tier 5 section gains a Blade bullet.
- `__version__`: this and Zi-O land together as one version bump (v2.5.4).
