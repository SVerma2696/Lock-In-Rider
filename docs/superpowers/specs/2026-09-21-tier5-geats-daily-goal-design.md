# Lock In: Tier 5 Rider #7 — Geats, the daily goal and streak

Date: 2026-09-21
Status: Approved

## Goal

The seventh of Tier 5's 10 Riders, built on the shared `tier5_effect` /
`lock_in/tier5/` plumbing that V3, Den-O, Decade, Zi-O, Blade, and W
already established. Geats' show is a game, so Geats' tab is a small
game: pick how many minutes you want to focus each day, fill a bar, and
keep a streak of days in a row where you reached it.

When Kamen Rider Geats (2022) is the picked Rider, a **"Goal"** tab shows:

1. **Today's bar**: how much you focused today against your daily goal.
2. **Goal buttons**: a minus and a plus that change the daily goal.
3. **The streak**: how many days in a row you reached the goal.
4. **Seven boxes**: the last 7 days, filled if the goal was reached.

Unlike V3, Den-O, Decade, Zi-O, Blade, and W, Geats is the first Tier 5
Rider that **remembers something**: one number, the daily goal. It still
reads the same focus-block history the other tabs read, and it never
changes that history.

The tab is called "Goal", not "Daily goal", to keep it short. X's
**goal gate** (the goal you type before a block starts) is a different,
older feature. In every word a person sees, this one is the **daily
goal**, so the two are never mixed up.

## The rules

Decided during brainstorming.

- **Setting the goal:** two buttons on the Geats tab itself, minus and
  plus. Each press changes it by **15 minutes**. There is no goal box in
  the Settings tab.
- **Range:** 15 minutes up to 12 hours. The minus button switches off at
  15 minutes and the plus button at 12 hours, so nobody can pick 0 or a
  negative goal. The starting goal is **1 hour**.
- **A day is "done"** when that day's total focus time is **at least** the
  goal. Every focus block counts, whether it finished, was skipped, or was
  reset early. That is the same rule V3, Decade, and W already use, and it
  is stated on the tab.
- **The streak** is the number of done days in a row.
  - If today is done, today counts, and the streak is every done day in a
    row ending today.
  - If today is **not done yet**, the streak is every done day in a row
    ending **yesterday**. Today is still in play until midnight, so being
    part-way through the day never breaks the streak or shows a scary zero.
  - A day with no focus blocks is not done, so it ends the streak.
  - The count goes back as far as the history goes and stops at the first
    day that is not done.
- **Changing the goal** re-judges **every** day, past ones too, by the new
  number. Decided during brainstorming: one goal number for everything,
  nothing extra saved. The caption says so. The trade-off is that raising
  the goal a lot can shrink the streak and lowering it can grow it.

## The tab

Tab label **"Goal"**; `Kamen Rider Geats (2022)` gets
`tier5_effect="goal_streak"`. The tab sits next to Help like every other
Tier 5 tab, and is hidden by Standard Mode and by picking a non-Tier-5
Rider through the existing mechanism (no new code for that).

Layout, top to bottom, inside a `CTkScrollableFrame` (matching every
other tab):

1. **Today's line.** `Today` on the left, `{done} of {goal}` on the
   right (for example `40m of 1h 0m`), written with the shared
   `format_hm()`. Under it, a progress bar filled to `today / goal`,
   capped at full.
2. **One sentence** about today (the table below).
3. **The goal row.** `Daily goal` on the left, then `[ - ]`, the goal
   (`1h 0m`, `1h 15m`), and `[ + ]`.
4. **The streak line.** `Streak` on the left, `{n} days in a row` on the
   right, in big text like V3's number. `1 day in a row` when it is one.
5. **One sentence** about the streak (the table below).
6. **Seven boxes**, oldest to newest with **today last (rightmost)**, the
   same as V3, Decade, and W. Each is a small square: filled if that day
   was done, empty if not. The weekday letter sits under each box, taken
   from that day's date.
