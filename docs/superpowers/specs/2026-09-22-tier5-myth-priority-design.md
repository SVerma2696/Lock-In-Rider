# Lock In: Tier 5 Rider #10 — MY-TH, the Priority tab

Date: 2026-09-22
Status: Approved

## Goal

The tenth and last of Tier 5's 10 Riders, built on the shared
`tier5_effect` / `lock_in/tier5/` plumbing that V3, Den-O, Decade, Zi-O,
Blade, W, Geats, Gotchard, and OOO already established. MY-TH's tab
answers one question in plain words: **"which of my open tasks have I
been neglecting the longest?"**

When Kamen Rider MY-TH (2026) is the picked Rider, a **"Priority"** tab
shows every open task (To Do and In Progress), numbered in one order:
the task you've gone the longest without working on sits at the top.

This reads existing data only — your task list and your session
history — and adds **no new stored state of its own**. Nothing is saved,
nothing is scheduled; the order is worked out fresh every time the tab
is built, exactly like V3's chart or Decade's ranking already are.

## The rule

Decided during brainstorming: **most neglected first.**

- For each open task, find its **last-worked date** — the calendar day
  of the most recent focus block that named that task in
  `sessions.jsonl`, using `HistoryStore.for_task(task_id)`. Every block
  counts toward this, finished, skipped, or reset early, the same "every
  block counts" rule V3, W, and Geats already use — a reset block still
  means you looked at the task that day.
- A task with **no blocks at all** has never been worked on. It ranks
  **above every task that has a last-worked date**, no matter how old
  that date is — a task you haven't started is the most neglected thing
  there is.
- **Among never-started tasks**, the order is by the task's own creation
  date, oldest first — the one that's been sitting untouched the longest
  goes first.
- **Among tasks with a last-worked date**, the order is by that date,
  oldest (stalest) first. A tie (two tasks last worked the same calendar
  day) is broken by creation date, oldest first — the same tie-break as
  above, so the whole ordering only ever needs two numbers per task.
- **In-progress vs. to-do status plays no part in the order.** Only
  neglect does. (Blade's Board is where status itself is the point.)

## The tab

Tab label **"Priority"**; `Kamen Rider MY-TH (2026)` gets
`tier5_effect="priority_order"`. The tab sits next to Help like every
other Tier 5 tab, and is hidden by Standard Mode and by picking a
non-Tier-5 Rider through the existing mechanism (no new code for that).

Layout, top to bottom, inside a `CTkScrollableFrame` (matching every
other tab):

1. **A numbered list**, one row per open task, in the order above:
   - `1.` the task's name.
   - Underneath, one small gray phrase: `"never started"`, `"today"`,
     `"yesterday"`, or `"{n} days ago"`.
2. **Empty state.** No open tasks at all: one line,
   `"No open tasks yet. Add one on the Tasks tab."` — no list.
3. **Caption**, same small gray style as every other tab's caption:
   `"Ranked by which task you've worked on least recently — nothing here is saved, it's worked out fresh every time you open this tab."`

The list is **read-only** — no buttons, no way to reorder it by hand,
matching V3/Den-O/Decade/W's plain-view posture rather than Blade's or
Zi-O's interactive one. Picking what to actually start still happens the
normal way, from the dropdown above the Start button.

`config` and `appearance_mode` are part of every Tier 5 builder's
signature. MY-TH uses neither — it reads `tasks` and `history`, the same
two Blade already reads (Blade ignores `history`; MY-TH is the mirror
case, ignoring `config`).

## Colors

MY-TH's `primary` is blue and `secondary` is blue-gray (see
`rider_themes.py`). So:

- **The number and task name:** `theme.primary_text_pair`.
- **The "never started" / "{n} days ago" phrase:** the same small gray
  CustomTkinter uses for every other tab's caption
  (`("gray40", "gray60")`), not a Rider color — it's a secondary detail,
  not the headline, the same visual weight Den-O gives its per-block
  detail line.

