# Lock In: Tier 5 Rider #2 — Den-O, the timeline view

Date: 2026-09-14
Status: Approved, ready for implementation plan

## Goal

The second of Tier 5's 10 Riders, built on the shared `tier5_effect` /
`lock_in/tier5/` plumbing V3 (Rider #1) established (see
`docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md`).
When Kamen Rider Den-O (2007) is the picked Rider, a "Timeline" tab
appears: one calendar day's focus blocks, chronological, with
`← Prev` / `Next →` to flip a day at a time. It reads
`HistoryStore.for_date()` and `.all()` — no new history-recording
behavior, purely a new way to look at data that already exists.

Den-O is also the first Tier 5 Rider with genuine interactivity (V3 was
a one-shot render of "today"). That turns out not to need any change to
the shared tab mechanism — see "Day-navigation state" below.

## Two small, generically-useful store additions

Neither is Den-O-specific; both are exactly the kind of small building
block a later Rider will also want.

- **`HistoryStore.earliest_date() -> Optional[date]`** (`lock_in/history.py`)
  — the calendar day of the very first record ever logged (by `start`),
  or `None` on a store with no records at all. Backs "how far back can
  Prev go."
- **`TaskStore.get(task_id: str) -> Optional[Task]`** (`lock_in/tasks.py`)
  — a direct id → `Task` lookup. `TaskStore` has `all()`/`open()`/`done()`
  today but no single-id lookup; Den-O needs one to turn a history
  record's `task_id` back into a task name.

## A shared formatting helper moves to its own leaf module

V3 has a private `_format_hm(seconds) -> "2h 30m"` in `tier5/v3.py`.
Den-O's rows need the exact same formatting for a block's duration.
Rather than have `den_o.py` import a private name out of a sibling
Rider's module (which would quietly couple two Riders that are supposed
to be independent — see V3's spec on why `tier5/` is one small module
per Rider), `_format_hm` becomes a public `format_hm()` in a new
**`lock_in/tier5/_shared.py`** — a plain leaf module with no imports
from anywhere else in `tier5/`.

