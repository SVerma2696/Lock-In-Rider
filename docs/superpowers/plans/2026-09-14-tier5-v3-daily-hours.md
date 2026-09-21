# Tier 5 Rider #1: V3 Daily Hours Tracker Implementation Plan

**Goal:** When Kamen Rider V3 (1973) is the picked Rider, a 6th "Hours" tab
appears showing today's total focused time and a 14-day bar chart, reading
only the history aggregate `HistoryStore.total_seconds_by_day()` already
exposes. This also builds the shared `tier5_effect` / `lock_in/tier5/`
plumbing every later Tier 5 Rider will reuse.

**Architecture:** A new `tier5_effect` field on `RiderTheme` (mirrors
`tier1_effect`/`tier3_effect`/`tier4_effect`). A new `lock_in/tier5/`
package holds one module per Rider; `v3.py` has two pure functions
(`last_14_days`, `_format_hm`) plus a Tk `build()`. `visuals.py` gets
`make_hours_chart()`, a Pillow bar-chart renderer that composites the
existing `make_panel_divider()` as its era accent instead of duplicating
three new drawing helpers. `ui.py`'s existing `_build_tabs()` /
`_rebuild_tabs()` machinery (already used by every Rider/appearance/
wording change) grows the tier5 tab conditionally — no new tab-lifecycle
code is needed.

**Tech Stack:** Python 3.11+, Pillow (chart rendering), CustomTkinter
(the tab + widgets), pytest.

## Global Constraints

- Every focus block counts toward the hours shown, whether it finished,
  was skipped, or was reset (`total_seconds_by_day()` already sums all
  of them — do not filter by `completed`).
- "Today" is `date.today()` in local time, matching how
  `total_seconds_by_day()` already keys records — no new day-boundary
  logic.
- Fixed last-14-days window and fixed 440×200 chart size — no resize
  handling, no streak, no goal line, no other range (see the spec's Out
  of scope section).
- No new `HistoryStore`/`TaskStore` methods — V3 reads
  `total_seconds_by_day()` and `all()` only.
- `tasks` and `appearance_mode` are part of every Tier 5 builder's
  signature for uniformity across the 10 Riders, even where a specific
  Rider (V3) doesn't need them — CustomTkinter's native `(light, dark)`
  color tuples and `CTkImage(light_image=, dark_image=)` already handle
  V3's light/dark switching, so V3's `build()` does not branch on
  `appearance_mode` itself.
- No git commit, tag, or push is executed as part of any task in this
  plan — every step below stops at "write the file" / "run the tests".
  The final task hands the exact commands to the user to run themselves.

## Deviation from the approved spec (found while planning — read before Task 5)

The spec (`docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md`)
describes a bespoke `_sync_tier5_tab()` that manually
`self.tabs.add()`/`self.tabs.delete()`s a 6th tab, plus a `hasattr`
startup guard. Re-reading `ui.py` while planning found something better
already in the codebase: `_rebuild_tabs()` (`ui.py:2302`) already
destroys and rebuilds the whole `CTkTabview` from scratch on every
Rider/Standard-Mode/wording change, via `_build_tabs()`
(`ui.py:974`) — and `_build_tabs()` already runs *after*
`self.tasks`/`self.history`/`self.current_tier5_effect` are guaranteed to
exist (they're set at `ui.py:273-274` and in `_apply_rider_theme()`,
both of which run before `_build_tabs()` is ever called, including at
startup — see `ui.py:343`).

So Task 5 below has `_build_tabs()` itself conditionally add the tier5
tab — no separate add/delete method, no `hasattr` guard, no new tab
lifecycle code at all. This is simpler than the spec and reuses an
existing, already-battle-tested mechanism instead of inventing a
parallel one. (The spec will be updated to match once this lands.)

---

### Task 1: `tier5_effect` field on `RiderTheme`

**Files:**
- Modify: `lock_in/rider_themes.py` (the `RiderTheme` dataclass, and the
  `Kamen Rider V3 (1973)` entry in `RIDER_THEMES`)
