# Lock In: Tier 5 Rider #3 — Decade, the analytics dashboard

Date: 2026-09-14
Status: Approved, ready for implementation plan

## Goal

The third of Tier 5's 10 Riders, built on the shared `tier5_effect` /
`lock_in/tier5/` plumbing V3 and Den-O already established (see their
specs, `2026-09-05-tier5-v3-daily-hours-design.md` and
`2026-09-14-tier5-deno-timeline-design.md`). Decade is explicitly the
"richer dashboard on top of V3 and Den-O" — this pass scopes that down
to two concrete pieces, both wider-lens reads of data those two Riders
already expose, no new interaction:

1. A **30-day version of V3's bar chart** — same rendering, wider window.
2. A **"Top tasks" ranking** — every task with any logged time, sorted
   by total time spent, descending.

When Kamen Rider Decade (2009) is the picked Rider, an "Analytics" tab
shows both, stacked.

## Three things move to (or grow in) the shared module

Following the exact pattern `format_hm` set when Den-O needed it too:

- **`last_14_days` generalizes to `last_n_days(totals, today, n)`** in
  `tier5/_shared.py`. `v3.py` calls it with `n=14`; Decade calls it with
  `n=30`. `last_14_days` stops existing as its own function — one
  function, two window sizes, instead of two near-identical copies.
  `tests/test_tier5_v3.py`'s existing `last_14_days` tests move to
  `tests/test_tier5_shared.py`, calling `last_n_days(..., n=14)`
  (behavior unchanged, only the name and home change), and gain a
  parallel `n=30` case for Decade's actual usage.
- **`resolve_task_name` moves from `den_o.py` to `tier5/_shared.py`.**
  Decade's ranking needs the exact same "id → name / 'No task' /
  'Deleted task'" logic Den-O already built. Importing it back out of
  `den_o.py` would be the same circular-import shape `format_hm` almost
  hit in V3's spec. `den_o.py` updates its import; its own 3
  `resolve_task_name` tests move to `tests/test_tier5_shared.py` too.
- **New `HistoryStore.total_seconds_by_task() -> Dict[Optional[str], int]`**
  (`lock_in/history.py`) — mirrors `total_seconds_by_day()` exactly,
  grouped by `task_id` instead of by calendar day. The `None` key holds
  every untagged block's total — real focused time, not something to
  hide from the ranking.

After this pass, `tier5/_shared.py` holds `format_hm`, `last_n_days`,
and `resolve_task_name` — three small, Rider-agnostic building blocks,
none of which import anything from `v3.py`, `den_o.py`, or
`tier5/__init__.py`.

## Decade's own pure function, in `lock_in/tier5/decade.py`

- **`ranked_tasks(totals_by_task: dict[Optional[str], int], tasks: TaskStore) -> list[tuple[str, int]]`**
  — resolves every `task_id` key through `resolve_task_name()`, sorts
  the resulting `(name, seconds)` pairs by `seconds` descending, and
  returns **at most the top 10**. A task with zero logged time never
  appears at all — there's nothing to rank; only `task_id`s that
  actually show up in history do.

**Why a cap, decided during review:** an account with many months of
history and dozens of small one-off tasks would otherwise render one
row per task forever — a long, low-value scroll, and more CTk row
widgets than the view needs. Ten is enough to answer "what have I
actually been spending time on" at a glance; it isn't a "show more"
feature, just a hard `[:10]` slice after sorting, applied inside
`ranked_tasks()` itself so the cap is part of the function's contract,
not something every caller has to remember to apply.

**On duplicate "Deleted task" rows:** if two *different* tasks were
both deleted after being logged against, `ranked_tasks` shows them as
two separate rows, both labeled "Deleted task," each with its own
total — not merged into one. `resolve_task_name` has no way to tell two
dangling ids apart by name (that information left with the deleted
task), and merging them would need new logic for a case this pass
doesn't need to solve. Accepted as-is, same spirit as V3/Den-O not
inventing machinery a real usage pattern hasn't asked for yet.

## The tab

Tab label **"Analytics"**; `Kamen Rider Decade (2009)` gets
`tier5_effect="analytics_dashboard"`.

Layout, top to bottom, inside a `CTkScrollableFrame` (matching every
other tab):

1. **Empty state first** — if `history.all()` is empty, show the exact
   same line V3 does (`"No focus blocks yet. Finish one and it shows up
   here."`) and stop — no chart, no "Top tasks" heading, nothing to rank.
2. **30-day chart** — `visuals.make_hours_chart()` reused exactly as
   V3 built it (it already generalizes over any number of bars), called
   with `last_n_days(totals_by_day, today, 30)`. Rendered at
   **640×200**, not V3's 440×200 — 30 bars at V3's width would be
   roughly 11px each with the existing 4px gaps; 640px keeps each bar
   close to V3's own ~19px, so Decade's chart doesn't read as a cramped
   version of V3's. Same light/dark `CTkImage` pairing V3 uses, same
   `theme.era` accent. Caption underneath: `"Last 30 days"`.
3. **"Top tasks" heading**, then one plain row per `ranked_tasks()`
   entry (at most 10): the name on the left, `format_hm(seconds)` on
   the right. No dot or colored border here — unlike Den-O's rows,
   there's no per-block outcome to color-code, just a name and a total.

`tasks` is used (for the ranking); `appearance_mode` is unused, same
reasoning as V3 and Den-O — CustomTkinter's native `(light, dark)`
tuples and `CTkImage(light_image=, dark_image=)` already cover it.

