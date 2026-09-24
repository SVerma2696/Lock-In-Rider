# Tier 6 Wizard (Mouse Gestures) Implementation Plan


**Goal:** When Kamen Rider Wizard (2012) is the picked Rider, holding the right mouse button and drawing a left line, right line, or circle on the Lock In window switches tabs.

**Architecture:** A new pure-math module (`lock_in/wizard_gestures.py`, only `math`) turns a list of mouse points into `"left"`, `"right"`, `"circle"`, or `None`, and picks the target tab. `ui.py` binds the right mouse button on the main window, collects points, and calls that module on release. A new `tier6_effect` field on `RiderTheme` gates it, and a new `mouse_gestures_enabled` config flag (default on) is exposed as a Settings switch shown only for Wizard.

**Tech Stack:** Python 3 stdlib (`math`), CustomTkinter (already used), pytest.

## Global Constraints

Copied from the spec (`docs/superpowers/specs/2026-09-23-tier6-wizard-mouse-gestures-design.md`). Every task implicitly includes these.

- Gestures work **only inside the Lock In window**. No system-wide mouse hook, no new dependency, no new permission.
- Gestures only **navigate tabs**. They must never start, pause, skip, or end a session, or touch tasks, blocking, or settings.
- **No learning, no downloads.** Recognition uses only Python's built-in `math`.
- Left/right go one tab in on-screen order and **never wrap around**. A circle goes to the **first tab (Tasks)**.
- Any unclear stroke does **nothing**, silently. Any exception while recognizing, switching tabs, or drawing the trail is **swallowed**.
- The fading trail is **best-effort**: gestures must work even if the trail fails. If it looks glitchy when checked by eye, remove it rather than hack around it.
- `mouse_gestures_enabled: bool = True`. The Settings switch is **shown only while Wizard is the picked Rider**. Other Riders' Settings tabs stay exactly as they are.
- Version is **2.6.0**.
- Plain, simple wording in every comment, README line, and Help-tab line (a young reader should be able to follow it).
- **No commits, pushes, or tags.** The project owner does all git steps. Do not run `git add`, `git commit`, `git push`, or `git tag`.
- Project files describe the software only: nothing about who or what wrote them.

---

## File Structure

| File | What it does |
|---|---|
| `lock_in/wizard_gestures.py` (new) | Pure math: `recognize()`, `next_tab_name()`, threshold constants. No Tk, no config. |
| `tests/test_wizard_gestures.py` (new) | Tests for the above, no display needed. |
| `lock_in/rider_themes.py` | New `tier6_effect` field; Wizard gets `"mouse_gestures"`. |
| `lock_in/config.py` | New `mouse_gestures_enabled` field. |
| `lock_in/ui.py` | Right-button bindings and handlers, tab-name list, trail dots, Settings switch, Help section. |
| `lock_in/__init__.py` | Version 2.6.0 and one line in the layout docstring. |
| `README.md` | Tier 6 section, file list line. |
| `tests/test_rider_themes.py`, `tests/test_config.py` | Grow, as described in each task. |

---

### Task 1: The gesture math

**Files:**
- Create: `lock_in/wizard_gestures.py`
- Create: `tests/test_wizard_gestures.py`

**Interfaces:**
- Consumes: nothing.
- Produces (used by Task 3):
  - `recognize(points: list[tuple[float, float]]) -> str | None` returning `"left"`, `"right"`, `"circle"`, or `None`.
  - `next_tab_name(tab_names: list[str], current: str, gesture: str | None) -> str | None`.
  - Constants `LEFT = "left"`, `RIGHT = "right"`, `CIRCLE = "circle"`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_wizard_gestures.py`:

```python
import math
import random

from lock_in.wizard_gestures import CIRCLE, LEFT, RIGHT, next_tab_name, recognize