It has to be a separate module, not simply moved onto
`tier5/__init__.py` itself: `__init__.py` already does `from . import
v3` (and will do the same for `den_o`) to build `TIER5_BUILDERS`, so if
`v3.py`/`den_o.py` imported `format_hm` back *from* `__init__.py`, that
would be a circular import (`__init__` → `v3` → `__init__`, which is
only non-fatal if every name the second half needs was already defined
before the first half's `from . import v3` line — a real footgun to
leave for whoever adds Rider #3). A separate `_shared.py` that nothing
in `tier5/` imports from `__init__.py` avoids the whole question: `v3.py`
and `den_o.py` both do `from ._shared import format_hm`, and
`__init__.py`'s own import order stops mattering.

`v3.py` changes to import `format_hm` from `._shared` instead of
defining its own `_format_hm` — one rename, one import change, no
behavior change. `tests/test_tier5_v3.py`'s existing `_format_hm` tests
move to a new `tests/test_tier5_shared.py` (testing `_shared.py`
directly, not through `v3`), same assertions, new import path.

## Pure logic in `lock_in/tier5/den_o.py`

- **`resolve_task_name(task_id: Optional[str], tasks: TaskStore) -> str`**
  — `"No task"` if `task_id is None`; the task's real `name` if
  `tasks.get(task_id)` finds it; **`"Deleted task"`** if `task_id` is set
  but `tasks.get()` returns `None` (the task was deleted after this
  block was logged). This is exactly the "dangling `task_id`" display
  question the Tier 5 foundation spec explicitly deferred to "whichever
  later Rider actually renders history by task" — that's this one.
- **`sorted_blocks(records: list[SessionRecord]) -> list[SessionRecord]`**
  — `records` sorted by `start`, earliest first. `HistoryStore.for_date()`
  filters but doesn't sort; Den-O sorts explicitly rather than trusting
  JSONL append order (a hand-edited or out-of-order file shouldn't
  scramble the display).
- **`format_time_range(start_iso: str, end_iso: str) -> str`** →
  `"09:00–09:25"`. Reuses the exact `%H:%M` 24-hour format the Activity
  tab already uses for its own timestamps (`ui.py`'s
  `datetime.now().strftime("%H:%M")`) — Den-O doesn't invent a second
  time-of-day convention.
- **`format_day_heading(day: date) -> str`** → `"Friday, September 12"`,
  built as `f"{day.strftime('%A, %B')} {day.day}"`. Deliberately **not**
  `%-d`/`%#d` — those are platform-specific strftime extensions (glibc
  vs. MSVCRT), and this app explicitly supports Windows/macOS/Linux from
  one codebase; the `.day` attribute sidesteps the whole platform split.

## Day-navigation state (the new thing this Rider introduces)

Every Tier 5 builder so far (`build(parent, *, history, tasks, theme,
appearance_mode)`) has been called once and rendered a fixed view. Den-O
needs "which day am I looking at" to survive across Prev/Next clicks
without going back through `ui.py`. It doesn't need to — this is fully
self-contained inside `den_o.py`'s `build()`, using an ordinary Python
closure:

```python
def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    state = {"day": date.today()}
    ...
    def render_day():
        # update the heading label, enable/disable the two buttons,
        # clear and repopulate the row list for state["day"]
        ...
    def go(delta):
        state["day"] += timedelta(days=delta)
        render_day()
    prev_button = ctk.CTkButton(..., command=lambda: go(-1))
    next_button = ctk.CTkButton(..., command=lambda: go(1))
    render_day()
```

`ui.py` and the `TIER5_BUILDERS` contract are untouched — no new
parameter, no new lifecycle method. Switching Riders away and back, or a
focus block ending (which calls `_build_tier5_tab()` again, exactly as
it does for V3's Hours tab today), tears down and rebuilds the whole
tab from scratch, which naturally resets the view to today. That's the
right default, not a gap to patch: if you just finished a block, seeing
today's timeline is more useful than staying on whatever day you'd
scrolled to.

**Bounds**, recomputed inside `render_day()` from data that can change
between opens (a new block might get logged while Den-O's tab isn't the
active one, though this app's Rider-per-tab-rebuild pattern means
`state` itself is thrown away whenever that happens anyway):

- `Next →` disabled when `state["day"] >= date.today()`.
- `← Prev` disabled when `state["day"] <= (history.earliest_date() or date.today())`
  — on a store with zero records, `earliest_date()` is `None`, so Prev
  starts disabled too (there is nothing earlier than "today, empty" to
  show).
- **Plain calendar-flip navigation.** Prev/Next always move exactly one
  calendar day, whether or not the day landed on has any blocks — Den-O
  does not skip forward/back to the next day *with* data. Navigating to
  an ordinary empty day (a real day off, mid-history) shows the exact
  same empty-state row as any other empty day; the header still updates
  normally and both buttons stay enabled/disabled purely by the date
  math above, independent of whether that specific day has data.

## The tab

Tab label **"Timeline"**; `Kamen Rider Den-O (2007)` gets
`tier5_effect="timeline_view"`.

Layout, top to bottom, inside a `CTkScrollableFrame` (matching every
other tab):

1. **Header row** — `← Prev` button, the `format_day_heading()` string
   centered between them, `Next →` button. Disabled state per the bounds
   above (CTk's own `state="disabled"`, not hidden — so the day heading
   and the working button stay put; nothing jumps around when you hit
   an edge).
2. **Row list** — one row per block in `sorted_blocks(history.for_date(state["day"]))`,
   styled exactly like the Activity tab's existing rows (`ui.py`'s
   `_render_activity`, ~line 2657): a `CTkFrame(border_width=1,
   border_color=dot_color)`, a colored `●` on the left, a bold
   `"{format_time_range(...)} · {format_hm(duration_seconds)}"` line, and
   `resolve_task_name(record.task_id, tasks)` underneath in the smaller,
   muted style the Activity tab already uses for its detail line.

   The dot is green if `record.completed`, amber if not (the *only*
   signal `SessionRecord` carries is `completed: bool`, so Den-O shows
   "finished naturally" vs. "ended early," never pretends to distinguish
   a skip from a reset since that's not data the model records). These
   two colors are **local constants in `den_o.py`**, not imported from
   `ui.py`'s `COLOR_BREAK`/`COLOR_WARN` — `ui.py` imports `TIER5_BUILDERS`
   *from* the `tier5` package, so a Rider module importing color
   constants back out of `ui.py` would be circular, the exact same
   problem `format_hm` hit above. `den_o.py` defines its own
   `_COMPLETED_COLOR`/`_ENDED_EARLY_COLOR` set to the same hex values as
   `ui.py`'s `COLOR_BREAK`/`COLOR_WARN`, with a comment cross-referencing
   them, so the app's "green = good, amber = caution" language stays
   visually consistent without a code dependency in either direction.
3. **Empty state** — when `sorted_blocks(...)` is empty for the current
   day: one centered `CTkLabel`, `"No focus blocks on this day."` — the
   same message regardless of which day or why it's empty (see "Day
   navigation" above).

## Wiring summary

- `session.py`, `history.py`'s recording path, and `ui.py`'s phase hooks
  are unaffected beyond the two new store methods above (both pure
  reads/lookups, no new writes). `_build_tier5_tab()` in `ui.py` (added
  for V3) needs no change at all — it already just calls
  `TIER5_BUILDERS[effect](frame, history=..., tasks=..., theme=...,
  appearance_mode=...)`, and Den-O's `build()` fits that exact signature.
- No new config field. Den-O has nothing to persist — the currently
  viewed day is deliberately ephemeral, like Kabuto's hover-reveal state
  or Fourze's constellation progress.

## Error handling

Same posture as every other store/Rider in this codebase:
`HistoryStore.earliest_date()` on an empty store returns `None`, not an
exception. `TaskStore.get()` on an unknown id returns `None`, not a
`KeyError` — `resolve_task_name` is exactly the function that turns
that `None` into the user-facing `"Deleted task"` rather than every
caller having to know to guard against it. A `state["day"]` that somehow
ends up before `earliest_date()` or after today (it can't, given the
button-disabling above, but a hand-edited `sessions.jsonl` changing
`earliest_date()` out from under an already-open tab is at least
conceivable) still just renders whatever `for_date()` returns for that
day — empty or not — never a crash.

## Testing

- `tests/test_history.py` *(grows)* — `earliest_date()`: `None` on an
  empty store; the single day on a one-record store; the minimum date
  across several out-of-order records.
- `tests/test_tasks.py` *(grows)* — `get()`: returns the matching `Task`
  for a known id; `None` for an unknown id.
- `tests/test_tier5_shared.py` *(new)* — the 4 existing `_format_hm`
  assertions from `tests/test_tier5_v3.py`, moved here and importing
  `format_hm` from `lock_in.tier5._shared` instead (same assertions, new
  home, since the function itself moved). `tests/test_tier5_v3.py` loses
  those 4 tests — V3 no longer defines the function they were testing.
- `tests/test_tier5_den_o.py` *(new)* — `resolve_task_name`: all three
  branches (`None`, a known id, an unknown/dangling id). `sorted_blocks`:
  an out-of-order list comes back sorted by `start`; an empty list stays
  empty. `format_time_range`: formats a known start/end pair correctly.
  `format_day_heading`: a known date formats to the expected string, no
  platform-specific format codes used. All pure, no Tk.
- Manual, in the running app (same as V3 — no automated GUI test): the
  Timeline tab appears only for Den-O; a day with several blocks shows
  them earliest-first with correct times/durations/task names/dot
  colors; a task deleted after being logged shows "Deleted task"; an
  untagged block shows "No task"; Prev/Next move exactly one day; Prev
  disables at `earliest_date()` (or immediately, on a fresh install);
  Next disables at today; a genuinely empty ordinary day (not today, not
  the boundary) shows the empty-state line with both buttons still
  correctly enabled; switching to a different Rider or finishing a focus
  block resets the view back to today; light and dark mode both render
  correctly (the row styling reuses existing `COLOR_*` constants, which
  are already mode-aware tuples).

## Out of scope for this pass

- Editing or deleting a logged block from this view (Zi-O's job later —
  Den-O is read-only, exactly like the foundation spec said).
- Skip-to-nearest-day-with-data navigation (considered during
  brainstorming, explicitly not this pass — plain calendar-flip only).
- Any date-range or multi-day view, trends, or per-task breakdowns
  (Decade's job next).
- A jump-to-specific-date picker beyond Prev/Next (no Rider in this
  batch needs it yet).
- Any git/GitHub action — commands are handed to the user, never run
  here.

## File-by-file change list

**New**
- `lock_in/tier5/_shared.py` — `format_hm()` (moved out of `v3.py`'s
  private `_format_hm`).
- `lock_in/tier5/den_o.py` — `resolve_task_name()`, `sorted_blocks()`,
  `format_time_range()`, `format_day_heading()`, `build()`.
- `tests/test_tier5_shared.py`.
- `tests/test_tier5_den_o.py`.

**Edit**
- `lock_in/history.py` — `earliest_date()`.
- `lock_in/tasks.py` — `get()`.
- `lock_in/tier5/__init__.py` — `TIER5_BUILDERS["timeline_view"] = den_o.build`.
- `lock_in/tier5/v3.py` — import `format_hm` from `._shared` instead of
  defining its own `_format_hm`.
- `lock_in/rider_themes.py` — `tier5_effect="timeline_view"` on
  `Kamen Rider Den-O (2007)`.
- `tests/test_history.py`, `tests/test_tasks.py` — new method coverage.
- `tests/test_tier5_v3.py` — its 4 `_format_hm` tests move out (see
  `tests/test_tier5_shared.py` above).
- `tests/test_rider_themes.py` — the tier5 completeness check grows to
  expect two Riders now (V3 and Den-O), not one.

**Docs — same pattern as V3, added once this actually ships**
- `README.md`'s Tier 5 subsection gains a Den-O bullet, next to V3's.
- `lock_in/ui.py` Help tab's Tier 5 section gains a Den-O bullet.
- `__version__`: to be decided once this (and, per the current plan,
  Decade alongside it) is actually complete — matching how every prior
  tier only bumped the version at the end of its own work.
