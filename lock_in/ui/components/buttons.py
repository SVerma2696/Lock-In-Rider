"""
ui/components/buttons.py
========================
Three kinds of button, so it's always clear which one matters most:

- PrimaryButton:   filled with the Rider's color. The ONE main action
                   (like Start / Henshin).
- SecondaryButton: plain grey with a thin border. Everything else.
- DangerButton:    red outline. Only for things you can't easily undo.
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from .. import theme as t


class PrimaryButton(ctk.CTkButton):
    def __init__(
        self,
        master,
        palette: t.Palette,
        *,
        text: str,
        command=None,
        height: int = t.BUTTON_HEIGHT,
        font_family=None,
        font_size: int = 15,
        **kwargs,
    ) -> None:
        kwargs.setdefault("corner_radius", 10)
        super().__init__(
            master,
            text=text,
            command=command,
            height=height,
            fg_color=palette.accent,
            hover_color=palette.accent_hover,
            text_color=palette.accent_on,
            font=t.font(family=font_family, size=font_size, weight="bold")
            if font_family
            else t.font(size=font_size, weight="bold"),
            **kwargs,
        )


class SecondaryButton(ctk.CTkButton):
    def __init__(
        self, master, palette: t.Palette, *, text: str, command=None, height: int = 36, **kwargs
    ) -> None:
        kwargs.setdefault("corner_radius", t.CONTROL_RADIUS)
        kwargs.setdefault("font", t.font(size=t.FONT_BODY))
        super().__init__(
            master,
            text=text,
            command=command,
            height=height,
            fg_color=palette.control_bg,
            hover_color=palette.control_hover,
            border_width=1,
            border_color=palette.card_border,
            text_color=palette.text_primary,
            **kwargs,
        )


class DangerButton(ctk.CTkButton):
    def __init__(
        self,
        master,
        palette: t.Palette,
        *,
        text: str,
        command=None,
        height: int = 34,
        filled: bool = False,
        **kwargs,
    ) -> None:
        kwargs.setdefault("corner_radius", t.CONTROL_RADIUS)
        kwargs.setdefault("font", t.font(size=t.FONT_BODY))
        colors: dict[str, Any]
        if filled:
            colors = dict(
                fg_color=t.DANGER, hover_color=("#A93226", "#D9534F"), text_color="#FFFFFF"
            )
        else:
            colors = dict(
                fg_color="transparent",
                hover_color=t.DANGER_SOFT,
                border_width=1,
                border_color=t.DANGER,
                text_color=t.DANGER,
            )
        super().__init__(master, text=text, command=command, height=height, **colors, **kwargs)