def line(x0, y0, x1, y1, n=20, jitter=0.0):
    """Evenly spaced dots from one spot to another, optionally shaken a bit."""
    rng = random.Random(1)
    return [
        (
            x0 + (x1 - x0) * i / (n - 1) + rng.uniform(-jitter, jitter),
            y0 + (y1 - y0) * i / (n - 1) + rng.uniform(-jitter, jitter),
        )
        for i in range(n)
    ]


def circle(cx, cy, r, n=30, clockwise=True, turns=1.0):
    """Dots around a circle. `turns` below 1 leaves it open."""
    sign = 1 if clockwise else -1
    return [
        (
            cx + r * math.cos(sign * 2 * math.pi * turns * i / (n - 1)),
            cy + r * math.sin(sign * 2 * math.pi * turns * i / (n - 1)),
        )
        for i in range(n)
    ]


# --- recognize(): things that should be understood ------------------------ #

def test_clean_left_line_is_left():
    assert recognize(line(300, 100, 100, 100)) == LEFT


def test_clean_right_line_is_right():
    assert recognize(line(100, 100, 300, 100)) == RIGHT


def test_slightly_tilted_left_line_still_counts():
    assert recognize(line(300, 100, 100, 160)) == LEFT


def test_slightly_shaky_right_line_still_counts():
    assert recognize(line(100, 100, 300, 70, jitter=4)) == RIGHT


def test_clockwise_circle_is_circle():
    assert recognize(circle(200, 200, 60)) == CIRCLE


def test_counter_clockwise_circle_is_circle():
    assert recognize(circle(200, 200, 60, clockwise=False)) == CIRCLE


def test_circle_that_does_not_quite_close_still_counts():
    assert recognize(circle(200, 200, 60, turns=0.95)) == CIRCLE


# --- recognize(): things that should be ignored --------------------------- #

def test_empty_and_single_point_do_nothing():
    assert recognize([]) is None
    assert recognize([(1, 1)]) is None


def test_all_identical_points_do_nothing():
    assert recognize([(5, 5)] * 10) is None


def test_tiny_stroke_does_nothing():
    assert recognize(line(100, 100, 110, 105)) is None


def test_short_line_does_nothing():
    assert recognize(line(100, 100, 140, 100)) is None


def test_diagonal_does_nothing():
    assert recognize(line(100, 100, 250, 250)) is None


def test_vertical_line_does_nothing():
    assert recognize(line(100, 100, 100, 300)) is None


def test_zigzag_does_nothing():
    zigzag = [(100 + i * 10, 100 + (40 if i % 2 else 0)) for i in range(20)]
    assert recognize(zigzag) is None


def test_out_and_back_line_does_nothing():
    out_and_back = line(100, 100, 300, 100, 10) + line(300, 100, 110, 102, 10)
    assert recognize(out_and_back) is None


def test_half_circle_does_nothing():
    assert recognize(circle(200, 200, 60, turns=0.5)) is None


def test_very_small_circle_does_nothing():
    assert recognize(circle(200, 200, 20)) is None


# --- next_tab_name() ------------------------------------------------------- #

TABS = ["Tasks", "Blocking", "Activity", "Settings", "Help"]


def test_left_moves_to_previous_tab():
    assert next_tab_name(TABS, "Activity", LEFT) == "Blocking"


def test_right_moves_to_next_tab():
    assert next_tab_name(TABS, "Activity", RIGHT) == "Settings"


def test_left_on_first_tab_does_nothing():
    assert next_tab_name(TABS, "Tasks", LEFT) is None


def test_right_on_last_tab_does_nothing():
    assert next_tab_name(TABS, "Help", RIGHT) is None


def test_circle_goes_to_first_tab():
    assert next_tab_name(TABS, "Settings", CIRCLE) == "Tasks"


def test_extra_rider_tab_at_the_end_counts_as_a_tab():
    tabs = TABS + ["Priority"]
    assert next_tab_name(tabs, "Help", RIGHT) == "Priority"
    assert next_tab_name(tabs, "Priority", RIGHT) is None


