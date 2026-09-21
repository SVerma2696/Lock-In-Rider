# Tier 5 Rider #6 (W, the week-vs-week chart) Implementation Plan

Spec: `docs/superpowers/specs/2026-09-21-tier5-w-week-compare-design.md`.
Work through the tasks in order and tick each box as you go. Steps use
checkbox (`- [ ]`) syntax.

**Goal:** When Kamen Rider W (2009) is the picked Rider, a "Week" tab
shows the last 7 days against the 7 days before them: two totals, one
plain sentence, and a paired bar chart.

**Architecture:** A new `lock_in/tier5/w.py` holds two small pure
functions (`week_pairs`, `compare_sentence`) plus the one Tk-dependent
`build()`. One new drawing function, `make_week_compare_chart`, is added
to `lock_in/visuals.py` next to `make_hours_chart` (which is not
changed). The tab plugs into the existing `TIER5_BUILDERS` registry and
`_TIER5_TAB_LABELS`, the same way V3, Den-O, Decade, Zi-O, and Blade did.

**Tech Stack:** Python 3, CustomTkinter, Pillow, pytest. No new
dependency.

## Global Constraints

Copied from the spec. Every task below includes these.

- **Tab label:** `"Week"`. **Effect name:** `"week_compare"`. **Rider:** `Kamen Rider W (2009)`.
- **Week rule:** this week = today and the 6 days before it; last week = the 7 days right before those. Each this-week day pairs with the same day 7 days earlier. Today is the rightmost group. Not Monday-to-Sunday.
- **Every focus block counts**, whether finished, skipped, or reset early (same rule as V3 and Decade).
- **Chart size:** 440×200. Last week's bar on the left in each pair, this week's on the right. Both weeks share one height scale.
- **Colors:** this week = `theme.primary`; last week = `theme.secondary`. Total-line text uses `theme.primary_text_pair` and `theme.secondary_text_pair`, so the lines double as the legend.
- **Sentences (exact text):**
  - more: `You did {diff} MORE than last week. Yay!`
  - less: `That's {diff} less than last week. You can do it!`
  - within a minute: `Same as last week. Nice and steady!`
  - both zero: `No focus blocks in the last 14 days. Start one and it shows up here.`
  - empty history: `No focus blocks yet. Finish one and it shows up here.`
  - caption: `Last 7 days vs the 7 days before · every focus block counts, finished or not`
- `{diff}` is written with the shared `format_hm()`. A gap under 60 seconds counts as "same". The "less" sentence never says "behind", "worse", or "fail".
- **`make_hours_chart()` is not modified.** V3's and Decade's charts stay byte-for-byte the same.
- **No new config field, no new file on disk, no write path.**
- **Words a young child can follow** in every visible string, the README, and the Help tab.
- **Version:** `2.5.5` to `2.5.6`.
- **No commit, push, or tag is run while doing this plan.** The commands are in the Handoff section at the end, for the project owner to run.
- **Project files describe the software only** -- nothing about who or what wrote it, in any file added or edited.
- **Line endings:** edit existing files in place and keep their current line-ending style. New files may use LF (Git converts on commit).

## File Structure

| File | What it's for |
|---|---|
| `lock_in/tier5/w.py` *(new)* | `week_pairs()`, `compare_sentence()`, `build()` |
| `lock_in/visuals.py` *(edit)* | `make_week_compare_chart()`, added right after `make_hours_chart()` |
| `lock_in/tier5/__init__.py` *(edit)* | Register `"week_compare": w.build` |
| `lock_in/rider_themes.py` *(edit)* | `tier5_effect="week_compare"` on W |
| `lock_in/ui.py` *(edit)* | `_TIER5_TAB_LABELS` entry; Help tab bullet and wording |
| `lock_in/__init__.py` *(edit)* | Version 2.5.6 |
| `README.md` *(edit)* | W bullet, "six of ten" wording, one known-limit line |
| `tests/test_tier5_w.py` *(new)* | Pairing, sentence, and wiring tests |
| `tests/test_visuals.py` *(edit)* | Chart tests |
| `tests/test_rider_themes.py` *(edit)* | The tier5 completeness check grows to six |

---

### Task 1: W's two pure functions (`week_pairs`, `compare_sentence`)

**Files:**
- Create: `lock_in/tier5/w.py`
- Create: `tests/test_tier5_w.py`

**Interfaces:**
- Consumes: `last_n_days(totals: dict[str, int], today: date, n: int) -> list[tuple[date, int]]` and `format_hm(seconds: int) -> str`, both from `lock_in/tier5/_shared.py`.
- Produces:
  - `week_pairs(totals: dict[str, int], today: date) -> list[tuple[date, int, int]]`: exactly 7 tuples `(this_week_day, last_week_seconds, this_week_seconds)`, oldest to newest.
  - `compare_sentence(this_seconds: int, last_seconds: int) -> str`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tier5_w.py`:

```python
from datetime import date, timedelta

from lock_in.tier5.w import compare_sentence, week_pairs

