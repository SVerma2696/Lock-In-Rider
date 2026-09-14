# Lock In: Tier 5 Rider #1 — V3, the daily hours tracker

Date: 2026-09-05
Status: Approved, ready for implementation plan

## Goal

The first of Tier 5's 10 Riders. Tier 5's foundation — the task/history
data model in `lock_in/tasks.py` and `lock_in/history.py` — shipped
already (see `2026-09-04-tier5-tasks-history-design.md`). This spec builds
the first UI on top of it: **when Kamen Rider V3 (1973) is the picked
Rider, a "Hours" tab appears showing how much you've focused today and a
14-day bar chart.**

It is deliberately the smallest of the 10. It reads one aggregate that
`HistoryStore` already exposes for exactly this purpose
(`total_seconds_by_day()`), adds no store logic, and changes no data
model. It also establishes the shared plumbing every later Tier 5 Rider
reuses: a `tier5_effect` field, a `lock_in/tier5/` package, and a dynamic
6th tab in `ui.py`.

## The shared Tier 5 mechanism (built here, reused by all 10)

Unlike Tiers 1–4, whose Riders share one mechanism (a progress-bar
shape, a settings preset, an enforcement tweak, a display mode), Tier 5's
10 Riders are 10 different UIs. What they share is only *how they surface*:

### `tier5_effect` on `RiderTheme`

`lock_in/rider_themes.py` gains one field on the `RiderTheme` dataclass:

```python
tier5_effect: str = "none"
```

Exactly like the existing `tier1_effect` / `tier3_effect` /
`tier4_effect`. Every Rider defaults to `"none"`. `Kamen Rider V3 (1973)`
is set to `tier5_effect="hours_tab"`. The other 9 Tier 5 Riders get their
own string as each is built.

`tests/test_rider_themes.py` gains a completeness check — `tier5_effect`
is present and is a `str` on all 38 Riders — mirroring the tier1/3/4
checks already there.

### `lock_in/tier5/` package — one module per Rider

A new package. Each Rider is one small, self-contained module exposing a
single builder with a fixed signature:

```python
# lock_in/tier5/v3.py
def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """Populate `parent` (an empty tab frame) with this Rider's view."""
```

`lock_in/tier5/__init__.py` maps effect string → builder:

```python
from . import v3

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    # grows one line per Rider
}
```

`tasks` is in every builder's signature for uniformity even when a given
Rider ignores it (V3 does). `appearance_mode` is the string from
`ctk.get_appearance_mode()` at build time.

**Why a package, not methods in `ui.py`:** `ui.py` is already ~3000
lines. Ten Rider views as `_build_*_tab` methods would push it past 4500
and mix ten unrelated concerns into one file. One module per Rider
matches the one-concern-per-file pattern `config.py` / `session.py` /
`classifier.py` / `enforcer.py` already establish, keeps each Rider
independently readable and testable, and means each later Rider's spec
touches essentially one new file plus two one-line registrations
(`TIER5_BUILDERS` and `_TIER5_TAB_LABELS`).

### Dynamic 6th tab in `ui.py`

