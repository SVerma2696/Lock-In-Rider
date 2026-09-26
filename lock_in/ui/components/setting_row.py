"""
ui/components/setting_row.py
============================
`SettingRow`: one line on the Settings page, like Windows Settings.

    [icon]  Title                                   [switch / box / menu]
            A short sentence saying what it does.

The thing on the right is made by a small function you pass in
(`control`), so the row can hold a switch, a number box, a menu, or a
button. Rows in the same card get a thin line between them.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from .. import theme as t
from .box import Box
from .text import Text


def divider_line(master, palette: t.Palette) -> Box:
    """A thin 1-pixel line. A Box paints its whole background in its
    color (a normal 1-pixel CTkFrame would draw an empty shape), and it
    still follows light and dark mode."""
    return Box(master, height=1, fg_color=palette.card_border)


class SettingRow(Box):
    def __init__(self, master, palette: t.Palette, *, layout, title: str,
                 description: str = "", icon=None,
                 control: Optional[Callable] = None, divider: bool = False,
                 wraplength: int = 380) -> None:
        super().__init__(master)
        self.control = None

        if divider:
            line = divider_line(self, palette)
            layout.grid(line, total_columns=3, row=0, column=0, columnspan=3,
                        sticky="ew", pady=(0, t.SPACE_3))

        column_for_words = 1
        self.grid_columnconfigure(1, weight=1)
        if icon is not None:
            layout.grid(ctk.CTkLabel(self, text="", image=icon, width=22, font=t.font()), total_columns=3,
                        row=1, column=0, sticky="nw", padx=(0, t.SPACE_3), pady=(2, 0))

        words = Box(self)
        layout.grid(words, total_columns=3, row=1, column=column_for_words, sticky="ew")
        self.title_label = Text(
            words, text=title, anchor="w", justify="left",
            text_color=palette.text_primary, font=t.font(size=t.FONT_BODY + 1),
        )
        layout.pack(self.title_label, anchor="w", fill="x")
        self.description_label = None
        if description:
            self.description_label = Text(
                words, text=description, anchor="w", justify="left", wraplength=wraplength,
                text_color=palette.text_muted, font=t.font(size=t.FONT_SMALL + 1),
            )
            layout.pack(self.description_label, anchor="w", fill="x")

        if control is not None:
            self.control = control(self)
            layout.grid(self.control, total_columns=3, row=1, column=2, sticky="e",
                        padx=(t.SPACE_4, 0))
