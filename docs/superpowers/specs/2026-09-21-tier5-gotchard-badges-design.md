# Lock In: Tier 5 Rider #8 — Gotchard, the collectible badges

Date: 2026-09-21
Status: Design approved

## Goal

The eighth of Tier 5's 10 Riders, built on the shared `tier5_effect` /
`lock_in/tier5/` plumbing that V3, Den-O, Decade, Zi-O, Blade, W, and
Geats already established. Gotchard's show is about collecting cards, so
Gotchard's tab is a small card collection: win badges by using the app,
and keep every one you win.

When Kamen Rider Gotchard (2023) is the picked Rider, a **"Badges"** tab
shows:

1. **A count**: how many of the 9 badges you have.
2. **One sentence** about your collection.
3. **Nine cards** in a 3-by-3 grid: a colored card for each badge you
   won, a gray card (with a hint) for each one you have not won yet.
4. **A caption** and a small note about the daily goal.

Gotchard is the second Tier 5 Rider that **remembers something**, after
Geats. It reads the same focus-block history and the same task list the
other tabs read, and it never changes either of them. The one thing it
saves is the list of badges you have won.

The badges that reward a streak use the **daily goal** that Geats added.
Gotchard has no goal buttons of its own: the goal is changed on Geats'
"Goal" tab, and Gotchard only reads it.

## The rules

Decided during brainstorming.

- **Nine badges**, in a fixed order (the table below). A badge is won when
  your numbers reach its target.
- **Every focus block counts**, whether it finished, was skipped, or was
  reset early. That is the same rule V3, Decade, W, and Geats already use,
  and it is stated on the tab.
- **Badges are kept forever.** Once you win one, it stays, even if you
  later delete a block in Zi-O or change your daily goal. Nothing on this
  tab ever takes a badge away.
- **When badges are checked:** every time the tab is built. That is when
  the app opens, when a focus block ends, and when you pick Gotchard. If
  you used another Rider for a while, the next build still finds every
  badge your history has earned, so nothing is missed.
- **Streak badges use the longest run of goal days in your whole
  history**, not only the streak you have today. A 7-day run from last
  month wins the badge the first time the tab is built.
- **A "goal day"** is a day whose total focus time is **at least** the
  daily goal (the same rule as Geats). The goal is
  `config.effective_daily_goal_minutes()`, the safe reader Geats added.
- **Not-yet badges show their hint**, so a child can see what to aim for.
  There are no secret badges.

### The nine badges

| Name | Hint (shown on the card) | Won when |
|---|---|---|
| First Step | Do your first focus block. | blocks is at least 1 |
| Ten Blocks | Do 10 focus blocks. | blocks is at least 10 |
| One Hour Day | Focus for 1 hour in one day. | best day is at least 3600 seconds |
| Big Day | Focus for 3 hours in one day. | best day is at least 10800 seconds |
| Ten Hours | Focus for 10 hours in all. | total is at least 36000 seconds |
| Task Done | Check off a task. | tasks done is at least 1 |
| Goal Done | Reach your daily goal once. | longest goal run is at least 1 |
| Three in a Row | Reach your daily goal 3 days in a row. | longest goal run is at least 3 |
| Seven in a Row | Reach your daily goal 7 days in a row. | longest goal run is at least 7 |

