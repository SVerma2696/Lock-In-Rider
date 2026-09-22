# Tier 5 Rider #8 (Gotchard, the collectible badges) Implementation Plan

Spec: `docs/superpowers/specs/2026-09-21-tier5-gotchard-badges-design.md`.
Work through the tasks in order and tick each box as you go.

**Goal:** When Kamen Rider Gotchard (2023) is the picked Rider, a "Badges" tab shows 9 collectible badges as a 3x3 grid of cards, each won for real progress (blocks done, a big day, total hours, a checked-off task, or a streak of days that reached the daily goal), and every badge you win stays won forever.

**Architecture:** One new saved setting (`badges_earned`, a list of badge ids) in `lock_in/config.py`. A new `lock_in/tier5/gotchard.py` holds a fixed `BADGES` table, a small `Progress` dataclass, six pure functions (`longest_goal_run`, `progress`, `earned_ids`, `saved_badges`, `newly_won`, `badge_sentence`), plus the one Tk-dependent `build()`. The tab plugs into the existing `TIER5_BUILDERS` registry and `_TIER5_TAB_LABELS`, the same way V3, Den-O, Decade, Zi-O, Blade, W, and Geats did. Gotchard reads the daily goal Geats already added (`config.effective_daily_goal_minutes()`), but has no goal buttons of its own.

