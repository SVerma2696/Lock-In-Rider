"""
ui/effects.py
=============
The Rider pictures the window shows: the background behind the page
area (Stronger's glow, Kiva's night tint, Gaim's dimming), the thin era
strip under the top bar, a Tier 1 Rider's progress shape, and Amazon's
draining field.

Each picture is only redrawn when what it shows really changes -- the
timer ticks five times a second, but Stronger's glow only moves in 14
small steps and a progress shape about one pixel every few seconds. The
"key" for each picture is what it looked like last time; the same key
means "nothing to redraw".

Every picture has a light-mode and a dark-mode version, as always.
"""

from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk
from PIL import Image, ImageOps

from ..rider_effects import EnforcementEffect, ProgressEffect
from ..rider_themes import RiderTheme
from ..visuals import (
    apply_gaim_lock_overlay,
    apply_tier1_background_effect,
    make_flat_fill,
    make_panel_divider,
    render_amazon_drain,
    render_progress,
)
from .components.timer_display import (
    PROGRESS_SHAPE_HEIGHT,
    PROGRESS_SHAPE_WIDTH,
    ZERO_UI_HEIGHT,
    ZERO_UI_WIDTH,
)
from .theme import Palette

# The picture behind the page area only shows in the thin gap around the
# page and gets stretched to fit, so a small picture is plenty -- and a
# small picture is much quicker to redraw and uses much less memory.
BG_TEXTURE_WIDTH = 480
BG_TEXTURE_HEIGHT = 640
# Stronger's glow grows in this many steps (see visuals.render_border_glow_overlay).
GLOW_STEPS = 14

# The thin era strip under the top bar (Riders only, never Standard Mode).
DIVIDER_WIDTH = 1400
DIVIDER_HEIGHT = 4

BACKGROUND_EFFECTS = (ProgressEffect.BORDER_GLOW, ProgressEffect.NIGHT_OVERLAY)


@dataclass(frozen=True)
class BackgroundState:
    """What the background should show right now."""

    progress_effect: ProgressEffect  # Tier 1 (only the glow and the tint paint here)
    enforcement_effect: EnforcementEffect  # Tier 3 (only Gaim's lock paints here)
    in_focus: bool
    mirrored: bool
    progress: float