TODAY = date(2026, 9, 21)


def _iso(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).isoformat()


# --- week_pairs -------------------------------------------------------- #

def test_week_pairs_always_returns_exactly_seven_entries():
    assert len(week_pairs({}, TODAY)) == 7


def test_week_pairs_are_oldest_to_newest_ending_on_today():
    days = [day for day, _, _ in week_pairs({}, TODAY)]
    assert days[-1] == TODAY
    assert days[0] == TODAY - timedelta(days=6)
    assert days == sorted(days)


def test_week_pairs_with_no_history_are_all_zero():
    assert all(last == 0 and this == 0 for _, last, this in week_pairs({}, TODAY))


def test_week_pairs_a_block_today_lands_in_the_this_week_column():
    assert week_pairs({_iso(0): 600}, TODAY)[-1] == (TODAY, 0, 600)


def test_week_pairs_a_block_seven_days_ago_lands_in_the_last_week_column():
    assert week_pairs({_iso(7): 900}, TODAY)[-1] == (TODAY, 900, 0)


def test_week_pairs_each_day_pairs_with_the_same_day_a_week_earlier():
    totals = {_iso(3): 100, _iso(10): 200}
    day, last, this = week_pairs(totals, TODAY)[3]
    assert day == TODAY - timedelta(days=3)
    assert (last, this) == (200, 100)


def test_week_pairs_the_oldest_day_counted_is_thirteen_days_back():
    assert week_pairs({_iso(13): 42}, TODAY)[0] == (TODAY - timedelta(days=6), 42, 0)


def test_week_pairs_ignores_blocks_older_than_fourteen_days():
    pairs = week_pairs({_iso(14): 5000, _iso(20): 5000}, TODAY)
    assert all(last == 0 and this == 0 for _, last, this in pairs)


def test_week_pairs_pairs_correctly_across_a_month_boundary():
    today = date(2026, 3, 3)
    pairs = week_pairs({"2026-02-28": 100, "2026-02-21": 300}, today)
    assert pairs[3] == (date(2026, 2, 28), 300, 100)


def test_week_pairs_pairs_correctly_across_a_year_boundary():
    today = date(2027, 1, 2)
    pairs = week_pairs({"2026-12-31": 100, "2026-12-24": 300}, today)
    assert pairs[4] == (date(2026, 12, 31), 300, 100)


# --- compare_sentence -------------------------------------------------- #

def test_compare_sentence_when_this_week_is_more():
    assert compare_sentence(this_seconds=6000, last_seconds=0) == (
        "You did 1h 40m MORE than last week. Yay!"
    )


def test_compare_sentence_when_this_week_is_less():
    assert compare_sentence(this_seconds=3600, last_seconds=5400) == (
        "That's 30m less than last week. You can do it!"
    )


def test_compare_sentence_when_this_week_is_zero_but_last_week_was_not():
    assert compare_sentence(this_seconds=0, last_seconds=16200) == (
        "That's 4h 30m less than last week. You can do it!"
    )


def test_compare_sentence_when_the_weeks_are_equal():
    assert compare_sentence(this_seconds=3600, last_seconds=3600) == (
        "Same as last week. Nice and steady!"
    )


def test_compare_sentence_a_gap_of_59_seconds_counts_as_the_same():
    assert compare_sentence(this_seconds=3659, last_seconds=3600) == (
        "Same as last week. Nice and steady!"
    )
    assert compare_sentence(this_seconds=3600, last_seconds=3659) == (
        "Same as last week. Nice and steady!"
    )


def test_compare_sentence_a_gap_of_exactly_60_seconds_is_more_or_less():
    assert compare_sentence(this_seconds=3660, last_seconds=3600) == (
        "You did 1m MORE than last week. Yay!"
    )
    assert compare_sentence(this_seconds=3600, last_seconds=3660) == (
        "That's 1m less than last week. You can do it!"
    )


def test_compare_sentence_when_both_weeks_are_empty():
    assert compare_sentence(this_seconds=0, last_seconds=0) == (
        "No focus blocks in the last 14 days. Start one and it shows up here."
    )


def test_compare_sentence_is_never_harsh():
    for this_seconds, last_seconds in [(0, 9000), (60, 9000), (100, 5000), (0, 61)]:
        text = compare_sentence(this_seconds, last_seconds).lower()
        for scary_word in ("behind", "worse", "fail"):
            assert scary_word not in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_w.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'lock_in.tier5.w'`.

- [ ] **Step 3: Write the minimal implementation**

Create `lock_in/tier5/w.py`. (`build()` comes in Task 3; the imports for it are added then, so this file only imports what it uses now.)

```python
"""
tier5/w.py
==========
Kamen Rider W's Tier 5 gimmick: a "Week" tab that puts two weeks side by
side -- the last 7 days against the 7 days right before them -- W being
two Riders sharing one body. The sixth of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-21-tier5-w-week-compare-design.md.

`week_pairs()` and `compare_sentence()` are plain logic, tested with no
Tk and no display server. `build()` (added later in this file) is the
only Tk-dependent piece; it's checked in the running app instead,
matching every other tab.
"""