7. **Caption:** `"Every focus block counts, finished or not · every day is
   judged by today's goal"`. Same small gray style as the other tabs'
   captions.

**No empty-history early exit.** V3, Decade, and W stop after one line
when there is no history, because they have nothing to show. Geats does
not: the goal buttons must work on the very first day, before any block
exists. With no history the bar is empty (`0m of 1h 0m`), the streak is 0,
and all seven boxes are empty.

`tasks` and `appearance_mode` are part of every Tier 5 builder's
signature. Geats uses neither, for the reason V3 and W give:
CustomTkinter's `(light, dark)` color tuples already cover light and
dark.

## Colors

Geats' `primary` is silver in light mode and white in dark mode (pale
next to the tab's pale surface), and `secondary` is red. So:

- **The bar's fill and the filled boxes:** `theme.secondary` (Geats' red).
  Easy to see in both modes.
- **Text:** `theme.primary_text_pair`, the pair that is already safe as
  text on the Rider's surface.
- **Empty boxes and the empty part of the bar:** CustomTkinter's normal
  gray track, so "not done" is visible in both modes.
- **The minus and plus buttons:** the app's normal button look, the same
  as Blade's arrow buttons.

Both modes are checked by eye in the running app.

## The words on screen

Every visible word is meant to be understood by a young child. None of
them says "failed", "behind", "lost", or "broke".

**About today** (`{left}` is the goal minus today's total, written with
`format_hm()`):

| Situation | Sentence |
|---|---|
| Nothing done today (0 seconds) | `Start a focus block to fill the bar.` |
| Some done, goal not reached | `{left} to go. You can do it!` |
| Goal reached | `You did it! Goal done for today. Yay!` |

**About the streak** (`{n}` is the streak; `day` is singular when it is 1):

| Situation | Sentence |
|---|---|
| Streak 1 or more, today done | `{n} days in a row. Wow!` |
| Streak 1 or more, today not done yet | `{n} days in a row. Do your goal today to keep it going!` |
| Streak 0 | `No streak yet. Reach your goal today to start one!` |

## New code

### `lock_in/tier5/geats.py` (new)

Six small pure functions, tested with no Tk and no display server, plus
the one Tk-dependent `build()`:

- **`streak_days(totals: dict[str, int], today: date, goal_seconds: int) -> int`**
  The streak as defined above. Walks back one day at a time from today
  (or from yesterday, if today is not done yet) until it meets a day that
  is not done. To stay safe on a huge history it never walks back past the
  earliest day in `totals`, and it returns 0 for an empty `totals`.
- **`week_dots(totals: dict[str, int], today: date, goal_seconds: int) -> list[tuple[date, bool]]`**
  Exactly 7 tuples `(day, done)`, oldest to newest, ending on today. Built
  from the existing `last_n_days(totals, today, 7)` in `tier5/_shared.py`,
  so no new day-math is written.
- **`goal_sentence(today_seconds: int, goal_seconds: int) -> str`** and
  **`streak_sentence(streak: int, today_done: bool) -> str`**
  Pick one sentence each from the tables above. `{left}` is rounded **up**
  to the next whole minute, so a gap of 30 seconds reads `1m to go`, never
  `0m to go`.
- **`days_in_a_row(streak: int) -> str`**
  `"5 days in a row"`, `"1 day in a row"`, `"0 days in a row"`. The one
  place the singular `day` is handled; the streak line and the streak
  sentence both use it.
- **`stepped_goal(minutes: int, direction: int) -> int`**
  What one button press does: `minutes + 15 * direction`, kept inside 15
  minutes to 12 hours. `direction` is `+1` or `-1`.
- **`build(parent, *, history, tasks, theme, appearance_mode, config) -> None`**
  Builds the tab described above. Reads the goal with
  `config.effective_daily_goal_minutes()`. Pressing minus or plus sets
  `config.daily_goal_minutes` to `stepped_goal(...)`, calls
  `config.save()`, and refreshes the tab **in place**: the widgets are
  built once and then re-configured (their text, bar fill, box colors, and
  button on/off), never destroyed and rebuilt from inside a button click.
  So the bar, both sentences, the streak, and the boxes all update at
  once. If `config.save()` raises `OSError` (say,
  the file is locked), the new goal still works for the rest of the
  session and the next press tries the save again. Nothing crashes and
  nothing is shown.

