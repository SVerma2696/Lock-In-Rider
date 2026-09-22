# Tier 5 Rider #7 (Geats, the daily goal and streak) Implementation Plan

Spec: `docs/superpowers/specs/2026-09-21-tier5-geats-daily-goal-design.md`.
Work through the tasks in order and tick each box as you go. Steps use
checkbox (`- [ ]`) syntax.

**Goal:** When Kamen Rider Geats (2022) is the picked Rider, a "Goal" tab lets you pick a daily focus goal with a minus and a plus button, shows a bar for today, a streak of days in a row that reached the goal, and seven boxes for the last 7 days.

**Architecture:** One new saved setting (`daily_goal_minutes`) and a safe reader for it in `lock_in/config.py`. A new `lock_in/tier5/geats.py` holds six small pure functions (`streak_days`, `week_dots`, `goal_sentence`, `days_in_a_row`, `streak_sentence`, `stepped_goal`) plus the one Tk-dependent `build()`. The tab plugs into the existing `TIER5_BUILDERS` registry and `_TIER5_TAB_LABELS`, the same way V3, Den-O, Decade, Zi-O, Blade, and W did. The one shared change: `ui.py` now hands every tab builder the app's settings as `config=`, and the other six builders accept it and ignore it.

**Tech Stack:** Python 3, CustomTkinter, pytest. No new dependency, and no new drawing code (the boxes are plain colored frames).

## Global Constraints

Copied from the spec. Every task below includes these.

- **Tab label:** `"Goal"`. **Effect name:** `"goal_streak"`. **Rider:** `Kamen Rider Geats (2022)`.
- **Goal:** set with a minus and a plus button on the Geats tab. Each press is **15 minutes**. Range **15 minutes to 12 hours**. Starts at **1 hour**. The buttons switch off at both ends. The goal is one new setting, `daily_goal_minutes`, in the existing `config.json`. There is no goal box in the Settings tab.
- **A day is "done"** when its total focus time is **at least** the goal. Every focus block counts, whether finished, skipped, or reset early (same rule as V3, Decade, and W).
- **Streak:** the number of done days in a row. If today is done, today counts. If today is **not done yet**, count back from **yesterday** (today is still in play until midnight). A day with no blocks is not done. Never look back past the first day in the history.
- **Changing the goal re-judges every day**, past ones too, by the new number. Nothing extra is saved.
- **The goal reader is safe:** anything that is not a whole number (not `True` or `False`) from 15 to 720 reads as 60. A number that is in range but not a multiple of 15 is kept.
- **Sentences (exact text):**
  - about today: `Start a focus block to fill the bar.` / `{left} to go. You can do it!` / `You did it! Goal done for today. Yay!`
  - about the streak: `{n} days in a row. Wow!` / `{n} days in a row. Do your goal today to keep it going!` / `No streak yet. Reach your goal today to start one!`
  - the streak line: `{n} days in a row` (`1 day in a row` when it is one)
  - caption: `Every focus block counts, finished or not · every day is judged by today's goal`
- `{left}` is written with the shared `format_hm()` and rounded **up** to a whole minute (30 seconds short reads `1m to go`, never `0m to go`). Hours read like `1h 0m` and `1h 15m`, the same as every other tab.
- **No sentence says** "fail", "behind", "lost", "broke", or "worse".
- **No early exit on an empty history.** The goal buttons must work on day one, so with no history the bar is empty, the streak is 0, and all seven boxes are empty.
- **Colors:** the bar and the filled boxes use `theme.secondary`; text uses `theme.primary_text_pair`; empty boxes are `("gray80", "gray30")`; the buttons use the app's normal button look, like Blade's arrow buttons.
- **Today is the last (rightmost) box**, the same as V3, Decade, and W.
- **The buttons never destroy and rebuild the tab from inside their own click.** The widgets are built once and re-configured.
- **Words a young child can follow** in every visible string, the README, and the Help tab.
- **Version:** `2.5.6` to `2.5.7`.
- **No commit, push, or tag is run while doing this plan.** The commands are in the Handoff section at the end, for the project owner to run.
- **Project files describe the software only** -- nothing about who or what wrote it, in any file added or edited.
- **Line endings:** edit existing files in place and keep their current line-ending style (most are CRLF). New files may use LF (Git converts on commit).

## File Structure

| File | What it's for |
|---|---|
| `lock_in/config.py` *(edit)* | The goal limits, the `daily_goal_minutes` setting, and `effective_daily_goal_minutes()` |
| `lock_in/tier5/geats.py` *(new)* | The six pure functions and `build()` |
| `lock_in/tier5/__init__.py` *(edit)* | Register `"goal_streak": geats.build`; one docstring line about `config` |
| `lock_in/tier5/{v3,den_o,decade,zi_o,blade,w}.py` *(edit)* | Each `build()` accepts `config=None` and ignores it |
| `lock_in/rider_themes.py` *(edit)* | `tier5_effect="goal_streak"` on Geats; the comment's list of Riders |
| `lock_in/ui.py` *(edit)* | `_TIER5_TAB_LABELS` entry; pass `config=`; Help tab bullet and wording |
| `lock_in/__init__.py` *(edit)* | Version 2.5.7 |
| `README.md` *(edit)* | Geats bullet, "seven of ten" wording, one known-limit line |
| `tests/test_config.py` *(edit)* | The goal setting and its safe reader |
| `tests/test_tier5_geats.py` *(new)* | The pure functions and the wiring |
| `tests/test_rider_themes.py` *(edit)* | The tier5 completeness check grows to seven |

---

### Task 1: The saved goal (`daily_goal_minutes` and its safe reader)

**Files:**
- Modify: `lock_in/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the constants `DAILY_GOAL_DEFAULT_MINUTES` (60), `DAILY_GOAL_MIN_MINUTES` (15), `DAILY_GOAL_MAX_MINUTES` (720), `DAILY_GOAL_STEP_MINUTES` (15); the setting `Config.daily_goal_minutes: int`; the method `Config.effective_daily_goal_minutes() -> int`.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/test_config.py` (it already imports `Config`), with two blank lines before them:

```python
def test_daily_goal_minutes_defaults_to_one_hour():
    assert Config().daily_goal_minutes == 60


def test_daily_goal_minutes_round_trips_through_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    Config(daily_goal_minutes=90).save(path)
    assert Config.load(path).daily_goal_minutes == 90


def test_effective_daily_goal_minutes_gives_back_a_good_value_as_it_is():
    assert Config(daily_goal_minutes=90).effective_daily_goal_minutes() == 90
    assert Config().effective_daily_goal_minutes() == 60


def test_effective_daily_goal_minutes_allows_exactly_fifteen_minutes_and_twelve_hours():
    assert Config(daily_goal_minutes=15).effective_daily_goal_minutes() == 15
    assert Config(daily_goal_minutes=720).effective_daily_goal_minutes() == 720


def test_effective_daily_goal_minutes_keeps_a_number_that_is_not_a_multiple_of_fifteen():
    assert Config(daily_goal_minutes=20).effective_daily_goal_minutes() == 20


def test_effective_daily_goal_minutes_falls_back_to_sixty_for_a_bad_number():
    """config.json can be edited by hand, and Config.load() does not check
    it, so a silly goal must never reach the tab (it would divide by zero)."""
    for bad in (0, -5, 14, 721, 100000):
        assert Config(daily_goal_minutes=bad).effective_daily_goal_minutes() == 60, bad


def test_effective_daily_goal_minutes_falls_back_to_sixty_for_the_wrong_kind_of_value():
    for bad in ("abc", "60", 60.0, None, True, False, [60]):
        assert Config(daily_goal_minutes=bad).effective_daily_goal_minutes() == 60, bad
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: the 7 new tests FAIL (`Config` has no `daily_goal_minutes` yet). The older tests still PASS.

- [ ] **Step 3: Write the implementation**

Three edits in `lock_in/config.py`.

First, the limits, right after the file paths near the top:

In `lock_in/config.py`, replace:

```python
TASKS_PATH = app_data_dir() / "tasks.json"
```

with:

```python
TASKS_PATH = app_data_dir() / "tasks.json"

# Geats' daily goal (see daily_goal_minutes on Config below): how many
# minutes of focus you want each day. It always sits between the smallest
# and the biggest, and the plus/minus buttons move it one step at a time.
DAILY_GOAL_DEFAULT_MINUTES = 60
DAILY_GOAL_MIN_MINUTES = 15
DAILY_GOAL_MAX_MINUTES = 12 * 60
DAILY_GOAL_STEP_MINUTES = 15
```

Second, the setting, in the `Config` dataclass:

In `lock_in/config.py`, replace:

```python
    check_for_updates: bool = True
```

with:

```python
    check_for_updates: bool = True

    # Geats' daily goal: how many minutes of focus you want each day, set
    # with the minus and plus buttons on Geats' Goal tab. Read it with
    # effective_daily_goal_minutes() below, not directly: that one is safe
    # even if a hand-edited config.json holds something silly.
    daily_goal_minutes: int = DAILY_GOAL_DEFAULT_MINUTES
```

Third, the safe reader, at the very end of the file, after `effective_auto_start_breaks`:

In `lock_in/config.py`, replace:

```python
        return False if self.blackrx_manual_breaks else self.auto_start_breaks
```

with:

```python
        return False if self.blackrx_manual_breaks else self.auto_start_breaks

    def effective_daily_goal_minutes(self) -> int:
        """The daily goal, made safe to use. Config.load() does no
        checking, so a hand-edited config.json could hold 0, a negative
        number, some words, or true. Anything that is not a whole number
        between the smallest and biggest allowed goal gives the normal
        goal instead, so the Goal tab never divides by zero."""
        value = self.daily_goal_minutes
        if isinstance(value, bool) or not isinstance(value, int):
            return DAILY_GOAL_DEFAULT_MINUTES
        if not DAILY_GOAL_MIN_MINUTES <= value <= DAILY_GOAL_MAX_MINUTES:
            return DAILY_GOAL_DEFAULT_MINUTES
        return value
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: all PASS.

- [ ] **Step 5: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 2: Geats' six pure functions

**Files:**
- Create: `lock_in/tier5/geats.py`
- Create: `tests/test_tier5_geats.py`

**Interfaces:**
- Consumes: `DAILY_GOAL_MIN_MINUTES`, `DAILY_GOAL_MAX_MINUTES`, `DAILY_GOAL_STEP_MINUTES` (Task 1); `format_hm()` and `last_n_days()` from `lock_in/tier5/_shared.py`.
- Produces, all in `lock_in/tier5/geats.py`:
  - `streak_days(totals: dict[str, int], today: date, goal_seconds: int) -> int`
  - `week_dots(totals: dict[str, int], today: date, goal_seconds: int) -> list[tuple[date, bool]]`
  - `goal_sentence(today_seconds: int, goal_seconds: int) -> str`
  - `days_in_a_row(streak: int) -> str`
  - `streak_sentence(streak: int, today_done: bool) -> str`
  - `stepped_goal(minutes: int, direction: int) -> int`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tier5_geats.py`:

```python
from datetime import date, timedelta

from lock_in.tier5.geats import (
    days_in_a_row,
    goal_sentence,
    stepped_goal,
    streak_days,
    streak_sentence,
    week_dots,
)

TODAY = date(2026, 9, 21)
HOUR = 3600


def _iso(days_ago: int, today: date = TODAY) -> str:
    return (today - timedelta(days=days_ago)).isoformat()


def _totals(*days_ago_and_seconds: tuple[int, int], today: date = TODAY) -> dict[str, int]:
    """_totals((0, 3600), (1, 3600)) -> today and yesterday, an hour each."""
    return {_iso(days_ago, today): seconds for days_ago, seconds in days_ago_and_seconds}


# --- streak_days ------------------------------------------------------- #

def test_streak_with_no_history_is_zero():
    assert streak_days({}, TODAY, HOUR) == 0


def test_streak_counts_today_when_today_is_done():
    assert streak_days(_totals((0, HOUR)), TODAY, HOUR) == 1


def test_streak_counts_every_done_day_in_a_row_ending_today():
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 3


