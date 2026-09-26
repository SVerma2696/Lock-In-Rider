"""
ui/components/status_badge.py
=============================
`StatusBadge`: a small rounded pill like "● Focus Active" or
"Blocking ON". It always has WORDS, not just a color, so it still makes
sense to someone who can't tell red from green.

Kinds: "success" (green), "warning" (amber), "danger" (red), "info"
(blue), "neutral" (grey), or "accent" (the Rider's color).
"""

from __future__ import annotations

import customtkinter as ctk

from .. import theme as t


def badge_colors(kind: str, palette: t.Palette):
    """(words color, background color) for one kind of badge."""
    if kind == "accent":
        return palette.accent_text, palette.control_bg
    return t.STATUS_COLORS.get(kind, t.STATUS_COLORS["neutral"])


class StatusBadge(ctk.CTkLabel):
    def __init__(self, master, palette: t.Palette, *, text: str = "",
                 kind: str = "neutral", dot: bool = True, **kwargs) -> None:
        self._palette = palette
        self._dot = dot
        fg, bg = badge_colors(kind, palette)
        super().__init__(
            master, text=self._words(text), fg_color=bg, text_color=fg,
            corner_radius=11, height=24, font=t.font(size=t.FONT_SMALL + 1, weight="bold"),
            **kwargs,
        )
        self._state = (text, kind)

    def _words(self, text: str) -> str:
        return f"  ● {text}  " if self._dot else f"  {text}  "

    def set_palette(self, palette: t.Palette) -> None:
        """Use a new Rider's colors (only "accent" badges change)."""
        self._palette = palette
        text, kind = self._state
        self._state = None
        self.set(text, kind)

    def set(self, text: str, kind: str = "neutral") -> None:
        """Change what the badge says. Skips the redraw when nothing
        changed, because this runs on every timer tick."""
        if (text, kind) == self._state:
            return
        self._state = (text, kind)
        fg, bg = badge_colors(kind, self._palette)
        self.configure(text=self._words(text), fg_color=bg, text_color=fg)
