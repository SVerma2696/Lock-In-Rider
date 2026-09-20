# Lock In: Tier 5 Rider #4 — Zi-O, the history editor

Date: 2026-09-17
Status: Approved, ready for implementation plan

## Goal

The fourth of Tier 5's 10 Riders, built on the shared `tier5_effect` /
`lock_in/tier5/` plumbing V3, Den-O, and Decade already established.
Zi-O — the Time King, whose entire show is about rewriting other Kamen
Riders' history — gets the one thing the Tier 5 foundation spec
explicitly deferred: **editing a past focus block.** Den-O's Timeline
is read-only by design; Zi-O reuses that exact day-by-day view and adds
the power to fix a mistake in it. When Kamen Rider Zi-O (2018) is the
picked Rider, a "History" tab shows the same day-at-a-time list Den-O
does, except each block can now have its task reassigned or be deleted
outright.

Scope, decided during brainstorming: **reassign task + delete only.** A
block's start/end time and duration stay locked — that's the one honest
fact the block actually measured, and this pass doesn't open editing it.

## `SessionRecord` gains a real id

Every other editable/deletable thing in this codebase (`Task`,
`Subtask`) already has a stable `id`; `SessionRecord` never needed one
because nothing before Zi-O ever pointed at one specific record —
Den-O and Decade only ever read whole lists or aggregates. Reassigning
or deleting one exact block needs a durable way to name it, so
`SessionRecord` gains `id: str` (a `uuid.uuid4().hex[:8]`, same shape as
`Task.id`), generated at `record()` time going forward.

**Migration for existing `sessions.jsonl` files:** `HistoryStore.load()`
assigns a fresh id to any loaded record whose line has no `"id"` key
(every record written before this change), then — if any record was
missing one — rewrites the whole file once with ids included, the same
"start fresh is fine, but never lose real data" posture this codebase
already applies everywhere else. This happens automatically, the first
time the app opens after upgrading; nothing asks the person using the app about it.

## Two new `HistoryStore` methods

Both rewrite the whole file, the same way `TaskStore`'s mutating methods
already rewrite `tasks.json` on every edit — history edits are
infrequent, deliberate, human actions, not the fast-polling write path
`ObservationStore` optimizes for.

- **`reassign_task(record_id: str, new_task_id: Optional[str]) -> bool`**
  — finds the record by id, sets its `task_id` (`None` is a valid
  target — "untag this block"), rewrites the file, returns whether a
  matching record was found. Does **not** touch `tasks.py` at all — this
  only changes which task a historical block is attributed to, it is
  not a status change and never calls `TaskStore.set_status()`, matching
  the foundation spec's "the two stores never write to each other" rule.
- **`delete(record_id: str) -> bool`** — removes the record by id,
  rewrites the file, returns whether a matching record was found.

Both are pure store operations with no UI concerns, tested exactly like
`HistoryStore`'s existing methods.

## Zi-O's own module: `lock_in/tier5/zi_o.py`

**Three functions move here from `den_o.py`, following the exact
pattern Decade already set with `resolve_task_name`:** `sorted_blocks`,
`format_time_range`, and `format_day_heading` are Rider-agnostic
day-view shaping, not anything specific to Den-O's *display* of a day —
Zi-O needs the identical browsing behavior. Rather than have `zi_o.py`
import them out of a sibling Rider's module (the exact coupling
Den-O's own spec rejected when it needed V3's `_format_hm`), all three
move to **`tier5/_shared.py`**, alongside `format_hm`,
`last_n_days`, and `resolve_task_name`. `den_o.py` updates its own
usage to import from `._shared` instead of defining them; its existing
tests for these three functions move to `tests/test_tier5_shared.py`
(same assertions, new home — no behavior change).

`zi_o.py` itself adds nothing new to the pure-logic side beyond what it
imports — the actual new behavior (reassign, delete, the confirm-flip
button) lives in `build()`, same as Den-O's own day-navigation state.

Local color constants `_COMPLETED_COLOR`/`_ENDED_EARLY_COLOR`/
`_MUTED_COLOR` are duplicated here rather than imported from `den_o.py`
— same reasoning Den-O's own spec already gave for defining its own
copies instead of importing from `ui.py`: two Rider modules importing
from each other for three hex strings is the wrong trade against
keeping each module independent.

## The tab

Tab label **"History"**; `Kamen Rider Zi-O (2018)` gets
`tier5_effect="history_editor"`.

Same layout as Den-O's Timeline (header row with `← Prev` /
`format_day_heading()` / `Next →`, one row per block, colored dot for
completed/ended-early), with each row gaining a second line of controls
underneath the existing time/task text:

1. **Reassign dropdown** — a `CTkOptionMenu` (same widget the Home tab's
   current-task picker already uses), listing every task's name plus
   "No task", currently showing `resolve_task_name(record.task_id,
   tasks)`. Picking a different entry calls
   `history.reassign_task(record.id, chosen_task_id_or_None)`
   immediately — no separate "save" step, matching how every other
   in-place edit in this app (subtask checkboxes, the Done button)
   applies on click. The row's own task-name line and the dropdown's
   shown value both update; the day re-renders via the same
   `render_day()` Den-O already calls after Prev/Next.
2. **Delete button**, starting as "Delete". First click flips its own
   text to "Really delete?" and reveals a "Cancel" button beside it —
   no popup window, matching this codebase's preference for the
   simplest interaction that actually works (this app has no
   popup-confirm-dialog pattern anywhere today, and this design doesn't
   introduce one). Clicking "Really delete?" calls
   `history.delete(record.id)` and re-renders the day; clicking
   "Cancel" flips the row's controls back to the plain "Delete" state
   without touching any data.