from __future__ import annotations

from datetime import date

from ._shared import format_hm, last_n_days


def week_pairs(totals: dict[str, int], today: date) -> list[tuple[date, int, int]]:
    """Exactly 7 tuples of (day, last_week_seconds, this_week_seconds),
    oldest to newest, where `day` is the THIS-week date. Each this-week day
    is paired with the same day 7 days earlier. Built from the 14-day list
    last_n_days() already makes: its first 7 entries are last week, its
    last 7 are this week, and entry i of one pairs with entry i of the
    other. A day with no focus blocks counts as 0 seconds."""
    days = last_n_days(totals, today, 14)
    last_week, this_week = days[:7], days[7:]
    return [
        (this_day, last_seconds, this_seconds)
        for (_, last_seconds), (this_day, this_seconds) in zip(last_week, this_week)
    ]


def compare_sentence(this_seconds: int, last_seconds: int) -> str:
    """One short, kind sentence about how this week went next to last
    week. A gap under a minute counts as "the same", so it never says
    something like "0m MORE"."""
    if this_seconds == 0 and last_seconds == 0:
        return "No focus blocks in the last 14 days. Start one and it shows up here."
    gap = this_seconds - last_seconds
    if abs(gap) < 60:
        return "Same as last week. Nice and steady!"
    if gap > 0:
        return f"You did {format_hm(gap)} MORE than last week. Yay!"
    return f"That's {format_hm(-gap)} less than last week. You can do it!"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_w.py -v`
Expected: all 18 tests PASS.

- [ ] **Step 5: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed (the passed count is higher than before this task).

---

### Task 2: The paired bar chart (`make_week_compare_chart`)

**Files:**
- Modify: `lock_in/visuals.py` (add one function immediately after `make_hours_chart`, before `load_app_icon`)
- Modify: `tests/test_visuals.py` (add the import, add the tests)

**Interfaces:**
- Consumes: `_hex_to_rgb(color: str) -> tuple[int, int, int]` and `make_panel_divider(width, height, primary, secondary, era=...)`, both already in `visuals.py`; `date` and `Image`/`ImageDraw` are already imported there.
- Produces: `make_week_compare_chart(width: int, height: int, pairs: list[tuple[str, int, int]], this_color: str, last_color: str, dark: bool, era: str = "Showa") -> Image.Image`, where `pairs` is a list of `(iso_day, last_week_seconds, this_week_seconds)`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_visuals.py`, add `make_week_compare_chart` to the import block at the top, keeping the names alphabetical-ish as they are now:

```python
from lock_in.visuals import (
    APP_ICON_PATH,
    display_font_family,
    load_app_icon,
    make_background_texture,
    make_flat_fill,
    make_glow,
    make_hours_chart,
    make_panel_divider,
    make_week_compare_chart,
)
```

Then insert these tests immediately after `test_make_hours_chart_each_era_looks_different` (the last hours-chart test, just before the "Tier 1: per-Rider progress bar variants" banner comment):

