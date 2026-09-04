# Lock In: Tier 5 core — Tasks & Session History

Date: 2026-09-04
Status: Approved, ready for implementation plan

## Goal

The first of several specs under Tier 5 (the larger 38-Rider project's
newest tier, following Tiers 0-4 shipped in v2.2.0-v2.4.0). Tier 5 is
pitched as 10 Riders — V3, Decade, W, OOO, Den-O, Zi-O, Gotchard, Geats,
Blade, MY-TH — but unlike every prior tier, those 10 don't share one
mechanism. They're 10 different UIs (a daily-hours tracker, an analytics
dashboard, a Kanban board, a timeline, a history editor, an algorithmic
rescheduler, and more) sitting on top of one thing none of them can work
without: **a task/history data model, which this codebase does not have
at all today.**

This spec covers only that foundation — the data model, its persistence,
and one plain, unthemed "Tasks" tab to make it real and testable end to
end. None of the 10 Riders are built here. Each becomes its own small
follow-on spec once this lands, the same way Tier 1's 9 progress-bar
shapes were each built one at a time atop one shared `render_progress()`
mechanism, rather than all at once.

## Why two files, not one

Tasks and session history are different shapes of data, and the
codebase already keeps different-shaped data in different files
(`config.json` vs `model.json` vs `observations.jsonl`) rather than one
combined blob:

- **A task is mutable, user-edited state.** You rename it, check off
  subtasks, reorder its status, delete it. It needs to be rewritten in
  place — the same shape `config.json` and `model.json` already are.