Both modes are checked by eye in the running app.

## New code

### `lock_in/tier5/my_th.py` (new)

Two small pure functions, tested with no Tk and no display server, plus
the one Tk-dependent `build()`:

- **`last_worked_date(records: list[SessionRecord]) -> Optional[date]`**
  The calendar day of the most recent block in `records` (by `start`),
  or `None` if `records` is empty. `records` is whatever
  `history.for_task(task_id)` returns — this function does no filtering
  of its own.
- **`neglect_order(open_tasks: list[Task], history: HistoryStore, today: date) -> list[Task]`**
  Sorts `open_tasks` by the rule above and returns the sorted list. Built
  as a plain Python `sorted()` with a key of
  `(has_a_date, sort_date, created_at)` — `has_a_date` is `False` (sorts
  first) for a never-worked task and `True` otherwise, `sort_date` is
  `last_worked_date(...)` or a sentinel that never wins a comparison
  against a real date, and `created_at` is the existing tie-break field
  already on `Task`. `today` is accepted but not used by the sort itself
  (there is no "how long ago" number baked into the order, only a
  relative one) — it exists so the same value can be threaded through to
  the display phrase in `build()` without computing "today" twice.
- **`days_ago_phrase(last: Optional[date], today: date) -> str`**
  `None` → `"never started"`; `today` itself → `"today"`;
  one day back → `"yesterday"`; anything older →
  `"{n} days ago"`. The one place this wording is decided, so the list
  and any future reuse of the phrase always agree.
- **`build(parent, *, history, tasks, theme, appearance_mode, config) -> None`**
  Builds the tab described above: calls `neglect_order(tasks.open(), history, date.today())`,
  then one row per task with its number, name, and
  `days_ago_phrase(last_worked_date(history.for_task(task.id)), today)`.
  Since the tab is read-only, there is nothing to wire up on rebuild
  beyond the normal per-tab-open refresh every Tier 5 tab already gets
  from `_build_tier5_tab()` — no in-place widget reconfiguration is
  needed the way Geats' and Gotchard's interactive widgets require.

`my_th.py` imports from `..tasks` (for the `Task` type hint) and
`..history` (for `HistoryStore`/`SessionRecord` type hints) purely for
typing, plus `customtkinter` — no import from `_shared.py`, since none of
its day-math or formatting helpers fit this particular phrasing.

### `lock_in/ui.py` (small)

- `_TIER5_TAB_LABELS` gains `"priority_order": "Priority"`.
- The tab build, the refresh after a finished block, and the show/hide
  logic already handle any registered effect and need no change.
- Help tab: add a MY-TH bullet, and change the "nine of ten" wording OOO's
  spec introduces to "all ten Tier 5 Riders are now built."

### Wiring summary

- `lock_in/tier5/__init__.py`:
  `TIER5_BUILDERS["priority_order"] = my_th.build`, plus `my_th` in the
  import line.
- `lock_in/rider_themes.py`: `tier5_effect="priority_order"` on
  `Kamen Rider MY-TH (2026)`, and the Rider count in the field's comment
  goes to ten (its final value — see "Out of scope").
- No new file on disk, and no changes to `history.py` or `tasks.py`:
  MY-TH only reads what already exists (`HistoryStore.for_task()` and
  `TaskStore.open()` are both already public methods).

## Error handling

- No open tasks: the empty-state line, no list.
- A task with no history at all: `"never started"`, ranked at the top
  alongside any other never-started tasks, tie-broken by creation date.
- A task whose every logged block was later deleted in Zi-O's History
  tab: `history.for_task(task.id)` simply returns an empty list by then,
  so the task reads as `"never started"` again — not a crash, and a fair
  read of the current truth (there is no record left that it was ever
  worked on).
- A task's `created_at` that is missing or blank on a very old,
  hand-edited `tasks.json` entry: `Task.created_at` already defaults to
  `""`, which sorts before any real ISO timestamp, so such a task simply
  wins its tie-breaks — no exception, no special-casing needed here.