`geats.py` imports only from `..visuals` (for `display_font_family()`,
which the big streak number uses, as W's totals do), `._shared`, and
`customtkinter`. It does not import from `tier5/__init__.py` or any
sibling Rider module, so there is no circular-import risk (see
`_shared.py`'s own docstring).

### `lock_in/config.py` (one new field, one new reader)

- **`daily_goal_minutes: int = 60`**, with a comment in the same plain
  style as the neighboring fields.
- **`effective_daily_goal_minutes() -> int`**: the safe reader, sitting
  beside the other `effective_*` helpers. `Config.load()` does no
  checking, so a hand-edited `config.json` could hold `0`, a negative
  number, `"abc"`, or `true`. The reader returns the stored value only if
  it is a real whole number (not a bool) inside 15 to 12 hours; anything
  else gives 60. A value that is in range but not a multiple of 15 is
  kept as-is (it is the person's own number); the buttons then step from
  there and stay in range.

### `lock_in/ui.py` (small)

- `_TIER5_TAB_LABELS` gains `"goal_streak": "Goal"`.
- `_build_tier5_tab()` passes `config=self.config_obj` to every builder.
  The other six builders gain a `config=None` argument and ignore it, the
  same way W already ignores `tasks` and `appearance_mode`.
- The tab build, the refresh after a finished block, and the show/hide
  logic already handle any registered effect and need no change.
- Help tab: add a Geats bullet, and change "these six are just the first"
  to seven.

### Wiring summary

- `lock_in/tier5/__init__.py`:
  `TIER5_BUILDERS["goal_streak"] = geats.build`, plus `geats` in the
  import line.
- `lock_in/rider_themes.py`: `tier5_effect="goal_streak"` on
  `Kamen Rider Geats (2022)`, and the count in the field's comment goes
  from five to seven Riders "so far".
- No new file on disk: the goal lives in the existing `config.json`.

## Error handling

Same posture as V3, Decade, and W, plus one write path:

- No history: bar empty, streak 0, seven empty boxes, buttons work.
- A blank, wrong, or out-of-range saved goal: read as 60 by
  `effective_daily_goal_minutes()`, never a crash and never a divide by
  zero (the goal is always at least 15 minutes).
- Saving the goal fails: see `build()` above.
- Midnight passing while the app is open: the tab uses today's date each
  time it is built, so the next redraw (a finished block, a button press,
  or reopening the tab) shows the new day. Same as V3 and W.
- A `CTkProgressBar` needs no stashed image. There are no images on this
  tab, so there is nothing to garbage-collect.

## Testing

- `tests/test_tier5_geats.py` *(new)*: the four pure functions, no Tk.
  - `streak_days()`: empty totals is 0; today done gives a streak that
    includes today; today not done yet gives the streak ending
    **yesterday**, not 0; a day exactly at the goal counts as done and one
    second under does not; a gap ends the streak; a streak that crosses a
    month boundary and one that crosses a year boundary both count right;
    a very long streak does not loop forever; a change of goal re-judges
    old days (the same totals give a different streak at a different
    goal).
  - `week_dots()`: always exactly 7 entries, oldest to newest, ending on
    today; done and not-done flags match the goal; a day with no blocks is
    not done.
  - `goal_sentence()`: zero, part-way, exactly at the goal, over the goal;
    `{left}` is formatted with `format_hm()` and rounded up to the next
    minute (30 seconds short reads `1m to go`).
  - `days_in_a_row()`: 0, 1 (singular), and many.
  - `stepped_goal()`: up, down, stopping at 15 minutes and at 12 hours, and
    a goal that is not a multiple of 15 steps from where it is and stays
    in range.
  - Every builder in `TIER5_BUILDERS` accepts `config` (a signature check),
    so the shared change cannot be missed on one of the six.
  - `streak_sentence()`: 0, 1 (singular `day`), many, today done and not
    done; no sentence contains "fail", "behind", "lost", or "broke".
- `tests/test_config.py` *(grows)*: the default is 60; a saved value
  round-trips; `effective_daily_goal_minutes()` gives 60 for `0`,
  negative, above 12 hours, a string, a float, `None`, and `True`; gives
  the stored value at exactly 15 minutes and at exactly 12 hours.
- `tests/test_rider_themes.py` *(grows)*: the tier5 completeness check now
  expects seven Riders, adding `"Kamen Rider Geats (2022)": "goal_streak"`.
  The test is renamed to say seven.
- **Manual, in the running app** (same as every other tab, no automated
  GUI test): the "Goal" tab appears only for Geats; a fresh install shows
  `0m of 1h 0m`, streak 0, and seven empty boxes; the buttons step by 15
  minutes, stop at both ends, and redraw everything at once; the goal
  survives closing and reopening the app; with history, the bar, the
  sentences, the streak, and the boxes agree with each other; light and
  dark mode both read clearly; finishing a block while the tab is open
  refreshes it; switching to a non-Tier-5 Rider or turning on Standard
  Mode hides the tab, and turning Standard Mode back off restores it; the
  other six Tier 5 tabs still open and look right (the shared `config=`
  change).

## Docs, version, and repo hygiene

- `README.md`, three small edits: a **Geats** bullet in the Tier 5 section
  in the same plain words; "these six are just the first of ten planned"
  becomes seven; and a "Known limits" line saying Geats uses one goal
  number for every day (the same trade-off as above), next to W's line.
  The Config table's `config.json` row already says "every setting", so
  it needs no change.
- `lock_in/ui.py`, Help tab: as above.
- `__version__`: `2.5.6` to **`2.5.7`**.
- `.gitignore`: Geats creates no new file (the goal lives in the existing
  `config.json`, which is already ignored). No change is expected; it is
  re-checked when this ships.
- Project files describe the software only: nothing about who or what
  wrote them, and commit messages carry no trailer or credit line.
- Committing, pushing, and tagging are done by the project owner. The
  exact commands are handed over at the end, with a plain commit message.

## Out of scope for this pass

- A "best streak ever" record.
- A goal saved per day (so changing the goal never touches old days).
- Streak "freezes", rewards, or badges (Gotchard's job).
- Sounds or pop-ups when the goal is reached.
- Weekend or rest-day rules.
- A goal box in the Settings tab.
- The other three Tier 5 Riders (OOO, Gotchard, MY-TH), each of which gets
  its own spec.

## File-by-file change list

**New**
- `lock_in/tier5/geats.py`: `streak_days()`, `week_dots()`,
  `goal_sentence()`, `days_in_a_row()`, `streak_sentence()`,
  `stepped_goal()`, `build()`.
- `tests/test_tier5_geats.py`.
- `docs/superpowers/plans/2026-09-21-tier5-geats-daily-goal.md`: the
  implementation plan (written after this spec is approved).

**Edit**
- `lock_in/config.py`: `daily_goal_minutes`, `effective_daily_goal_minutes()`.
- `lock_in/tier5/__init__.py`: one registry entry.
- `lock_in/tier5/{v3,den_o,decade,zi_o,blade,w}.py`: `config=None`
  argument, ignored.
- `lock_in/rider_themes.py`: `tier5_effect="goal_streak"` on Geats, and the
  comment count.
- `lock_in/ui.py`: `_TIER5_TAB_LABELS` entry, `config=` passed to builders,
  Help tab bullet and wording.
- `lock_in/__init__.py`: version to 2.5.7.
- `tests/test_config.py`, `tests/test_rider_themes.py`: as described above.
- `README.md`: Tier 5 bullet, count wording, Known-limits line.