- **A session-history entry is an immutable, append-only fact.** Once a
  focus block ends, that record never changes (editing history is
  explicitly Zi-O's job later, not this pass). That's exactly the shape
  `observations.jsonl` already is — one line per event, safe to append,
  tolerant of a corrupted trailing line.

Forcing both into one file or one module would blur that distinction for
no benefit, so this spec adds two small modules instead, matching the
one-concern-per-module pattern `config.py`/`session.py`/`classifier.py`/
`observations.py` already establish.

## Data model

### `lock_in/tasks.py` (new)

- `Subtask` — `id`, `text`, `done: bool`.
- `Task` — `id`, `name`, `subtasks: List[Subtask]`, `status` (one of
  `todo` / `in_progress` / `done`), `created_at`, `completed_at` (`None`
  until done). No `notes` field in this pass — nothing in Tier 5's 10
  Riders was pitched needing one, and there's no UI planned to edit it,
  so adding it now would be a field nothing reads or writes (an easy,
  additive change later if a Rider genuinely needs it).
- `TaskStore` — loads and saves the whole task list as one JSON file
  (`tasks.json`, a new path alongside `config.json` in `app_data_dir()`).
  Same load-tolerance shape as `Config.load`: a missing file starts
  empty, a corrupted file starts fresh rather than crashing the app.
  Methods: `add(name)`, `add_subtask(task_id, text)`,
  `toggle_subtask(task_id, subtask_id)`, `set_status(task_id, status)`,
  `complete(task_id)` (sets `status=done` + `completed_at=now`),
  `delete(task_id)`, `all()`, `open()` (todo + in_progress), `done()`.

### `lock_in/history.py` (new)

- `SessionRecord` — `start`, `end`, `duration_seconds`, `task_id`
  (nullable — an untagged focus block still gets logged, same as today's
  behavior with no task system at all), `completed: bool` (`False` if
  the block was skipped or reset before its time ran out, so a cut-short
  block is visible in history but distinguishable from a real one).
- `HistoryStore` — append-only JSONL, reusing the `LOG_PATH =
  app_data_dir() / "sessions.jsonl"` constant that already exists in
  `config.py` today but is never used anywhere else in the codebase.
  Same corrupt-line tolerance as `ObservationStore.load`. Methods:
  `record(session_record)`, `all()`, `for_date(date)`,
  `for_task(task_id)`, and `total_seconds_by_day()` — the one aggregate
  every history-reading Rider downstream (V3, Decade, Den-O) will need
  as its starting point, so it's built once here rather than
  reimplemented per Rider later.

## Wiring into the existing app

`ui.py` gets `self.tasks = TaskStore(...)` and `self.history =
HistoryStore(...)`, constructed in `__init__` alongside
`self.observations`/`self.model` today — same pattern, no new
initialization shape.

A new **"Tasks" tab** (plain list, no board/kanban styling — that's
Blade's job later, no drag-reorder — YAGNI, nothing in Tier 5's 10 items
needs manual task ordering yet) holds:

- Todo and in-progress tasks together, done tasks in their own
  collapsed section.
- Inline subtask checkboxes per task.
- An add-task field and a per-task add-subtask field.
- A "current task" picker (dropdown of open tasks + quick-add), shown
  above the Home tab's Start button — not buried on the Tasks tab
  itself, since picking what you're about to work on is a Home-tab
  action, same reasoning Tier 3's X goal-prompt already established for
  not living on a settings-style tab.

**Starting a focus block with no task picked is still allowed** — it
logs to history exactly like it does today, just with `task_id=None`.
Nothing about the existing timer requires a task to function.

## Session completion vs. task completion — two separate, deliberately different events

This is the one behavior in this spec worth stating explicitly rather
than leaving implied, because Pomodoro focus blocks routinely span more
than one session per task, and getting this wrong would be a real
"the app decided something for me" surprise:

- **Picking a task and pressing Start** flips that task's status to
  `in_progress` automatically (`TaskStore.set_status`). This is the only
  automatic status change in the whole model.
- **A focus block ending — for any reason (ran out naturally, skipped,
  reset) — never changes a task's status.** A task that was
  `in_progress` stays `in_progress` when its block finishes. Session
  completion is logged to `history.py`; task completion is a
  completely separate fact recorded in `tasks.py`. The two stores never
  write to each other.
- **The only way a task becomes `done` is you clicking its "done"
  checkbox on the Tasks tab.** There is no block count, timer, or
  subtask-completion threshold that marks a task done on its own in this
  pass. Only you know when something is actually finished, not just
  "a timer ran on it once" — auto-completing a task because a 25-minute
  block happened to end would frequently be wrong for real work that
  spans multiple sessions, and silently wrong is worse than
  inconvenient.

`_on_phase_started` (Home tab, current-task picker → Start) is the only
call site that touches `tasks.py`. `_on_phase_ended` (the same
phase-transition hook Tier 4's Hibiki/Ghost/Ryuki already use) is the
only call site that touches `history.py`. They do not call into each
other. `session.py` itself stays exactly as unaware that tasks or
history exist as it already is of windows, blocking, or Claude — this
is an additive change at the UI layer, not a change to the pure-logic
timer.

**A history record's `task_id` is a snapshot, not a live reference.**
`SessionRecord.task_id` is set once, at `record()` time, from whichever
task was current at that moment — `HistoryStore` never looks a task up
again afterward. If that task is later deleted from `tasks.py`, its
past history entries are untouched and keep the now-dangling id rather
than being deleted, rewritten, or silently reassigned to "untagged."
(Resolving a dangling `task_id` back to a task name for display — e.g.
showing "Deleted task" instead of a blank — is a per-Rider UI concern
for whichever of the 10 later Riders actually renders history by task,
not something `history.py` itself needs to solve.)

## Error handling

Same posture as every existing store in this codebase: a missing
`tasks.json` or `sessions.jsonl` means "empty, start fresh." A corrupted
file (bad JSON, a broken JSONL line) means "start fresh" (`tasks.json`)
or "skip that one line and keep the rest" (`sessions.jsonl`, matching
`ObservationStore.load`'s existing per-line tolerance) — never a crash
over user data.

## Testing

- `tests/test_tasks.py` — add/complete/delete, subtask toggling, status
  transitions (including that completing a block never touches status —
  a regression test for the exact behavior above), JSON round-trip,
  corrupt-file tolerance. Same shape as `tests/test_config.py`.
- `tests/test_history.py` — record/query, `for_date`/`for_task`
  filtering, `total_seconds_by_day` aggregation, JSONL round-trip,
  corrupt-line tolerance. Same shape as `tests/test_observations.py`.
- `ui.py` wiring (the Tasks tab, the current-task picker, the two
  phase-transition hooks): screenshot-driven manual verification of the
  real running app, same approach every prior tier has used — no
  automated GUI test.

## Out of scope for this pass

- All 10 Tier 5 Riders (V3, Decade, W, OOO, Den-O, Zi-O, Gotchard,
  Geats, Blade, MY-TH) — each gets its own spec once this foundation
  ships.
- Task ordering / drag-reorder, due dates, priorities, dependencies,
  recurring tasks.
- Editing or deleting a past history entry (Zi-O's job later).
- Any automatic task-completion inference of any kind (see the section
  above).
- Any git/GitHub action — every command runs manually, at the end.

## File-by-file change list

- New: `lock_in/tasks.py`, `lock_in/history.py`.
- Edit: `lock_in/ui.py` (`self.tasks`/`self.history` construction, the
  new Tasks tab, the current-task picker on the Home tab, the two
  phase-transition hooks).
- New: `tests/test_tasks.py`, `tests/test_history.py`.
- Edit: `README.md` (once this ships — not part of this design pass).
- Version: to be decided once this slice's implementation is actually
  complete, matching how prior tiers only bumped `__version__` at the
  end of their own work, not at spec time.
