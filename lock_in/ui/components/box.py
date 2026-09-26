"""
ui/components/box.py
====================
`Box`: an invisible holder for laying widgets out in rows and columns.

It's a see-through CustomTkinter frame that skips the drawing. A normal
CTkFrame, even a see-through one, draws a rounded shape on its own little
canvas every time its size changes -- and a page has dozens of these
invisible holders, so that drawing added up to a big part of the time
it took to open a page or pick a new Rider. A Box just paints its
background in the color of whatever it sits on, which looks exactly the
same, and still follows light and dark mode.
"""

from __future__ import annotations

import customtkinter as ctk


class Box(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, corner_radius=0, border_width=0, **kwargs)

    def _draw(self, no_color_updates: bool = False) -> None:
        # Skip CTkFrame's rounded-shape drawing; keep CustomTkinter's own
        # bookkeeping from the class above it.
        super(ctk.CTkFrame, self)._draw(no_color_updates)
        try:
            if self._canvas.winfo_exists():
                color = self._bg_color if self._fg_color == "transparent" else self._fg_color
                self._canvas.configure(bg=self._apply_appearance_mode(color))
        except Exception:
            pass
