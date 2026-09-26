"""
ui/components/card.py
=====================
`ModernCard`: the rounded box almost everything sits in. A card has a
thin border and an optional title, a short line under the title, and
an optional thing on the right of the title (like a button or badge).

Put your own widgets in `card.body`.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from .. import theme as t
from .box import Box
from .text import Text


def _plain(widget, **kwargs):
    widget.pack(**kwargs)


class ModernCard(ctk.CTkFrame):
    def __init__(self, master, palette: t.Palette, *, layout=None,
                 title: Optional[str] = None, subtitle: Optional[str] = None,
                 trailing: Optional[Callable] = None, icon=None,
                 padding: int = t.SPACE_4, elevated: bool = False,
                 border_color=None, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=palette.card_bg_elevated if elevated else palette.card_bg,
            border_color=border_color or palette.card_border,
            border_width=1, corner_radius=t.CARD_RADIUS, **kwargs,
        )
        self.palette = palette
        pack = layout.pack if layout is not None else _plain
        self.title_label = None
        self.subtitle_label = None
        self.trailing_widget = None

        if title or subtitle or trailing is not None:
            head = Box(self)
            pack(head, fill="x", padx=padding, pady=(padding, 0))
            if trailing is not None:
                # `trailing` is a function that builds the widget, so it
                # can be made inside the card's own title row.
                self.trailing_widget = trailing(head)
                pack(self.trailing_widget, side="right", anchor="n", padx=(t.SPACE_2, 0))
            if icon is not None:
                pack(ctk.CTkLabel(head, text="", image=icon, width=20, font=t.font()),
                     side="left", anchor="n", padx=(0, t.SPACE_2), pady=(1, 0))
            words = Box(head)
            pack(words, side="left", fill="x", expand=True)
            if title:
                self.title_label = Text(
                    words, text=title, anchor="w", justify="left",
                    text_color=palette.text_primary,
                    font=t.font(size=t.FONT_SECTION, weight="bold"),
                )
                pack(self.title_label, anchor="w", fill="x")
            if subtitle:
                self.subtitle_label = Text(
                    words, text=subtitle, anchor="w", justify="left",
                    text_color=palette.text_secondary, wraplength=520,
                    font=t.font(size=t.FONT_SMALL + 1),
                )
                pack(self.subtitle_label, anchor="w", fill="x")
            body_top = t.SPACE_3
        else:
            body_top = padding

        self.body = Box(self)
        pack(self.body, fill="both", expand=True, padx=padding, pady=(body_top, padding))


class StatCard(ModernCard):
    """A small card with a label, one big value, and a line of detail --
    for the summary rows on Focus, Blocking, and Insights."""

    def __init__(self, master, palette: t.Palette, *, layout=None, label: str,
                 value: str = "", detail: str = "", icon=None,
                 value_color=None, value_size: int = 20, value_wrap: int = 0,
                 **kwargs) -> None:
        super().__init__(master, palette, layout=layout, padding=t.SPACE_4, **kwargs)
        pack = layout.pack if layout is not None else _plain
        top = Box(self.body)
        pack(top, fill="x")
        if icon is not None:
            pack(ctk.CTkLabel(top, text="", image=icon, width=18, font=t.font()), side="left", padx=(0, t.SPACE_2))
        self.label = Text(top, text=label, anchor="w",
                                  text_color=palette.text_secondary,
                                  font=t.font(size=t.FONT_SMALL + 1))
        pack(self.label, side="left", fill="x", expand=True)
        self.value = Text(self.body, text=value, anchor="w", justify="left",
                                  text_color=value_color or palette.text_primary,
                                  wraplength=value_wrap,
                                  font=t.font(size=value_size, weight="bold"))
        pack(self.value, anchor="w", fill="x", pady=(t.SPACE_1, 0))
        self.detail = Text(self.body, text=detail, anchor="w", justify="left",
                                   text_color=palette.text_muted,
                                   font=t.font(size=t.FONT_SMALL))
        pack(self.detail, anchor="w", fill="x")
        self._value_color = value_color

    def set(self, value: Optional[str] = None, detail: Optional[str] = None,
            value_color=None) -> None:
        """Change the words, only touching what actually changed (this
        runs on every timer tick for the Focus page)."""
        if value is not None and self.value.cget("text") != value:
            self.value.configure(text=value)
        if value_color is not None and value_color != self._value_color:
            self._value_color = value_color
            self.value.configure(text_color=value_color)
        if detail is not None and self.detail.cget("text") != detail:
            self.detail.configure(text=detail)
