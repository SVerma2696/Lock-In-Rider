"""
ui/components/timer_display.py
==============================
The big clock on the Focus page, and the bar under it.

`TimerDisplay` holds the words: which part you're in ("Focus",
"Short Break"), the big numbers, how many blocks are done, and the
Rider's name. The app fills in the words on every tick.

`ProgressArea` holds the bar under the clock. It has three ways to look,
and only one shows at a time:

- the plain bar (every Rider without a special shape, and Standard Mode)
- a drawn picture, for the Tier 1 Riders with their own shape (the
  windmill, the rising bar, the stars, the bottles, the bookmark)
- Amazon's green tank that drains during a focus block

The drawing itself happens in visuals.py, exactly like before. This
file only holds the places the pictures go.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import theme as t
from .box import Box

# The Tier 1 shape pictures are a fixed size, kept from before so every
# shape still looks the way it was designed.
PROGRESS_SHAPE_WIDTH = 340
PROGRESS_SHAPE_HEIGHT = 48

# Amazon's zero-UI picture is bigger on purpose -- it's meant to fill
# the Focus page, not sit in a thin strip.
ZERO_UI_WIDTH = 340
ZERO_UI_HEIGHT = 120


class TimerDisplay(Box):
    def __init__(
        self, master, palette: t.Palette, *, layout, font_family: str, label_font_family: str
    ) -> None:
        super().__init__(master)
        self.phase_label = ctk.CTkLabel(
            self,
            text="Standing By",
            text_color=palette.text_secondary,
            font=t.font(family=font_family, size=t.FONT_PHASE, weight="bold"),
        )
        layout.pack(self.phase_label, pady=(0, 0))

        self.time_label = ctk.CTkLabel(
            self,
            text="25:00",
            text_color=palette.text_primary,
            font=t.font(family=font_family, size=t.FONT_TIMER, weight="bold"),
        )
        layout.pack(self.time_label, pady=(0, 0))

        self.streak_label = ctk.CTkLabel(
            self,
            text="",
            text_color=palette.text_muted,
            font=t.font(size=t.FONT_SMALL + 1),
        )
        layout.pack(self.streak_label)

        self.driver_label = ctk.CTkLabel(
            self,
            text="",
            text_color=palette.secondary_text,
            font=t.font(family=label_font_family, size=10, weight="bold"),
        )
        layout.pack(self.driver_label, pady=(2, 0))

    def set_font_family(self, family: str) -> None:
        """Ex-Aid swaps in a pixel font; everyone else uses the normal one."""
        self.time_label.configure(font=t.font(family=family, size=t.FONT_TIMER, weight="bold"))
        self.phase_label.configure(font=t.font(family=family, size=t.FONT_PHASE, weight="bold"))


class ProgressArea(Box):
    def __init__(self, master, palette: t.Palette, *, layout) -> None:
        super().__init__(master)
        self._layout = layout
        self.progress = ctk.CTkProgressBar(
            self,
            height=8,
            corner_radius=4,
            width=PROGRESS_SHAPE_WIDTH,
            fg_color=palette.control_bg,
            progress_color=palette.accent,
        )
        self.progress.set(0)
        self.progress_shape = ctk.CTkLabel(self, text="", image=None, font=t.font())
        self.zero_ui_label = ctk.CTkLabel(self, text="", image=None, font=t.font())
        self._mode: str | None = None

    def show(self, mode: str) -> None:
        """mode is "bar", "shape", or "zero_ui". Hides the other two."""
        if mode == self._mode:
            return
        self._mode = mode
        for widget in (self.progress, self.progress_shape, self.zero_ui_label):
            widget.pack_forget()
        if mode == "shape":
            self._layout.pack(self.progress_shape, pady=(t.SPACE_1, t.SPACE_2))
        elif mode == "zero_ui":
            self._layout.pack(self.zero_ui_label, pady=(t.SPACE_5, t.SPACE_5))
        else:
            self._layout.pack(self.progress, pady=(t.SPACE_3, t.SPACE_4))

    @property
    def mode(self):
        return self._mode
