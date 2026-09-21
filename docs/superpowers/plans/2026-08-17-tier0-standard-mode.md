# Tier 0: Standard Mode Implementation Plan

**Goal:** Add a single Settings-tab switch, "Standard Mode," that strips every Kamen Rider's color, art, and Tier 1/2/3 gimmick down to a plain, fast, generic grey-and-blue timer — without touching or forgetting the Rider/Wording you actually have picked.

**Architecture:** `_apply_rider_theme()` in `ui.py` is already the single place every Tier 1/3 gimmick reads its behavior from (`self.current_tier1_effect`, `self.current_tier3_effect`). Standard Mode substitutes a new, real `RiderTheme` instance (`STANDARD_THEME`, `tier1_effect="none"`, `tier3_effect="none"`) for whichever Rider is actually selected — every color, text-contrast pair, and effect flag that method computes falls out of that substitution automatically, with no separate "disable" step required anywhere. The one place that reads `rider_theme` directly instead of going through that method (the Tier 2 preset-button block in Settings) gets one explicit guard. A new `make_flat_fill()` helper replaces the textured Pillow art with a plain solid fill only while Standard Mode is active.

**Tech Stack:** Python 3.11+, CustomTkinter, Pillow — same as the rest of this project. No new dependencies.

## Global Constraints

- No git commands anywhere in this plan — every git step runs manually, at the end, after all tasks are marked complete.
- New code comments stay plain-English and explain *why*, not *what* — match the existing voice in `rider_themes.py`, `visuals.py`, and `config.py`.
- TDD throughout: a failing test before each piece of new pure-logic code (`Config.standard_mode`, `STANDARD_THEME`, `make_flat_fill`). `ui.py` wiring has no automated GUI test in this codebase — it's verified by screenshotting the real running app, same as every prior tier.
- Every new/changed value in Settings must be wording-aware where the surrounding code already is (`self._is_tokusatsu()`), and must never overwrite `rider_theme` or `terminology` — only change what gets read.
- Palette: primary (slate grey) `("#475569", "#94a3b8")`, secondary (blue) `("#1c7ed6", "#4dabf7")` — exact values, copied from the approved spec.

---

### Task 1: `Config.standard_mode` field

**Files:**
- Modify: `lock_in/config.py:132-140` (the existing override-flag cluster)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config.standard_mode: bool` (default `False`), a plain dataclass field — read directly by `ui.py` in later tasks, no `effective_*()` method needed (unlike `zero_grace_mode`/`stealth_mute_mode`, nothing outside `ui.py` needs to read this one).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py`:

```python
def test_standard_mode_defaults_to_off():
    assert Config().standard_mode is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_standard_mode_defaults_to_off -v`
Expected: FAIL with `AttributeError: 'Config' object has no attribute 'standard_mode'`

- [ ] **Step 3: Add the field**

In `lock_in/config.py`, right after `stealth_mute_mode` (line 140):

```python
    # Tier 0's kill switch: while this is on, _apply_rider_theme() in
    # ui.py swaps in the neutral STANDARD_THEME instead of whichever
    # Rider is picked below, and Wording reads as Professional no matter
    # what the switch says. Same non-destructive, read-side pattern as
    # the three flags above -- rider_theme and terminology are never
    # overwritten, so turning this back off instantly restores both.
    standard_mode: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_standard_mode_defaults_to_off -v`
Expected: PASS

- [ ] **Step 5: Run the full test file to check nothing else broke**

Run: `pytest tests/test_config.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add lock_in/config.py tests/test_config.py
git commit -m "Add Config.standard_mode field for Tier 0"
```

---

### Task 2: `STANDARD_THEME` constant

**Files:**
- Modify: `lock_in/rider_themes.py` (add after the `RIDER_THEMES` dict and `DEFAULT_RIDER_THEME`, around line 324)
- Test: `tests/test_rider_themes.py`