```python
# --- make_week_compare_chart ------------------------------------------- #
# this_color is green, last_color is red in every test below, so a pixel
# check can tell the two weeks' bars apart at a glance.

_WEEK_PAIRS_EQUAL = [("2026-01-01", 100, 100), ("2026-01-02", 100, 100)]


def test_make_week_compare_chart_returns_the_requested_size():
    image = make_week_compare_chart(280, 100, _WEEK_PAIRS_EQUAL, "#00ff00", "#ff0000", dark=False)
    assert image.size == (280, 100)
    assert image.mode == "RGBA"


def test_make_week_compare_chart_handles_an_empty_list_without_crashing():
    image = make_week_compare_chart(100, 50, [], "#00ff00", "#ff0000", dark=True)
    assert image.size == (100, 50)


def test_make_week_compare_chart_handles_all_zero_days_without_dividing_by_zero():
    pairs = [("2026-01-01", 0, 0), ("2026-01-02", 0, 0)]
    image = make_week_compare_chart(150, 60, pairs, "#00ff00", "#ff0000", dark=False)
    assert image.size == (150, 60)


def test_make_week_compare_chart_last_week_is_left_and_this_week_is_right():
    """Width 280, two groups: each group is 135px wide with a 10px gap
    between groups. Inside a group the left bar is last week (red) and the
    right bar is this week (green). Both values are equal, so every bar is
    full height and a sample at y=40 is safely inside all four bars."""
    image = make_week_compare_chart(280, 100, _WEEK_PAIRS_EQUAL, "#00ff00", "#ff0000", dark=False)
    assert image.getpixel((30, 40))[:3] == (0xff, 0x00, 0x00)    # group 1, last week
    assert image.getpixel((100, 40))[:3] == (0x00, 0xff, 0x00)   # group 1, this week
    assert image.getpixel((170, 40))[:3] == (0xff, 0x00, 0x00)   # group 2, last week
    assert image.getpixel((250, 40))[:3] == (0x00, 0xff, 0x00)   # group 2, this week


def test_make_week_compare_chart_leaves_a_gap_between_groups():
    image = make_week_compare_chart(280, 100, _WEEK_PAIRS_EQUAL, "#00ff00", "#ff0000", dark=False)
    assert image.getpixel((140, 40))[3] == 0    # the gap between group 1 and group 2


def test_make_week_compare_chart_both_weeks_share_one_height_scale():
    """One group, last week 100 and this week 50, on a 200x116 image (plot
    area 100px tall). The last-week bar fills it; the this-week bar must be
    exactly half as tall no matter which side the bigger number is on."""
    image = make_week_compare_chart(
        200, 116, [("2026-01-01", 100, 50)], "#00ff00", "#ff0000", dark=False)
    assert image.getpixel((50, 10))[:3] == (0xff, 0x00, 0x00)     # last week, full height
    assert image.getpixel((150, 10))[3] == 0                       # this week: empty above half height
    assert image.getpixel((150, 60))[:3] == (0x00, 0xff, 0x00)    # this week: filled below half height


def test_make_week_compare_chart_a_zero_day_draws_no_bar():
    image = make_week_compare_chart(
        200, 116, [("2026-01-01", 0, 100)], "#00ff00", "#ff0000", dark=False)
    assert image.getpixel((50, 50))[3] == 0                        # last week is 0: nothing drawn
    assert image.getpixel((150, 50))[:3] == (0x00, 0xff, 0x00)    # this week is full height


def test_make_week_compare_chart_light_and_dark_renders_differ():
    pairs = [("2026-01-01", 100, 200), ("2026-01-02", 300, 50)]
    light = make_week_compare_chart(200, 80, pairs, "#00ff00", "#ff0000", dark=False)
    dark = make_week_compare_chart(200, 80, pairs, "#00ff00", "#ff0000", dark=True)
    assert light.tobytes() != dark.tobytes()


def test_make_week_compare_chart_default_era_matches_showa():
    pairs = [("2026-01-01", 100, 200), ("2026-01-02", 300, 50)]
    default = make_week_compare_chart(200, 80, pairs, "#00ff00", "#ff0000", dark=True)
    showa = make_week_compare_chart(200, 80, pairs, "#00ff00", "#ff0000", dark=True, era="Showa")
    assert default.tobytes() == showa.tobytes()


def test_make_week_compare_chart_each_era_looks_different():
    pairs = [("2026-01-01", 100, 200), ("2026-01-02", 300, 50)]
    showa = make_week_compare_chart(200, 80, pairs, "#00ff00", "#ff0000", dark=True, era="Showa")
    heisei = make_week_compare_chart(200, 80, pairs, "#00ff00", "#ff0000", dark=True, era="Heisei")
    reiwa = make_week_compare_chart(200, 80, pairs, "#00ff00", "#ff0000", dark=True, era="Reiwa")
    assert showa.tobytes() != heisei.tobytes()
    assert heisei.tobytes() != reiwa.tobytes()
    assert showa.tobytes() != reiwa.tobytes()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_visuals.py -v`
Expected: collection error, `ImportError: cannot import name 'make_week_compare_chart' from 'lock_in.visuals'`.

- [ ] **Step 3: Write the implementation**

In `lock_in/visuals.py`, add this function immediately after `make_hours_chart` (which ends with `return image`) and before `def load_app_icon`:

```python
def make_week_compare_chart(
    width: int, height: int, pairs: list[tuple[str, int, int]],
    this_color: str, last_color: str, dark: bool, era: str = "Showa",
) -> Image.Image:
    """
    Draw a paired bar chart: one GROUP per day, oldest on the left and
    today on the right, with two bars in each group. The left bar is that
    day's number from LAST week (`last_color`) and the right bar is the
    same day THIS week (`this_color`), so time also reads left to right
    inside a group.

    `pairs` is `(iso_day, last_week_seconds, this_week_seconds)`, already
    zero-filled by the caller. `iso_day` is the this-week date (its
    weekday letter goes under the group). Both weeks share ONE height
    scale -- the biggest number in either week -- so a bar means the same
    amount on both sides. A day with 0 seconds draws no bar, and all-zero
    input never divides by zero.

    Sits next to make_hours_chart() and reuses its label and era-accent
    approach, but is its own function on purpose: make_hours_chart() draws
    V3's and Decade's charts and is left exactly as it was.
    """
    LABEL_MARGIN = 16
    GROUP_GAP = 10
    PAIR_GAP = 2
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if not pairs:
        return image

    draw = ImageDraw.Draw(image, "RGBA")
    plot_height = height - LABEL_MARGIN
    this_rgba = (*_hex_to_rgb(this_color), 255)
    last_rgba = (*_hex_to_rgb(last_color), 255)
    label_color = (190, 190, 190, 220) if dark else (90, 90, 90, 220)

    count = len(pairs)
    max_secs = max(max(last, this) for _, last, this in pairs) or 1
    group_width = (width - GROUP_GAP * (count - 1)) / count
    bar_width = (group_width - PAIR_GAP) / 2

    for index, (iso_day, last_secs, this_secs) in enumerate(pairs):
        group_x = index * (group_width + GROUP_GAP)
        bars = (
            (group_x, last_secs, last_rgba),
            (group_x + bar_width + PAIR_GAP, this_secs, this_rgba),
        )
        for x_start, secs, color in bars:
            bar_height = plot_height * secs / max_secs
            if bar_height > 0:
                y0 = round(plot_height - bar_height)
                draw.rectangle(
                    [round(x_start), y0, round(x_start + bar_width), plot_height],
                    fill=color,
                )

        letter = date.fromisoformat(iso_day).strftime("%a")[0]
        bbox = draw.textbbox((0, 0), letter)
        letter_width = bbox[2] - bbox[0]
        text_x = group_x + group_width / 2 - letter_width / 2
        draw.text((text_x, plot_height + 5), letter, fill=label_color)

    accent = make_panel_divider(width, 8, this_color, last_color, era=era)
    image.alpha_composite(accent, (0, max(plot_height - 4, 0)))

    return image
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_visuals.py -v`
Expected: all PASS, including the 10 new `make_week_compare_chart` tests and every existing `make_hours_chart` test (unchanged).