A record deleted mid-flip-confirm (e.g., the day is re-rendered by a
focus block finishing while "Really delete?" is showing) is a non-issue
— the whole tab is torn down and rebuilt from scratch on every
`_build_tier5_tab()` call, exactly like Den-O, so there's no stale
confirm state to worry about across renders, only within one still-open
render.

**Reassigning a dangling id is impossible by construction** — the
dropdown is built from `tasks.all()`, so it only ever offers live tasks
plus "No task"; there is no way to pick "Deleted task" as a target, and
a row already showing "Deleted task" (because its `task_id` points at a
task that no longer exists) can still be reassigned to any current task
or to "No task", which clears the dangling reference.

## Wiring summary

- `_build_tier5_tab()` in `ui.py` needs no change beyond the existing
  one-line `TIER5_BUILDERS` / `_TIER5_TAB_LABELS` additions every prior
  Rider has needed — Zi-O's `build()` fits the same
  `build(parent, *, history, tasks, theme, appearance_mode)` signature.
- No new config field. No new write path beyond the two `HistoryStore`
  methods above.
- The Tasks tab, the Timeline tab, and every history-reading aggregate
  (`total_seconds_by_day`, `total_seconds_by_task`) are unaffected by a
  reassignment or deletion beyond the fact that the underlying data
  genuinely changed — the next time V3/Decade/Den-O read history, they
  see the corrected picture, which is the entire point.

## Error handling

Same posture as every other store in this codebase.
`reassign_task()`/`delete()` on an unknown `record_id` return `False`
and change nothing — this can't happen from Zi-O's own UI (every button
is built from a record that was just rendered), but the method itself
doesn't assume that. The one-time id-backfill migration on load never
raises: if `sessions.jsonl` can't be rewritten (e.g. a permissions
issue), the in-memory records still get their generated ids for this
session, and the app keeps running rather than crashing over a file it
couldn't rewrite — the next successful load just retries the same
backfill.

## Testing

- `tests/test_history.py` *(grows)* — id backfill: a record loaded
  from JSON with no `"id"` key gets one assigned, and the file is
  rewritten with it present; a record that already has an id keeps it
  unchanged; a store with a mix of both only rewrites once.
  `reassign_task()`: changes `task_id` on the matching record (including
  to `None`); returns `True`/`False` correctly; other records
  untouched. `delete()`: removes exactly the matching record; returns
  `True`/`False` correctly; other records untouched, order preserved.
- `tests/test_tier5_shared.py` *(grows)* — the `sorted_blocks`,
  `format_time_range`, `format_day_heading` assertions currently in
  `tests/test_tier5_den_o.py` move here unchanged (new import path
  only). `tests/test_tier5_den_o.py` loses those three, keeping only
  what's specific to Den-O's own `build()` (`resolve_task_name` already
  moved out to `_shared.py` in Decade's pass, before this one).
- `tests/test_rider_themes.py` — the tier5 completeness check grows to
  expect four Riders now (V3, Den-O, Decade, Zi-O).
- Manual, in the running app (same as every prior Tier 5 Rider — no
  automated GUI test): the History tab appears only for Zi-O; reassigning
  a block's task via the dropdown updates the row and persists after
  restarting the app; reassigning to "No task" clears it; deleting a
  block requires the two-click flip and removes it from the day (and
  from `sessions.jsonl`) permanently; a block whose task was deleted
  elsewhere shows "Deleted task" and can be reassigned away from that
  state; an upgrade from a `sessions.jsonl` written before this version
  still loads its old entries correctly with ids backfilled; light and
  dark mode both render; switching to a non-Tier-5 Rider or turning on
  Standard Mode hides the tab.

## Out of scope for this pass

- Editing a block's start time, end time, or duration.
- Bulk delete, undo-after-confirm (the flip-to-"Really delete?" state
  *is* the undo window), or a trash/recovery bin.
- Any change to `tasks.py` triggered by reassigning a block's task —
  reassignment is purely a `history.py` fact.
- The other 6 Tier 5 Riders (W, OOO, Gotchard, Geats, Blade, MY-TH) —
  each gets its own spec.
- Any git/GitHub step — the maintainer does those by hand.

## File-by-file change list

**New**
- `lock_in/tier5/zi_o.py` — `build()`.
- `tests/test_tier5_zi_o.py`.

**Edit**
- `lock_in/history.py` — `SessionRecord.id`, id-backfill-on-load,
  `reassign_task()`, `delete()`.
- `lock_in/tier5/_shared.py` — gains `sorted_blocks()`,
  `format_time_range()`, `format_day_heading()` (moved from `den_o.py`).
- `lock_in/tier5/den_o.py` — imports those three from `._shared` instead
  of defining them; otherwise unchanged.
- `lock_in/tier5/__init__.py` — `TIER5_BUILDERS["history_editor"] = zi_o.build`.
- `lock_in/rider_themes.py` — `tier5_effect="history_editor"` on
  `Kamen Rider Zi-O (2018)`.
- `lock_in/ui.py` — one line: `_TIER5_TAB_LABELS` gains
  `"history_editor": "History"`.
- `tests/test_history.py` — new coverage described above.
- `tests/test_tier5_shared.py`, `tests/test_tier5_den_o.py` — tests move
  as described above.
- `tests/test_rider_themes.py` — the tier5 completeness check grows to
  four Riders.

**Docs — same pattern as every prior Rider, added once this ships**
- `README.md`'s Tier 5 subsection gains a Zi-O bullet.
- `lock_in/ui.py` Help tab's Tier 5 section gains a Zi-O bullet.
- `__version__`: this and Blade land together as one version bump (v2.5.4).