**Interfaces:**
- Consumes: the existing `RiderTheme` dataclass (fields: `era: str`, `year: int`, `primary: tuple[str, str]`, `secondary: tuple[str, str]`, `tier1_effect: str = "none"`, `tier3_effect: str = "none"`, plus its computed properties `primary_pair`, `secondary_pair`, `surface_pair`, `primary_text_pair`, `secondary_text_pair`, `button_text_pair`).
- Produces: `STANDARD_THEME: RiderTheme` — a module-level constant, importable from `lock_in.rider_themes`, deliberately **not** a member of `RIDER_THEMES`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rider_themes.py` (needs `STANDARD_THEME` in the top-of-file import):

```python
from lock_in.rider_themes import (
    DEFAULT_RIDER_THEME,
    RIDER_THEMES,
    STANDARD_THEME,
    darken,
    lighten,
    readable_text_color,
)
```

```python
def test_standard_theme_is_not_one_of_the_38_riders():
    """STANDARD_THEME lives outside RIDER_THEMES on purpose -- it isn't a
    Kamen Rider costume, it's Tier 0's neutral baseline."""
    assert STANDARD_THEME not in RIDER_THEMES.values()
    assert len(RIDER_THEMES) == 38  # unchanged by adding this constant


def test_standard_theme_has_no_tier_1_or_tier_3_effect():
    assert STANDARD_THEME.tier1_effect == "none"
    assert STANDARD_THEME.tier3_effect == "none"


def test_standard_theme_uses_the_approved_neutral_palette():
    assert STANDARD_THEME.primary == ("#475569", "#94a3b8")
    assert STANDARD_THEME.secondary == ("#1c7ed6", "#4dabf7")