"Blocks" is the number of focus blocks in the history. "Best day" is the
biggest one-day total. "Total" is every second of focus ever logged.
"Tasks done" is `len(tasks.done())`, the tasks you checked off (the Tasks
tab checkbox or Blade's Done column). Each badge also has a short
saved name, its **id**: `first_step`, `ten_blocks`, `hour_day`,
`big_day`, `ten_hours`, `task_done`, `goal_done`, `three_days`,
`seven_days`.

## The tab

Tab label **"Badges"**; `Kamen Rider Gotchard (2023)` gets
`tier5_effect="badge_cards"`. The tab sits next to Help like every other
Tier 5 tab, and is hidden by Standard Mode and by picking a non-Tier-5
Rider through the existing mechanism (no new code for that).

Layout, top to bottom, inside a `CTkScrollableFrame` (matching every
other tab):

1. **The count line.** `Badges` on the left, `{have} of 9` on the right,
   in big text like Geats' streak line (for example `3 of 9`).
2. **One sentence** about the collection (the table below).
3. **The grid.** Nine cards, 3 in each row, in the order of the badge
   table. Each card is a rounded frame that shows, top to bottom:
   - the badge **name**, in bold;
   - the **hint**, in small text (wrapped, so it never runs off the card);
   - the **state**: `Got it!` or `Not yet`.
4. **Caption:** `Every focus block counts, finished or not · a badge is
   yours to keep`. Same small gray style as the other tabs' captions.
5. **The goal note:** `Goal badges use your daily goal of {goal}. Pick
   Geats to change it.` (`{goal}` is written with the shared
   `format_hm()`, for example `1h 0m`.)

**No empty-history early exit.** With no history the count is `0 of 9`,
the sentence says how to win the first badge, and all nine cards are
gray. The tab always shows the cards, because the cards are the
collection.

`tasks` and `appearance_mode` are part of every Tier 5 builder's
signature. Gotchard uses `tasks` (for Task Done) and does not use
`appearance_mode`, for the reason V3 and W give: CustomTkinter's
`(light, dark)` color tuples already cover light and dark.

## Colors

Gotchard's `primary` is teal and its `secondary` is orange
(`#b33f00` in light mode, `#ffb74d` in dark mode). So:

- **A badge you won:** the card is filled with `theme.secondary`. Its
  words use `theme.button_text_pair`, the pair that is already safe as
  text sitting directly on `secondary`.
- **A badge you have not won yet:** the card uses CustomTkinter's normal
  gray, `("gray80", "gray30")`. Its name uses `("gray20", "gray80")` and
  its hint and state use `("gray30", "gray70")`.
- **The count and the sentence:** `theme.primary_text_pair`.
- **The state words** (`Got it!`, `Not yet`) carry the meaning as well as
  the color, so nobody has to tell the two cards apart by color alone.

Both modes are checked by eye in the running app.

## The words on screen

Every visible word is meant to be understood by a young child. None of
them says "failed", "behind", "lost", "missed", or "broke".

**The sentence** (`{have}` is how many of the 9 you have; `{name}` is a
new badge's name):

| Situation | Sentence |
|---|---|
| Exactly one badge is new | `New! You won {name}!` |
| More than one badge is new | `New! You won {n} badges!` |
| Nothing new, and you have 0 | `Do a focus block to win your first badge.` |
| Nothing new, and you have all 9 | `You got them all! Wow!` |
| Nothing new, and you have 1 to 8 | `You have {have} of 9. Keep going!` |

A "new" badge is one this build just won. The `New!` sentence shows only
in the build that saved the badge. The next build says the normal
sentence, because the badge is no longer new.

## New code

### `lock_in/tier5/gotchard.py` (new)

The badge table, six small pure functions and one small class, tested
with no Tk and no display server, plus the one Tk-dependent `build()`:

- **`BADGES`**: the nine badges in order, each with its id, name, hint,
  the number it looks at, and the target. It is plain data: adding a
  badge later is one new row.
- **`Progress`**: a small frozen dataclass of the five numbers the badges
  look at: `blocks`, `best_day_seconds`, `total_seconds`, `longest_run`,
  and `tasks_done`.
- **`longest_goal_run(totals: dict[str, int], goal_seconds: int) -> int`**
  The longest stretch of days in a row that each reached the goal, found
  anywhere in the history. 0 for empty `totals`. It works from the day
  dates themselves, so a run across a month or a year boundary counts
  right, and it never loops forever on a long history.
- **`progress(totals: dict[str, int], block_count: int, goal_seconds: int, tasks_done: int) -> Progress`**
  Builds the five numbers. `totals` is `history.total_seconds_by_day()`
  and `block_count` is `len(history.all())`. With no history: all zeros
  except `tasks_done`.
- **`earned_ids(p: Progress) -> list[str]`**
  The ids of every badge `p` has won, in badge order.
- **`saved_badges(raw) -> list[str]`**
  The safe reader for the saved list (see `config.py` below). A value
  that is not a list gives `[]`. Entries that are not text are dropped,
  and repeats are dropped, keeping the first. Names this app does not
  know are **kept** (so a list saved by a newer app is not shortened),
  and they are never counted or shown.
- **`newly_won(earned: list[str], saved: list[str]) -> list[str]`**
  The ids in `earned` that are not in `saved`, in badge order.
- **`badge_sentence(have: int, total: int, new_names: list[str]) -> str`**
  Picks one sentence from the table above.
- **`build(parent, *, history, tasks, theme, appearance_mode, config) -> None`**
  Builds the tab described above:
  1. Reads the goal with `config.effective_daily_goal_minutes()`.
  2. Works out `progress(...)`, then `earned_ids(...)`.
  3. Reads the saved list with `saved_badges(config.badges_earned)`.
  4. Finds the new ones with `newly_won(...)`. If there are any, it sets
     `config.badges_earned` to the saved list followed by the new ids and
     calls `config.save()`. If `config.save()` raises `OSError` (say, the
     file is locked), the badges still show for the rest of the session
     and the next build tries the save again. Nothing crashes and nothing
     is shown.
  5. Draws the tab. A card is "won" if its id is in the saved list or was
     just won. The count is the number of the nine ids that are won.

Every widget is built once, in a single pass. There are no buttons on
this tab, so nothing is ever rebuilt from inside a click.

`gotchard.py` imports only from `..visuals` (for `display_font_family()`,
which the big count uses, as W's totals and Geats' streak do),
`._shared`, and `customtkinter`. It does not import from
`tier5/__init__.py` or any sibling Rider module, so there is no
circular-import risk (see `_shared.py`'s own docstring). It does not
reuse Geats' `streak_days()`, because that one counts only the streak
that reaches today, and the badges need the longest run anywhere.

### `lock_in/config.py` (one new field)

- **`badges_earned: List[str]`**, default an empty list
  (`field(default_factory=list)`), with a comment in the same plain style
  as the neighboring fields. `Config.load()` does no checking, so a
  hand-edited `config.json` could hold anything. That is why the tab
  never reads the field directly: it goes through `saved_badges()`.
- There is no new helper in `config.py`, so `config.py` does not have to
  know the badge names. That keeps the import one-way (`tier5` imports
  from `config`, never the other way round).

### `lock_in/ui.py` (small)

- `_TIER5_TAB_LABELS` gains `"badge_cards": "Badges"`.
- Help tab: add a Gotchard bullet, and change "these seven are just the
  first" to eight.
- Nothing else changes. `_build_tier5_tab()` already passes `config=` to
  every builder, and the tab build, the refresh after a finished block,
  and the show/hide logic already handle any registered effect.

### Wiring summary

- `lock_in/tier5/__init__.py`:
  `TIER5_BUILDERS["badge_cards"] = gotchard.build`, plus `gotchard` in
  the import line, and the docstring line about `config` now says Geats
  and Gotchard use it.
- `lock_in/rider_themes.py`: `tier5_effect="badge_cards"` on
  `Kamen Rider Gotchard (2023)`, and the comment's list of Riders "so
  far" gains Gotchard.
- The other seven builders already accept `config`. They need no change.
- No new file on disk: the badge list lives in the existing
  `config.json`.

## Error handling

Same posture as V3, Decade, W, and Geats, plus one write path:

- No history: `0 of 9`, nine gray cards, nothing saved.
- A blank, wrong, or hand-edited saved list (`null`, a number, text, a
  list with numbers in it): `saved_badges()` reads it as best it can and
  never raises. The tab then re-wins whatever the history has earned.
- A bad saved goal: `effective_daily_goal_minutes()` already gives 60.
- Saving the badge list fails: see `build()` above.
- A task deleted by hand-editing `tasks.json`: `tasks.done()` simply
  counts fewer tasks. A badge already won stays won.
- Blocks deleted in Zi-O, or the goal changed on Geats' tab: a badge
  already won stays won. Only badges not won yet can change.
- Midnight passing while the app is open: the tab uses the history each
  time it is built, so the next redraw shows any new badge. Same as V3
  and W.

## Testing

- `tests/test_tier5_gotchard.py` *(new)*: the pure functions, no Tk.
  - `BADGES`: exactly 9; ids are all different; every id in the table
    above is there, in that order; every badge has a name and a hint; no
    name, hint, or sentence contains "fail", "behind", "lost", "missed",
    or "broke".
  - `longest_goal_run()`: empty is 0; one goal day is 1; a gap splits a
    run and the longer one wins; a day exactly at the goal counts and one
    second under does not; a run across a month boundary and one across a
    year boundary both count right; a very long run is counted; a
    bigger goal gives a shorter run for the same history.
  - `progress()`: no history is all zeros; `blocks`, `best_day_seconds`,
    and `total_seconds` are right for a small made-up history;
    `tasks_done` is passed through.
  - `earned_ids()`: nothing for all zeros; each badge turns on at exactly
    its target and not one below it; the ids come back in badge order;
    a rich `Progress` wins all nine.
  - `saved_badges()`: a good list comes back as it is; `None`, a number,
    text, a dict, and a bool all give `[]`; entries that are not text
    are dropped; repeats are dropped, keeping the first; unknown names
    are kept.
  - `newly_won()`: nothing new; some new; all new; badge order is kept.
  - `badge_sentence()`: one new (uses the name); several new (uses the
    number); none won; all nine; some won; a `New!` sentence beats the
    "all" and "some" ones.
  - Wiring: `TIER5_BUILDERS["badge_cards"] is gotchard.build`, and the tab
    label is `"Badges"`.
- `tests/test_config.py` *(grows)*: `badges_earned` defaults to an empty
  list, two `Config()` objects do not share one list, and a saved list
  round-trips through `save()` and `load()`.
- `tests/test_rider_themes.py` *(grows)*: the tier5 completeness check now
  expects eight Riders, adding `"Kamen Rider Gotchard (2023)":
  "badge_cards"`. The test is renamed to say eight.
- **Manual, in the running app** (same as every other tab, no automated
  GUI test): the "Badges" tab appears only for Gotchard; a fresh install
  shows `0 of 9`, the first-badge sentence, and nine gray cards; with
  history, the right cards turn orange and read `Got it!`; the `New!`
  sentence shows once and then goes back to the normal one; closing and
  reopening the app keeps the badges; removing lines from the history
  file by hand does not take a won badge away; light and dark mode both read clearly; the
  hints wrap and never run off a card; finishing a block while the tab is
  open refreshes it; switching to a non-Tier-5 Rider or turning on
  Standard Mode hides the tab, and turning Standard Mode back off
  restores it; the other seven Tier 5 tabs still open and look right.

## Docs, version, and repo hygiene

- `README.md`, three small edits: a **Gotchard** bullet in the Tier 5
  section, in the same plain words; "these seven are just the first of
  ten planned" becomes eight; and two "Known limits" lines: one saying a
  badge you win is yours to keep, so a very small daily goal can win the
  streak badges quickly, and one saying Gotchard cannot change the goal
  (only Geats can). The Config table's `config.json` row already says
  "every setting", so it needs no change.
- `lock_in/ui.py`, Help tab: as above.
- `__version__`: `2.5.7` to **`2.5.8`**.
- `.gitignore`: Gotchard creates no new file (the badge list lives in the
  existing `config.json`, which is already ignored). No change is
  expected; it is re-checked when this ships.
- Project files describe the software only: nothing about who or what
  wrote them, and commit messages carry no trailer or credit line.
- Committing, pushing, and tagging are done by the project owner. The
  exact commands are handed over at the end, with a plain commit message.

## Out of scope for this pass

- The date a badge was won.
- Sounds, pop-ups, or animations when a badge is won.
- Secret badges, or more than nine badges.
- A goal saved with each badge, or a goal box on this tab.
- Taking a badge back, or a "reset my badges" button.
- Badges on any other Rider's tab.
- OOO and MY-TH, each of which gets its own spec.

## File-by-file change list

**New**
- `lock_in/tier5/gotchard.py`: `BADGES`, `Progress`, `longest_goal_run()`,
  `progress()`, `earned_ids()`, `saved_badges()`, `newly_won()`,
  `badge_sentence()`, `build()`.
- `tests/test_tier5_gotchard.py`.
- `docs/superpowers/plans/2026-09-21-tier5-gotchard-badges.md`: the
  implementation plan (written after this spec is approved).

**Edit**
- `lock_in/config.py`: `badges_earned`.
- `lock_in/tier5/__init__.py`: one registry entry, and the docstring line.
- `lock_in/rider_themes.py`: `tier5_effect="badge_cards"` on Gotchard, and
  the comment's list of Riders.
- `lock_in/ui.py`: `_TIER5_TAB_LABELS` entry, Help tab bullet and wording.
- `lock_in/__init__.py`: version to 2.5.8.
- `tests/test_config.py`, `tests/test_rider_themes.py`: as described above.
- `README.md`: Tier 5 bullet, count wording, Known-limits lines.
