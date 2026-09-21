# Lock In: Tier 5 Rider #6 — W, the week-vs-week chart

Date: 2026-09-21
Status: Draft, waiting for review

## Goal

The sixth of Tier 5's 10 Riders, built on the shared `tier5_effect` /
`lock_in/tier5/` plumbing that V3, Den-O, Decade, Zi-O, and Blade already
established. W is two Riders sharing one body (Cyclone, green, and Joker,
black), so W's tab puts **two weeks side by side**: the last 7 days
against the 7 days right before them.

When Kamen Rider W (2009) is the picked Rider, a **"Week"** tab shows:

1. Two total lines, **This week** and **Last week**.
2. One plain sentence saying which one is bigger.
3. A **paired bar chart**: 7 groups of two bars, one group per day.

Like V3, Den-O, Decade, and Blade, W is a *read-only* view. It reads the
same focus-block history the other tabs read. It saves nothing, changes
nothing, and needs **no new setting and no new data-model change**.

## What "this week" and "last week" mean

Decided during brainstorming: the last 7 days against the 7 days before
them, **not** Monday-to-Sunday calendar weeks.

- **This week** = today and the 6 days before it.
- **Last week** = the 7 days right before those.
- Every day in "this week" has a partner exactly 7 days earlier in
  "last week". Bars are paired by that partner, so Thursday sits next to
  the Thursday before it.

Why: it is always 7 full days against 7 full days, so the comparison is
fair on every day of the week. With calendar weeks, a Tuesday would
compare 2 days to 7 and need a "so far" rule to avoid saying "you're way
behind!" on Monday. Nothing here needs that rule. Same as V3 and Decade,
**today is the last (rightmost) group**.

Every focus block counts, whether it finished, was skipped, or was reset
early. That is the same rule V3 and Decade already use, and it is stated
on the tab so nobody is surprised.

## The tab

Tab label **"Week"**; `Kamen Rider W (2009)` gets
`tier5_effect="week_compare"`. The tab sits next to Help, exactly like
every other Tier 5 tab, and is hidden by Standard Mode and by picking a
non-Tier-5 Rider, through the existing mechanism (no new code for that).

Layout, top to bottom, inside a `CTkScrollableFrame` (matching every
other tab):

1. **Empty state first.** If `history.all()` is empty, show the exact
   line V3 and Decade show, `"No focus blocks yet. Finish one and it
   shows up here."`, and stop. No totals, no sentence, no chart.
2. **Two total lines.**
   - `This week` on the left, its total on the right, in
     `theme.primary_text_pair` (W's green).
   - `Last week` on the left, its total on the right, in
     `theme.secondary_text_pair` (W's black in light mode, a light grey in
     dark mode).
   - The two colors match the two bar colors, so these lines are also the
     chart's legend. There is no separate legend to draw.
3. **One sentence** from `compare_sentence()` (below).
4. **The paired bar chart**, 440×200 (the same size as V3's chart; 7
   groups fit comfortably at that width). Last week's bar is on the left
   in each group and this week's is on the right, so time reads left to
   right inside a group too.
5. **Caption** under the chart: `"Last 7 days vs the 7 days before ·
   every focus block counts, finished or not"`. Same small gray style as
   V3's caption.

`tasks` and `appearance_mode` are part of every Tier 5 builder's
signature for consistency. W uses neither, for the same reason V3 and
Decade don't: CustomTkinter's `(light, dark)` color tuples and
`CTkImage(light_image=, dark_image=)` already cover light and dark.

## Colors

- **This week's bar:** `theme.primary` (W: green).
- **Last week's bar:** `theme.secondary` (W: black in light mode, grey in
  dark mode).

This differs from V3, where `secondary` marks *today*. Here `secondary`
means *last week*, so there is no separate "today" highlight. Today is
already obvious because it is the rightmost group.

## The words on screen

Every visible word is meant to be understood by a young child.