- Test: `tests/test_rider_themes.py`

**Interfaces:**
- Produces: `RiderTheme.tier5_effect: str` (default `"none"`). Every
  later task reads `theme.tier5_effect`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rider_themes.py`:

```python
def test_tier5_effect_defaults_to_none():
    from lock_in.rider_themes import RiderTheme
    theme = RiderTheme("Heisei", 2000, ("#000000", "#ffffff"), ("#111111", "#eeeeee"))
    assert theme.tier5_effect == "none"


def test_v3_has_the_hours_tab_tier5_effect():
    from lock_in.rider_themes import RIDER_THEMES
    assert RIDER_THEMES["Kamen Rider V3 (1973)"].tier5_effect == "hours_tab"
    tier5_riders = {n for n, t in RIDER_THEMES.items() if t.tier5_effect != "none"}
    assert tier5_riders == {"Kamen Rider V3 (1973)"}


def test_standard_theme_has_no_tier5_effect():
    from lock_in.rider_themes import STANDARD_THEME
    assert STANDARD_THEME.tier5_effect == "none"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_rider_themes.py -k tier5 -v`
Expected: FAIL — `AttributeError: 'RiderTheme' object has no attribute 'tier5_effect'`

- [ ] **Step 3: Add the field**

In `lock_in/rider_themes.py`, right after the existing `tier4_effect`
field (find the block that ends with `tier4_effect: str = "none"`), add:

```python
    # "none" for every Rider except V3, the first of Tier 5's 10
    # history/task-reading Riders (see
    # docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md).
    # ui.py reads this to decide whether a 6th tab exists at all, and
    # lock_in/tier5/__init__.py's TIER5_BUILDERS maps it to the module
    # that fills that tab in.
    tier5_effect: str = "none"
```

Then find the `"Kamen Rider V3 (1973)"` entry in `RIDER_THEMES` (currently
`RiderTheme("Showa", 1973, ("#225c25", "#4caf50"), ("#a83225", "#d94436"))`
with no trailing kwargs) and add the effect:

```python
    "Kamen Rider V3 (1973)": RiderTheme(
        "Showa", 1973, ("#225c25", "#4caf50"), ("#a83225", "#d94436"),
        tier5_effect="hours_tab",
    ),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_rider_themes.py -v`
Expected: PASS — all tests, including the 3 new ones and every existing
completeness test (they should be unaffected).

- [ ] **Step 5: Commit**

(Per this plan's Global Constraints, no commit is run here — the final
task hands over the git steps.)

---

### Task 2: Pure V3 data functions — `last_14_days()` and `_format_hm()`

**Files:**
- Create: `lock_in/tier5/__init__.py`
- Create: `lock_in/tier5/v3.py`
- Test: `tests/test_tier5_v3.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `last_14_days(totals: dict[str, int], today: date) -> list[tuple[date, int]]`
  and `_format_hm(seconds: int) -> str`, both in `lock_in.tier5.v3`. Task
  4's `build()` calls both.

- [ ] **Step 1: Create the package marker**

`lock_in/tier5/__init__.py`:

```python
"""
tier5/
======
One module per Tier 5 Rider (V3, Decade, W, OOO, Den-O, Zi-O, Gotchard,
Geats, Blade, MY-TH). Each module exposes a single `build(parent, *,
history, tasks, theme, appearance_mode)` function that populates an
empty tab frame with that Rider's view -- see
docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md for why
this is a package of small modules instead of more methods on ui.py's
already-large LockInApp.

TIER5_BUILDERS grows one entry per Rider as each one is built.
"""
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_tier5_v3.py`:

```python
from datetime import date

from lock_in.tier5.v3 import _format_hm, last_14_days


def test_last_14_days_returns_exactly_14_entries():
    result = last_14_days({}, date(2026, 9, 14))
    assert len(result) == 14


def test_last_14_days_is_oldest_to_newest_ending_today():
    result = last_14_days({}, date(2026, 9, 14))
    assert result[0][0] == date(2026, 9, 1)
    assert result[-1][0] == date(2026, 9, 14)


def test_last_14_days_fills_missing_days_with_zero():
    totals = {"2026-09-14": 1200}
    result = last_14_days(totals, date(2026, 9, 14))
    assert result[-1] == (date(2026, 9, 14), 1200)
    assert result[0] == (date(2026, 9, 1), 0)


def test_last_14_days_crosses_a_month_boundary():
    result = last_14_days({}, date(2026, 3, 5))
    assert result[0][0] == date(2026, 2, 20)
    assert result[-1][0] == date(2026, 3, 5)


def test_last_14_days_crosses_a_year_boundary():
    result = last_14_days({}, date(2026, 1, 3))
    assert result[0][0] == date(2025, 12, 21)
    assert result[-1][0] == date(2026, 1, 3)


def test_format_hm_zero_seconds():
    assert _format_hm(0) == "0m"


def test_format_hm_minutes_only():
    assert _format_hm(600) == "10m"


def test_format_hm_hours_and_minutes():
    assert _format_hm(9000) == "2h 30m"


def test_format_hm_exact_hour_still_shows_minutes():
    assert _format_hm(3600) == "1h 0m"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pytest tests/test_tier5_v3.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.tier5.v3'`

- [ ] **Step 4: Write the minimal implementation**

Create `lock_in/tier5/v3.py`:

```python
"""
tier5/v3.py
===========
Kamen Rider V3's Tier 5 gimmick: a new "Hours" tab showing how long
you've focused today, plus a 14-day bar chart. The first, and smallest,
of Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md.

Two plain functions do the shaping (`last_14_days`, `_format_hm`) --
tested with no Tk, no display server, same as every pure-logic module
in this codebase. `build()` is the only Tk-dependent piece; it's
screenshot-verified in the running app instead, matching how every
other tab in ui.py is verified.
"""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from .. import visuals


def last_14_days(totals: dict[str, int], today: date) -> list[tuple[date, int]]:
    """14 entries, oldest -> newest, ending on `today`. A day absent
    from `totals` (no focus blocks that day) contributes 0 seconds --
    the chart always has 14 bars, even on a brand new install."""
    return [
        (day, totals.get(day.isoformat(), 0))
        for day in (today - timedelta(days=offset) for offset in range(13, -1, -1))
    ]


def _format_hm(seconds: int) -> str:
    """3900 -> '1h 5m'; 600 -> '10m'; 0 -> '0m'. Hours are only shown at
    all once there's at least one -- an under-an-hour total never shows
    a redundant '0h'."""
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_tier5_v3.py -v`
Expected: PASS — all 9 tests.

- [ ] **Step 6: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 3: `make_hours_chart()` in `visuals.py`

**Files:**
- Modify: `lock_in/visuals.py` (add `from datetime import date` to the
  imports, add the new function near `make_panel_divider`)
- Test: `tests/test_visuals.py`

**Interfaces:**
- Consumes: `make_panel_divider(width, height, primary, secondary, era)`
  (already exists in this file) and `_hex_to_rgb(hex_color)` (already
  exists in this file).
- Produces: `make_hours_chart(width, height, day_values, primary,
  secondary, dark, era="Showa") -> Image.Image`, where `day_values` is
  `list[tuple[str, int]]` (ISO date string, seconds), oldest first. Task
  4's `build()` calls this twice (once per appearance mode).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_visuals.py`. First add `make_hours_chart` to the
existing `from lock_in.visuals import (...)` block at the top of the
file, then append:

```python
def test_make_hours_chart_returns_the_requested_size():
    image = make_hours_chart(
        280, 100, [("2026-01-01", 100), ("2026-01-02", 100)],
        "#ff0000", "#00ff00", dark=False,
    )
    assert image.size == (280, 100)
    assert image.mode == "RGBA"


def test_make_hours_chart_handles_an_empty_list_without_crashing():
    image = make_hours_chart(100, 50, [], "#ff0000", "#00ff00", dark=True)
    assert image.size == (100, 50)


def test_make_hours_chart_handles_all_zero_days_without_dividing_by_zero():
    day_values = [("2026-01-01", 0), ("2026-01-02", 0), ("2026-01-03", 0)]
    image = make_hours_chart(150, 60, day_values, "#ff0000", "#00ff00", dark=False)
    assert image.size == (150, 60)


def test_make_hours_chart_last_bar_uses_secondary_color():
    """The last entry is 'today' -- it should stand out in `secondary`,
    every earlier bar stays in `primary`. Both entries here have equal
    seconds, so both bars are the same (near-full) height, which makes
    picking an unambiguous sample point inside each bar's middle easy."""
    day_values = [("2026-01-01", 100), ("2026-01-02", 100)]
    image = make_hours_chart(280, 100, day_values, "#ff0000", "#00ff00", dark=False)
    first_bar_pixel = image.getpixel((69, 40))     # inside the left (primary) bar
    today_bar_pixel = image.getpixel((210, 40))    # inside the right (today) bar
    assert first_bar_pixel[:3] == (0xff, 0x00, 0x00)
    assert today_bar_pixel[:3] == (0x00, 0xff, 0x00)


def test_make_hours_chart_light_and_dark_renders_differ():
    day_values = [("2026-01-01", 100), ("2026-01-02", 200)]
    light = make_hours_chart(200, 80, day_values, "#ff0000", "#00ff00", dark=False)
    dark = make_hours_chart(200, 80, day_values, "#ff0000", "#00ff00", dark=True)
    assert light.tobytes() != dark.tobytes()


def test_make_hours_chart_default_era_matches_showa():
    day_values = [("2026-01-01", 100), ("2026-01-02", 200)]
    default = make_hours_chart(200, 80, day_values, "#ff0000", "#00ff00", dark=True)
    showa = make_hours_chart(200, 80, day_values, "#ff0000", "#00ff00", dark=True, era="Showa")
    assert default.tobytes() == showa.tobytes()


def test_make_hours_chart_each_era_looks_different():
    day_values = [("2026-01-01", 100), ("2026-01-02", 200)]
    showa = make_hours_chart(200, 80, day_values, "#ff0000", "#00ff00", dark=True, era="Showa")
    heisei = make_hours_chart(200, 80, day_values, "#ff0000", "#00ff00", dark=True, era="Heisei")
    reiwa = make_hours_chart(200, 80, day_values, "#ff0000", "#00ff00", dark=True, era="Reiwa")
    assert showa.tobytes() != heisei.tobytes()
    assert heisei.tobytes() != reiwa.tobytes()
    assert showa.tobytes() != reiwa.tobytes()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_visuals.py -k make_hours_chart -v`
Expected: FAIL — `ImportError: cannot import name 'make_hours_chart'`

- [ ] **Step 3: Write the minimal implementation**

In `lock_in/visuals.py`, add `from datetime import date` to the imports
at the top of the file (alongside the existing `import random` /
`import sys` block). Then add this function, placed after
`make_panel_divider` and its `_draw_*_divider` helpers:

```python
def make_hours_chart(
    width: int, height: int, day_values: list[tuple[str, int]],
    primary: str, secondary: str, dark: bool, era: str = "Showa",
) -> Image.Image:
    """
    Draw a simple bar chart: one bar per day, oldest on the left,
    tallest bar for whichever day has the most focused time. The LAST
    entry (today) is drawn in `secondary` instead of `primary`, so it
    stands out from the history behind it.

    `day_values` is `(iso_day, seconds)` pairs, already zero-filled by
    the caller for any day with no focus blocks -- this function never
    has to guess about a missing day, only draw what it's given.

    The era accent along the baseline reuses `make_panel_divider()`
    instead of duplicating its three per-era drawing helpers -- same
    ticks/facets/circuit-nodes look the panel gap already has.
    """
    LABEL_MARGIN = 16
    BAR_GAP = 4
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if not day_values:
        return image

    draw = ImageDraw.Draw(image, "RGBA")
    plot_height = height - LABEL_MARGIN
    r1, g1, b1 = _hex_to_rgb(primary)
    r2, g2, b2 = _hex_to_rgb(secondary)
    bar_color = (r1, g1, b1, 255)
    today_color = (r2, g2, b2, 255)
    label_color = (190, 190, 190, 220) if dark else (90, 90, 90, 220)

    count = len(day_values)
    max_secs = max(secs for _, secs in day_values) or 1
    bar_width = (width - BAR_GAP * (count - 1)) / count

    for index, (iso_day, secs) in enumerate(day_values):
        x0 = round(index * (bar_width + BAR_GAP))
        x1 = round(x0 + bar_width)
        bar_height = plot_height * secs / max_secs
        if bar_height > 0:
            y0 = round(plot_height - bar_height)
            color = today_color if index == count - 1 else bar_color
            draw.rectangle([x0, y0, x1, plot_height], fill=color)

        letter = date.fromisoformat(iso_day).strftime("%a")[0]
        bbox = draw.textbbox((0, 0), letter)
        letter_width = bbox[2] - bbox[0]
        text_x = (x0 + x1) / 2 - letter_width / 2
        draw.text((text_x, plot_height + 5), letter, fill=label_color)

    accent = make_panel_divider(width, 8, primary, secondary, era=era)
    image.alpha_composite(accent, (0, max(plot_height - 4, 0)))

    return image
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_visuals.py -v`
Expected: PASS — all tests, including the 7 new ones and every existing
`visuals.py` test (unaffected).

- [ ] **Step 5: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 4: V3's `build()` — the Hours tab content

**Files:**
- Modify: `lock_in/tier5/v3.py` (add `build()`)
- Modify: `lock_in/tier5/__init__.py` (add `TIER5_BUILDERS`)

**Interfaces:**
- Consumes: `last_14_days`, `_format_hm` (Task 2), `visuals.make_hours_chart`
  (Task 3), `visuals.display_font_family()` (already exists),
  `history.total_seconds_by_day()` and `history.all()` (already exist on
  `HistoryStore`), `theme.primary`, `theme.secondary`, `theme.era`,
  `theme.primary_text_pair` (already exist on `RiderTheme`).
- Produces: `build(parent, *, history, tasks, theme, appearance_mode) -> None`
  in `lock_in.tier5.v3`, registered in `TIER5_BUILDERS["hours_tab"]`.
  Task 5's `ui.py` wiring calls `TIER5_BUILDERS[effect](...)`.

No automated test for this step — it only builds Tk widgets, and this
codebase verifies tab-building methods by running the real app and
looking at them (see `ui.py`'s other `_build_*_tab` methods, none of
which have a unit test either). Task 7 covers manual verification.

- [ ] **Step 1: Add `build()` to `lock_in/tier5/v3.py`**

Append to the bottom of `lock_in/tier5/v3.py`:

```python
def build(parent, *, history, tasks, theme, appearance_mode) -> None:
    """
    Populate `parent` (an empty Tier 5 tab frame) with V3's Hours view:
    a headline number for today, and a 14-day bar chart below it.

    `tasks` and `appearance_mode` are part of every Tier 5 builder's
    signature for consistency across the 10 Riders -- V3 doesn't need
    either. CustomTkinter's own `(light, dark)` color-tuple support and
    `CTkImage(light_image=, dark_image=)` already handle V3's light/dark
    switching without checking `appearance_mode` by hand.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    totals = history.total_seconds_by_day()
    today = date.today()
    headline_seconds = totals.get(today.isoformat(), 0)

    ctk.CTkLabel(
        frame, text=_format_hm(headline_seconds), text_color=theme.primary_text_pair,
        font=ctk.CTkFont(family=visuals.display_font_family(), size=32, weight="bold"),
    ).pack(anchor="w", pady=(4, 0))
    ctk.CTkLabel(
        frame, text="focused today", text_color=theme.primary_text_pair,
    ).pack(anchor="w", pady=(0, 12))

    if not history.all():
        ctk.CTkLabel(
            frame, text="No focus blocks yet. Finish one and it shows up here.",
            justify="left", wraplength=400,
        ).pack(anchor="w", pady=8)
        return

    day_values = [(day.isoformat(), secs) for day, secs in last_14_days(totals, today)]
    light_image = visuals.make_hours_chart(
        440, 200, day_values, theme.primary[0], theme.secondary[0],
        dark=False, era=theme.era,
    )
    dark_image = visuals.make_hours_chart(
        440, 200, day_values, theme.primary[1], theme.secondary[1],
        dark=True, era=theme.era,
    )
    chart_image = ctk.CTkImage(light_image=light_image, dark_image=dark_image, size=(440, 200))
    chart_label = ctk.CTkLabel(frame, text="", image=chart_image)
    # CTkImage is garbage-collected the moment nothing references it,
    # which would blank the label the next time Tk redraws -- stashing
    # it as a plain attribute on the label itself keeps it alive for as
    # long as the label is.
    chart_label._v3_chart_image = chart_image
    chart_label.pack(anchor="w")

    ctk.CTkLabel(
        frame, text="Last 14 days · every focus block counts, finished or not",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
    ).pack(anchor="w", pady=(6, 0))
```