class RiderVisuals:
    """Holds the pictures, and redraws each one only when it changes."""

    def __init__(self) -> None:
        self.bg_image: ctk.CTkImage | None = None
        self.divider_image: ctk.CTkImage | None = None
        self.progress_shape_image: ctk.CTkImage | None = None
        self.zero_ui_image: ctk.CTkImage | None = None
        self._base_bg: tuple[Image.Image, Image.Image] | None = None
        self._base_divider: tuple[Image.Image, Image.Image] | None = None
        self._effect_pair: tuple[str, str] = ("#000000", "#000000")
        self._bg_key: tuple | None = None
        self._shape_key: tuple | None = None
        self._drain_key: int | None = None

    # ------------------------------------------------------------------ #
    def apply_theme(self, theme: RiderTheme, palette: Palette, standard_mode: bool) -> None:
        """New Rider colors: make the plain background and the era strip
        again, and forget every picture drawn in the old colors."""
        bg_light, bg_dark = palette.app_bg
        self._base_bg = (
            make_flat_fill(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, bg_light),
            make_flat_fill(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, bg_dark),
        )
        if standard_mode:
            border_light, border_dark = palette.card_border
            self._base_divider = (
                make_flat_fill(DIVIDER_WIDTH, DIVIDER_HEIGHT, border_light),
                make_flat_fill(DIVIDER_WIDTH, DIVIDER_HEIGHT, border_dark),
            )
        else:
            (primary_light, primary_dark), (secondary_light, secondary_dark) = (
                theme.primary,
                theme.secondary,
            )
            self._base_divider = (
                make_panel_divider(
                    DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_light, secondary_light, era=theme.era
                ),
                make_panel_divider(
                    DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_dark, secondary_dark, era=theme.era
                ),
            )
        # Stronger's glow uses the Rider's own primary (a red); Kiva's
        # night wash uses the secondary (the amber gold).
        self._effect_pair = (
            theme.primary if theme.tier1_effect is ProgressEffect.BORDER_GLOW else theme.secondary
        )
        if self.bg_image is None:
            self.bg_image = ctk.CTkImage(
                light_image=self._base_bg[0],
                dark_image=self._base_bg[1],
                size=(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT),
            )
            self.divider_image = ctk.CTkImage(
                light_image=self._base_divider[0],
                dark_image=self._base_divider[1],
                size=(DIVIDER_WIDTH, DIVIDER_HEIGHT),
            )
        else:
            assert self.divider_image is not None
            self.divider_image.configure(
                light_image=self._base_divider[0], dark_image=self._base_divider[1]
            )
        # A new theme drops the old Tier 1 picture's size and colors, and the
        # background must be drawn again.
        self.progress_shape_image = None
        self._shape_key = None
        self._bg_key = None

    def forget_page_images(self) -> None:
        """The Focus page was rebuilt: its new widgets make their own."""
        self.progress_shape_image = None
        self.zero_ui_image = None
        self._shape_key = None
        self._drain_key = None

    # ------------------------------------------------------------------ #
    def refresh_background(self, state: BackgroundState) -> None:
        """Paint Stronger's glow, Kiva's tint, or Gaim's dimming onto the
        background -- only DURING a focus block. Everyone else just gets
        the plain picture."""
        if self.bg_image is None or self._base_bg is None:
            return
        effect = state.progress_effect if state.in_focus else ProgressEffect.NONE
        if effect not in BACKGROUND_EFFECTS:
            effect = ProgressEffect.NONE
        lock_on = state.enforcement_effect is EnforcementEffect.LOCK_OVERLAY and state.in_focus
        # Drawing this picture is the slowest thing the timer does, so it is
        # only redrawn when what it shows really changes.
        step = (
            round(GLOW_STEPS * max(0.0, min(1.0, state.progress)))
            if effect is ProgressEffect.BORDER_GLOW
            else 0
        )
        painted = effect is not ProgressEffect.NONE or lock_on
        key = (effect, step, lock_on, state.mirrored and painted)
        if key == self._bg_key:
            return
        self._bg_key = key
        base_light, base_dark = self._base_bg
        if not painted:
            self.bg_image.configure(light_image=base_light, dark_image=base_dark)
            return
        fraction = step / GLOW_STEPS
        color_light, color_dark = self._effect_pair
        bg_light = apply_tier1_background_effect(base_light, effect, color_light, fraction)
        bg_dark = apply_tier1_background_effect(base_dark, effect, color_dark, fraction)
        if lock_on:
            bg_light = apply_gaim_lock_overlay(bg_light, True)
            bg_dark = apply_gaim_lock_overlay(bg_dark, True)
        if state.mirrored:
            bg_light = ImageOps.mirror(bg_light)
            bg_dark = ImageOps.mirror(bg_dark)
        self.bg_image.configure(light_image=bg_light, dark_image=bg_dark)

    def sync_divider(self, mirrored: bool) -> None:
        """Ryuki's flip for the era strip under the top bar."""
        if self.divider_image is None or self._base_divider is None:
            return
        light, dark = self._base_divider
        if mirrored:
            light, dark = ImageOps.mirror(light), ImageOps.mirror(dark)
        self.divider_image.configure(light_image=light, dark_image=dark)

    def resize(self, content_size: tuple[int, int], window_width: int) -> None:
        """Stretch the background to the page area, and the era strip to
        the window. Skips the work unless the size really changed."""
        if self.bg_image is not None and self.bg_image.cget("size") != content_size:
            self.bg_image.configure(size=content_size)
        strip = (window_width, DIVIDER_HEIGHT)
        if self.divider_image is not None and self.divider_image.cget("size") != strip:
            self.divider_image.configure(size=strip)

    # ------------------------------------------------------------------ #
    def progress_shape(
        self,
        effect: ProgressEffect,
        progress: float,
        primary: tuple[str, str],
        secondary: tuple[str, str],
    ) -> ctk.CTkImage:
        """A Tier 1 Rider's progress shape, redrawn only when it would come
        out different (the bar only moves about one pixel every few
        seconds)."""
        key = (effect, round(progress * PROGRESS_SHAPE_WIDTH))
        if key == self._shape_key and self.progress_shape_image is not None:
            return self.progress_shape_image
        self._shape_key = key
        light = render_progress(
            effect,
            PROGRESS_SHAPE_WIDTH,
            PROGRESS_SHAPE_HEIGHT,
            progress,
            primary[0],
            secondary[0],
            False,
        )
        dark = render_progress(
            effect,
            PROGRESS_SHAPE_WIDTH,
            PROGRESS_SHAPE_HEIGHT,
            progress,
            primary[1],
            secondary[1],
            True,
        )
        if self.progress_shape_image is None:
            self.progress_shape_image = ctk.CTkImage(
                light_image=light,
                dark_image=dark,
                size=(PROGRESS_SHAPE_WIDTH, PROGRESS_SHAPE_HEIGHT),
            )
        else:
            self.progress_shape_image.configure(light_image=light, dark_image=dark)
        return self.progress_shape_image

    def zero_ui_drain(self, progress: float) -> ctk.CTkImage:
        """Amazon's draining field. Its green never depends on light or
        dark mode, so both halves get the same picture."""
        key = round(progress * ZERO_UI_HEIGHT)
        if key == self._drain_key and self.zero_ui_image is not None:
            return self.zero_ui_image
        self._drain_key = key
        drain = render_amazon_drain(ZERO_UI_WIDTH, ZERO_UI_HEIGHT, progress)
        if self.zero_ui_image is None:
            self.zero_ui_image = ctk.CTkImage(
                light_image=drain, dark_image=drain, size=(ZERO_UI_WIDTH, ZERO_UI_HEIGHT)
            )
        else:
            self.zero_ui_image.configure(light_image=drain, dark_image=drain)
        return self.zero_ui_image