**Tech Stack:** Python 3, CustomTkinter, pytest. No new dependency, and no new drawing code (the cards are plain colored frames, same idea as Geats' boxes).

## Global Constraints

Copied from the spec. Every task below includes these.

- **Tab label:** `"Badges"`. **Effect name:** `"badge_cards"`. **Rider:** `Kamen Rider Gotchard (2023)`.
- **Nine badges**, fixed order, fixed ids: `first_step`, `ten_blocks`, `hour_day`, `big_day`, `ten_hours`, `task_done`, `goal_done`, `three_days`, `seven_days`.
- **Every focus block counts**, whether it finished, was skipped, or was reset early (same rule as V3, Decade, W, and Geats).
- **Badges are kept forever.** A badge already won never disappears, even if history is edited or the goal changes later.
- **Badges are checked every time the tab is built** (app open, block end, picking Gotchard).
- **Streak badges use the longest run of goal days anywhere in the history**, not just today's streak. A "goal day" is a day whose total is at least `config.effective_daily_goal_minutes() * 60` seconds.
- **The saved setting is `badges_earned`, a list of badge ids**, in the existing `config.json`. There is no goal box, and no badge-reset button, on this tab.
- **The goal reader is `Config.effective_daily_goal_minutes()`** (already built by Geats) — Gotchard never reads `daily_goal_minutes` directly.
- **`saved_badges()` is the safe reader** for `config.badges_earned`: anything that is not a list reads as `[]`; non-text entries are dropped; repeats are dropped, keeping the first; unknown names are kept but never counted or shown.
- **Sentences (exact text):**
  - exactly one new badge: `New! You won {name}!`
  - more than one new badge: `New! You won {n} badges!`
  - nothing new, 0 won: `Do a focus block to win your first badge.`
  - nothing new, all 9 won: `You got them all! Wow!`
  - nothing new, 1-8 won: `You have {have} of 9. Keep going!`
  - caption: `Every focus block counts, finished or not · a badge is yours to keep`
  - goal note: `Goal badges use your daily goal of {goal}. Pick Geats to change it.` (`{goal}` via the shared `format_hm()`)
  - a won card reads `Got it!`; a not-yet card reads `Not yet` plus its hint.
- **No sentence, name, or hint says** "fail", "behind", "lost", "missed", or "broke".
- **No early exit on an empty history.** With no history the count is `0 of 9` and all nine cards are gray.
- **Colors:** a won card uses `theme.secondary` with `theme.button_text_pair` text; a not-yet card uses `("gray80", "gray30")` with `("gray20", "gray80")` for its name and `("gray30", "gray70")` for its hint/state; the count and sentence use `theme.primary_text_pair`.
- **The tab has no buttons.** Every widget is built once, in a single pass — there is nothing to re-configure from inside a click.
- **Words a young child can follow** in every visible string, the README, and the Help tab.
- **Version:** `2.5.7` to `2.5.8`.
- **No commit, push, or tag is run while doing this plan.** The commands are in the Handoff section at the end, for the project owner to run.
- **Project files describe the software only** -- nothing about who or what wrote it, in any file added or edited.
- **Line endings:** edit existing files in place and keep their current line-ending style (most are CRLF). New files may use LF (Git converts on commit).

## File Structure

| File | What it's for |
|---|---|
| `lock_in/config.py` *(edit)* | The `badges_earned` setting |
| `lock_in/tier5/gotchard.py` *(new)* | `BADGES`, `Progress`, the six pure functions, and `build()` |
| `lock_in/tier5/__init__.py` *(edit)* | Register `"badge_cards": gotchard.build`; docstring line about `config` |
| `lock_in/rider_themes.py` *(edit)* | `tier5_effect="badge_cards"` on Gotchard; the comment's list of Riders |
| `lock_in/ui.py` *(edit)* | `_TIER5_TAB_LABELS` entry; Help tab bullet and wording |
| `lock_in/__init__.py` *(edit)* | Version 2.5.8 |
| `README.md` *(edit)* | Gotchard bullet, "eight of ten" wording, two known-limit lines |
| `tests/test_config.py` *(edit)* | The `badges_earned` setting |
| `tests/test_tier5_gotchard.py` *(new)* | The pure functions and the wiring |
| `tests/test_rider_themes.py` *(edit)* | The tier5 completeness check grows to eight |

---

### Task 1: The saved badge list (`badges_earned`)

**Files:**
- Modify: `lock_in/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `Config.badges_earned: List[str]` (default `[]`).

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/test_config.py` (it already imports `Config`), with two blank lines before them:

```python
def test_badges_earned_defaults_to_an_empty_list():
    assert Config().badges_earned == []


def test_two_configs_do_not_share_one_badges_earned_list():
    a = Config()
    b = Config()
    a.badges_earned.append("first_step")
    assert b.badges_earned == []


def test_badges_earned_round_trips_through_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    Config(badges_earned=["first_step", "ten_blocks"]).save(path)
    assert Config.load(path).badges_earned == ["first_step", "ten_blocks"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: the 3 new tests FAIL (`Config` has no `badges_earned` yet). The older tests still PASS.

- [ ] **Step 3: Write the implementation**

In `lock_in/config.py`, replace:

```python
    daily_goal_minutes: int = DAILY_GOAL_DEFAULT_MINUTES
```

with:

```python
    daily_goal_minutes: int = DAILY_GOAL_DEFAULT_MINUTES

    # Gotchard's badge collection: the ids of every badge you've won so
    # far (see lock_in/tier5/gotchard.py's BADGES). A badge is added here
    # the first time you earn it and is never removed by this app -- once
    # you have it, it's yours to keep. Read it with
    # lock_in.tier5.gotchard.saved_badges(), not directly: that one is
    # safe even if a hand-edited config.json holds something silly.
    badges_earned: List[str] = field(default_factory=list)
```

Only the `daily_goal_minutes` line above needs to match — the file has exactly one line that reads `daily_goal_minutes: int = DAILY_GOAL_DEFAULT_MINUTES`, so this replace is unambiguous.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: all PASS.

- [ ] **Step 5: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 2: Gotchard's badge table and pure functions

**Files:**
- Create: `lock_in/tier5/gotchard.py`
- Create: `tests/test_tier5_gotchard.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (these functions take plain values, not a `Config`).
- Produces, all in `lock_in/tier5/gotchard.py`:
  - `Badge` (a frozen dataclass: `id: str`, `name: str`, `hint: str`, `metric: str`, `target: int`)
  - `BADGES: list[Badge]`, exactly 9 entries in the fixed order
  - `Progress` (a frozen dataclass: `blocks: int`, `best_day_seconds: int`, `total_seconds: int`, `longest_run: int`, `tasks_done: int`)
  - `longest_goal_run(totals: dict[str, int], goal_seconds: int) -> int`
  - `progress(totals: dict[str, int], block_count: int, goal_seconds: int, tasks_done: int) -> Progress`
  - `earned_ids(p: Progress) -> list[str]`
  - `saved_badges(raw) -> list[str]`
  - `newly_won(earned: list[str], saved: list[str]) -> list[str]`
  - `badge_sentence(have: int, total: int, new_names: list[str]) -> str`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tier5_gotchard.py`:

```python
from datetime import date, timedelta

from lock_in.tier5.gotchard import (
    BADGES,
    Progress,
    badge_sentence,
    earned_ids,
    longest_goal_run,
    newly_won,
    progress,
    saved_badges,
)

TODAY = date(2026, 9, 22)
HOUR = 3600
HARSH_WORDS = ("fail", "behind", "lost", "missed", "broke")


def _iso(days_ago: int, today: date = TODAY) -> str:
    return (today - timedelta(days=days_ago)).isoformat()


def _totals(*days_ago_and_seconds: tuple[int, int], today: date = TODAY) -> dict[str, int]:
    """_totals((0, 3600), (1, 3600)) -> today and yesterday, an hour each."""
    return {_iso(days_ago, today): seconds for days_ago, seconds in days_ago_and_seconds}


# --- BADGES -------------------------------------------------------------- #

def test_there_are_exactly_nine_badges():
    assert len(BADGES) == 9


def test_every_badge_has_a_different_id():
    ids = [badge.id for badge in BADGES]
    assert len(ids) == len(set(ids))


def test_the_badges_are_exactly_these_nine_ids_in_order():
    assert [badge.id for badge in BADGES] == [
        "first_step", "ten_blocks", "hour_day", "big_day", "ten_hours",
        "task_done", "goal_done", "three_days", "seven_days",
    ]


def test_every_badge_has_a_name_and_a_hint():
    for badge in BADGES:
        assert badge.name
        assert badge.hint


def test_no_badge_name_or_hint_is_harsh():
    for badge in BADGES:
        for word in HARSH_WORDS:
            assert word not in badge.name.lower(), badge.name
            assert word not in badge.hint.lower(), badge.hint


# --- longest_goal_run ------------------------------------------------------ #

def test_longest_goal_run_with_no_history_is_zero():
    assert longest_goal_run({}, HOUR) == 0


def test_longest_goal_run_counts_one_goal_day():
    assert longest_goal_run(_totals((0, HOUR)), HOUR) == 1


def test_longest_goal_run_counts_a_run_of_days_in_a_row():
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR))
    assert longest_goal_run(totals, HOUR) == 3


def test_longest_goal_run_picks_the_longer_of_two_runs_split_by_a_gap():
    totals = _totals(
        (0, HOUR), (1, HOUR),                # a 2-day run, ending today
        (5, HOUR), (6, HOUR), (7, HOUR),     # a 3-day run, further back
    )
    assert longest_goal_run(totals, HOUR) == 3


def test_a_day_exactly_at_the_goal_counts_and_one_second_under_does_not():
    totals = _totals((0, HOUR), (1, HOUR - 1))
    assert longest_goal_run(totals, HOUR) == 1


def test_longest_goal_run_across_a_month_boundary():
    today = date(2026, 10, 2)
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR), (3, HOUR), today=today)
    assert longest_goal_run(totals, HOUR) == 4


def test_longest_goal_run_across_a_year_boundary():
    today = date(2027, 1, 2)
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR), (3, HOUR), today=today)
    assert longest_goal_run(totals, HOUR) == 4


def test_longest_goal_run_over_a_very_long_history_does_not_loop_forever():
    totals = _totals(*[(days_ago, HOUR) for days_ago in range(400)])
    assert longest_goal_run(totals, HOUR) == 400