- [ ] **Step 5: Look at the chart with your own eyes**

The tests check numbers; this checks it *looks* right. Run from the project folder (Git Bash or PowerShell, same command):

```
python -c "import tempfile, os; from lock_in.visuals import make_week_compare_chart as f; pairs=[('2026-09-15',30*60,60*60),('2026-09-16',45*60,0),('2026-09-17',0,90*60),('2026-09-18',60*60,25*60),('2026-09-19',25*60,50*60),('2026-09-20',0,0),('2026-09-21',80*60,120*60)]; out=tempfile.gettempdir(); [f(440,200,pairs,'#4caf50','#616161',dark=True,era='Heisei').save(os.path.join(out,'w_chart_dark.png')), f(440,200,pairs,'#225c25','#111111',dark=False,era='Heisei').save(os.path.join(out,'w_chart_light.png')), print('saved in', out)]"
```

Open `w_chart_dark.png` and `w_chart_light.png` from the folder it prints. Expected: 7 groups; in each group a dark/grey bar on the left and a green bar on the right; the two bars are the same height scale (the 120-minute green bar on the last group is the tallest thing on the chart); weekday letters under each group; two empty bars on the day that is 0 and 0; the thin era line along the bottom of the bars.

- [ ] **Step 6: Confirm nothing else broke**

Run: `python -m pytest`
Expected: 0 failed.

---

### Task 3: The "Week" tab, plus the wiring

**Files:**
- Modify: `lock_in/tier5/w.py` (add imports and `build()`)
- Modify: `lock_in/tier5/__init__.py`
- Modify: `lock_in/rider_themes.py` (the `Kamen Rider W (2009)` entry)
- Modify: `lock_in/ui.py` (`_TIER5_TAB_LABELS`)
- Modify: `tests/test_tier5_w.py` (wiring tests)
- Modify: `tests/test_rider_themes.py`

**Interfaces:**
- Consumes: `week_pairs`, `compare_sentence` (Task 1); `visuals.make_week_compare_chart` (Task 2); `history.all()`, `history.total_seconds_by_day()`; the theme's `primary`, `secondary`, `primary_text_pair`, `secondary_text_pair`, `era`.
- Produces: `build(parent, *, history, tasks, theme, appearance_mode) -> None` (the same signature as every other Tier 5 builder), registered as `TIER5_BUILDERS["week_compare"]`; the tab label `"Week"`.

- [ ] **Step 1: Write the failing wiring tests**

Append to `tests/test_tier5_w.py`:

```python
# --- wiring ------------------------------------------------------------- #

def test_week_compare_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, w
    assert TIER5_BUILDERS["week_compare"] is w.build


def test_week_compare_has_the_week_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["week_compare"] == "Week"
```

In `tests/test_rider_themes.py`, replace the function
`test_exactly_these_five_riders_have_a_tier5_effect` with:

```python
def test_exactly_these_six_riders_have_a_tier5_effect():
    from lock_in.rider_themes import RIDER_THEMES
    expected = {
        "Kamen Rider V3 (1973)": "hours_tab",
        "Kamen Rider Den-O (2007)": "timeline_view",
        "Kamen Rider Decade (2009)": "analytics_dashboard",
        "Kamen Rider Zi-O (2018)": "history_editor",
        "Kamen Rider Blade (2004)": "kanban_board",
        "Kamen Rider W (2009)": "week_compare",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier5_effect == effect, name
    tier5_riders = {n for n, t in RIDER_THEMES.items() if t.tier5_effect != "none"}
    assert tier5_riders == set(expected)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tier5_w.py tests/test_rider_themes.py -v`