- [ ] **Step 2: Register it in `TIER5_BUILDERS`**

Append to `lock_in/tier5/__init__.py`:

```python

from . import v3

TIER5_BUILDERS = {
    "hours_tab": v3.build,
}
```

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `pytest -v`
Expected: PASS — every test from Tasks 1-3 plus the whole pre-existing
suite. (No new tests in this task; `build()` is manually verified in
Task 7.)

- [ ] **Step 4: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 5: Wire the dynamic tab into `ui.py`

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `RiderTheme.tier5_effect` (Task 1), `TIER5_BUILDERS` (Task 4).
- Produces: `self.current_tier5_effect`, `self._current_rider_theme`,
  `_TIER5_TAB_LABELS`, `self._build_tier5_tab()`. No later task consumes
  these — this is the last task that touches app wiring.

No automated test for this step (see the note in Task 4 — `ui.py`
wiring is manually verified, matching the rest of the file). Task 7
covers manual verification.

- [ ] **Step 1: Import `TIER5_BUILDERS`**

In `lock_in/ui.py`, find this line (around line 58):

```python
from .history import HistoryStore, SessionRecord
```

Add directly after it:

```python
from .tier5 import TIER5_BUILDERS
```

- [ ] **Step 2: Add the tab-label map**

Find the color-constants block near the top of the file (right after the
`COLOR_*` constants, before the `LockInApp` class starts). Add:

```python
# Tier 5's dynamic 6th tab: effect string (RiderTheme.tier5_effect) ->
# what the tab is called. Grows one entry per Rider as each one ships.
_TIER5_TAB_LABELS = {"hours_tab": "Hours"}
```

- [ ] **Step 3: Store the effect and the resolved theme in `_apply_rider_theme()`**

In `_apply_rider_theme()`, find these three lines (around `ui.py:487-495`):

```python
        self.current_tier1_effect = theme.tier1_effect
        # Which Tier 3 gimmick (if any) this Rider has -- read by the
        # goal-gate, zero-UI, lock-overlay, and code-unlock code later
        # in this file.
        self.current_tier3_effect = theme.tier3_effect
        # Which Tier 4 gimmick (if any) this Rider has -- read by the
        # mirror-flip, hidden-timer, dashboard-cards, ghost-widget, and
        # hotkey code later in this file.
        self.current_tier4_effect = theme.tier4_effect
```

Add right after the `self.current_tier4_effect = theme.tier4_effect`
line:

```python
        # Which Tier 5 gimmick (if any) this Rider has -- read by
        # _build_tabs() to decide whether a 6th tab exists at all.
        self.current_tier5_effect = theme.tier5_effect
        # The resolved RiderTheme itself (after ZX's desaturation, if
        # that applied above) -- _build_tier5_tab() needs the actual
        # theme object, not just the derived colors already unpacked
        # onto self above.
        self._current_rider_theme = theme
```

- [ ] **Step 4: Add the tier5 tab to `_build_tabs()`**

Find `_build_tabs()` (around `ui.py:974`):