def test_unknown_gesture_or_tab_does_nothing():
    assert next_tab_name(TABS, "Activity", None) is None
    assert next_tab_name(TABS, "Activity", "up") is None
    assert next_tab_name(TABS, "Nope", LEFT) is None
    assert next_tab_name([], "Tasks", LEFT) is None
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `python -m pytest tests/test_wizard_gestures.py -q`
Expected: collection error / `ModuleNotFoundError: No module named 'lock_in.wizard_gestures'`.

- [ ] **Step 3: Write the module**

Create `lock_in/wizard_gestures.py`:

```python
"""
wizard_gestures.py
===================
Kamen Rider Wizard's whole trick, in plain math. While you hold the right
mouse button and drag on the Lock In window, the app writes down where the
mouse went. When you let go, this file looks at that list of dots and
decides: did you draw a line to the left, a line to the right, a circle,
or just wiggle around?

Nothing in here touches the window, the mouse, or the disk. It gets a list
of (x, y) dots in and hands one word back. That is on purpose: it means
every rule below can be tested without opening the app.

There is nothing to download or train. It only measures
distances with Python's built-in `math`, so the same drawing always gets
the same answer.

The numbers below are in "pixels" (the tiny dots on your screen). Each
one has a comment saying what it means in plain words, so you can change
one and see what happens.
"""

from __future__ import annotations

import math

# A drawing needs at least this many dots before we even look at it.
MIN_POINTS = 5
# If the whole drawing fits in a box smaller than this on both sides, it
# was just a wiggle or a click, so we ignore it.
MIN_STROKE_PIXELS = 30

# A left/right line has to go at least this far sideways.
MIN_SWIPE_PIXELS = 60
# How much up-and-down is allowed, compared with sideways. 0.5 means "up
# to half as much up-and-down as sideways": a slightly tilted line is
# fine, a diagonal is not.
MAX_SWIPE_SLOPE = 0.5
# How wobbly a line may be. The path the mouse walked may be at most this
# many times longer than the straight distance from start to end.
MAX_SWIPE_WIGGLE = 1.3

# A circle's box must be at least this big on both sides.
MIN_CIRCLE_PIXELS = 50
# The end of a circle has to come back near its start: at most this
# fraction of the drawing's biggest side away.
CIRCLE_CLOSE_FRACTION = 0.35
# A circle's box is roughly square: the longer side may be at most this
# many times the shorter side.
CIRCLE_MAX_ASPECT = 2.0
# A circle really went around: the path walked must be at least this many
# times the drawing's biggest side. (A perfect circle is about 3.1 times.)
CIRCLE_MIN_PATH_RATIO = 2.5

LEFT = "left"
RIGHT = "right"
CIRCLE = "circle"


def _path_length(points) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def recognize(points) -> str | None:
    """
    Turn the dots you drew into "left", "right", "circle", or None.

    None means "not sure" -- and when the app isn't sure it does nothing
    at all, so a wobbly drag never causes a surprise.
    """
    if len(points) < MIN_POINTS:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    biggest = max(width, height)
    smallest = min(width, height)
    if biggest < MIN_STROKE_PIXELS:
        return None

    path = _path_length(points)
    start, end = points[0], points[-1]

    # Circle: comes back near where it started, roughly square, went around.
    if (
        smallest >= MIN_CIRCLE_PIXELS
        and math.dist(start, end) <= CIRCLE_CLOSE_FRACTION * biggest
        and biggest <= CIRCLE_MAX_ASPECT * smallest
        and path >= CIRCLE_MIN_PATH_RATIO * biggest
    ):
        return CIRCLE

    # Swipe: mostly sideways, long enough, and mostly straight.
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if (
        abs(dx) >= MIN_SWIPE_PIXELS
        and abs(dy) <= MAX_SWIPE_SLOPE * abs(dx)
        and path <= MAX_SWIPE_WIGGLE * math.hypot(dx, dy)
    ):
        return LEFT if dx < 0 else RIGHT

    return None


def next_tab_name(tab_names, current, gesture) -> str | None:
    """
    Given the tabs in the order they're shown, which tab you're on, and
    what you drew, say which tab to go to -- or None to stay put.

    Left and right move one tab and never wrap around. A circle goes to
    the first tab.
    """
    if not tab_names or current not in tab_names:
        return None
    index = tab_names.index(current)
    if gesture == CIRCLE:
        return tab_names[0]
    if gesture == LEFT:
        return tab_names[index - 1] if index > 0 else None
    if gesture == RIGHT:
        return tab_names[index + 1] if index < len(tab_names) - 1 else None
    return None
```