Expected: 3 FAIL: the two new wiring tests (`KeyError: 'week_compare'`) and the six-Riders test (W's `tier5_effect` is still `"none"`). Everything else passes.

- [ ] **Step 3: Add `build()` to `w.py`**

Change the import block of `lock_in/tier5/w.py` from:

```python
from datetime import date

from ._shared import format_hm, last_n_days
```

to:

```python
from datetime import date

import customtkinter as ctk

from .. import visuals
from ._shared import format_hm, last_n_days
```

Then append this to the end of the file:

```python
def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` with W's Week view: two total lines (this week and
    last week, colored to match their bars), one short sentence, and a
    paired bar chart of the last 7 days against the 7 days before.

    `tasks` and `appearance_mode` are part of every Tier 5 builder's
    signature for consistency -- W needs neither. CustomTkinter's own
    (light, dark) color pairs and CTkImage(light_image=, dark_image=)
    already handle light and dark switching.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    if not history.all():
        ctk.CTkLabel(
            frame, text="No focus blocks yet. Finish one and it shows up here.",
            justify="left", wraplength=400,
        ).pack(anchor="w", pady=8)
        return

    pairs = week_pairs(history.total_seconds_by_day(), date.today())
    this_total = sum(this for _, _, this in pairs)
    last_total = sum(last for _, last, _ in pairs)

    # The colored words below double as the chart's legend: "This week"
    # is in the same green as this week's bars, "Last week" in the same
    # dark/grey as last week's bars.
    for name, seconds, color in (
        ("This week", this_total, theme.primary_text_pair),
        ("Last week", last_total, theme.secondary_text_pair),
    ):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(row, text=name, text_color=color, anchor="w").pack(
            side="left", fill="x", expand=True)
        ctk.CTkLabel(
            row, text=format_hm(seconds), text_color=color, anchor="e",
            font=ctk.CTkFont(family=visuals.display_font_family(), size=20, weight="bold"),
        ).pack(side="right")

    ctk.CTkLabel(
        frame, text=compare_sentence(this_total, last_total),
        justify="left", wraplength=400, anchor="w",
    ).pack(anchor="w", pady=(10, 12))

    chart_pairs = [(day.isoformat(), last, this) for day, last, this in pairs]
    light_image = visuals.make_week_compare_chart(
        440, 200, chart_pairs, theme.primary[0], theme.secondary[0],
        dark=False, era=theme.era,
    )
    dark_image = visuals.make_week_compare_chart(
        440, 200, chart_pairs, theme.primary[1], theme.secondary[1],
        dark=True, era=theme.era,
    )
    chart_image = ctk.CTkImage(light_image=light_image, dark_image=dark_image, size=(440, 200))
    chart_label = ctk.CTkLabel(frame, text="", image=chart_image)
    # CTkImage is garbage-collected the moment nothing references it,
    # which would blank the label the next time Tk redraws -- stashing it
    # as an attribute on the label keeps it alive as long as the label is.
    chart_label._w_chart_image = chart_image
    chart_label.pack(anchor="w")

    ctk.CTkLabel(
        frame, text="Last 7 days vs the 7 days before · every focus block counts, finished or not",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(6, 0))
```

Also update the module docstring's last sentence so it is true: replace
`` `build()` (added later in this file) is the `` with `` `build()` is the ``
(so it reads: "`build()` is the only Tk-dependent piece; ...").

- [ ] **Step 4: Register the builder**

In `lock_in/tier5/__init__.py`, replace:

```python
from . import blade, decade, den_o, v3, zi_o

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
    "analytics_dashboard": decade.build,
    "history_editor": zi_o.build,
    "kanban_board": blade.build,
}
```

with:

```python
from . import blade, decade, den_o, v3, w, zi_o

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
    "analytics_dashboard": decade.build,
    "history_editor": zi_o.build,
    "kanban_board": blade.build,
    "week_compare": w.build,
}
```

- [ ] **Step 5: Give W its effect**

In `lock_in/rider_themes.py`, replace:

```python
    "Kamen Rider W (2009)": RiderTheme(
        "Heisei", 2009, ("#225c25", "#4caf50"), ("#111111", "#616161"),
    ),
```

with:

```python
    "Kamen Rider W (2009)": RiderTheme(
        "Heisei", 2009, ("#225c25", "#4caf50"), ("#111111", "#616161"),
        tier5_effect="week_compare",
    ),
```

- [ ] **Step 6: Give the tab its name**

In `lock_in/ui.py`, replace:

```python
_TIER5_TAB_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
    "history_editor": "History", "kanban_board": "Board",
}
```

with:

```python
_TIER5_TAB_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
    "history_editor": "History", "kanban_board": "Board", "week_compare": "Week",
}
```

Nothing else in `ui.py` changes for the tab itself: building it, refreshing it after a finished block, and hiding it for Standard Mode all already work for any registered effect.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tier5_w.py tests/test_rider_themes.py -v`
Expected: all PASS.

- [ ] **Step 8: Drive the real tab in the real app**