**As actually implemented** (revised from this section's original
design while writing the implementation plan — see
`docs/superpowers/plans/2026-09-14-tier5-v3-daily-hours.md`'s "Deviation
from the approved spec" note): `ui.py` already had a mechanism that does
this job. `_rebuild_tabs()` destroys and rebuilds the whole
`CTkTabview` from scratch, via `_build_tabs()`, on every Rider /
Standard-Mode / wording change — and `_build_tabs()` always runs after
`self.tasks`, `self.history`, and `self.current_tier5_effect` already
exist. So no bespoke add/delete tab-lifecycle method was needed:

- `_TIER5_TAB_LABELS = {"hours_tab": "Hours"}` — a small map in `ui.py`,
  effect string → tab label. Grows one line per Rider.
- `_apply_rider_theme()` stores `self.current_tier5_effect =
  theme.tier5_effect` and `self._current_rider_theme = theme` (the
  resolved theme object, needed by the tab builder below) — plain state,
  no tab manipulation at this point.
- `_build_tabs()` conditionally adds the tier5 tab
  (`self.tabs.add(_TIER5_TAB_LABELS[effect])`) right after the five
  fixed tabs, then calls a new `_build_tier5_tab()`, which looks up
  `TIER5_BUILDERS[effect]` and calls it with `history=self.history,
  tasks=self.tasks, theme=self._current_rider_theme,
  appearance_mode=ctk.get_appearance_mode()`.
- `_build_tier5_tab()` is also called directly (not via a full
  `_rebuild_tabs()`) from `_on_phase_ended()`, right after the history
  write, whenever `current_tier5_effect != "none"` — this refreshes just
  the Hours tab's content in place so a finished block shows up
  immediately, without rebuilding the other five tabs.
- No `hasattr` startup guard is needed: `_build_tabs()` is only ever
  called after `self.tasks`/`self.history` are constructed, both at
  startup and from every `_rebuild_tabs()` call site.
- **Standard Mode** already neutralises every other tier's effect via
  `STANDARD_THEME` (which, having no `tier5_effect` kwarg, defaults to
  `"none"` like every other tier) — so no separate Standard-Mode
  neutralisation code was needed either.

## V3 itself

### What it reads

A pure read of `history.total_seconds_by_day()` →
`{'2026-09-05': 9000, ...}`. No new `HistoryStore` method.

One pure, Tk-free function in `lock_in/tier5/v3.py` does the shaping:

```python
def last_14_days(totals: dict[str, int], today: date) -> list[tuple[date, int]]:
    """14 entries, oldest -> newest, ending on `today`.
    Days absent from `totals` contribute 0."""
```

- The chart always has 14 bars, even on a fresh install (all zero) — no
  special-casing a short history in the renderer.
- **Headline number** = `totals.get(today.isoformat(), 0)`, run through
  `_format_hm(seconds)` → `"2h 40m"`, `"40m"`, or `"0m"`.
- "Today" is defined by `date.today()` in local time, matching
  `total_seconds_by_day()`, which already keys each record by
  `datetime.fromisoformat(r.start).date()` — a block that starts at 11:50pm
  and ends after midnight counts entirely on its start day. V3 inherits
  that definition rather than introducing its own.
- **Every logged block counts** — `completed=True` and `completed=False`
  alike. `total_seconds_by_day()` already sums all of them; "hours
  focused" means time the focus timer was actually running, whether or
  not the block was seen through to the end. (Decided during
  brainstorming: a block skipped one minute early still had real focus
  time in it, and filtering would mean re-implementing the aggregate V3
  is meant to just read.)

### The tab layout

`lock_in/tier5/v3.py :: build(parent, *, history, tasks, theme, appearance_mode)`.
Everything sits inside a `CTkScrollableFrame` (every other tab does), top
to bottom:

1. **Headline** — a `CTkLabel` with the `"2h 40m"` string in the display
   font (`visuals.display_font_family()`), large, tinted
   `theme.primary_text_pair`; a smaller `"focused today"` label beneath.
2. **Chart** — a single `CTkLabel(image=chart_image)` where `chart_image`
   is one `ctk.CTkImage(light_image=<light>, dark_image=<dark>,
   size=(440, 200))`. Both PIL images are generated in `build()` by
   calling `make_hours_chart()` twice (once `dark=False`, once
   `dark=True`) and handed to CustomTkinter, which swaps them on OS / app
   appearance-mode changes with no redraw hook needed. Fixed 440×200 in
   this pass — no resize-on-`<Configure>` re-render (the divider does
   that at `ui.py:651` and it is a known-fiddly bit V3 does not need to
   be useful).
3. **Caption** — a small muted `CTkLabel`:
   `"Last 14 days · every focus block counts, finished or not"`.
4. **Empty state** — when `history.all()` is empty: no chart is built at
   all, just one centered `CTkLabel` —
   `"No focus blocks yet. Finish one and it shows up here."` The headline
   still renders (`"0m focused today"`).

`tasks` is unused by V3.

### `visuals.py :: make_hours_chart(...)`

```python
def make_hours_chart(
    width: int, height: int, day_values: list[tuple[str, int]],
    primary: str, secondary: str, dark: bool, era: str = "Showa",
) -> Image.Image:
```

Same shape as `make_panel_divider` and the `render_*_progress` family:
plain colors, a `dark: bool`, an `era: str`, returns a `PIL.Image.Image`,
and knows nothing about Riders, tabs, or CustomTkinter. `ui.py` /
`tier5/v3.py` decide what to do with the image.

- `day_values`: 14 `(iso_day, seconds)` pairs, oldest → newest. (The
  caller passes `date.isoformat()` strings; the renderer only needs the
  weekday letter and the value.)
- Transparent RGBA canvas of `width × height`.
- Bottom ~18px reserved for one-letter weekday labels
  (`date.fromisoformat(day).strftime("%a")[0]` → `M T W T F S S`), drawn
  in muted grey with `ImageDraw`'s built-in bitmap font — the existing
  `_draw_*` helpers load no font file, and neither does this.
- `max_secs = max(secs for _, secs in day_values) or 1`; each bar's
  height is `plot_area_height * secs / max_secs`. 2px gaps between bars.
- Bars filled with `primary` (already the correct shade for this
  `dark` value, since `ui.py` passes the mode's own hex). **The last bar
  — today — is filled with `secondary`** so it stands out from the
  history behind it.
- **Era accent.** `era == "Showa"` (V3): a faint tick-mark baseline
  beneath the bars, reusing `_draw_tick_divider`'s visual idea.
  `era == "Heisei"`: a row of tiny diamonds. `era == "Reiwa"`: small
  circuit nodes. All three branches are written now — Decade (Heisei) and
  Den-O (Heisei) reuse this function unchanged later, so its era handling
  is finished in this pass rather than retrofitted.

## Wiring summary

- `session.py` is untouched — it stays as unaware of tasks, history, and
  Tier 5 tabs as it already is of windows and blocking. This is an
  additive change at the `ui.py` layer plus one new `visuals.py`
  function plus a new leaf package.
- The only `ui.py` call sites that touch Tier 5 are `_apply_rider_theme()`
  (sync the tab) and `_on_phase_ended()` (refresh the Hours number). They
  do not call into `tasks.py` or `history.py` beyond the already-existing
  `self.history` read.
- No new config field. V3 has nothing to persist.

## Error handling

Same posture as the rest of the codebase. `history.total_seconds_by_day()`
and `history.all()` already tolerate a missing or partly-corrupt
`sessions.jsonl` (per-line skip). `make_hours_chart` guards the
divide-by-zero on an all-zero / empty input. A malformed ISO day string
from a hand-edited `sessions.jsonl` is already dropped at
`HistoryStore.load()` time, so `last_14_days` and the renderer never see
one. If `_sync_tier5_tab()` is somehow handed an unknown effect string
(a `config.json` naming a Rider the code doesn't have a builder for), it
treats it as `"none"` — no tab, no crash — matching how an unrecognised
`rider_theme` already falls back to the default.

## Testing

- `tests/test_tier5_v3.py` *(new)* — `last_14_days()`: returns exactly 14
  entries; oldest → newest ordering; days absent from `totals` come back
  as 0; `today` is the last entry; correct behaviour across a
  month boundary and a year boundary. `_format_hm()`: `0 -> "0m"`,
  `600 -> "10m"`, `9000 -> "2h 30m"`, `3600 -> "1h 0m"`. All pure, no Tk,
  no display server.
- `tests/test_visuals.py` *(grows)* — `make_hours_chart()`: returned
  image size equals `(width, height)`; an all-zero `day_values` and an
  empty list both render without dividing by zero; 14 values produce 14
  visually distinct bar regions; a pixel sampled from the last bar is
  `secondary`, not `primary`; the light (`dark=False`) and dark
  (`dark=True`) renders differ; the function runs for `era` in
  `{"Showa", "Heisei", "Reiwa"}`.
- `tests/test_rider_themes.py` *(grows)* — `tier5_effect` present and a
  `str` on all 38 Riders; exactly one Rider (`Kamen Rider V3 (1973)`) has
  `tier5_effect == "hours_tab"`.
- Manual, in the running app (same as every prior tier — no automated GUI
  test): V3 selected shows the Hours tab; a non-Tier-5 Rider does not;
  Standard Mode does not; light and dark modes both render; fresh install
  shows the empty state; after finishing a block the today number and the
  last bar update without a tab switch.

## Out of scope for this pass

- Streak counter, a daily goal, a goal line (all offered during
  brainstorming and cut — a later Rider may add them).
- Any range other than a fixed last-14-days; no scrolling back through
  older history (Den-O / Decade).
- Re-rendering the chart on tab resize (fixed 440×200).
- Per-task breakdown of the hours (Decade).
- Clicking a bar to open that day's blocks (Den-O).
- The other 9 Tier 5 Riders — each gets its own spec.
- Any git / GitHub action — all commands are handed to the user at the
  very end, after Rider #10.

## File-by-file change list

**New**
- `lock_in/tier5/__init__.py` — `TIER5_BUILDERS` (one entry).
- `lock_in/tier5/v3.py` — `last_14_days()`, `_format_hm()`, `build()`.
- `tests/test_tier5_v3.py`.

**Edit**
- `lock_in/rider_themes.py` — `tier5_effect: str = "none"` on
  `RiderTheme`; `tier5_effect="hours_tab"` on `Kamen Rider V3 (1973)`.
- `lock_in/visuals.py` — `make_hours_chart()` with all three `era`
  branches.
- `lock_in/ui.py` — `self.current_tier5_effect` in `_apply_rider_theme()`;
  `_TIER5_TAB_LABELS`; `_sync_tier5_tab()`; calls from
  `_apply_rider_theme()` and `_on_phase_ended()`; Standard-Mode
  neutralisation of `tier5_effect`.
- `tests/test_visuals.py` — `make_hours_chart` cases.
- `tests/test_rider_themes.py` — `tier5_effect` completeness + the one
  `hours_tab` assignment.

**Docs — deferred, tracked per Rider**
- `README.md` — a new **Tier 5** subsection under "Kamen Rider theme",
  growing one plain-language bullet per Rider as each lands. The final
  language-simplification pass and the `.gitignore` check happen after
  Rider #10.
- `lock_in/ui.py` Help tab — a one-line V3 entry alongside the Tier 1–4
  gimmick list.
- `__version__` stays `2.5.0` (already set). The `v2.5.0` tag is the last
  step of the whole tier, after all 10 Riders — handed to the user as a
  command, never run here.