## Wiring summary

- No new config field, no new write path. Decade is two reads
  (`total_seconds_by_day`, now-new `total_seconds_by_task`) plus the
  chart renderer and a sort — nothing it touches can fail in a way that
  needs new error handling beyond what those already have.
- `_build_tabs()` / `_build_tier5_tab()` / the `_on_phase_ended()`
  refresh hook in `ui.py` need **zero changes** beyond the one-line
  `_TIER5_TAB_LABELS` addition — the mechanism built for V3 and already
  proven generic for Den-O handles a third registered effect exactly
  the same way.

## Error handling

Same posture as every other store/Rider in this codebase.
`total_seconds_by_task()` on an empty store returns `{}`, not an
exception — `ranked_tasks({}, tasks)` then returns `[]`, and `build()`
never reaches that code path anyway since the empty-state check above
already returned first. `resolve_task_name` (already shipped with
Den-O) already turns a dangling `task_id` into `"Deleted task"` rather
than crashing; `ranked_tasks` inherits that for free.

## Testing

- `tests/test_history.py` *(grows)* — `total_seconds_by_task()`: `{}`
  on an empty store; sums multiple records against the same `task_id`;
  keeps different `task_id`s (including `None`, for untagged blocks)
  separate.
- `tests/test_tier5_shared.py` *(grows)* — `last_n_days()`: the 5
  existing `last_14_days` assertions (count, ordering, zero-fill, month
  boundary, year boundary) re-homed with `n=14`, plus a parallel count
  check with `n=30`. `resolve_task_name()`: the 3 existing assertions
  from `tests/test_tier5_den_o.py` (`None`, a known id, a dangling id),
  re-homed unchanged.
- `tests/test_tier5_v3.py`, `tests/test_tier5_den_o.py` — lose the tests
  that moved above; keep everything specific to their own Rider.
- `tests/test_tier5_decade.py` *(new)* — `ranked_tasks()`: sorts
  descending by seconds; resolves a real task's id to its name; an
  empty input returns an empty list; a `None` key (untagged time)
  appears as `"No task"` at its correct rank; two different dangling
  ids both surface as separate `"Deleted task"` rows rather than being
  merged (pins the "on duplicate Deleted task rows" behavior above);
  **more than 10 entries come back truncated to exactly the top 10 by
  seconds** — the 11th-highest and below never appear.
- `tests/test_rider_themes.py` — the tier5 completeness check grows to
  expect three Riders now (V3, Den-O, Decade).
- Manual, in the running app (same as V3/Den-O — no automated GUI
  test): the Analytics tab appears only for Decade; a fresh install
  shows the empty state and nothing else; the 30-day chart renders at
  the wider size with today's bar in `secondary`; the ranking lists up
  to 10 tasks, correctly sorted, with "No task" and "Deleted task" (if
  applicable) appearing like any other row where they rank; with 11 or
  more tasks logged, exactly 10 show and the smallest ones don't; light
  and dark modes both render; switching to a
  non-Tier-5 Rider or turning on Standard Mode hides the tab; turning
  Standard Mode back off (with Decade still selected) restores it.

## Out of scope for this pass

- Any drill-down (clicking a task row to see its own history — that's
  closer to what Den-O/Zi-O already do or will do).
- Any UI to see *past* the top 10 (no "show more," no pagination, no
  scrolling to reveal an 11th row) — the cap is a hard limit for this
  pass, not a default page size.
- Per-task trend charts, week-over-week comparison, streaks, or any
  other "richer" analytics beyond the two pieces this spec scopes.
- The other 7 Tier 5 Riders (W, OOO, Zi-O, Gotchard, Geats, Blade,
  MY-TH) — each gets its own spec.
- Any git/GitHub action — commands are handed to the user, never run
  here.

## File-by-file change list

**New**
- `lock_in/tier5/decade.py` — `ranked_tasks()`, `build()`.
- `tests/test_tier5_decade.py`.

**Edit**
- `lock_in/history.py` — `total_seconds_by_task()`.
- `lock_in/tier5/_shared.py` — `last_n_days()` (replaces `v3.py`'s
  `last_14_days`), `resolve_task_name()` (moved from `den_o.py`).
- `lock_in/tier5/v3.py` — call `last_n_days(totals, today, 14)` instead
  of a locally-defined `last_14_days()`.
- `lock_in/tier5/den_o.py` — import `resolve_task_name` from `._shared`
  instead of defining its own.
- `lock_in/tier5/__init__.py` — `TIER5_BUILDERS["analytics_dashboard"] = decade.build`.
- `lock_in/rider_themes.py` — `tier5_effect="analytics_dashboard"` on
  `Kamen Rider Decade (2009)`.
- `lock_in/ui.py` — one line: `_TIER5_TAB_LABELS` gains
  `"analytics_dashboard": "Analytics"`.
- `tests/test_history.py` — new method coverage.
- `tests/test_tier5_shared.py`, `tests/test_tier5_v3.py`,
  `tests/test_tier5_den_o.py` — tests move as described above.
- `tests/test_rider_themes.py` — the tier5 completeness check grows to
  three Riders.

**Docs — same pattern as V3/Den-O, added once this actually ships**
- `README.md`'s Tier 5 subsection gains a Decade bullet.
- `lock_in/ui.py` Help tab's Tier 5 section gains a Decade bullet.
- `__version__`: to be decided once this ships — per the current
  session, this and Den-O land together as one version bump, not two.