| Situation | Sentence |
|---|---|
| This week is more (by a minute or more) | `You did {diff} MORE than last week. Yay!` |
| This week is less (by a minute or more) | `That's {diff} less than last week. You can do it!` |
| Within a minute of each other (but not both zero) | `Same as last week. Nice and steady!` |
| Both weeks are zero (older history exists, nothing recent) | `No focus blocks in the last 14 days. Start one and it shows up here.` |

`{diff}` is the positive gap, written with the shared `format_hm()`
("1h 40m", "30m"). "Within a minute" means a gap under 60 seconds. The
gap is never shown as "0m MORE".

The "less" sentence is deliberately kind: it says the gap plainly and
then cheers. It never says "behind", "worse", or "failed".

## New code

### `lock_in/tier5/w.py` (new)

Two small pure functions, tested with no Tk and no display server, plus
the one Tk-dependent `build()`:

- **`week_pairs(totals: dict[str, int], today: date) -> list[tuple[date, int, int]]`**
  Returns exactly 7 tuples `(day, last_week_seconds, this_week_seconds)`,
  oldest to newest, where `day` is the *this-week* date. It calls the
  existing `last_n_days(totals, today, 14)` from `tier5/_shared.py`: the
  first 7 entries are last week, the last 7 are this week, and entry `i`
  of one pairs with entry `i` of the other. A day with no focus blocks
  contributes 0. No new day-math is written.
- **`compare_sentence(this_seconds: int, last_seconds: int) -> str`**
  Picks one sentence from the table above.
- **`build(parent, *, history, tasks, theme, appearance_mode) -> None`**
  Builds the tab described above. Week totals are simply the sums of the
  two columns of `week_pairs()`.

`w.py` imports only from `..visuals`, `._shared`, and `customtkinter`.
It does not import from `tier5/__init__.py`, `v3.py`, `den_o.py`, or
`decade.py`, so there is no circular-import risk (see `_shared.py`'s own
docstring for why that matters).

### `lock_in/visuals.py` (one new function)

**`make_week_compare_chart(width, height, pairs, this_color, last_color, dark, era="Showa") -> Image.Image`**
where `pairs` is a list of `(iso_day, last_seconds, this_seconds)`.

It is a sibling of `make_hours_chart()` and follows the same rules:

- RGBA image at the requested size, see-through background.
- Both weeks share **one height scale** (the largest value in either
  week), so a bar's height means the same thing on both sides. A day with
  0 seconds draws no bar. All-zero input never divides by zero.
- Each group is two bars side by side with a small gap between them, and
  a larger gap between groups. The weekday letter goes under the group's
  center, taken from the this-week date, exactly like
  `make_hours_chart()`'s label code.
- Light and dark modes pick different label colors, as V3's chart does.
- The era accent along the baseline reuses `make_panel_divider()`, the
  same as `make_hours_chart()`.
- An empty `pairs` list returns a blank image instead of crashing.

`make_hours_chart()` itself is **not changed**. V3's and Decade's charts
are untouched, so nothing already shipped can regress. A separate function
was chosen over adding an optional second series to `make_hours_chart()`
for that reason.

## Wiring summary

- `lock_in/tier5/__init__.py`:
  `TIER5_BUILDERS["week_compare"] = w.build`, plus `w` in the import line.
- `lock_in/rider_themes.py`: `tier5_effect="week_compare"` on
  `Kamen Rider W (2009)`.
- `lock_in/ui.py`: one line, `_TIER5_TAB_LABELS` gains
  `"week_compare": "Week"`. The tab build, the tab refresh after a
  finished block, and the show/hide logic already handle any registered
  effect and need no change.
- No new config field, no new write path, no new file on disk.

## Error handling

Same posture as V3 and Decade. There is nothing new that can fail:

- Empty history: the empty-state line above, then `build()` returns
  before touching the chart.
- History that exists but is older than 14 days: both totals are 0, and
  the "No focus blocks in the last 14 days" sentence shows with an empty
  (zero-height) chart.
- Blocks older than 14 days are simply outside the window.
- A `CTkImage` is garbage-collected when nothing holds it, which would
  blank the chart at the next redraw. As V3 and Decade do, `build()` keeps
  a reference on the chart label (`chart_label._w_chart_image = ...`).