```python
    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(
            self, height=340,
            fg_color=self.color_surface,
            segmented_button_selected_color=self.color_rider_accent,
            text_color=self.color_button_text,
        )
        self._mpack(self.tabs, fill="both", expand=True, padx=20, pady=(0, 16))

        for name in ("Tasks", "Blocking", "Activity", "Settings", "Help"):
            self.tabs.add(name)

        self._build_tasks_tab(self.tabs.tab("Tasks"))
        self._build_blocking_tab(self.tabs.tab("Blocking"))
        self._build_activity_tab(self.tabs.tab("Activity"))
        self._build_settings_tab(self.tabs.tab("Settings"))
        self._build_help_tab(self.tabs.tab("Help"))
```

Replace it with:

```python
    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(
            self, height=340,
            fg_color=self.color_surface,
            segmented_button_selected_color=self.color_rider_accent,
            text_color=self.color_button_text,
        )
        self._mpack(self.tabs, fill="both", expand=True, padx=20, pady=(0, 16))

        for name in ("Tasks", "Blocking", "Activity", "Settings", "Help"):
            self.tabs.add(name)
        if self.current_tier5_effect != "none":
            self.tabs.add(_TIER5_TAB_LABELS[self.current_tier5_effect])

        self._build_tasks_tab(self.tabs.tab("Tasks"))
        self._build_blocking_tab(self.tabs.tab("Blocking"))
        self._build_activity_tab(self.tabs.tab("Activity"))
        self._build_settings_tab(self.tabs.tab("Settings"))
        self._build_help_tab(self.tabs.tab("Help"))
        if self.current_tier5_effect != "none":
            self._build_tier5_tab()

    def _build_tier5_tab(self) -> None:
        """Fills in whichever Tier 5 tab `_build_tabs()` just added, by
        looking up this Rider's builder in TIER5_BUILDERS. Safe to call
        again later (e.g. from _on_phase_ended) to refresh the tab's
        content in place without rebuilding the other five tabs."""
        label = _TIER5_TAB_LABELS[self.current_tier5_effect]
        frame = self.tabs.tab(label)
        for child in frame.winfo_children():
            child.destroy()
        TIER5_BUILDERS[self.current_tier5_effect](
            frame, history=self.history, tasks=self.tasks,
            theme=self._current_rider_theme, appearance_mode=ctk.get_appearance_mode(),
        )
```

This is why no `hasattr` startup guard is needed (see this plan's
"Deviation from the approved spec" section above): `_build_tabs()`
already only ever runs after `self.tasks`, `self.history`, and
`self.current_tier5_effect` exist, both at startup (`ui.py:343`, well
after `self.tasks`/`self.history` are constructed at `ui.py:273-274`)
and from every `_rebuild_tabs()` call site (`_on_rider_theme_change`,
`_on_standard_mode_toggled`, the wording toggle) — each of those already
calls `_apply_rider_theme()` first.

- [ ] **Step 5: Refresh the Hours tab's content when a focus block ends**

Find `_on_phase_ended()` (around `ui.py:2010`):

```python
        self.observations.save()
        self._log_focus_block_if_any(completed=True)

        self._sync_mirror_layout()
        self._sync_mirror_divider()
```

Add the refresh right after the history write, before the mirror sync
calls:

```python
        self.observations.save()
        self._log_focus_block_if_any(completed=True)

        # V3's Hours tab (and any later Tier 5 Rider reading history)
        # should show this block the moment it's over, not wait for the
        # next Rider change. A no-op for every Rider without a Tier 5 tab.
        if self.current_tier5_effect != "none":
            self._build_tier5_tab()

        self._sync_mirror_layout()
        self._sync_mirror_divider()
```

- [ ] **Step 6: Run the full test suite**

Run: `pytest -v`
Expected: PASS — the whole suite, unchanged in count from Task 4 (this
task adds no new automated tests; see Task 7 for manual verification).

- [ ] **Step 7: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 6: Docs — Help tab entry and README