Save the script below as `w_drive.py` in any scratch folder OUTSIDE the project (for example your temp folder). It points the app at a throwaway data folder, so your real settings and history are not touched. It seeds two weeks of fake history:

- this week (today back to 6 days ago): 60, 0, 90, 25, 50, 0, 120 minutes, a total of 5h 45m
- last week (7 to 13 days ago): 30, 45, 0, 60, 25, 0, 80 minutes, a total of 4h 0m
- so the sentence must be `You did 1h 45m MORE than last week. Yay!`

```python
"""Drives the real Lock In window with fake history. Run from the PROJECT
folder so `lock_in` can be imported:

  Git Bash:    PYTHONPATH=. python /path/to/w_drive.py
  PowerShell:  $env:PYTHONPATH="."; python C:\\path\\to\\w_drive.py

Optional switches (environment variables):
  EMPTY=1                   fresh install, no history
  RIDER="Kamen Rider (1971)"   a Rider other than W (the Week tab must be absent)
  SHOT=C:\\some\\folder\\week     also saves week-dark.png and week-light.png
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

W = "Kamen Rider W (2009)"
RIDER = os.environ.get("RIDER", W)
EMPTY = bool(os.environ.get("EMPTY"))
SHOT = os.environ.get("SHOT")
CAPTION = "Last 7 days vs the 7 days before · every focus block counts, finished or not"

config = Config()
config.rider_theme = RIDER
config.save()

if not EMPTY:
    now = datetime.now()
    this_week_minutes = [60, 0, 90, 25, 50, 0, 120]   # today first, then 1 day ago, ...
    last_week_minutes = [30, 45, 0, 60, 25, 0, 80]    # 7 days ago first, ...
    days = list(enumerate(this_week_minutes)) + [(7 + i, m) for i, m in enumerate(last_week_minutes)]
    lines = []
    for days_ago, minutes in days:
        if minutes == 0:
            continue
        start = (now - timedelta(days=days_ago)).replace(hour=9, minute=0, second=0, microsecond=0)
        end = start + timedelta(minutes=minutes)
        record = SessionRecord(start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds"),
                               minutes * 60, None, True)
        lines.append(json.dumps(dataclasses.asdict(record)))
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

import customtkinter as ctk
from lock_in.ui import LockInApp

failures = []
def check(label, condition):
    print(("  PASS  " if condition else "  FAIL  ") + label)
    if not condition:
        failures.append(label)

def label_texts(widget):
    found = []
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel):
            text = child.cget("text")
            if text:
                found.append(text)
        found.extend(label_texts(child))
    return found

app = LockInApp()
app.update()
has_tab = "Week" in app.tabs._tab_dict

if RIDER != W:
    check("no Week tab for a Rider that isn't W", not has_tab)
else:
    check("Week tab exists for W", has_tab)
    app.tabs.set("Week")
    app.update()
    texts = label_texts(app.tabs.tab("Week"))
    print("  tab text:", texts)
    if EMPTY:
        check("fresh install shows only the empty-state line",
              texts == ["No focus blocks yet. Finish one and it shows up here."])
    else:
        for expected in ("This week", "Last week", "5h 45m", "4h 0m",
                         "You did 1h 45m MORE than last week. Yay!", CAPTION):
            check(f"shows {expected!r}", expected in texts)

    if SHOT:
        app.geometry("560x1000")
        for mode in ("dark", "light"):
            app._on_appearance_change(mode)
            app.update(); time.sleep(0.4); app.update()
            x, y = app.winfo_rootx(), app.winfo_rooty()
            from PIL import ImageGrab
            ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(f"{SHOT}-{mode}.png")
            print("  saved", f"{SHOT}-{mode}.png")

app.destroy()
print("\nFAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
```

Run it three ways, from the project folder:
1. With history: every line prints PASS and `FAILURES: none`.
2. `EMPTY=1`: the fresh-install line passes.
3. `RIDER="Kamen Rider (1971)"`: the "no Week tab" line passes.

Then run it once more with `SHOT` set and open the two PNGs. Expected in both light and dark: "This week" and its total in green, "Last week" and its total in a dark or grey tone, the sentence under them, then the chart with a black or grey bar on the left and a green bar on the right in each pair, and the small caption. If the tab area is too short to show the whole chart, scroll the tab and look again; if the window is taller than your screen, lower the `560x1000` value.

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
- Produces: version `2.5.6`; the W bullet in the Help tab and README; the "six" wording.

- [ ] **Step 1: Bump the version**

In `lock_in/__init__.py`, replace `__version__ = "2.5.5"` with `__version__ = "2.5.6"`.

- [ ] **Step 2: Help tab**

In `lock_in/ui.py`, in the Tier 5 section of the Help tab, replace:

```python
        bullet(
            "Blade — a \"Board\" tab appears, with your tasks in three "
            "columns: To Do, In Progress and Done. Tap the little arrow "
            "on a task to move it one column over."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "five are just the first."
        )
```