def test_a_bigger_goal_gives_a_shorter_run_for_the_same_history():
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR))
    assert longest_goal_run(totals, HOUR) == 3
    assert longest_goal_run(totals, 2 * HOUR) == 0


# --- progress ---------------------------------------------------------------- #

def test_progress_with_no_history_is_all_zero_except_tasks_done():
    result = progress({}, 0, HOUR, tasks_done=2)
    assert result == Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=0, tasks_done=2)


def test_progress_reads_blocks_best_day_and_total_from_a_small_history():
    totals = _totals((0, 30 * 60), (1, 2 * HOUR))
    result = progress(totals, block_count=5, goal_seconds=HOUR, tasks_done=1)
    assert result.blocks == 5
    assert result.best_day_seconds == 2 * HOUR
    assert result.total_seconds == 30 * 60 + 2 * HOUR
    assert result.longest_run == 1
    assert result.tasks_done == 1


# --- earned_ids --------------------------------------------------------------- #

def test_earned_ids_with_all_zero_progress_wins_nothing():
    assert earned_ids(Progress(0, 0, 0, 0, 0)) == []


def test_each_badge_turns_on_at_exactly_its_target():
    assert earned_ids(Progress(blocks=1, best_day_seconds=0, total_seconds=0, longest_run=0, tasks_done=0)) == ["first_step"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=3600, total_seconds=0, longest_run=0, tasks_done=0)) == ["hour_day"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=10800, total_seconds=0, longest_run=0, tasks_done=0)) == ["hour_day", "big_day"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=36000, longest_run=0, tasks_done=0)) == ["ten_hours"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=0, tasks_done=1)) == ["task_done"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=1, tasks_done=0)) == ["goal_done"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=3, tasks_done=0)) == ["goal_done", "three_days"]


def test_earned_ids_does_not_win_a_badge_one_below_its_target():
    assert "ten_blocks" not in earned_ids(Progress(blocks=9, best_day_seconds=0, total_seconds=0, longest_run=0, tasks_done=0))
    assert "hour_day" not in earned_ids(Progress(blocks=0, best_day_seconds=3599, total_seconds=0, longest_run=0, tasks_done=0))
    assert "big_day" not in earned_ids(Progress(blocks=0, best_day_seconds=10799, total_seconds=0, longest_run=0, tasks_done=0))
    assert "ten_hours" not in earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=35999, longest_run=0, tasks_done=0))
    assert "three_days" not in earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=2, tasks_done=0))
    assert "seven_days" not in earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=6, tasks_done=0))


def test_earned_ids_come_back_in_badge_order():
    rich = Progress(blocks=10, best_day_seconds=10800, total_seconds=36000, longest_run=7, tasks_done=1)
    assert earned_ids(rich) == [badge.id for badge in BADGES]


# --- saved_badges -------------------------------------------------------------- #

def test_saved_badges_returns_a_good_list_as_it_is():
    assert saved_badges(["first_step", "ten_blocks"]) == ["first_step", "ten_blocks"]


def test_saved_badges_gives_an_empty_list_for_the_wrong_kind_of_value():
    for bad in (None, 5, "first_step", {"first_step": True}, True, False):
        assert saved_badges(bad) == [], bad


def test_saved_badges_drops_entries_that_are_not_text():
    assert saved_badges(["first_step", 5, None, "ten_blocks"]) == ["first_step", "ten_blocks"]


def test_saved_badges_drops_repeats_keeping_the_first():
    assert saved_badges(["first_step", "ten_blocks", "first_step"]) == ["first_step", "ten_blocks"]


def test_saved_badges_keeps_names_it_does_not_recognize():
    assert saved_badges(["first_step", "made_up_badge"]) == ["first_step", "made_up_badge"]


# --- newly_won ----------------------------------------------------------------- #

def test_newly_won_is_empty_when_nothing_is_new():
    assert newly_won(["first_step"], ["first_step"]) == []


def test_newly_won_finds_the_new_ones():
    assert newly_won(["first_step", "ten_blocks"], ["first_step"]) == ["ten_blocks"]


def test_newly_won_when_everything_is_new():
    assert newly_won(["first_step", "ten_blocks"], []) == ["first_step", "ten_blocks"]


def test_newly_won_keeps_badge_order():
    assert newly_won(["ten_blocks", "first_step"], []) == ["ten_blocks", "first_step"]


# --- badge_sentence -------------------------------------------------------------- #

def test_badge_sentence_for_exactly_one_new_badge():
    assert badge_sentence(3, 9, ["Big Day"]) == "New! You won Big Day!"


def test_badge_sentence_for_more_than_one_new_badge():
    assert badge_sentence(4, 9, ["Big Day", "Task Done"]) == "New! You won 2 badges!"


def test_badge_sentence_with_none_won_and_nothing_new():
    assert badge_sentence(0, 9, []) == "Do a focus block to win your first badge."


def test_badge_sentence_with_everything_won_and_nothing_new():
    assert badge_sentence(9, 9, []) == "You got them all! Wow!"


def test_badge_sentence_with_some_won_and_nothing_new():
    assert badge_sentence(3, 9, []) == "You have 3 of 9. Keep going!"


def test_badge_sentence_new_beats_having_everything():
    assert badge_sentence(9, 9, ["Seven in a Row"]) == "New! You won Seven in a Row!"


def test_no_badge_sentence_is_ever_harsh():
    sentences = [badge_sentence(have, 9, []) for have in range(0, 10)]
    sentences += [badge_sentence(1, 9, ["X"]), badge_sentence(2, 9, ["X", "Y"])]
    for sentence in sentences:
        for word in HARSH_WORDS:
            assert word not in sentence.lower(), sentence
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_gotchard.py -v`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'lock_in.tier5.gotchard'`.

- [ ] **Step 3: Write the minimal implementation**

Create `lock_in/tier5/gotchard.py`:

```python
"""
tier5/gotchard.py
==================
Kamen Rider Gotchard's Tier 5 gimmick: a "Badges" tab. Nine collectible
badges reward real progress -- blocks done, a big day, total hours, a
checked-off task, and streaks of days that reached the daily goal
Geats' "Goal" tab controls. The eighth of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-21-tier5-gotchard-badges-design.md.

Once a badge is won it is saved to Config.badges_earned and never taken
away by this module, even if the history changes or the goal is edited
later -- see build() below.

Everything except build() is plain logic, tested with no Tk and no
display server. build() is the only Tk-dependent piece; it's checked in
the running app instead, matching every other tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Badge:
    """One badge's fixed description. `metric` names which number in a
    Progress it looks at; `target` is the smallest value that wins it."""

    id: str
    name: str
    hint: str
    metric: str
    target: int


# The nine badges, in the fixed order they're shown and checked. Adding a
# badge later is one new row here -- nothing else needs to change shape.
BADGES: list[Badge] = [
    Badge("first_step", "First Step", "Do your first focus block.", "blocks", 1),
    Badge("ten_blocks", "Ten Blocks", "Do 10 focus blocks.", "blocks", 10),
    Badge("hour_day", "One Hour Day", "Focus for 1 hour in one day.", "best_day_seconds", 3600),
    Badge("big_day", "Big Day", "Focus for 3 hours in one day.", "best_day_seconds", 10800),
    Badge("ten_hours", "Ten Hours", "Focus for 10 hours in all.", "total_seconds", 36000),
    Badge("task_done", "Task Done", "Check off a task.", "tasks_done", 1),
    Badge("goal_done", "Goal Done", "Reach your daily goal once.", "longest_run", 1),
    Badge("three_days", "Three in a Row", "Reach your daily goal 3 days in a row.", "longest_run", 3),
    Badge("seven_days", "Seven in a Row", "Reach your daily goal 7 days in a row.", "longest_run", 7),
]


@dataclass(frozen=True)
class Progress:
    """The five numbers the badges look at."""

    blocks: int
    best_day_seconds: int
    total_seconds: int
    longest_run: int
    tasks_done: int


def longest_goal_run(totals: dict[str, int], goal_seconds: int) -> int:
    """The longest stretch of days in a row that each reached the goal,
    found anywhere in the history -- not just a streak ending today.
    0 for empty `totals`. Works from the calendar dates of the days that
    reached the goal, so a run across a month or year boundary counts
    right, and a long history is sorted once instead of walked one day
    at a time, so it never loops forever."""
    goal_days = sorted(
        date.fromisoformat(day) for day, seconds in totals.items()
        if seconds >= goal_seconds
    )
    if not goal_days:
        return 0
    longest = current = 1
    for previous, day in zip(goal_days, goal_days[1:]):
        current = current + 1 if day == previous + timedelta(days=1) else 1
        longest = max(longest, current)
    return longest


def progress(totals: dict[str, int], block_count: int, goal_seconds: int, tasks_done: int) -> Progress:
    """Turn the raw history into the five numbers the badges compare
    against their targets. `totals` is history.total_seconds_by_day()
    and `block_count` is len(history.all())."""
    return Progress(
        blocks=block_count,
        best_day_seconds=max(totals.values(), default=0),
        total_seconds=sum(totals.values()),
        longest_run=longest_goal_run(totals, goal_seconds),
        tasks_done=tasks_done,
    )


def earned_ids(p: Progress) -> list[str]:
    """The ids of every badge `p` has won, in badge order."""
    values = {
        "blocks": p.blocks,
        "best_day_seconds": p.best_day_seconds,
        "total_seconds": p.total_seconds,
        "tasks_done": p.tasks_done,
        "longest_run": p.longest_run,
    }
    return [badge.id for badge in BADGES if values[badge.metric] >= badge.target]


def saved_badges(raw) -> list[str]:
    """The safe reader for Config.badges_earned. A hand-edited
    config.json could hold anything, so this never raises: anything that
    isn't a list becomes an empty list. Entries that aren't text are
    dropped, and repeats are dropped, keeping the first. Names this app
    doesn't recognize are KEPT as-is (so a list saved by a newer app is
    never shortened here), but the tab never counts or shows them."""
    if not isinstance(raw, list):
        return []
    kept: list[str] = []
    for item in raw:
        if isinstance(item, str) and item not in kept:
            kept.append(item)
    return kept


def newly_won(earned: list[str], saved: list[str]) -> list[str]:
    """The ids in `earned` that aren't in `saved` yet, in badge order --
    what build() needs to add to Config.badges_earned this time."""
    return [badge_id for badge_id in earned if badge_id not in saved]


def badge_sentence(have: int, total: int, new_names: list[str]) -> str:
    """One short, kind sentence about the collection. A badge just won
    this build always gets its own sentence, even on the build where you
    also complete the whole set."""
    if len(new_names) == 1:
        return f"New! You won {new_names[0]}!"
    if len(new_names) > 1:
        return f"New! You won {len(new_names)} badges!"
    if have == 0:
        return "Do a focus block to win your first badge."
    if have == total:
        return "You got them all! Wow!"
    return f"You have {have} of {total}. Keep going!"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_gotchard.py -v`
Expected: all PASS.

- [ ] **Step 5: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 3: The "Badges" tab, plus the wiring

**Files:**
- Modify: `lock_in/tier5/gotchard.py` (add `build()`)
- Modify: `lock_in/tier5/__init__.py`
- Modify: `lock_in/rider_themes.py` (the `Kamen Rider Gotchard (2023)` entry, and one comment)
- Modify: `lock_in/ui.py` (`_TIER5_TAB_LABELS`)
- Modify: `tests/test_tier5_gotchard.py` (wiring tests)
- Modify: `tests/test_rider_themes.py`