- [ ] **Step 4: Run the tests and see them pass**

Run: `python -m pytest tests/test_wizard_gestures.py -q`
Expected: all pass (about 24 tests). These exact numbers were checked against the same shapes in advance; if a test fails, fix the code or constant, not the test's shape, and tell the reviewer.

---

### Task 2: The `tier6_effect` field and the config flag

**Files:**
- Modify: `lock_in/rider_themes.py` (dataclass around line 116-125, Wizard entry around line 297)
- Modify: `lock_in/config.py` (after `camera_monitoring_enabled`, around line 171)
- Modify: `tests/test_rider_themes.py` (append)
- Modify: `tests/test_config.py` (append)

**Interfaces:**
- Consumes: nothing.
- Produces (used by Task 3): `RiderTheme.tier6_effect: str = "none"`; Wizard's value `"mouse_gestures"`; `Config.mouse_gestures_enabled: bool = True`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rider_themes.py`:

```python
def test_tier6_effect_defaults_to_none():
    from lock_in.rider_themes import RiderTheme
    theme = RiderTheme("Heisei", 2000, ("#000000", "#ffffff"), ("#111111", "#eeeeee"))
    assert theme.tier6_effect == "none"


def test_only_wizard_has_a_tier6_effect():
    from lock_in.rider_themes import RIDER_THEMES
    assert RIDER_THEMES["Kamen Rider Wizard (2012)"].tier6_effect == "mouse_gestures"
    tier6_riders = {n for n, t in RIDER_THEMES.items() if t.tier6_effect != "none"}
    assert tier6_riders == {"Kamen Rider Wizard (2012)"}


def test_standard_theme_has_no_tier6_effect():
    from lock_in.rider_themes import STANDARD_THEME
    assert STANDARD_THEME.tier6_effect == "none"
```

Append to `tests/test_config.py`:

```python
def test_mouse_gestures_default_to_on():
    assert Config().mouse_gestures_enabled is True


def test_mouse_gestures_setting_round_trips_through_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    Config(mouse_gestures_enabled=False).save(path)
    assert Config.load(path).mouse_gestures_enabled is False


def test_old_settings_file_without_mouse_gestures_loads_as_on(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"focus_minutes": 30}', encoding="utf-8")
    loaded = Config.load(path)
    assert loaded.focus_minutes == 30
    assert loaded.mouse_gestures_enabled is True
```

- [ ] **Step 2: Run them and see them fail**

Run: `python -m pytest tests/test_rider_themes.py tests/test_config.py -q`
Expected: the six new tests fail (`AttributeError`/`TypeError` for the missing fields).

- [ ] **Step 3: Add the theme field**

In `lock_in/rider_themes.py`, directly after the `tier5_effect: str = "none"` line, add:

```python
    # "none" for every Rider except Wizard, the first of Tier 6's two
    # "new infrastructure" Riders (see
    # docs/superpowers/specs/2026-09-23-tier6-wizard-mouse-gestures-design.md).
    # ui.py reads this to decide whether right-button mouse gestures
    # (draw a line left or right, or a circle, to switch tabs) are
    # listened for at all. lock_in/wizard_gestures.py does the drawing math.
    tier6_effect: str = "none"
```