def test_streak_ends_yesterday_when_today_is_not_done_yet():
    """Part-way through the day must never show a scary zero."""
    totals = _totals((0, 600), (1, HOUR), (2, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 2


def test_streak_ends_yesterday_when_today_has_no_blocks_at_all():
    totals = _totals((1, HOUR), (2, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 2


def test_streak_is_zero_when_today_and_yesterday_both_missed():
    totals = _totals((0, 600), (2, HOUR), (3, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 0


def test_a_day_exactly_at_the_goal_is_done():
    assert streak_days(_totals((0, HOUR)), TODAY, HOUR) == 1


def test_a_day_one_second_under_the_goal_is_not_done():
    totals = _totals((0, HOUR - 1), (1, HOUR))
    # Today is not done yet, so the streak ends yesterday: 1, not 2.
    assert streak_days(totals, TODAY, HOUR) == 1


def test_a_missed_day_ends_the_streak():
    totals = _totals((0, HOUR), (1, HOUR), (3, HOUR))   # day 2 is missing
    assert streak_days(totals, TODAY, HOUR) == 2


def test_streak_across_a_month_boundary():
    today = date(2026, 10, 2)
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR), (3, HOUR), today=today)
    assert streak_days(totals, today, HOUR) == 4   # Oct 2, Oct 1, Sep 30, Sep 29


def test_streak_across_a_year_boundary():
    today = date(2027, 1, 2)
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR), (3, HOUR), today=today)
    assert streak_days(totals, today, HOUR) == 4   # Jan 2, Jan 1, Dec 31, Dec 30


def test_a_very_long_streak_is_counted_and_stops_at_the_first_day():
    totals = _totals(*[(days_ago, HOUR) for days_ago in range(400)])
    assert streak_days(totals, TODAY, HOUR) == 400


def test_a_bigger_goal_re_judges_old_days():
    """One goal number for every day: the same history gives a different
    streak at a different goal."""
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 3
    assert streak_days(totals, TODAY, 2 * HOUR) == 0
    assert streak_days(totals, TODAY, HOUR // 2) == 3


# --- week_dots --------------------------------------------------------- #

def test_week_dots_always_returns_exactly_seven_entries():
    assert len(week_dots({}, TODAY, HOUR)) == 7


def test_week_dots_are_oldest_to_newest_ending_on_today():
    days = [day for day, _ in week_dots({}, TODAY, HOUR)]
    assert days[-1] == TODAY
    assert days[0] == TODAY - timedelta(days=6)
    assert days == sorted(days)


def test_week_dots_with_no_history_are_all_not_done():
    assert [done for _, done in week_dots({}, TODAY, HOUR)] == [False] * 7


def test_week_dots_mark_the_days_that_reached_the_goal():
    totals = _totals((0, HOUR), (1, 100), (2, 2 * HOUR), (6, HOUR))
    flags = [done for _, done in week_dots(totals, TODAY, HOUR)]
    # oldest -> newest: 6 ago, 5, 4, 3, 2, 1, today
    assert flags == [True, False, False, False, True, False, True]


def test_week_dots_exactly_at_the_goal_is_done_and_one_second_under_is_not():
    totals = _totals((0, HOUR), (1, HOUR - 1))
    flags = [done for _, done in week_dots(totals, TODAY, HOUR)]
    assert flags[-1] is True     # today, exactly at the goal
    assert flags[-2] is False    # yesterday, one second under


# --- goal_sentence ----------------------------------------------------- #

def test_goal_sentence_when_nothing_is_done_yet():
    assert goal_sentence(0, HOUR) == "Start a focus block to fill the bar."


def test_goal_sentence_part_way_says_how_much_is_left():
    assert goal_sentence(40 * 60, HOUR) == "20m to go. You can do it!"


def test_goal_sentence_shows_hours_when_a_lot_is_left():
    assert goal_sentence(10 * 60, 2 * HOUR) == "1h 50m to go. You can do it!"


def test_goal_sentence_rounds_the_time_left_up_to_a_whole_minute():
    # 30 seconds short: never "0m to go".
    assert goal_sentence(HOUR - 30, HOUR) == "1m to go. You can do it!"
    # 61 seconds short is 2 minutes, rounded up.
    assert goal_sentence(HOUR - 61, HOUR) == "2m to go. You can do it!"


def test_goal_sentence_when_the_goal_is_reached():
    assert goal_sentence(HOUR, HOUR) == "You did it! Goal done for today. Yay!"


def test_goal_sentence_when_the_goal_is_beaten():
    assert goal_sentence(2 * HOUR, HOUR) == "You did it! Goal done for today. Yay!"


# --- days_in_a_row ----------------------------------------------------- #

def test_days_in_a_row_is_singular_for_one():
    assert days_in_a_row(1) == "1 day in a row"


def test_days_in_a_row_is_plural_for_zero_and_many():
    assert days_in_a_row(0) == "0 days in a row"
    assert days_in_a_row(5) == "5 days in a row"


# --- streak_sentence --------------------------------------------------- #

def test_streak_sentence_with_no_streak():
    assert streak_sentence(0, False) == "No streak yet. Reach your goal today to start one!"


def test_streak_sentence_when_today_is_done():
    assert streak_sentence(5, True) == "5 days in a row. Wow!"
    assert streak_sentence(1, True) == "1 day in a row. Wow!"


def test_streak_sentence_when_today_is_not_done_yet():
    assert streak_sentence(5, False) == "5 days in a row. Do your goal today to keep it going!"
    assert streak_sentence(1, False) == "1 day in a row. Do your goal today to keep it going!"


def test_no_sentence_is_ever_harsh():
    words = ("fail", "behind", "lost", "broke", "worse")
    sentences = [streak_sentence(n, done) for n in range(0, 6) for done in (True, False)]
    sentences += [goal_sentence(s, HOUR) for s in (0, 1, 30, 1800, 3599, 3600, 7200)]
    for sentence in sentences:
        for word in words:
            assert word not in sentence.lower(), sentence


# --- stepped_goal ------------------------------------------------------ #

def test_stepped_goal_goes_up_and_down_by_fifteen_minutes():
    assert stepped_goal(60, +1) == 75
    assert stepped_goal(60, -1) == 45


def test_stepped_goal_stops_at_fifteen_minutes():
    assert stepped_goal(30, -1) == 15
    assert stepped_goal(15, -1) == 15


def test_stepped_goal_stops_at_twelve_hours():
    assert stepped_goal(705, +1) == 720
    assert stepped_goal(720, +1) == 720


def test_stepped_goal_from_a_number_that_is_not_a_multiple_of_fifteen():
    assert stepped_goal(20, +1) == 35
    assert stepped_goal(20, -1) == 15    # 5 is clamped up to the floor
    assert stepped_goal(718, +1) == 720  # 733 is clamped down to the ceiling
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_geats.py -v`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'lock_in.tier5.geats'`.

- [ ] **Step 3: Write the minimal implementation**

Create `lock_in/tier5/geats.py`:

```python
"""
tier5/geats.py
==============
Kamen Rider Geats' Tier 5 gimmick: a "Goal" tab. You pick how many
minutes you want to focus each day, a bar fills up as you focus, and a
streak counts the days in a row you reached your goal. The seventh of
Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-21-tier5-geats-daily-goal-design.md.

The six small functions below are plain logic, tested with no Tk and no
display server. `build()` is the only Tk-dependent piece; it's checked in
the running app instead, matching every other tab.
"""

from __future__ import annotations

from datetime import date, timedelta

from ..config import (
    DAILY_GOAL_MAX_MINUTES,
    DAILY_GOAL_MIN_MINUTES,
    DAILY_GOAL_STEP_MINUTES,
)
from ._shared import format_hm, last_n_days


def streak_days(totals: dict[str, int], today: date, goal_seconds: int) -> int:
    """How many days in a row reached the goal. A day is done when its
    total is at least the goal. If today is done, today counts. If today
    is NOT done yet, it is still in play until midnight, so the streak is
    counted back from yesterday instead -- being part-way through the day
    never breaks it. The walk also stops at the first day in `totals`, as
    a second safety net."""
    if not totals:
        return 0
    earliest = date.fromisoformat(min(totals))
    day = today
    if totals.get(day.isoformat(), 0) < goal_seconds:
        day = today - timedelta(days=1)
    count = 0
    while day >= earliest and totals.get(day.isoformat(), 0) >= goal_seconds:
        count += 1
        day -= timedelta(days=1)
    return count


def week_dots(totals: dict[str, int], today: date, goal_seconds: int) -> list[tuple[date, bool]]:
    """Exactly 7 tuples of (day, done), oldest to newest, ending on today.
    Uses last_n_days(), so a day with no focus blocks counts as 0 seconds
    and is not done."""
    return [
        (day, seconds >= goal_seconds)
        for day, seconds in last_n_days(totals, today, 7)
    ]


def goal_sentence(today_seconds: int, goal_seconds: int) -> str:
    """One short, kind sentence about today. The time left is rounded UP
    to a whole minute, so 30 seconds short reads "1m to go", never
    "0m to go"."""
    if today_seconds >= goal_seconds:
        return "You did it! Goal done for today. Yay!"
    if today_seconds == 0:
        return "Start a focus block to fill the bar."
    left_seconds = -(-(goal_seconds - today_seconds) // 60) * 60
    return f"{format_hm(left_seconds)} to go. You can do it!"


def days_in_a_row(streak: int) -> str:
    """'5 days in a row', '1 day in a row', '0 days in a row'. The one
    place the word "day" is made singular."""
    unit = "day" if streak == 1 else "days"
    return f"{streak} {unit} in a row"


def streak_sentence(streak: int, today_done: bool) -> str:
    """One short, kind sentence about the streak."""
    if streak == 0:
        return "No streak yet. Reach your goal today to start one!"
    if today_done:
        return f"{days_in_a_row(streak)}. Wow!"
    return f"{days_in_a_row(streak)}. Do your goal today to keep it going!"


def stepped_goal(minutes: int, direction: int) -> int:
    """What one press of the minus (direction -1) or plus (direction +1)
    button does: 15 minutes up or down, never below 15 minutes or above
    12 hours."""
    stepped = minutes + DAILY_GOAL_STEP_MINUTES * direction
    return max(DAILY_GOAL_MIN_MINUTES, min(DAILY_GOAL_MAX_MINUTES, stepped))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_geats.py -v`
Expected: 34 tests, all PASS.

- [ ] **Step 5: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 3: The "Goal" tab, plus the wiring

**Files:**
- Modify: `lock_in/tier5/geats.py` (add imports and `build()`)
- Modify: `lock_in/tier5/__init__.py`
- Modify: `lock_in/tier5/v3.py`, `den_o.py`, `decade.py`, `zi_o.py`, `blade.py`, `w.py` (one line each)
- Modify: `lock_in/rider_themes.py` (the `Kamen Rider Geats (2022)` entry, and one comment)
- Modify: `lock_in/ui.py` (`_TIER5_TAB_LABELS`, and the builder call)
- Modify: `tests/test_tier5_geats.py` (wiring tests)
- Modify: `tests/test_rider_themes.py`

**Interfaces:**
- Consumes: the six functions (Task 2); `Config.effective_daily_goal_minutes()`, `Config.daily_goal_minutes`, `Config.save()` and the limits (Task 1); `history.total_seconds_by_day()`; `visuals.display_font_family()`; the theme's `secondary`, `primary_text_pair`.
- Produces: `build(parent, *, history, tasks, theme, appearance_mode, config) -> None`, registered as `TIER5_BUILDERS["goal_streak"]`; the tab label `"Goal"`; every other builder now also accepts `config=None`; `ui.py` passes `config=self.config_obj` to all of them.

- [ ] **Step 1: Write the failing wiring tests**

Append to `tests/test_tier5_geats.py`, with two blank lines before them:

```python
# --- wiring ------------------------------------------------------------ #

def test_every_tier5_builder_accepts_config():
    """ui.py passes config= to every builder, so all of them must take it."""
    import inspect
    from lock_in.tier5 import TIER5_BUILDERS
    for effect, builder in TIER5_BUILDERS.items():
        assert "config" in inspect.signature(builder).parameters, effect


def test_goal_streak_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, geats
    assert TIER5_BUILDERS["goal_streak"] is geats.build


def test_goal_streak_has_the_goal_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["goal_streak"] == "Goal"
```

In `tests/test_rider_themes.py`, the completeness check grows from six Riders to seven. Two edits:

In `tests/test_rider_themes.py`, replace:

```python
def test_exactly_these_six_riders_have_a_tier5_effect():
```

with:

```python
def test_exactly_these_seven_riders_have_a_tier5_effect():
```

In `tests/test_rider_themes.py`, replace:

```python
        "Kamen Rider W (2009)": "week_compare",
    }
```

with:

```python
        "Kamen Rider W (2009)": "week_compare",
        "Kamen Rider Geats (2022)": "goal_streak",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_geats.py tests/test_rider_themes.py -v`
Expected: 4 FAIL (the builder-signature check, the registry check, the tab-label check, and the seven-Riders check). Everything else PASSES.

- [ ] **Step 3: Add `build()` to `geats.py`**

First, in `lock_in/tier5/geats.py`, replace the import block at the top with this one. It adds the CustomTkinter import, the `visuals` import, and the small color constant the boxes use:

Replace:

```python
from datetime import date, timedelta

from ..config import (
    DAILY_GOAL_MAX_MINUTES,
    DAILY_GOAL_MIN_MINUTES,
    DAILY_GOAL_STEP_MINUTES,
)
from ._shared import format_hm, last_n_days
```

with:

```python
from datetime import date, timedelta

import customtkinter as ctk

from .. import visuals
from ..config import (
    DAILY_GOAL_MAX_MINUTES,
    DAILY_GOAL_MIN_MINUTES,
    DAILY_GOAL_STEP_MINUTES,
)
from ._shared import format_hm, last_n_days

# What an empty (goal not reached) box looks like -- CustomTkinter's own
# gray, picked for light and dark mode.
_EMPTY_BOX = ("gray80", "gray30")
```

Then add this to the very end of the file, with two blank lines before it:

```python
def build(parent, *, history, tasks, theme, appearance_mode, config) -> None:
    """
    Populate `parent` with Geats' Goal view: today's bar against the daily
    goal, the goal's minus and plus buttons, the streak, and seven boxes
    for the last 7 days.

    Every widget is built once, and refresh() then re-configures them. The
    buttons never destroy and rebuild the tab from inside their own click,
    which is what makes them safe to press.

    `tasks` and `appearance_mode` are part of every Tier 5 builder's
    signature for consistency -- Geats needs neither. CustomTkinter's own
    (light, dark) color pairs already handle light and dark switching.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    totals = history.total_seconds_by_day()
    today = date.today()
    today_seconds = totals.get(today.isoformat(), 0)
    week = last_n_days(totals, today, 7)
    text_color = theme.primary_text_pair
    big_font = ctk.CTkFont(family=visuals.display_font_family(), size=20, weight="bold")

    def line(name: str) -> ctk.CTkLabel:
        """A row with `name` on the left and a big value on the right.
        Returns the value label so refresh() can change it."""
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(row, text=name, text_color=text_color, anchor="w").pack(
            side="left", fill="x", expand=True)
        value = ctk.CTkLabel(row, text="", text_color=text_color, anchor="e", font=big_font)
        value.pack(side="right")
        return value

    def sentence() -> ctk.CTkLabel:
        label = ctk.CTkLabel(frame, text="", justify="left", wraplength=400, anchor="w")
        label.pack(anchor="w", pady=(6, 12))
        return label

    # --- today's bar ------------------------------------------------------ #
    today_value = line("Today")
    bar = ctk.CTkProgressBar(frame, progress_color=theme.secondary)
    bar.pack(fill="x", pady=(6, 0))
    today_sentence = sentence()

    # --- the goal row: Daily goal ........ [-] 1h [+] --------------------- #
    goal_row = ctk.CTkFrame(frame, fg_color="transparent")
    goal_row.pack(fill="x", pady=(0, 12))
    ctk.CTkLabel(goal_row, text="Daily goal", text_color=text_color, anchor="w").pack(
        side="left", fill="x", expand=True)
    # Packed from the right edge inward: plus first, then the number, then
    # minus, so they read minus, number, plus from left to right.
    plus_button = ctk.CTkButton(goal_row, text="+", width=36, command=lambda: change_goal(+1))
    plus_button.pack(side="right")
    goal_value = ctk.CTkLabel(goal_row, text="", text_color=text_color, width=80)
    goal_value.pack(side="right", padx=6)
    minus_button = ctk.CTkButton(goal_row, text="-", width=36, command=lambda: change_goal(-1))
    minus_button.pack(side="right")

    # --- the streak ------------------------------------------------------- #
    streak_value = line("Streak")
    streak_text = sentence()

    # --- seven boxes, today last ------------------------------------------ #
    boxes_row = ctk.CTkFrame(frame, fg_color="transparent")
    boxes_row.pack(anchor="w")
    boxes = []
    for day, _ in week:
        cell = ctk.CTkFrame(boxes_row, fg_color="transparent")
        cell.pack(side="left", padx=4)
        box = ctk.CTkFrame(cell, width=28, height=28, corner_radius=6, fg_color=_EMPTY_BOX)
        box.pack()
        ctk.CTkLabel(
            cell, text=day.strftime("%a")[0],
            text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
        ).pack()
        boxes.append(box)

    ctk.CTkLabel(
        frame, text="Every focus block counts, finished or not · every day is judged by today's goal",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(10, 0))

    def refresh() -> None:
        """Re-configure every widget that depends on the goal."""
        goal_minutes = config.effective_daily_goal_minutes()
        goal_seconds = goal_minutes * 60
        streak = streak_days(totals, today, goal_seconds)

        today_value.configure(text=f"{format_hm(today_seconds)} of {format_hm(goal_seconds)}")
        bar.set(min(1.0, today_seconds / goal_seconds))
        today_sentence.configure(text=goal_sentence(today_seconds, goal_seconds))

        goal_value.configure(text=format_hm(goal_seconds))
        minus_button.configure(state="normal" if goal_minutes > DAILY_GOAL_MIN_MINUTES else "disabled")
        plus_button.configure(state="normal" if goal_minutes < DAILY_GOAL_MAX_MINUTES else "disabled")

        streak_value.configure(text=days_in_a_row(streak))
        streak_text.configure(text=streak_sentence(streak, today_seconds >= goal_seconds))
        for box, (_, done) in zip(boxes, week_dots(totals, today, goal_seconds)):
            box.configure(fg_color=theme.secondary if done else _EMPTY_BOX)

    def change_goal(direction: int) -> None:
        config.daily_goal_minutes = stepped_goal(config.effective_daily_goal_minutes(), direction)
        try:
            config.save()
        except OSError:
            # For example, the file is locked. The new goal still works for
            # the rest of this session, and the next press tries the save again.
            pass
        refresh()

    refresh()
```

- [ ] **Step 4: Let every builder accept `config`**

`ui.py` is about to hand `config=` to every builder, so the other six must accept it. In each of `lock_in/tier5/v3.py`, `den_o.py`, `decade.py`, `zi_o.py`, `blade.py`, and `w.py`, replace this one line (each file has it exactly once):

```python
def build(parent, *, history, tasks, theme, appearance_mode) -> None:
```

with:

```python
def build(parent, *, history, tasks, theme, appearance_mode, config=None) -> None:
```

They accept `config` and ignore it, the same way they already ignore whatever they don't need.

- [ ] **Step 5: Register the builder**

In `lock_in/tier5/__init__.py`, replace:

```python
from . import blade, decade, den_o, v3, w, zi_o
```

with:

```python
from . import blade, decade, den_o, geats, v3, w, zi_o
```

In `lock_in/tier5/__init__.py`, replace:

```python
    "week_compare": w.build,
}
```

with:

```python
    "week_compare": w.build,
    "goal_streak": geats.build,
}
```

And the same file's top comment gets one line about `config`:

In `lock_in/tier5/__init__.py`, replace:

```python
TIER5_BUILDERS grows one entry per Rider as each one is built.
```

with:

```python
Every builder also accepts `config` (the app's settings). Only Geats uses
it, to read and save the daily goal; the others ignore it.

TIER5_BUILDERS grows one entry per Rider as each one is built.
```

- [ ] **Step 6: Give Geats its effect**

In `lock_in/rider_themes.py`, replace:

```python
    "Kamen Rider Geats (2022)": RiderTheme(
        "Reiwa", 2022, ("#9e9e9e", "#ffffff"), ("#9c1e1e", "#ef5350"),
    ),
```

with:

```python
    "Kamen Rider Geats (2022)": RiderTheme(
        "Reiwa", 2022, ("#9e9e9e", "#ffffff"), ("#9c1e1e", "#ef5350"),
        tier5_effect="goal_streak",
    ),
```

And the comment above `tier5_effect` in the same file lists the Riders "so far". Update it:

In `lock_in/rider_themes.py`, replace:

```python
    # history (V3, Den-O, Decade, Zi-O and Blade so far, out of 10
```

with:

```python
    # history (V3, Den-O, Decade, Zi-O, Blade, W and Geats so far, out of 10
```

- [ ] **Step 7: Give the tab its name, and hand over `config`**

In `lock_in/ui.py`:

In `lock_in/ui.py`, replace:

```python
    "history_editor": "History", "kanban_board": "Board", "week_compare": "Week",
}
```

with:

```python
    "history_editor": "History", "kanban_board": "Board", "week_compare": "Week",
    "goal_streak": "Goal",
}
```

And in `_build_tier5_tab()`:

In `lock_in/ui.py`, replace:

```python
            theme=self._current_rider_theme, appearance_mode=ctk.get_appearance_mode(),
        )
```

with:

```python
            theme=self._current_rider_theme, appearance_mode=ctk.get_appearance_mode(),
            config=self.config_obj,
        )
```

Nothing else in `ui.py` changes for the tab itself: building it, refreshing it after a finished block, and hiding it for Standard Mode all already work for any registered effect.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_geats.py tests/test_rider_themes.py -v`
Expected: all PASS.

- [ ] **Step 9: Drive the real tab in the real app**

Save the script below as `geats_drive.py` in any scratch folder OUTSIDE the project (for example your temp folder). It points the app at a throwaway data folder, so your real settings and history are not touched. It seeds fake history, then **presses the real minus and plus buttons**:

- today 40 minutes, 1 day ago 65, 2 ago 60, 3 ago 30, 4 ago 120, 5 ago 90, 6 ago nothing
- at the starting goal of 1 hour: today is not done yet, so the streak counts back from yesterday and is **2**, and **4** of the 7 boxes are filled

```python
"""Drives the real Lock In window with fake history, pressing the real
minus and plus buttons. Run from the PROJECT folder so `lock_in` can be
imported:

  Git Bash:    PYTHONPATH=. python /path/to/geats_drive.py
  PowerShell:  $env:PYTHONPATH="."; python C:\\path\\to\\geats_drive.py

Optional switches (environment variables):
  EMPTY=1                          fresh install, no history
  RIDER="Kamen Rider (1971)"       a Rider other than Geats (the Goal tab must be absent)
  SHOT=C:\\some\\folder\\goal      also saves goal-dark.png and goal-light.png
"""
import ctypes, dataclasses, json, os, sys, tempfile, time
from datetime import datetime, timedelta
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="lockin_fake_appdata_")

from lock_in.config import Config, LOG_PATH
from lock_in.history import SessionRecord

GEATS = "Kamen Rider Geats (2022)"
RIDER = os.environ.get("RIDER", GEATS)
EMPTY = bool(os.environ.get("EMPTY"))
SHOT = os.environ.get("SHOT")
CAPTION = "Every focus block counts, finished or not · every day is judged by today's goal"
EMPTY_BOX = ("gray80", "gray30")

config = Config()
config.rider_theme = RIDER
config.save()

# Minutes focused, by how many days ago. With the starting goal of 1 hour:
#   today 40m (not done yet), 1 ago 65m, 2 ago 60m, 3 ago 30m, 4 ago 120m,
#   5 ago 90m, 6 ago nothing.
MINUTES = {0: 40, 1: 65, 2: 60, 3: 30, 4: 120, 5: 90}


def make_record(days_ago, minutes):
    start = (datetime.now() - timedelta(days=days_ago)).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=minutes)
    return SessionRecord(start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds"),
                         minutes * 60, None, True)


if not EMPTY:
    lines = [json.dumps(dataclasses.asdict(make_record(d, m))) for d, m in MINUTES.items()]
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

import customtkinter as ctk
from lock_in.ui import LockInApp

failures = []
def check(label, condition):
    print(("  PASS  " if condition else "  FAIL  ") + label)
    if not condition:
        failures.append(label)

def walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from walk(child)

def label_texts(widget):
    return [w.cget("text") for w in walk(widget) if isinstance(w, ctk.CTkLabel) and w.cget("text")]

def button(widget, text):
    return next(w for w in walk(widget) if isinstance(w, ctk.CTkButton) and w.cget("text") == text)

def filled_boxes(widget):
    boxes = [w for w in walk(widget)
             if isinstance(w, ctk.CTkFrame) and w.cget("width") == 28 and w.cget("height") == 28]
    assert len(boxes) == 7, f"expected 7 boxes, found {len(boxes)}"
    return sum(1 for b in boxes if tuple(b.cget("fg_color")) != EMPTY_BOX)

def bar_value(widget):
    return next(w for w in walk(widget) if isinstance(w, ctk.CTkProgressBar)).get()

app = LockInApp()
app.update()
has_tab = "Goal" in app.tabs._tab_dict

if RIDER != GEATS:
    check("no Goal tab for a Rider that isn't Geats", not has_tab)
else:
    check("Goal tab exists for Geats", has_tab)
    app.tabs.set("Goal")
    app.update()
    tab = app.tabs.tab("Goal")

    def press(text):
        button(tab, text).invoke()
        app.update()

    def saved_goal():
        return Config.load().daily_goal_minutes

    def expect(expected_texts):
        texts = label_texts(tab)
        for expected in expected_texts:
            check(f"shows {expected!r}", expected in texts)

    if EMPTY:
        print("fresh install:")
        expect(["Today", "0m of 1h 0m", "Start a focus block to fill the bar.", "Daily goal", "1h 0m",
                "Streak", "0 days in a row", "No streak yet. Reach your goal today to start one!", CAPTION])
        check("no boxes filled", filled_boxes(tab) == 0)
        check("bar is empty", bar_value(tab) == 0)
        print("press plus on a fresh install:")
        press("+")
        expect(["0m of 1h 15m", "1h 15m"])
        check("goal saved as 75", saved_goal() == 75)
    else:
        print("goal 1h (the starting goal):")
        expect(["Today", "40m of 1h 0m", "20m to go. You can do it!", "Daily goal", "1h 0m", "Streak",
                "2 days in a row", "2 days in a row. Do your goal today to keep it going!", CAPTION])
        check("4 boxes filled", filled_boxes(tab) == 4)
        check("bar is two thirds full", abs(bar_value(tab) - 40 / 60) < 0.01)
        check("goal not saved yet as anything but the default", saved_goal() == 60)

        if SHOT:
            app.geometry("560x1000+40+0")
            app.attributes("-topmost", True)   # keep other windows off the picture
            for mode in ("dark", "light"):
                app._on_appearance_change(mode)
                app.tabs.set("Goal")
                app.lift(); app.update(); time.sleep(0.6); app.update()
                x, y = app.winfo_rootx(), app.winfo_rooty()
                from PIL import ImageGrab
                ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(f"{SHOT}-{mode}.png")
                print("  saved", f"{SHOT}-{mode}.png")
            tab = app.tabs.tab("Goal")   # the tabs were rebuilt

        print("press plus (75 minutes):")
        press("+")
        expect(["1h 15m", "40m of 1h 15m", "35m to go. You can do it!", "0 days in a row",
                "No streak yet. Reach your goal today to start one!"])
        check("2 boxes filled", filled_boxes(tab) == 2)
        check("goal saved as 75", saved_goal() == 75)

        print("press minus twice (45 minutes):")
        press("-"); press("-")
        expect(["45m", "40m of 45m", "5m to go. You can do it!", "2 days in a row"])
        check("4 boxes filled", filled_boxes(tab) == 4)
        check("goal saved as 45", saved_goal() == 45)

        print("press minus (30 minutes, today's goal is now done):")
        press("-")
        expect(["30m", "40m of 30m", "You did it! Goal done for today. Yay!",
                "6 days in a row", "6 days in a row. Wow!"])
        check("6 boxes filled", filled_boxes(tab) == 6)
        check("bar is full", abs(bar_value(tab) - 1.0) < 0.001)

        print("press minus (15 minutes, the smallest goal):")
        press("-")
        expect(["15m"])
        check("minus button switches off", button(tab, "-").cget("state") == "disabled")
        check("goal saved as 15", saved_goal() == 15)

        print("press plus until it stops (12 hours, the biggest goal):")
        presses = 0
        while button(tab, "+").cget("state") != "disabled" and presses < 100:
            press("+")
            presses += 1
        expect(["12h 0m"])
        check("it took 47 presses to get from 15 minutes to 12 hours", presses == 47)
        check("plus button switches off", button(tab, "+").cget("state") == "disabled")
        check("goal saved as 720", saved_goal() == 720)

        print("finish a block while the tab is open:")
        app.history.record(make_record(0, 30))
        app._build_tier5_tab()
        app.update()
        tab = app.tabs.tab("Goal")
        expect(["1h 10m of 12h 0m"])
        check("plus stays switched off after the refresh", button(tab, "+").cget("state") == "disabled")

app.destroy()
print("\nFAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
```

Run it three ways, from the project folder:
1. With history: every line prints PASS and `FAILURES: none`.
2. `EMPTY=1`: the fresh-install lines pass, and pressing plus works.
3. `RIDER="Kamen Rider (1971)"`: the "no Goal tab" line passes.

Then run it once more with `SHOT` set and open the two PNGs. Expected in both light and dark: "Today" with `40m of 1h 0m` on the right and a red bar about two thirds full, the sentence `20m to go. You can do it!`, the "Daily goal" row with a small `-` button, `1h 0m`, and a `+` button, "Streak" with `2 days in a row`, the streak sentence, seven boxes with weekday letters (four red, three gray, today last), and the small caption. If the tab area is too short to show everything, scroll the tab and look again; if the window is taller than your screen, lower the `560x1000` value.

- [ ] **Step 10: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 4: Docs, version, and final checks

**Files:**
- Modify: `lock_in/__init__.py`
- Modify: `lock_in/ui.py` (Help tab)
- Modify: `README.md`

**Interfaces:**
- Consumes: the finished feature from Tasks 1 to 3.
- Produces: version `2.5.7`; the Geats bullet in the Help tab and README; the "seven" wording; one known-limit line.

- [ ] **Step 1: Bump the version**

In `lock_in/__init__.py`, replace:

```python
__version__ = "2.5.6"
```

with:

```python
__version__ = "2.5.7"
```

- [ ] **Step 2: Help tab**

In `lock_in/ui.py`, in the Tier 5 section of the Help tab (right after the W bullet):

In `lock_in/ui.py`, replace:

```python
        body(
            "More heroes will get a tab like this over time -- these "
            "six are just the first."
        )
```

with:

```python
        bullet(
            "Geats — a \"Goal\" tab appears. Pick how many minutes you "
            "want to focus each day with the minus and plus buttons. A "
            "bar fills up as you focus, and a streak counts the days in "
            "a row you reached your goal. Every block counts, finished "
            "or not."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "seven are just the first."
        )
```

- [ ] **Step 3: README, the Geats bullet and the count**

In `README.md`, in the "Tier 5" section, directly after the W bullet (which ends "...Every block counts, finished or not."):

In `README.md`, replace:

```
More Riders will read your tasks and history this way over time — these
six are just the first of ten planned.
```

with:

```
- **Geats** — adds a "Goal" tab. You pick how many minutes you want to
  focus each day with a minus and a plus button (each press is 15
  minutes, and the app remembers your pick). A bar fills up as you
  focus, and a streak counts how many days in a row you reached your
  goal. Seven little boxes show the last 7 days, filled in for the days
  you made it. Every block counts, finished or not.

More Riders will read your tasks and history this way over time — these
seven are just the first of ten planned.
```

Keep one blank line between the Geats bullet and the "More Riders..." paragraph.

- [ ] **Step 4: README, one known limit**

In the "Known limits" list, directly before the line starting `- **Auto-update only replaces the downloaded app**`:

In `README.md`, replace:

```
- **Auto-update only replaces the downloaded app**
```

with:

```
- **Geats judges every day by the goal you have now** — there is one
  goal number, not a different one for each day. Making the goal bigger
  can make your streak shorter, and making it smaller can make it longer.
- **Auto-update only replaces the downloaded app**
```

The Config table in the README already says `config.json` holds "every setting", so it needs no change.

- [ ] **Step 5: Run everything**

Run: `python -m pytest`
Expected: 0 failed, 1 skipped (the same skip as before).

Run the existing real-window smoke test in a throwaway data folder. Git Bash: `APPDATA="$(mktemp -d)" PYTHONPATH=. python tests/smoke_ui.py`. PowerShell: `$env:APPDATA=(New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([guid]::NewGuid()))).FullName; $env:PYTHONPATH="."; python tests/smoke_ui.py`.
Expected: ends with `smoke test passed`.

Re-run `geats_drive.py` (Task 3, Step 9) with history. Expected: `FAILURES: none`. Then open the real app once with a Rider that is **not** Geats and open Help: it should now say v2.5.7.

- [ ] **Step 6: Repo hygiene checks**

Run: `git status --short`
Expected: exactly these paths, and nothing else (in particular nothing generated):
`README.md`, `lock_in/__init__.py`, `lock_in/config.py`, `lock_in/rider_themes.py`, `lock_in/tier5/__init__.py`, `lock_in/tier5/blade.py`, `lock_in/tier5/decade.py`, `lock_in/tier5/den_o.py`, `lock_in/tier5/geats.py` (new), `lock_in/tier5/v3.py`, `lock_in/tier5/w.py`, `lock_in/tier5/zi_o.py`, `lock_in/ui.py`, `tests/test_config.py`, `tests/test_rider_themes.py`, `tests/test_tier5_geats.py` (new), plus the spec and this plan under `docs/superpowers/`.
If anything else shows up (a picture, a data file, a folder), add a matching line to `.gitignore`. If nothing does, `.gitignore` needs no change. Geats makes no new file, because its goal is saved inside the existing `config.json`, which is already ignored, so none is expected.

Now check that the changes describe the software only. This looks at the lines you added and at the four new files, and prints any line that names a helper tool or a co-writer, or that has a credit line. The square brackets are on purpose: they stop the check from matching its own words.

```bash
git diff -U0 | grep '^+' | grep -inE "cl[a]ude|anthrop[i]c|co-[a]uthor|generated [w]ith|[a]ssistant|sub[a]gent|[a]gentic" ; grep -inE "cl[a]ude|anthrop[i]c|co-[a]uthor|generated [w]ith|[a]ssistant|sub[a]gent|[a]gentic" lock_in/tier5/geats.py tests/test_tier5_geats.py docs/superpowers/specs/2026-09-21-tier5-geats-daily-goal-design.md docs/superpowers/plans/2026-09-21-tier5-geats-daily-goal.md
```

Expected: nothing printed. The README's older lines about the app's own optional window-check helper are not "added lines", so they do not show up here.

---

## Handoff: git steps for the project owner

Nothing above runs any of these. Run them yourself once you have looked at the result. The commit message is plain, with **one** `-m` and no extra lines under it, so no trailer or credit line can end up in it.

```bash
git status
git add -A
git commit -m "v2.5.7: add Geats (Tier 5 Rider 7), the daily goal and streak"
git log -1 --format=%B
git shortlog -sne
git push origin main
git tag v2.5.7
git push origin v2.5.7
```

Two safety looks after the commit and before the pushes:
- `git log -1 --format=%B` should print only the one-line message above, and nothing under it.
- `git shortlog -sne` should list only you, with your own name and email, and nobody else. Anyone listed there would show up as a contributor on GitHub.

Pushing the tag starts the release build (`.github/workflows/release.yml`), so push it last, after you are happy with the result. Git may print harmless "LF will be replaced by CRLF" warnings.

## Spec coverage check

| Spec section | Where it's covered |
|---|---|
| The rules (goal buttons, range, "done", streak, changing the goal) | Task 2 (`streak_days`, `week_dots`, `stepped_goal` + their tests, including today-not-done-yet, exact-goal, month and year boundaries, a long streak, re-judging), Task 3 (`build()`, checked in the real app) |
| The tab (bar, sentences, goal row, streak line, seven boxes, caption, no early exit) | Task 3, Step 3 (`build()`) and Step 9 (checked in the real app, with and without history) |
| Colors | Task 3, Step 3, and the screenshots in Step 9 |
| The words on screen | Task 2 (`goal_sentence`, `days_in_a_row`, `streak_sentence` + tests for each row, the round-up rule, singular "day", and "never harsh") |
| The six pure functions and `build()` | Tasks 2 and 3 |
| `daily_goal_minutes`, `effective_daily_goal_minutes()` | Task 1 |
| Shared change (`config=` to every builder) | Task 3, Steps 1 (signature test), 4, and 7 |
| Wiring (registry, theme, tab label, theme comment) | Task 3, Steps 5 to 7, with wiring tests in Steps 1 and 8 |
| Error handling (bad saved goal, empty history, save failure, refresh keeps buttons right) | Task 1 (bad values), Task 2 (empty totals), Task 3 (`change_goal`'s save handling; Step 9's "finish a block while open" check) |
| Testing list | Tasks 1 to 3; manual checks in Task 3 Step 9 and Task 4 Step 5 |
| Docs, version, repo hygiene | Task 4 and the Handoff section |
| Out of scope (best streak, per-day goals, rewards, alerts, Settings box) | Nothing in this plan builds any of it |