## Testing

- `tests/test_tier5_w.py` *(new)*: `week_pairs()` and
  `compare_sentence()`, no Tk.
  - `week_pairs()`: always exactly 7 tuples; oldest to newest, ending on
    today; each this-week day pairs with the same weekday 7 days earlier;
    a day with no blocks is 0 on that side; last week and this week are
    not mixed up (a block today lands in the *this* column of the last
    tuple, a block 7 days ago in the *last* column of the last tuple);
    a window that crosses a month boundary and one that crosses a year
    boundary both pair correctly; a block 14 or more days old is ignored.
  - `compare_sentence()`: more, less, same; a gap of exactly 59 seconds
    reads as "same"; a gap of exactly 60 seconds reads as more/less; both
    zero gives the "no focus blocks" sentence; the gap is formatted with
    `format_hm()` (for example `"1h 40m"`); the "less" sentence never
    contains "behind", "worse", or "fail".
- `tests/test_visuals.py` *(grows)*: `make_week_compare_chart()` returns
  the requested size in RGBA; handles an empty list; handles all-zero
  days without dividing by zero; in a group where both weeks are equal,
  the left bar's pixels are `last_color` and the right bar's are
  `this_color`; both weeks use one shared scale (a 100 next to a 50 draws
  the 50 bar half as tall, on either side); light and dark renders
  differ; the default era matches `"Showa"`; each era looks different.
- `tests/test_rider_themes.py` *(grows)*: the tier5 completeness check now
  expects six Riders, adding `"Kamen Rider W (2009)": "week_compare"`. The
  test is renamed to say six.
- **Manual, in the running app** (same as every other tab, no automated
  GUI test): the "Week" tab appears only for W; a fresh install shows the
  empty state and nothing else; with history, the two lines, the
  sentence, and the chart all show; this-week bars are green and
  last-week bars are black or grey; the totals equal the sum of the bars;
  light and dark mode both read clearly; finishing a block while the tab
  is open refreshes it; switching to a non-Tier-5 Rider or turning on
  Standard Mode hides the tab, and turning Standard Mode back off
  restores it.

## Docs, version, and repo hygiene

- `README.md`, Tier 5 section: add a **W** bullet in the same plain
  words, and change "these five are just the first of ten planned" to
  six.
- `lock_in/ui.py`, Help tab: add a W bullet, and change "these five are
  just the first" to six.
- `__version__`: `2.5.5` to **`2.5.6`**.
- `.gitignore`: nothing new is generated, so no change is expected. It
  is re-checked when this ships.
- Committing, pushing, and tagging are done by the project owner. The
  exact commands are handed over at the end, with a plain commit message.

## Out of scope for this pass

- Picking a different pair of weeks (no back/forward buttons).
- A per-task split inside a week (Decade already ranks tasks).
- Goals, targets, or streaks (a better fit for Geats).
- Weekday averages or any trend line.
- Calendar (Monday-to-Sunday) weeks.
- The other four Tier 5 Riders (OOO, Gotchard, Geats, MY-TH), each of
  which gets its own spec.

## File-by-file change list

**New**
- `lock_in/tier5/w.py`: `week_pairs()`, `compare_sentence()`, `build()`.
- `tests/test_tier5_w.py`.
- `docs/superpowers/plans/2026-09-21-tier5-w-week-compare.md`: the
  implementation plan (written after this spec is approved).

**Edit**
- `lock_in/visuals.py`: `make_week_compare_chart()`.
- `lock_in/tier5/__init__.py`: one registry entry.
- `lock_in/rider_themes.py`: `tier5_effect="week_compare"` on W.
- `lock_in/ui.py`: `_TIER5_TAB_LABELS` entry, Help tab bullet and wording.
- `lock_in/__init__.py`: version to 2.5.6.
- `tests/test_visuals.py`, `tests/test_rider_themes.py`: as described
  above.
- `README.md`: Tier 5 bullet and count wording.