Change the Wizard entry from:

```python
    "Kamen Rider Wizard (2012)": RiderTheme(
        "Heisei", 2012, ("#9c1e1e", "#ef5350"), ("#1a1a1a", "#757575"),
    ),
```

to:

```python
    "Kamen Rider Wizard (2012)": RiderTheme(
        "Heisei", 2012, ("#9c1e1e", "#ef5350"), ("#1a1a1a", "#757575"),
        tier6_effect="mouse_gestures",
    ),
```

- [ ] **Step 4: Add the config flag**

In `lock_in/config.py`, directly after `camera_monitoring_enabled: bool = False`, add:

```python

    # Wizard's mouse gestures: while Kamen Rider Wizard is the picked
    # Rider, holding the right mouse button and drawing a line left or
    # right (or a circle) on the Lock In window switches tabs. This
    # switch turns that off without changing your Rider. On by default.
    # It only ever watches the mouse inside the Lock In window itself.
    mouse_gestures_enabled: bool = True
```

- [ ] **Step 5: Run the tests and see them pass**

Run: `python -m pytest tests/test_rider_themes.py tests/test_config.py -q`
Expected: all pass.

---

### Task 3: Wire it into the window

**Files:**
- Modify: `lock_in/ui.py`
  - imports (~line 66)
  - `_apply_rider_theme()` (~line 526)
  - `__init__` bindings (~lines 373-375)
  - `_build_tabs()` (~lines 1211-1228)
  - Settings tab (~lines 1766-1771)
  - `_save_from_widgets()` (~lines 2850-2863)
  - Help tab (~lines 1601-1700)
  - new handler methods (next to `_on_zeztz_reset`, ~line 2535)

**Interfaces:**
- Consumes: `recognize`, `next_tab_name` (Task 1); `RiderTheme.tier6_effect`, `Config.mouse_gestures_enabled` (Task 2).
- Produces: nothing later tasks use.