with:

```python
        bullet(
            "Blade — a \"Board\" tab appears, with your tasks in three "
            "columns: To Do, In Progress and Done. Tap the little arrow "
            "on a task to move it one column over."
        )
        bullet(
            "W — a \"Week\" tab appears. It puts the last 7 days next to "
            "the 7 days before them: one total for each, a little "
            "sentence about which is bigger, and a chart with two bars "
            "for every day. Every block counts, finished or not."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "six are just the first."
        )
```

- [ ] **Step 3: README, the W bullet and the count**

In `README.md`, replace:

```
More Riders will read your tasks and history this way over time — these
five are just the first of ten planned.
```

with:

```
- **W** — adds a "Week" tab. It puts two weeks side by side: the last 7
  days, and the 7 days right before them. You see one total for each, a
  short sentence that says which one is bigger, and a chart with two
  bars for every day, one for last week and one for this week. Every
  block counts, finished or not.

More Riders will read your tasks and history this way over time — these
six are just the first of ten planned.
```

(The new W bullet goes directly after the Blade bullet, which ends with
"...so a move on the Board shows up there too." Keep one blank line
between the W bullet and the "More Riders..." paragraph.)

- [ ] **Step 4: README, one known limit**

In the "known limits" list, directly before the line starting
`- **Auto-update only replaces the downloaded app**`, add:

```
- **W only compares two fixed weeks** — the last 7 days against the 7
  days right before them. There are no buttons to pick other weeks.
```

- [ ] **Step 5: Run everything**

Run: `python -m pytest`
Expected: 0 failed, 1 skipped (the same skip as before).

Run the existing real-window smoke test in a throwaway data folder. Git Bash: `APPDATA="$(mktemp -d)" PYTHONPATH=. python tests/smoke_ui.py`. PowerShell: `$env:APPDATA=(New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([guid]::NewGuid()))).FullName; $env:PYTHONPATH="."; python tests/smoke_ui.py`.
Expected: ends with `smoke test passed`.

Re-run `w_drive.py` (Task 3, Step 8) with history. Expected: `FAILURES: none`, and the Help tab's version line now says v2.5.6 if you open Help.

- [ ] **Step 6: Repo hygiene checks**

Run: `git status --short`
Expected: exactly these paths, and nothing else (in particular nothing generated):
`README.md`, `lock_in/__init__.py`, `lock_in/rider_themes.py`, `lock_in/tier5/__init__.py`, `lock_in/tier5/w.py` (new), `lock_in/ui.py`, `lock_in/visuals.py`, `tests/test_rider_themes.py`, `tests/test_tier5_w.py` (new), `tests/test_visuals.py`, plus the spec and this plan under `docs/superpowers/`.
If anything else shows up (a picture, a data file, a folder), add a matching line to `.gitignore`. If nothing does, `.gitignore` needs no change.

Read the added lines (`git diff`) and the four new files (`lock_in/tier5/w.py`, `tests/test_tier5_w.py`, the spec, and this plan) and confirm none of them names a tool, an assistant, or an author, and none has a credit line of any kind. Nothing about who or what wrote the code belongs in the project files. Expected: nothing found.

---

## Handoff: git steps for the project owner

Nothing above runs any of these. Run them yourself once you have looked at the result. The commit message is plain, with no extra lines under it.

```bash
git status
git add -A
git commit -m "v2.5.6: add W (Tier 5 Rider 6), the week-vs-week chart"
git push origin main
git tag v2.5.6
git push origin v2.5.6
```

Pushing the tag starts the release build (`.github/workflows/release.yml`), so push it last, after you are happy with the result. Git may print harmless "LF will be replaced by CRLF" warnings.

## Spec coverage check

| Spec section | Where it's covered |
|---|---|
| What "this week" and "last week" mean | Task 1 (`week_pairs` + its tests) |
| The tab (empty state, two total lines, sentence, chart, caption) | Task 3, Step 3 (`build()`) and Step 8 (checked in the real app) |
| Colors | Task 2 (pixel tests), Task 3 Step 3 |
| The words on screen | Task 1 (`compare_sentence` + tests for each row, the 59/60-second edge, and "never harsh") |
| `week_pairs`, `compare_sentence`, `build` | Tasks 1 and 3 |
| `make_week_compare_chart` (shared scale, zero-height, empty, light/dark, eras, leaves `make_hours_chart` alone) | Task 2 |
| Wiring (registry, theme, tab label) | Task 3, Steps 4 to 6, with wiring tests in Steps 1 and 7 |
| Error handling (empty history, older-than-14-days, CTkImage kept alive) | Task 1 (older-than-14-days test, both-zero sentence), Task 3 (`_w_chart_image`, empty-state branch) |
| Testing list (pairing, sentences, chart, six-Riders test, manual checks) | Tasks 1 to 3; manual checks in Task 3 Step 8 and Task 4 Step 5 |
| Docs, version, repo hygiene | Task 4 |
| Out of scope | Nothing in this plan builds any of it |