- Midnight passing while the app is open: `build()` computes `today` at
  build time, so the next rebuild (a finished block, switching tabs, or
  reopening the app) reflects the new day, the same timing V3 and W
  already have.

## Testing

- `tests/test_tier5_myth.py` *(new)*:
  - `last_worked_date()`: empty list is `None`; one record returns its
    day; several records return the **latest** one's day, regardless of
    list order.
  - `neglect_order()`: a never-worked task sorts before a worked one no
    matter how stale the worked one is; among several never-worked
    tasks, oldest `created_at` sorts first; among several worked tasks,
    the one with the oldest last-worked date sorts first; two tasks last
    worked the same day are tie-broken by `created_at`; an empty
    `open_tasks` list returns an empty list; a task's own `status`
    (to-do vs. in-progress) has no effect on the order.
  - `days_ago_phrase()`: `None` → `"never started"`; `today` → `"today"`;
    one day back → `"yesterday"`; several days back → the `"{n} days
    ago"` form with the right number; a gap that crosses a month or year
    boundary still gives the right day count.
- `tests/test_rider_themes.py` *(grows)*: the tier5 completeness check
  now expects ten Riders, adding
  `"Kamen Rider MY-TH (2026)": "priority_order"`. The test is renamed to
  say ten (its final value for Tier 5).
- **Manual, in the running app** (same as every other tab, no automated
  GUI test): the "Priority" tab appears only for MY-TH; a brand new
  install with no history shows every open task as "never started," in
  creation order; logging a focus block for a task moves it toward the
  bottom of the list on the next rebuild; deleting or completing a task
  removes it from the list; light and dark mode both read clearly; the
  other nine Tier 5 tabs still open and look right.

## Docs, version, and repo hygiene

- `README.md`, two small edits: a **MY-TH** bullet in the Tier 5 section
  in the same plain words, and the "X of ten planned" line changes to say
  all ten Tier 5 Riders are built — Tier 5 is complete as of this
  release.
- `lock_in/ui.py`, Help tab: as above.
- `__version__`: bumped once, covering both OOO and MY-TH together (this
  release ships both, since Tier 5 only reads as "complete" with both
  in). Exact number decided in the implementation plan.
- `.gitignore`: MY-TH creates no new file. No change is expected; it is
  re-checked when this ships.
- Project files describe the software only: nothing about who or what
  wrote them, and commit messages carry no trailer or credit line.
- Committing, pushing, and tagging are done by the project owner. The
  exact commands are handed over at the end, with a plain commit message.

## Out of scope for this pass

- Any way to pin a task above its computed spot, snooze it, or exclude
  it from the ranking.
- Blending in OOO's combo progress, subtask count, or task size as a
  second ranking factor (the brainstorming session picked neglect alone,
  on purpose, for a one-sentence-explainable rule).
- A "start this task" button on the list itself.
- Any actual schedule, time blocks, or calendar — "rescheduling" here
  means *reordering a list*, not planning a day.
- Notifications or nudges pointing at the top of the list.

## File-by-file change list

**New**
- `lock_in/tier5/my_th.py`: `last_worked_date()`, `neglect_order()`,
  `days_ago_phrase()`, `build()`.
- `tests/test_tier5_myth.py`.
- `docs/superpowers/plans/2026-09-22-tier5-myth-priority.md`: the
  implementation plan (written after this spec is approved).

**Edit**
- `lock_in/tier5/__init__.py`: one registry entry.
- `lock_in/rider_themes.py`: `tier5_effect="priority_order"` on MY-TH,
  and the comment count.
- `lock_in/ui.py`: `_TIER5_TAB_LABELS` entry, Help tab bullet and wording.
- `lock_in/__init__.py`: version bump (see OOO's spec — one bump covers
  both).
- `tests/test_rider_themes.py`: as described above.
- `README.md`: Tier 5 bullet, "Tier 5 complete" wording.