**Files:**
- Modify: `lock_in/ui.py` (`_build_help_tab`)
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing (pure documentation, no behavior change).
- Produces: nothing consumed by a later task.

- [ ] **Step 1: Add a Help tab section for V3**

In `_build_help_tab()`, find the end of the Tier 4 section and the start
of Strict Camera Monitoring (around `ui.py:1362-1369`):

```python
        body(
            "One more hero, Saber, actually lives in the progress-bar "
            "list above instead -- its bookmark-ribbon shape uses the "
            "exact same picture-drawing code Fourze and Build already do."
        )

        # --- Strict Camera Monitoring ------------------------------------ #
        heading("5. Strict Camera Monitoring (optional)", COLOR_ENFORCE_ACCENT)
```

Insert a new numbered section between them, and renumber the Camera
Monitoring heading from "5." to "6.":

```python
        body(
            "One more hero, Saber, actually lives in the progress-bar "
            "list above instead -- its bookmark-ribbon shape uses the "
            "exact same picture-drawing code Fourze and Build already do."
        )

        # --- Tier 5 -------------------------------------------------------- #
        heading("5. One hero reads your own history", COLOR_ENFORCE_ACCENT)
        body(
            "Something new, separate from the display tricks above: pick "
            "this hero and an extra tab appears next to Help, built from "
            "your own past focus blocks instead of just changing colors "
            "or sounds."
        )
        bullet(
            "V3 — an \"Hours\" tab appears, showing how long you've "
            "focused today plus a bar chart of the last 14 days. Every "
            "block counts toward it, finished or not."
        )
        body(
            "More heroes will get a tab like this over time -- V3 is "
            "just the first."
        )

        # --- Strict Camera Monitoring ------------------------------------ #
        heading("6. Strict Camera Monitoring (optional)", COLOR_ENFORCE_ACCENT)
```

- [ ] **Step 2: Add V3 to README's Kamen Rider theme section**

In `README.md`, find the end of the Tier 4 subsection and the start of
"### Look and feel" (search for `### Tier 4: Alternate display modes`,
then further down `### Look and feel`). Insert a new subsection between
them:

```markdown
### Tier 5: Riders that read your own history

A new kind of Rider gimmick, separate from every tier above: picking one
of these Riders adds a whole new tab next to Help, built from your own
tasks and past focus blocks instead of just changing colors, sounds, or
behavior.

- **V3** — adds an "Hours" tab: a big number showing how long you've
  focused today, plus a simple bar chart of the last 14 days. Every
  block counts toward it, whether you finished it, skipped it, or reset
  it early.

More Riders will read your tasks and history this way over time — V3 is
the first of ten planned.
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: PASS — documentation-only changes, no test should be affected.

- [ ] **Step 4: Commit**

(No commit run here — see Task 1, Step 5.)

---

### Task 7: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire automated test suite**

Run: `pytest -v`
Expected: PASS — every test in the suite, old and new.

- [ ] **Step 2: Manually verify the running app**

Using the `run` skill (or `python main.py` / `run.bat` directly), check:

1. Settings → Kamen Rider theme → pick "Kamen Rider V3 (1973)". An
   "Hours" tab appears after Help.
2. On a fresh install (no `sessions.jsonl` yet), the Hours tab shows
   "0m focused today" and the empty-state message, no chart.
3. Run one short focus block to completion (or skip/reset one early).
   Without leaving the Hours tab's Rider, revisit the Hours tab — the
   headline number and the last bar should reflect that block.
4. Switch Settings → Appearance between light and dark while on the
   Hours tab (or just check both once). The chart's colors and the
   weekday-letter contrast should both look right in each mode.
5. Pick a different Rider (e.g. Kuuga). The Hours tab disappears.
6. Turn on Standard Mode. The Hours tab stays gone even if V3 is still
   selected underneath.
7. Pick V3 again with Standard Mode off. The Hours tab reappears.

- [ ] **Step 3: Report results**

Confirm to the user: full test count and pass/fail, and the outcome of
each manual check above. Do not run any git command — hand over the
commit/tag/push steps as its own message, per this plan's Global
Constraints.