def test_standard_theme_passes_the_same_contrast_check_every_rider_does():
    """Same shape as test_primary_text_pair_is_readable_against_its_own_surface_both_modes
    below, just for this one theme -- it gets the identical color-math
    guarantees every real Rider gets, for free, from the dataclass."""
    light_text, dark_text = STANDARD_THEME.primary_text_pair
    light_surface, dark_surface = STANDARD_THEME.surface_pair
    assert abs(_brightness(light_text) - _brightness(light_surface)) > 150
    assert abs(_brightness(dark_text) - _brightness(dark_surface)) > 150
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rider_themes.py -k standard_theme -v`
Expected: FAIL with `ImportError: cannot import name 'STANDARD_THEME'`

- [ ] **Step 3: Add the constant**

In `lock_in/rider_themes.py`, right after the `RIDER_THEMES` dict closes and after `DEFAULT_RIDER_THEME` (currently lines 320-324):

```python
# Tier 0's baseline: NOT one of the 38 Kamen Rider costumes above, and
# deliberately kept out of RIDER_THEMES (see this file's own docstring —
# that dict is specifically "a big list of Kamen Rider costume colors").
# Reuses the same RiderTheme dataclass purely for its color math
# (surface tinting, contrast-safe text pairs) -- Standard Mode gets
# those guarantees for free instead of duplicating them.
STANDARD_THEME = RiderTheme(
    "Standard", 0, ("#475569", "#94a3b8"), ("#1c7ed6", "#4dabf7"),
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rider_themes.py -k standard_theme -v`
Expected: PASS

- [ ] **Step 5: Run the full test file to check nothing else broke**

Run: `pytest tests/test_rider_themes.py -v`
Expected: all PASS (including the existing `test_has_all_38_riders` — unaffected, since `STANDARD_THEME` was never added to the dict)

- [ ] **Step 6: Commit**

```bash
git add lock_in/rider_themes.py tests/test_rider_themes.py
git commit -m "Add STANDARD_THEME constant for Tier 0"
```

---

### Task 3: `make_flat_fill()` helper

**Files:**
- Modify: `lock_in/visuals.py` (add near `make_glow`, e.g. right after it, around line 86)
- Test: `tests/test_visuals.py`

**Interfaces:**
- Consumes: the existing `_hex_to_rgb(hex_color: str) -> tuple[int, int, int]` private helper already in `visuals.py`.
- Produces: `make_flat_fill(width: int, height: int, hex_color: str, alpha: int = 255) -> Image.Image` — an `RGBA` Pillow image, one solid color throughout, at the given opacity.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_visuals.py` (needs `make_flat_fill` in the top-of-file import):

```python
from lock_in.visuals import (
    APP_ICON_PATH,
    display_font_family,
    load_app_icon,
    make_background_texture,
    make_flat_fill,
    make_glow,
    make_panel_divider,
)
```

```python
def test_make_flat_fill_returns_the_requested_size():
    image = make_flat_fill(100, 60, "#ff0000")
    assert image.size == (100, 60)
    assert image.mode == "RGBA"


def test_make_flat_fill_is_the_same_solid_color_everywhere():
    image = make_flat_fill(50, 50, "#336699")
    corner = image.getpixel((0, 0))
    center = image.getpixel((25, 25))
    assert corner == center == (0x33, 0x66, 0x99, 255)


def test_make_flat_fill_defaults_to_fully_opaque():
    image = make_flat_fill(10, 10, "#000000")
    assert image.getpixel((5, 5))[3] == 255


def test_make_flat_fill_supports_full_transparency():
    """Standard Mode uses alpha=0 in place of a real glow -- no soft
    light behind the timer digits or the Start button at all."""
    image = make_flat_fill(20, 20, "#000000", alpha=0)
    assert image.getpixel((10, 10))[3] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_visuals.py -k make_flat_fill -v`
Expected: FAIL with `ImportError: cannot import name 'make_flat_fill'`

- [ ] **Step 3: Add the function**

In `lock_in/visuals.py`, right after `make_glow` (after line 85):

```python
def make_flat_fill(width: int, height: int, hex_color: str, alpha: int = 255) -> Image.Image:
    """
    Make one plain, solid-colored picture — no pattern, no gradient, no
    glow. Standard Mode uses this in place of the textured art every
    Kamen Rider theme gets: a single solid fill is virtually free to
    draw, which is the actual point of a "lightweight, vanilla" mode.
    `alpha=0` makes a fully see-through picture, the same size a real
    glow would have been, used where Standard Mode wants no glow at all.
    """
    r, g, b = _hex_to_rgb(hex_color)
    return Image.new("RGBA", (width, height), (r, g, b, alpha))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_visuals.py -k make_flat_fill -v`
Expected: PASS

- [ ] **Step 5: Run the full test file to check nothing else broke**

Run: `pytest tests/test_visuals.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add lock_in/visuals.py tests/test_visuals.py
git commit -m "Add make_flat_fill() helper for Tier 0"
```

---

### Task 4: Wire `_apply_rider_theme()` to Standard Mode

**Files:**
- Modify: `lock_in/ui.py` (imports near the top, and inside `_apply_rider_theme()`, currently lines 243-368)

**Interfaces:**
- Consumes: `Config.standard_mode` (Task 1), `STANDARD_THEME` (Task 2), `make_flat_fill()` (Task 3).
- Produces: no new public interface — this task makes `self.current_tier1_effect`, `self.current_tier3_effect`, `self.color_focus`, `self.color_rider_accent`, `self.color_surface`, and every Pillow-rendered image on screen correctly reflect Standard Mode whenever `self.config_obj.standard_mode` is `True`.

No automated test for this task — it's `ui.py` wiring, verified manually via screenshot in Task 7, consistent with how every prior tier's UI wiring was verified in this codebase (no display server in the unit test suite).

- [ ] **Step 1: Add the two new imports**

In `lock_in/ui.py`, change:

```python
from .rider_themes import DEFAULT_RIDER_THEME, RIDER_THEMES, desaturate
```

to:

```python
from .rider_themes import DEFAULT_RIDER_THEME, RIDER_THEMES, STANDARD_THEME, desaturate
```

And change:

```python
from .visuals import (
    SHAPE_EFFECTS,
    apply_gaim_lock_overlay,
    apply_tier1_background_effect,
    display_font_family,
    ease_drive_progress,
    interpolate_agito_color,
    load_app_icon,
    make_background_texture,
    make_glow,
    make_panel_divider,
    render_amazon_drain,
    render_progress,
)
```

to:

```python
from .visuals import (
    SHAPE_EFFECTS,
    apply_gaim_lock_overlay,
    apply_tier1_background_effect,
    display_font_family,
    ease_drive_progress,
    interpolate_agito_color,
    load_app_icon,
    make_background_texture,
    make_flat_fill,
    make_glow,
    make_panel_divider,
    render_amazon_drain,
    render_progress,
)
```

- [ ] **Step 2: Substitute the theme**

In `_apply_rider_theme()`, change:

```python
        theme = RIDER_THEMES.get(
            self.config_obj.rider_theme, RIDER_THEMES[DEFAULT_RIDER_THEME]
        )
```

to:

```python
        theme = STANDARD_THEME if self.config_obj.standard_mode else RIDER_THEMES.get(
            self.config_obj.rider_theme, RIDER_THEMES[DEFAULT_RIDER_THEME]
        )
```

Everything below this line already reads from `theme` (`primary_pair`, `surface_pair`, `primary_text_pair`, `era`, `tier1_effect`, `tier3_effect`, and so on) — substituting `STANDARD_THEME` here is what makes `self.current_tier1_effect`/`self.current_tier3_effect` come out `"none"` automatically, with no separate "disable" step needed. The ZX-desaturation check just above (`if theme.tier3_effect == "stealth_mute":`) also simply won't match, since `STANDARD_THEME.tier3_effect == "none"`.

- [ ] **Step 3: Branch the Pillow art on `standard_mode`**

Change:

```python
        primary_light, primary_dark = theme.primary
        secondary_light, secondary_dark = theme.secondary
        timer_glow_light = make_glow(300, 120, primary_light)
        timer_glow_dark = make_glow(300, 120, primary_dark)
        button_glow_light = make_glow(170, 70, secondary_light)
        button_glow_dark = make_glow(170, 70, secondary_dark)
        bg_dark = make_background_texture(
            BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, primary_dark, secondary_dark,
            dark=True, era=theme.era,
        )
        bg_light = make_background_texture(
            BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, primary_light, secondary_light,
            dark=False, era=theme.era,
        )
        divider_light = make_panel_divider(
            DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_light, secondary_light, era=theme.era,
        )
        divider_dark = make_panel_divider(
            DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_dark, secondary_dark, era=theme.era,
        )
```

to:

```python
        primary_light, primary_dark = theme.primary
        secondary_light, secondary_dark = theme.secondary
        if self.config_obj.standard_mode:
            # No glow, and a flat fill instead of an era pattern -- a
            # solid-color fill is what actually makes this "bypass the
            # Pillow art": virtually free to draw, versus a
            # procedurally-generated texture.
            surface_light, surface_dark = self.color_surface
            timer_glow_light = make_flat_fill(300, 120, primary_light, alpha=0)
            timer_glow_dark = make_flat_fill(300, 120, primary_dark, alpha=0)
            button_glow_light = make_flat_fill(170, 70, secondary_light, alpha=0)
            button_glow_dark = make_flat_fill(170, 70, secondary_dark, alpha=0)
            bg_dark = make_flat_fill(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, surface_dark)
            bg_light = make_flat_fill(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, surface_light)
            divider_light = make_flat_fill(DIVIDER_WIDTH, DIVIDER_HEIGHT, surface_light)
            divider_dark = make_flat_fill(DIVIDER_WIDTH, DIVIDER_HEIGHT, surface_dark)
        else:
            timer_glow_light = make_glow(300, 120, primary_light)
            timer_glow_dark = make_glow(300, 120, primary_dark)
            button_glow_light = make_glow(170, 70, secondary_light)
            button_glow_dark = make_glow(170, 70, secondary_dark)
            bg_dark = make_background_texture(
                BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, primary_dark, secondary_dark,
                dark=True, era=theme.era,
            )
            bg_light = make_background_texture(
                BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, primary_light, secondary_light,
                dark=False, era=theme.era,
            )
            divider_light = make_panel_divider(
                DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_light, secondary_light, era=theme.era,
            )
            divider_dark = make_panel_divider(
                DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_dark, secondary_dark, era=theme.era,
            )
```

(`self.color_surface` was already set a few lines above this block, from `theme.surface_pair` — reused here rather than recomputed.)

- [ ] **Step 4: Sanity-check by hand**

Run: `python -c "import lock_in.ui"`
Expected: no `ImportError`/`SyntaxError` (this only confirms the module still parses and imports cleanly — Task 7 does the real verification).

- [ ] **Step 5: Run the full test suite to confirm nothing broke**

Run: `pytest -q`
Expected: all existing tests still PASS (this task touches only `ui.py`, which has no direct unit tests, so this is a regression check on everything else).

- [ ] **Step 6: Commit**

```bash
git add lock_in/ui.py
git commit -m "Wire _apply_rider_theme() to Standard Mode"
```

---

### Task 5: Settings switch, driver label, Wording override, Tier 2 guard

**Files:**
- Modify: `lock_in/ui.py` — `_is_tokusatsu()` (line 232-233), a new `_driver_label_text()` method, `_build_header()`'s `driver_label` creation (around line 490), `_build_settings_tab()` (the appearance/rider-row area, around line 866-906), `_on_rider_theme_change()` (around line 1344-1350), and a new `_on_standard_mode_toggled()` method (near `_on_rider_theme_change`).

**Interfaces:**
- Consumes: `Config.standard_mode` (Task 1); everything else already wired in Task 4.
- Produces: `self._driver_label_text() -> str`, `self._on_standard_mode_toggled() -> None`, `self.standard_mode_switch` (a `CTkSwitch`).

No automated test — same reasoning as Task 4, verified in Task 7.

- [ ] **Step 1: Force Professional wording while Standard Mode is on**

Change:

```python
    def _is_tokusatsu(self) -> bool:
        return self.config_obj.terminology == "tokusatsu"
```

to:

```python
    def _is_tokusatsu(self) -> bool:
        # Standard Mode always reads as Professional, no matter what the
        # Wording switch itself says -- the switch's real value is never
        # overwritten, so it's back the instant Standard Mode is off.
        return self.config_obj.terminology == "tokusatsu" and not self.config_obj.standard_mode
```

- [ ] **Step 2: Add a driver-label helper**

Right after `_rider_row_label_text()` (which ends around line 241), add:

```python
    def _driver_label_text(self) -> str:
        """What the name label under the timer digits should say right now."""
        if self.config_obj.standard_mode:
            return "STANDARD MODE"
        return self.config_obj.rider_theme.upper()
```

- [ ] **Step 3: Use it when the label is first built**

In `_build_header()`, change:

```python
        self.driver_label = ctk.CTkLabel(
            self.normal_header_content, text=self.config_obj.rider_theme.upper(),
            font=ctk.CTkFont(family=DISPLAY_FONT, size=10, weight="bold"),
            text_color=self.color_driver_text,
        )
```

to:

```python
        self.driver_label = ctk.CTkLabel(
            self.normal_header_content, text=self._driver_label_text(),
            font=ctk.CTkFont(family=DISPLAY_FONT, size=10, weight="bold"),
            text_color=self.color_driver_text,
        )
```

- [ ] **Step 4: Use it when the Rider dropdown changes**

In `_on_rider_theme_change()`, change:

```python
        self.driver_label.configure(text=value.upper(), text_color=self.color_driver_text)
```

to:

```python
        self.driver_label.configure(text=self._driver_label_text(), text_color=self.color_driver_text)
```

(`self.config_obj.rider_theme` is already set to `value` on the line just above this one, so `_driver_label_text()` sees the new value — and if Standard Mode happens to be on, it correctly keeps showing "STANDARD MODE" instead.)

- [ ] **Step 5: Add the Settings-tab switch**

In `_build_settings_tab()`, right after the `appearance_menu` row (right after `self.appearance_menu.pack(side="left")`, and before the `rider_row = ctk.CTkFrame(...)` line), insert:

```python
        ctk.CTkLabel(frame, text="Standard Mode", text_color=COLOR_LOOK_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(14, 4))
        ctk.CTkLabel(
            frame,
            text=("Strips every Rider's color, art, and gimmick for a plain, "
                  "fast, distraction-free look. Your Rider pick below is "
                  "remembered and comes right back the moment you turn this "
                  "back off."),
            text_color=COLOR_IDLE, justify="left", wraplength=440,
        ).pack(anchor="w", pady=(0, 6))
        self.standard_mode_switch = ctk.CTkSwitch(
            frame, text="Standard Mode (plain, no Rider flavor)",
            progress_color=COLOR_LOOK_ACCENT,
            command=self._on_standard_mode_toggled,
        )
        if self.config_obj.standard_mode:
            self.standard_mode_switch.select()
        else:
            self.standard_mode_switch.deselect()
        self.standard_mode_switch.pack(anchor="w", pady=(0, 10))

```

- [ ] **Step 6: Guard the Tier 2 preset-button block**

Still in `_build_settings_tab()`, change:

```python
        if self.config_obj.rider_theme == "Kamen Rider Kuuga (2000)":
            self._build_timer_preset_row(
                frame, KUUGA_PRESETS,
                "Kuuga presets" if self._is_tokusatsu() else "Interval presets",
            )
        elif self.config_obj.rider_theme == "Kamen Rider Super-1 (1980)":
            self._build_timer_preset_row(
                frame, SUPER1_PRESETS,
                "Super-1's Five Hands" if self._is_tokusatsu() else "Task-type presets",
            )
        elif self.config_obj.rider_theme == "Kamen Rider Gavv (2024)":
            self._build_gavv_toggle_row(frame)
```

to (wrap the existing chain in one guard, indent unchanged otherwise):

```python
        if not self.config_obj.standard_mode:
            if self.config_obj.rider_theme == "Kamen Rider Kuuga (2000)":
                self._build_timer_preset_row(
                    frame, KUUGA_PRESETS,
                    "Kuuga presets" if self._is_tokusatsu() else "Interval presets",
                )
            elif self.config_obj.rider_theme == "Kamen Rider Super-1 (1980)":
                self._build_timer_preset_row(
                    frame, SUPER1_PRESETS,
                    "Super-1's Five Hands" if self._is_tokusatsu() else "Task-type presets",
                )
            elif self.config_obj.rider_theme == "Kamen Rider Gavv (2024)":
                self._build_gavv_toggle_row(frame)
```

- [ ] **Step 7: Add the toggle handler**

Right after `_on_rider_theme_change()` (it ends around line 1365, just before `_on_terminology_switch_toggled`), add:

```python
    def _on_standard_mode_toggled(self) -> None:
        """Called when you flip the Standard Mode switch in Settings."""
        self.config_obj.standard_mode = self.standard_mode_switch.get()
        self.config_obj.save()
        self._apply_rider_theme()
        self.driver_label.configure(text=self._driver_label_text(), text_color=self.color_driver_text)
        self.start_button.configure(
            text=self._henshin_word(), fg_color=self.color_rider_accent,
            text_color=self.color_button_text,
        )
        self.header_frame.configure(fg_color=self.color_surface)
        self._sync_progress_widget_visibility()
        self._refresh_timer_widgets()
        # Same reason _on_rider_theme_change() rebuilds the tabs: the tab
        # panel colors, and here also the Tier 2 preset row, need to pick
        # up the change, and the whole Settings tab already gets rebuilt
        # from scratch on every relevant change.
        self._rebuild_tabs()
```

- [ ] **Step 8: Sanity-check by hand**

Run: `python -c "import lock_in.ui"`
Expected: no `ImportError`/`SyntaxError`.

- [ ] **Step 9: Run the full test suite to confirm nothing broke**

Run: `pytest -q`
Expected: all existing tests still PASS.

- [ ] **Step 10: Commit**

```bash
git add lock_in/ui.py
git commit -m "Add Standard Mode switch, driver label, and Wording override"
```

---

### Task 6: Help tab and README

**Files:**
- Modify: `lock_in/ui.py` (`_build_help_tab()`, the "2. Change how it looks and talks" section)
- Modify: `README.md` (Features list, and a new "Tier 0" subsection in the Kamen Rider theme section)

**Interfaces:** none — documentation only.

- [ ] **Step 1: Add a Help tab bullet**

In `_build_help_tab()`, right after the existing theme-dropdown bullet (the one ending `"...never changes how blocking or timers work."`) and before the `# --- Special Rider powers ---` comment, insert:

```python
        bullet(
            "Want zero Rider flavor at all? Flip \"Standard Mode\" on, "
            "right above the theme dropdown — it strips every color, "
            "glow, and gimmick down to a plain grey-and-blue look, no "
            "matter which Rider is picked underneath. Flip it back off "
            "and your Rider comes right back, exactly as it was."
        )
```

- [ ] **Step 2: Add a README Features bullet**

In `README.md`, in the `## ⚙️ Features` list, right after the bullet that starts `* Switches between **38 Kamen Rider color themes**...` and before the `**9 of those Riders go further still**` sentence inside that same bullet ends, add a new bullet:

```markdown
* A **Standard Mode** switch (Settings tab) strips every Rider's color,
  art, and gimmick for a plain, fast, distraction-free look — your
  actual Rider pick is remembered and comes right back the moment you
  turn it back off.
```

- [ ] **Step 3: Add a README "Tier 0" subsection**

In `README.md`, right before `### Tier 1: 9 Riders with their own gimmick`, add:

```markdown
### Tier 0: Standard Mode (no Rider flavor at all)

Settings → "Standard Mode" is a single switch, independent of which
Rider is picked below it. Turning it on swaps in a plain slate-grey and
blue palette, turns off every Tier 1/2/3 Rider gimmick, forces Wording
to Professional, and replaces every piece of Pillow-rendered art (the
timer/button glow, the background wallpaper, the divider strip) with a
flat, patternless fill — the same rendering pipeline, just fed a
neutral color and no texture, which is what makes it the lightest,
fastest-drawing look in the app. Your actual Rider and Wording choices
are never overwritten; turning Standard Mode back off restores both
instantly.

```

- [ ] **Step 4: Sanity-check by hand**

Run: `python -c "import lock_in.ui"`
Expected: no `ImportError`/`SyntaxError`.

- [ ] **Step 5: Commit**

```bash
git add lock_in/ui.py README.md
git commit -m "Document Standard Mode in the Help tab and README"
```

---

### Task 7: Manual screenshot verification

**Files:**
- Create (scratch, not committed): a throwaway verification script, same pattern as prior tiers' `verify_tier1.py`/`verify_help.py`.

- [ ] **Step 1: Write a verification script**

Create `verify_tier0.py` in the scratch/temp directory (**not** inside the repo):

```python
import sys, time
sys.path.insert(0, r"c:\Users\saksh\OneDrive\Desktop\Coding_Projects\Lock_In")

import lock_in.ui as ui
from lock_in.session import Event
from PIL import ImageGrab

app = ui.LockInApp()
app.update()
app.geometry("560x720+40+40")


def screenshot(name: str) -> None:
    app.attributes("-topmost", True)
    app.lift()
    app.focus_force()
    for _ in range(8):
        app.update()
        time.sleep(0.05)
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path = rf"C:\Users\saksh\AppData\Local\Temp\claude\tier0_{name}.png"
    img.save(path)
    print("saved:", path)


# 1. Pick Build (a Tier 1 Rider with a visible progress-bar gimmick),
#    start a focus block partway through, screenshot -- vials should show.
app.config_obj.rider_theme = "Kamen Rider Build (2017)"
app._on_rider_theme_change(app.config_obj.rider_theme)
for event in app.session.start():
    if event is Event.PHASE_STARTED:
        app._on_phase_started()
for _ in range(400):
    app.session.tick()
app._refresh_timer_widgets()
app.update()
screenshot("build_before_standard_mode")

# 2. Flip Standard Mode ON, same Rider still selected underneath, same
#    point in the same focus block -- vials should be GONE, colors flat
#    grey/blue, driver label should say STANDARD MODE.
app.standard_mode_switch.select()
app._on_standard_mode_toggled()
app.update()
screenshot("build_during_standard_mode")

# 3. Flip Standard Mode back OFF -- Build's vials and colors should be
#    back exactly as they were in screenshot 1, proving nothing was lost.
app.standard_mode_switch.deselect()
app._on_standard_mode_toggled()
app.update()
screenshot("build_after_standard_mode_off")

app.session.reset()
app._on_close()
```

- [ ] **Step 2: Run it and look at each screenshot**

Run: `python verify_tier0.py` (from the scratchpad directory, with the app's venv active)

Confirm:
- `build_before_standard_mode.png`: Build's two-vial progress shape is visible, driver label says "KAMEN RIDER BUILD (2017)".
- `build_during_standard_mode.png`: plain native progress bar (no vials), flat slate-grey/blue coloring, no background texture or glow, driver label says "STANDARD MODE".
- `build_after_standard_mode_off.png`: looks the same as screenshot 1 again — vials back, Rider colors back, driver label back to Build's name.

Also open the app interactively once and confirm the Settings tab: the Standard Mode switch sits above the theme dropdown, the Tier 2 preset row (try selecting Kuuga or Super-1 first) disappears while Standard Mode is on and reappears when it's off, and the Help tab shows the new bullet.

- [ ] **Step 3: Fix anything that looks wrong**

If a color looks off or art still shows through, go back to Task 4/5 and adjust.

- [ ] **Step 4: Delete the scratch script and screenshots**

They're verification-only, not part of the app — don't commit them.

---

### Task 8: Docs and version

**Files:**
- Modify: `lock_in/__init__.py`

- [ ] **Step 1: Bump the version**

In `lock_in/__init__.py`, change:

```python
__version__ = "2.2.1"
```

to:

```python
__version__ = "2.3.0"
```

This is the version bump Tier 0 earns — matching the "v2.3.0" label already chosen for this round, the same way each prior tier's slice earned its own version.

- [ ] **Step 2: Run the full test suite one final time**

Run: `pytest -q`
Expected: all tests PASS (227 previously, plus the new tests from Tasks 1-3).

- [ ] **Step 3: Commit**

```bash
git add lock_in/__init__.py
git commit -m "v2.3.0: add Tier 0 Standard Mode"
```

---

## Self-review

- **Spec coverage:** every section of `docs/superpowers/specs/2026-08-15-tier0-standard-mode-design.md` maps to a task — `Config.standard_mode` (Task 1), `STANDARD_THEME` (Task 2), `make_flat_fill()` (Task 3), the rendering intercept (Task 4), Wording/driver-label/Settings-switch/Tier-2-guard (Task 5), docs (Task 6), verification (Task 7), version (Task 8).
- **Simplification found during planning:** the spec described the rendering intercept as "forcing `current_tier1_effect`/`current_tier3_effect` to `none`." Tracing the actual code showed that substituting `theme = STANDARD_THEME` in Task 4 already makes those two attributes come out `"none"` as a side effect of `STANDARD_THEME`'s own field defaults — no separate forcing step exists in the plan because none is needed. This is a genuine simplification, not a scope cut: every behavior the spec asked for is still fully covered.
- **Placeholder scan:** no TBD/TODO; every step has real, runnable code or an exact manual command.
- **Type consistency:** `make_flat_fill(width: int, height: int, hex_color: str, alpha: int = 255) -> Image.Image` is defined once in Task 3 and called with that exact signature in Task 4. `_driver_label_text() -> str` is defined once in Task 5 and called identically in Task 5's own later steps. `STANDARD_THEME` is defined once in Task 2 with the exact palette values Task 2's own tests pin down, and consumed as-is in Task 4.