**Interfaces:**
- Consumes: `BADGES`, `Progress`, `progress()`, `earned_ids()`, `saved_badges()`, `newly_won()`, `badge_sentence()` (Task 2); `Config.badges_earned`, `Config.effective_daily_goal_minutes()`, `Config.save()` (Task 1 and Geats' existing `effective_daily_goal_minutes()`); `history.total_seconds_by_day()`, `history.all()`; `tasks.done()`; `format_hm()` from `lock_in/tier5/_shared.py`; `visuals.display_font_family()`; the theme's `secondary`, `primary_text_pair`, `button_text_pair`.
- Produces: `build(parent, *, history, tasks, theme, appearance_mode, config) -> None`, registered as `TIER5_BUILDERS["badge_cards"]`; the tab label `"Badges"`.

Every one of the other seven Tier 5 builders already accepts `config=` (Geats' plan added that), so this task needs no change to `v3.py`, `den_o.py`, `decade.py`, `zi_o.py`, `blade.py`, or `w.py`, and `ui.py`'s `_build_tier5_tab()` already passes `config=self.config_obj` to every builder.

- [ ] **Step 1: Write the failing wiring tests**

Append to `tests/test_tier5_gotchard.py`, with two blank lines before them:

```python
# --- wiring --------------------------------------------------------------- #

def test_badge_cards_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, gotchard
    assert TIER5_BUILDERS["badge_cards"] is gotchard.build


def test_badge_cards_has_the_badges_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["badge_cards"] == "Badges"


def test_gotchard_builder_accepts_config():
    """ui.py passes config= to every builder, same check Geats' plan
    added for the other seven -- this pins Gotchard to the same rule."""
    import inspect
    from lock_in.tier5 import gotchard
    assert "config" in inspect.signature(gotchard.build).parameters
```

In `tests/test_rider_themes.py`, the completeness check grows from seven Riders to eight. Two edits:

In `tests/test_rider_themes.py`, replace:

```python
def test_exactly_these_seven_riders_have_a_tier5_effect():
```

with:

```python
def test_exactly_these_eight_riders_have_a_tier5_effect():
```

In `tests/test_rider_themes.py`, replace:

```python
        "Kamen Rider Geats (2022)": "goal_streak",
    }
```

with:

```python
        "Kamen Rider Geats (2022)": "goal_streak",
        "Kamen Rider Gotchard (2023)": "badge_cards",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_gotchard.py tests/test_rider_themes.py -v`
Expected: 4 FAIL (the registry check, the tab-label check, the builder-signature check, and the eight-Riders check). Everything else PASSES.

- [ ] **Step 3: Add `build()` to `gotchard.py`**

First, in `lock_in/tier5/gotchard.py`, replace the import block at the top with this one. It adds the CustomTkinter import, the `visuals` import, `format_hm` from `_shared`, and the small color constants the cards use:

Replace:

```python
from dataclasses import dataclass
from datetime import date, timedelta
```

with:

```python
from dataclasses import dataclass
from datetime import date, timedelta

import customtkinter as ctk

from .. import visuals
from ._shared import format_hm

# What a not-yet-won card and its text look like -- CustomTkinter's own
# grays, picked for light and dark mode.
_EMPTY_CARD = ("gray80", "gray30")
_EMPTY_NAME = ("gray20", "gray80")
_EMPTY_BODY = ("gray30", "gray70")
```

Then add this to the very end of the file, with two blank lines before it:

```python
def build(parent, *, history, tasks, theme, appearance_mode, config) -> None:
    """
    Populate `parent` with Gotchard's Badges view: how many of the 9
    badges are won, one sentence about the collection, and a 3-by-3 grid
    of cards.

    Every widget is built once -- there are no buttons on this tab, so
    nothing is ever destroyed and rebuilt from inside a click.

    `tasks` is used for tasks.done() (the Task Done badge). `appearance_
    mode` is part of every Tier 5 builder's signature for consistency --
    Gotchard doesn't need it, since CustomTkinter's own (light, dark)
    color pairs already handle light and dark switching.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    totals = history.total_seconds_by_day()
    goal_seconds = config.effective_daily_goal_minutes() * 60
    current = progress(totals, len(history.all()), goal_seconds, len(tasks.done()))
    earned = earned_ids(current)

    saved = saved_badges(config.badges_earned)
    new_ids = newly_won(earned, saved)
    if new_ids:
        config.badges_earned = saved + new_ids
        try:
            config.save()
        except OSError:
            # For example, the file is locked. The new badges still show
            # for the rest of this session, and the next build tries the
            # save again.
            pass

    won = set(saved) | set(new_ids)
    have = sum(1 for badge in BADGES if badge.id in won)
    new_names = [badge.name for badge in BADGES if badge.id in new_ids]

    text_color = theme.primary_text_pair
    big_font = ctk.CTkFont(family=visuals.display_font_family(), size=20, weight="bold")

    # --- the count line ----------------------------------------------- #
    header = ctk.CTkFrame(frame, fg_color="transparent")
    header.pack(fill="x", pady=(4, 0))
    ctk.CTkLabel(header, text="Badges", text_color=text_color, anchor="w").pack(
        side="left", fill="x", expand=True)
    ctk.CTkLabel(
        header, text=f"{have} of {len(BADGES)}", text_color=text_color,
        anchor="e", font=big_font,
    ).pack(side="right")

    ctk.CTkLabel(
        frame, text=badge_sentence(have, len(BADGES), new_names),
        justify="left", wraplength=400, anchor="w",
    ).pack(anchor="w", pady=(6, 12))

    # --- the 3-by-3 grid ------------------------------------------------ #
    grid = ctk.CTkFrame(frame, fg_color="transparent")
    grid.pack(fill="x")
    for column in range(3):
        grid.grid_columnconfigure(column, weight=1, uniform="badge")

    won_text_color = theme.button_text_pair
    for index, badge in enumerate(BADGES):
        row, column = divmod(index, 3)
        is_won = badge.id in won
        card = ctk.CTkFrame(
            grid, corner_radius=8,
            fg_color=theme.secondary if is_won else _EMPTY_CARD,
        )
        card.grid(row=row, column=column, padx=4, pady=4, sticky="nsew")
        name_color = won_text_color if is_won else _EMPTY_NAME
        body_color = won_text_color if is_won else _EMPTY_BODY
        ctk.CTkLabel(
            card, text=badge.name, text_color=name_color,
            font=ctk.CTkFont(weight="bold"), wraplength=120, justify="left",
        ).pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(
            card, text=badge.hint, text_color=body_color,
            font=ctk.CTkFont(size=11), wraplength=120, justify="left",
        ).pack(anchor="w", padx=10)
        ctk.CTkLabel(
            card, text="Got it!" if is_won else "Not yet", text_color=body_color,
            font=ctk.CTkFont(size=11, weight="bold"), wraplength=120, justify="left",
        ).pack(anchor="w", padx=10, pady=(2, 10))

    # --- captions --------------------------------------------------------- #
    ctk.CTkLabel(
        frame, text="Every focus block counts, finished or not · a badge is yours to keep",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(10, 0))
    ctk.CTkLabel(
        frame,
        text=f"Goal badges use your daily goal of {format_hm(goal_seconds)}. Pick Geats to change it.",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
        justify="left", wraplength=400,
    ).pack(anchor="w")
```

- [ ] **Step 4: Register the builder**

In `lock_in/tier5/__init__.py`, replace:

```python
from . import blade, decade, den_o, geats, v3, w, zi_o
```

with:

```python
from . import blade, decade, den_o, geats, gotchard, v3, w, zi_o
```

In `lock_in/tier5/__init__.py`, replace:

```python
    "goal_streak": geats.build,
}
```

with:

```python
    "goal_streak": geats.build,
    "badge_cards": gotchard.build,
}
```

And the same file's top comment gets `Gotchard` added next to `Geats`:

In `lock_in/tier5/__init__.py`, replace:

```python
Every builder also accepts `config` (the app's settings). Only Geats uses
it, to read and save the daily goal; the others ignore it.
```

with:

```python
Every builder also accepts `config` (the app's settings). Geats uses it
to read and save the daily goal, and Gotchard uses it to read the goal
and to read and save the badge list; the others ignore it.
```

- [ ] **Step 5: Give Gotchard its effect**

In `lock_in/rider_themes.py`, replace:

```python
    "Kamen Rider Gotchard (2023)": RiderTheme(
        "Reiwa", 2023, ("#008394", "#4dd0e1"), ("#b33f00", "#ffb74d"),
    ),
```

with:

```python
    "Kamen Rider Gotchard (2023)": RiderTheme(
        "Reiwa", 2023, ("#008394", "#4dd0e1"), ("#b33f00", "#ffb74d"),
        tier5_effect="badge_cards",
    ),
```

And the comment above `tier5_effect` in the same file lists the Riders "so far". Update it:

In `lock_in/rider_themes.py`, replace:

```python
    # history (V3, Den-O, Decade, Zi-O, Blade, W and Geats so far, out of 10
```

with:

```python
    # history (V3, Den-O, Decade, Zi-O, Blade, W, Geats and Gotchard so
    # far, out of 10
```

- [ ] **Step 6: Give the tab its name**

In `lock_in/ui.py`, replace:

```python
    "history_editor": "History", "kanban_board": "Board", "week_compare": "Week",
    "goal_streak": "Goal",
}
```

with:

```python
    "history_editor": "History", "kanban_board": "Board", "week_compare": "Week",
    "goal_streak": "Goal", "badge_cards": "Badges",
}
```

Nothing else in `ui.py` changes for the tab itself: building it, refreshing it after a finished block, and hiding it for Standard Mode all already work for any registered effect, and `_build_tier5_tab()` already passes `config=self.config_obj`.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_gotchard.py tests/test_rider_themes.py -v`
Expected: all PASS.

- [ ] **Step 8: Drive the real tab in the real app**

Save the script below as `gotchard_drive.py` in any scratch folder OUTSIDE the project (for example your temp folder). It points the app at a throwaway data folder, so your real settings and history are not touched. It seeds fake history and a fake task, then reads the real tab:

- 12 blocks total: today 20 minutes, then 11 more blocks on the 6 days before that, with 2 of those days reaching 1 hour (a 2-day run) and one earlier day alone at 3 hours 30 minutes
- one task checked off
- at the starting goal of 1 hour, this wins: First Step, Ten Blocks, One Hour Day, Big Day, Task Done, Goal Done -- **6 of 9**

```python
"""Drives the real Lock In window with fake history and a fake task, and
reads the real Badges tab. Run from the PROJECT folder so `lock_in` can
be imported:

  Git Bash:    PYTHONPATH=. python /path/to/gotchard_drive.py
  PowerShell:  $env:PYTHONPATH="."; python C:\\path\\to\\gotchard_drive.py

Optional switches (environment variables):
  EMPTY=1                          fresh install, no history, no tasks
  RIDER="Kamen Rider (1971)"       a Rider other than Gotchard (the Badges tab must be absent)
  SHOT=C:\\some\\folder\\badges    also saves badges-dark.png and badges-light.png
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
from lock_in.tasks import TaskStore

GOTCHARD = "Kamen Rider Gotchard (2023)"
RIDER = os.environ.get("RIDER", GOTCHARD)
EMPTY = bool(os.environ.get("EMPTY"))
SHOT = os.environ.get("SHOT")
CAPTION = "Every focus block counts, finished or not · a badge is yours to keep"
GOAL_NOTE = "Goal badges use your daily goal of 1h 0m. Pick Geats to change it."

config = Config()
config.rider_theme = RIDER
config.save()

# (days ago, minutes) for 12 blocks in all. Day 1 and day 2 each reach
# a full hour (a 2-day run); day 5 alone is 3h 30m (Big Day, One Hour
# Day); today is only 20 minutes (not part of any run).
BLOCKS = [
    (0, 20),
    (1, 40), (1, 20),
    (2, 45), (2, 15),
    (3, 25),
    (4, 30),
    (5, 200),
    (5, 10),
    (6, 10),
    (6, 15),
    (6, 20),
]


def make_record(days_ago, minutes):
    start = (datetime.now() - timedelta(days=days_ago)).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=minutes)
    return SessionRecord(start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds"),
                         minutes * 60, None, True)


if not EMPTY:
    lines = [json.dumps(dataclasses.asdict(make_record(d, m))) for d, m in BLOCKS]
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    from lock_in.config import app_data_dir
    seed_tasks = TaskStore(app_data_dir() / "tasks.json")
    seed_task = seed_tasks.add("Read a chapter")
    seed_tasks.complete(seed_task.id)

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

app = LockInApp()
app.update()
has_tab = "Badges" in app.tabs._tab_dict

if RIDER != GOTCHARD:
    check("no Badges tab for a Rider that isn't Gotchard", not has_tab)
else:
    check("Badges tab exists for Gotchard", has_tab)
    app.tabs.set("Badges")
    app.update()
    tab = app.tabs.tab("Badges")
    texts = label_texts(tab)

    if EMPTY:
        print("fresh install:")
        for expected in ["Badges", "0 of 9", "Do a focus block to win your first badge.",
                          "First Step", "Not yet", "Seven in a Row", CAPTION, GOAL_NOTE]:
            check(f"shows {expected!r}", expected in texts)
    else:
        print("with history and one done task:")
        for expected in [
            "Badges", "6 of 9", "First Step", "Ten Blocks", "One Hour Day", "Big Day",
            "Task Done", "Goal Done", "Got it!", "Three in a Row", "Not yet", CAPTION, GOAL_NOTE,
        ]:
            check(f"shows {expected!r}", expected in texts)
        check("sentence names a new badge or gives the count",
              any(t.startswith("New!") or t == "You have 6 of 9. Keep going!" for t in texts))
        check("goal saved is still the default 1h 0m", Config.load().effective_daily_goal_minutes() == 60)
        check("badges were saved", set(Config.load().badges_earned) >= {
            "first_step", "ten_blocks", "hour_day", "big_day", "task_done", "goal_done",
        })

        if SHOT:
            app.geometry("620x1000+40+0")
            app.attributes("-topmost", True)
            for mode in ("dark", "light"):
                app._on_appearance_change(mode)
                app.tabs.set("Badges")
                app.lift(); app.update(); time.sleep(0.6); app.update()
                x, y = app.winfo_rootx(), app.winfo_rooty()
                from PIL import ImageGrab
                ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(f"{SHOT}-{mode}.png")
                print("  saved", f"{SHOT}-{mode}.png")

        print("re-opening the app keeps the badges (no new badges this time):")
        app.destroy()
        app = LockInApp()
        app.update()
        app.tabs.set("Badges")
        app.update()
        tab = app.tabs.tab("Badges")
        texts = label_texts(tab)
        check("still 6 of 9", "6 of 9" in texts)
        check("sentence is the plain 'keep going' one now, not 'New!'",
              "You have 6 of 9. Keep going!" in texts)

app.destroy()
print("\nFAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
```

Run it three ways, from the project folder:
1. With history: every line prints PASS and `FAILURES: none`.
2. `EMPTY=1`: the fresh-install lines pass.
3. `RIDER="Kamen Rider (1971)"`: the "no Badges tab" line passes.

Then run it once more with `SHOT` set and open the two PNGs. Expected in both light and dark: "Badges" with `6 of 9` on the right, a sentence about the new badge or the count, and a 3x3 grid where First Step, Ten Blocks, One Hour Day, Big Day, Task Done, and Goal Done are filled orange and read "Got it!", and Three in a Row, Seven in a Row, and Ten Hours are gray with their hint and "Not yet". If the tab area is too short to show everything, scroll the tab and look again; if the window is taller than your screen, lower the `620x1000` value.

- [ ] **Step 9: Confirm nothing else broke**

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
- Produces: version `2.5.8`; the Gotchard bullet in the Help tab and README; the "eight" wording; two known-limit lines.

- [ ] **Step 1: Bump the version**

In `lock_in/__init__.py`, replace:

```python
__version__ = "2.5.7"
```

with:

```python
__version__ = "2.5.8"
```

- [ ] **Step 2: Help tab**

In `lock_in/ui.py`, in the Tier 5 section of the Help tab (right after the Geats bullet):

In `lock_in/ui.py`, replace:

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

with:

```python
        bullet(
            "Geats — a \"Goal\" tab appears. Pick how many minutes you "
            "want to focus each day with the minus and plus buttons. A "
            "bar fills up as you focus, and a streak counts the days in "
            "a row you reached your goal. Every block counts, finished "
            "or not."
        )
        bullet(
            "Gotchard — a \"Badges\" tab appears: 9 cards to collect, "
            "for things like your first focus block, a 3-hour day, or a "
            "7-day streak of reaching your daily goal. A badge you win "
            "is yours to keep."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "eight are just the first."
        )
```

- [ ] **Step 3: README, the Gotchard bullet and the count**

In `README.md`, in the "Tier 5" section, directly after the Geats bullet (which ends "...Every block counts, finished or not."):

In `README.md`, replace:

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

with:

```
- **Geats** — adds a "Goal" tab. You pick how many minutes you want to
  focus each day with a minus and a plus button (each press is 15
  minutes, and the app remembers your pick). A bar fills up as you
  focus, and a streak counts how many days in a row you reached your
  goal. Seven little boxes show the last 7 days, filled in for the days
  you made it. Every block counts, finished or not.
- **Gotchard** — adds a "Badges" tab: 9 cards to collect, for things
  like your first focus block, doing 10 blocks, a 1-hour day, a 3-hour
  day, 10 hours in all, checking off a task, and reaching your daily
  goal once, 3 days in a row, or 7 days in a row. A card you haven't
  won yet shows a gray hint so you know what to aim for; once you win a
  badge, it's yours to keep.

More Riders will read your tasks and history this way over time — these
eight are just the first of ten planned.
```

Keep one blank line between the Gotchard bullet and the "More Riders..." paragraph.

- [ ] **Step 4: README, two known limits**

In the "Known limits" list, directly before the line starting `- **Auto-update only replaces the downloaded app**`:

In `README.md`, replace:

```
- **Geats judges every day by the goal you have now** — there is one
  goal number, not a different one for each day. Making the goal bigger
  can make your streak shorter, and making it smaller can make it longer.
- **Auto-update only replaces the downloaded app**
```

with:

```
- **Geats judges every day by the goal you have now** — there is one
  goal number, not a different one for each day. Making the goal bigger
  can make your streak shorter, and making it smaller can make it longer.
- **Gotchard's badges are yours to keep, forever** — even if you delete a
  focus block in Zi-O or change your goal on Geats' tab afterward. That
  also means a very small daily goal makes the streak badges quick to
  win, on purpose — the goal is yours to set however you like.
- **Only Geats can change the daily goal** — Gotchard's Badges tab has no
  goal buttons of its own; it just reads whatever goal is set.
- **Auto-update only replaces the downloaded app**
```

- [ ] **Step 5: Run everything**

Run: `python -m pytest`
Expected: 0 failed, 1 skipped (the same skip as before).

Run the existing real-window smoke test in a throwaway data folder. Git Bash: `APPDATA="$(mktemp -d)" PYTHONPATH=. python tests/smoke_ui.py`. PowerShell: `$env:APPDATA=(New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([guid]::NewGuid()))).FullName; $env:PYTHONPATH="."; python tests/smoke_ui.py`.
Expected: ends with `smoke test passed`.

Re-run `gotchard_drive.py` (Task 3, Step 8) with history. Expected: `FAILURES: none`. Then open the real app once with a Rider that is **not** Gotchard and open Help: it should now say v2.5.8.

- [ ] **Step 6: Repo hygiene checks**

Run: `git status --short`
Expected: exactly these paths, and nothing else (in particular nothing generated):
`README.md`, `lock_in/__init__.py`, `lock_in/config.py`, `lock_in/rider_themes.py`, `lock_in/tier5/__init__.py`, `lock_in/tier5/gotchard.py` (new), `lock_in/ui.py`, `tests/test_config.py`, `tests/test_rider_themes.py`, `tests/test_tier5_gotchard.py` (new), plus the spec and this plan under `docs/superpowers/`.
If anything else shows up (a picture, a data file, a folder), add a matching line to `.gitignore`. If nothing does, `.gitignore` needs no change. Gotchard makes no new file, because its badge list is saved inside the existing `config.json`, which is already ignored, so none is expected.

Now check that the changes describe the software only. This looks at the lines you added and at the two new files, and prints any line that names a helper tool or a co-writer, or that has a credit line. The square brackets are on purpose: they stop the check from matching its own words.

```bash
git diff -U0 | grep '^+' | grep -inE "cl[a]ude|anthrop[i]c|co-[a]uthor|generated [w]ith|[a]ssistant|sub[a]gent|[a]gentic" ; grep -inE "cl[a]ude|anthrop[i]c|co-[a]uthor|generated [w]ith|[a]ssistant|sub[a]gent|[a]gentic" lock_in/tier5/gotchard.py tests/test_tier5_gotchard.py docs/superpowers/specs/2026-09-21-tier5-gotchard-badges-design.md docs/superpowers/plans/2026-09-21-tier5-gotchard-badges.md
```

Expected: nothing printed.

---

## Handoff: git steps for the project owner

Nothing above runs any of these. Run them yourself once you have looked at the result. The commit message is plain, with **one** `-m` and no extra lines under it, so no trailer or credit line can end up in it.

```bash
git status
git add -A
git commit -m "v2.5.8: add Gotchard (Tier 5 Rider 8), the collectible badges"
git log -1 --format=%B
git shortlog -sne
git push origin main
git tag v2.5.8
git push origin v2.5.8
```

Two safety looks after the commit and before the pushes:
- `git log -1 --format=%B` should print only the one-line message above, and nothing under it.
- `git shortlog -sne` should list only you, with your own name and email, and nobody else. Anyone listed there would show up as a contributor on GitHub.

Pushing the tag starts the release build (`.github/workflows/release.yml`), so push it last, after you are happy with the result. Git may print harmless "LF will be replaced by CRLF" warnings.

## Spec coverage check

| Spec section | Where it's covered |
|---|---|
| The nine badges, their hints and targets | Task 2 (`BADGES` + its tests) |
| Badges kept forever, checked on every tab build | Task 3, Step 3 (`build()`); Step 8's "re-opening the app keeps the badges" check |
| Longest run anywhere in history, not just today's streak | Task 2 (`longest_goal_run` + its tests, including month/year boundaries and a long history) |
| The tab (count, sentence, 3x3 grid, caption, goal note, no early exit) | Task 3, Step 3 (`build()`) and Step 8 (checked in the real app, with and without history) |
| Colors | Task 3, Step 3, and the screenshots in Step 8 |
| The words on screen | Task 2 (`badge_sentence` + tests for each row, and "never harsh" for both badge text and sentences) |
| `badges_earned`, the safe `saved_badges()` reader | Task 1 (the field), Task 2 (`saved_badges` + its tests) |
| Wiring (registry, theme, tab label, theme comment) | Task 3, Steps 4 to 6, with wiring tests in Steps 1 and 7 |
| Error handling (bad saved list, empty history, save failure, deleted blocks/tasks don't un-win a badge) | Task 1 (bad values via `saved_badges`), Task 2 (empty totals/progress), Task 3 (`build()`'s save handling; Step 8's re-open check) |
| Testing list | Tasks 1 to 3; manual checks in Task 3 Step 8 and Task 4 Step 5 |
| Docs, version, repo hygiene | Task 4 and the Handoff section |
| Out of scope (badge dates, sounds/animations, secret badges, goal-per-badge, un-winning, badges on other tabs) | Nothing in this plan builds any of it |