There is no automated GUI test for `ui.py` in this project (see the spec's Testing section), so this task is checked by the full test suite plus the manual checklist in Task 4. Read each surrounding block before editing so the new code matches its style.

- [ ] **Step 1: Import**

Next to `from .tier5 import TIER5_BUILDERS` add:

```python
from .wizard_gestures import next_tab_name, recognize
```

- [ ] **Step 2: Remember the Rider's Tier 6 effect**

In `_apply_rider_theme()`, right after `self.current_tier5_effect = theme.tier5_effect`, add:

```python
        # Which Tier 6 gimmick (if any) this Rider has -- read by the
        # Wizard mouse-gesture handlers below. Standard Mode swaps in
        # STANDARD_THEME above, so this reads "none" there automatically.
        self.current_tier6_effect = theme.tier6_effect
```

- [ ] **Step 3: Keep a list of tab names, in order**

In `_build_tabs()`, replace:

```python
        for name in ("Tasks", "Blocking", "Activity", "Settings", "Help"):
            self.tabs.add(name)
        if self.current_tier5_effect != "none":
            self.tabs.add(_TIER5_TAB_LABELS[self.current_tier5_effect])
```

with:

```python
        self._tab_names = ["Tasks", "Blocking", "Activity", "Settings", "Help"]
        if self.current_tier5_effect != "none":
            self._tab_names.append(_TIER5_TAB_LABELS[self.current_tier5_effect])
        for name in self._tab_names:
            self.tabs.add(name)
```

- [ ] **Step 4: Bind the right mouse button once, at startup**

In `__init__`, right after the three `self.bind_all("<space>"...)`, `("s"...)`, `("r"...)` lines, add:

```python
        # Wizard's mouse gestures. Bound once here; each handler checks
        # for itself whether Wizard is picked and the switch is on, so
        # changing Rider later needs no re-binding. add="+" keeps any
        # other binding on the window working.
        self._wizard_points: list = []
        self._wizard_last_dot = None
        self.bind("<ButtonPress-3>", self._on_wizard_press, add="+")
        self.bind("<B3-Motion>", self._on_wizard_motion, add="+")
        self.bind("<ButtonRelease-3>", self._on_wizard_release, add="+")
```

- [ ] **Step 5: Add the handlers**

Add these methods to `LockInApp`, directly after `_on_zeztz_reset` (the last of the Zeztz handlers, just before `_on_appearance_change`):

```python
    # ------------------------------------------------------------------ #
    # Wizard's mouse gestures (see lock_in/wizard_gestures.py)
    # ------------------------------------------------------------------ #
    def _wizard_listening(self, event) -> bool:
        """True only while Wizard is picked, the Settings switch is on,
        and the mouse event happened in THIS window (not, say, the
        lockdown screen)."""
        try:
            return (
                self.current_tier6_effect == "mouse_gestures"
                and self.config_obj.mouse_gestures_enabled
                and event.widget.winfo_toplevel() is self
            )
        except Exception:
            return False

    def _on_wizard_press(self, event) -> None:
        self._wizard_points = []
        self._wizard_last_dot = None
        if self._wizard_listening(event):
            self._wizard_points.append((event.x_root, event.y_root))

    def _on_wizard_motion(self, event) -> None:
        # An empty list means the press wasn't one we're listening to.
        if not self._wizard_points or not self._wizard_listening(event):
            return
        self._wizard_points.append((event.x_root, event.y_root))
        self._wizard_draw_trail_dot(event)

    def _on_wizard_release(self, event) -> None:
        points, self._wizard_points = self._wizard_points, []
        if not points:
            return
        # Any surprise in here means "do nothing" -- a gesture is a
        # nice-to-have shortcut, never worth an error.
        try:
            if not self._wizard_listening(event):
                return
            gesture = recognize(points)
            target = next_tab_name(self._tab_names, self.tabs.get(), gesture)
            if target:
                self.tabs.set(target)
        except Exception:
            pass

    def _wizard_draw_trail_dot(self, event) -> None:
        """The little fading trail. Best-effort only: recognizing and
        switching tabs never depend on it, so any problem drawing it is
        silently ignored."""
        try:
            x = event.x_root - self.winfo_rootx()
            y = event.y_root - self.winfo_rooty()
            last = self._wizard_last_dot
            if last is not None and abs(x - last[0]) < 10 and abs(y - last[1]) < 10:
                return
            self._wizard_last_dot = (x, y)
            dot = ctk.CTkFrame(self, width=6, height=6, corner_radius=3,
                               fg_color=self.color_rider_accent)
            dot.place(x=x - 3, y=y - 3)
            self.after(400, lambda d=dot: self._wizard_remove_dot(d))
        except Exception:
            pass

    def _wizard_remove_dot(self, dot) -> None:
        try:
            dot.destroy()
        except Exception:
            pass
```

- [ ] **Step 6: The Settings switch (Wizard only)**

In `_build_settings_tab()`, directly after the `check_updates_var` switch block (the one ending `command=self._save_from_widgets), anchor="w", pady=4)` for "Automatically check for updates"), add:

```python
        # Wizard's switch only shows up while Wizard is the picked Rider,
        # so every other Rider's Settings tab stays exactly as it was.
        self.gestures_var = None
        if self.current_tier6_effect == "mouse_gestures":
            self.gestures_var = ctk.BooleanVar(value=self.config_obj.mouse_gestures_enabled)
            self._mpack(ctk.CTkSwitch(
                frame, text="Mouse gestures (right-drag: left/right/circle)",
                variable=self.gestures_var, progress_color=COLOR_LOOK_ACCENT,
                command=self._save_from_widgets), anchor="w", pady=4)
```

In `_save_from_widgets()`, inside the existing `if hasattr(self, "autobreak_var"):` block, after `c.check_for_updates = self.check_updates_var.get()`, add:

```python
            if getattr(self, "gestures_var", None) is not None:
                c.mouse_gestures_enabled = self.gestures_var.get()
```

- [ ] **Step 7: Help tab section**

In the Help tab builder, directly after the Tier 5 section's closing `body("All ten Tier 5 heroes are built now -- ...")` call and before the `# --- Strict Camera Monitoring` comment, add:

```python
        # --- Tier 6 -------------------------------------------------------- #
        heading("6. A hero that listens to your mouse", COLOR_ENFORCE_ACCENT)
        bullet(
            "Wizard — hold the right mouse button and draw on this "
            "window. A line to the left goes back one tab. A line to the "
            "right goes forward one tab. A circle jumps to the first "
            "tab, Tasks. It only works inside this window, it only "
            "changes tabs, and if it isn't sure what you drew, it does "
            "nothing. You can turn it off with the \"Mouse gestures\" "
            "switch in Settings."
        )
```

Then renumber the two headings after it: `"6. Strict Camera Monitoring (optional)"` becomes `"7. Strict Camera Monitoring (optional)"`, and `"7. Version"` becomes `"8. Version"`. Run `grep -rn "6. Strict\|7. Version" lock_in tests README.md` first; if anything else quotes those numbers, update it to match.

- [ ] **Step 8: Confirm nothing broke**

Run: `python -m pytest -q`
Expected: everything passes (627 existing tests plus the new ones).

Run: `python -c "import lock_in.ui"`
Expected: no output, no error.

- [ ] **Step 9: Try it in the running app**

Run: `python main.py`, pick Kamen Rider Wizard (2012) in Settings, then check the manual list in Task 4, Step 5. If the trail dots look clipped, flicker, or sit behind widgets, delete `_wizard_draw_trail_dot`, `_wizard_remove_dot`, the `_wizard_last_dot` lines, and the call to `_wizard_draw_trail_dot(event)`, and tell the reviewer the trail was dropped per the spec. If they look fine, leave them.

---

### Task 4: Docs, version, checks, and the git hand-off

**Files:**
- Modify: `lock_in/__init__.py`
- Modify: `README.md`
- Check only: `.gitignore`

**Interfaces:** none.

- [ ] **Step 1: Version and layout docstring**

In `lock_in/__init__.py`, change `__version__ = "2.5.9"` to `__version__ = "2.6.0"`, and in the "Package layout" list add a line in the same column style, after the `rider_themes.py` line:

```
    wizard_gestures.py  mouse-gesture recognizer for Wizard  (no deps, pure logic)
```

(If the column alignment looks off against the existing lines, adjust spacing to match. The docstring's "first five modules import nothing outside the standard library" sentence is left alone.)

- [ ] **Step 2: README, file list**

In the file-tree block (around line 194), add a line under `rider_themes.py` in the same style:

```
│   ├── wizard_gestures.py      Draws-a-line-or-circle math for Wizard's mouse gestures.
```

and under `test_rider_themes.py` (around line 230) a matching line for `test_wizard_gestures.py`, copying the exact tree characters and column spacing of its neighbors.

- [ ] **Step 3: README, Tier 6 section**

Directly after the line `All ten Tier 5 Riders now read your tasks and history this way.`, add:

```markdown
### Tier 6: Riders that add something new

The last two Riders do things no earlier Rider does. The first one is
built:

- **Wizard** — you can now move between tabs with your mouse, like
  drawing a magic spell. Hold the **right mouse button** and drag on the
  Lock In window:
  - Draw a line to the **left** to go back one tab.
  - Draw a line to the **right** to go forward one tab.
  - Draw a **circle** to jump to the first tab (Tasks).

  A quick right-click does nothing, and if the app isn't sure what you
  drew, it does nothing too. A thin trail follows your mouse while you
  draw and fades away. Gestures only ever change tabs — they can't start,
  pause, or end a focus block. They only work inside the Lock In window;
  the app never watches your mouse anywhere else on your computer, and
  nothing is recorded or sent anywhere. When Wizard is your Rider, a
  "Mouse gestures" switch appears in Settings (on by default) if you'd
  rather turn it off.

The other one, Revice, is still to come.
```

- [ ] **Step 4: `.gitignore` check**

Wizard writes no new file. Run `git status --short` and confirm only the expected files show up (listed at the end of this task) and no stray output files. If something unexpected appears (a cache folder, a log), add its pattern to `.gitignore` with a one-line plain comment; otherwise change nothing.

- [ ] **Step 5: Full verification**

Run: `python -m pytest -q`
Expected: all pass. Report the exact final count.

Then by hand in `python main.py` (this is the only test of `ui.py`):
- With Wizard picked, a "Mouse gestures" switch shows in Settings; with any other Rider, it does not.
- Right-drag left/right moves exactly one tab; on the first tab a left drag and on the last tab a right drag do nothing.
- A circle goes to Tasks.
- A plain right-click, a tiny drag, a diagonal drag, and a squiggle all do nothing.
- Turning the switch off stops gestures at once; turning it on brings them back, without restarting.
- Pick another Rider: gestures stop and the switch disappears. Pick Wizard again: the switch is back with the choice you left it on.
- Standard Mode on: gestures stop. Off again: they return.
- The trail follows the mouse and fades, or has been removed per Task 3, Step 9.
- Light and dark mode both look right.
- A gesture never touches the timer, a running focus block, or tasks.

- [ ] **Step 6: Hand-off (do not run these; give them to the project owner)**

Expected changed files, for the owner to double-check with `git status`:

```
modified:   README.md
modified:   lock_in/__init__.py
modified:   lock_in/config.py
modified:   lock_in/rider_themes.py
modified:   lock_in/ui.py
modified:   tests/test_config.py
modified:   tests/test_rider_themes.py
new file:   docs/superpowers/plans/2026-09-23-tier6-wizard-mouse-gestures.md
new file:   docs/superpowers/specs/2026-09-23-tier6-wizard-mouse-gestures-design.md
new file:   lock_in/wizard_gestures.py
new file:   tests/test_wizard_gestures.py
```

The owner's steps:

```bash
git status
git add -A
git commit -m "v2.6.0: add Wizard (Tier 6 Rider 1, right-button mouse gestures)"
git push origin main
git tag v2.6.0
git push origin v2.6.0
```

The commit message is plain: no trailer, no credit line.

---

## Self-review against the spec

- **Gestures and rules** (left/right/circle, no wrap, circle → Tasks, ignore unclear): Task 1 (`recognize`, `next_tab_name`) with tests for every ignore case the spec lists.
- **Only in-window, only navigation, no new dependency**: Task 3 binds on the main window only and checks `winfo_toplevel() is self`; only `math` is imported in Task 1.
- **Settings switch, default on, Wizard-only, remembered across Riders, instant effect, Standard Mode off**: Task 2 (config) and Task 3 Steps 2, 5, 6 (the switch is read fresh in `_wizard_listening`; Standard Mode masks the theme so `tier6_effect` is `"none"`).
- **`tier6_effect` field and Wizard's value**: Task 2.
- **Best-effort fading trail, droppable**: Task 3 Steps 5 and 9.
- **Fail-silent error handling, lockdown window ignored**: Task 3 Step 5.
- **Tests for recognition, themes, config; manual UI checklist**: Tasks 1, 2, 4.
- **README, Help tab, version 2.6.0, `.gitignore` check, no git actions, no credit lines**: Tasks 3 and 4, plus Global Constraints.
- **Names used across tasks match**: `recognize`, `next_tab_name`, `LEFT`/`RIGHT`/`CIRCLE`, `tier6_effect`, `mouse_gestures_enabled`, `current_tier6_effect`, `_tab_names`, `gestures_var`.
