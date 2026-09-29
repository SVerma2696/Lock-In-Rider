"""
ui/components/menu_button.py
============================
`MenuButton`: a button that shows the picked choice and opens a list
when you click it -- used for the Rider picker and the current-task
picker.

Why not CustomTkinter's own CTkOptionMenu? Each time that widget draws
itself it forces the whole window to lay itself out again right away.
On a page with many widgets that made the Settings page take almost a
second longer to open. This button uses the very same drop-down list
underneath, but draws like an ordinary button, so it's quick.

It answers the same few calls the old menus did: `set()`, `get()`, and
`configure(values=[...])`.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk
from customtkinter.windows.widgets.core_widget_classes import DropdownMenu

from .. import theme as t
from ..icons import icon_image


class MenuButton(ctk.CTkButton):
    def __init__(
        self,
        master,
        palette: t.Palette,
        *,
        values: list[str],
        command: Callable[[str], None] | None = None,
        width: int = 240,
        height: int = 32,
        font=None,
        anchor: str = "w",
    ) -> None:
        self._menu_values = list(values)
        self._on_pick = command
        self._value = self._menu_values[0] if self._menu_values else ""
        super().__init__(
            master,
            text=self._value,
            width=width,
            height=height,
            anchor=anchor,
            corner_radius=t.CONTROL_RADIUS,
            fg_color=palette.control_bg,
            hover_color=palette.control_hover,
            text_color=palette.text_primary,
            image=icon_image("chevron_down", palette.text_secondary, 14),
            compound="right",
            font=font or t.font(size=t.FONT_BODY),
            command=self._open,
        )
        self._dropdown = DropdownMenu(
            master=self,
            values=self._menu_values,
            command=self._picked,
            fg_color=palette.card_bg_elevated,
            hover_color=palette.control_hover,
            text_color=palette.text_primary,
        )

    def _open(self) -> None:
        try:
            self._dropdown.open(
                self.winfo_rootx(),
                self.winfo_rooty() + self._apply_widget_scaling(self._current_height),
            )
        except Exception:
            pass

    def _picked(self, value: str) -> None:
        self.set(value)
        if self._on_pick is not None:
            self._on_pick(value)

    def set(self, value: str) -> None:
        self._value = value
        super().configure(text=value)

    def get(self) -> str:
        return self._value

    def configure(self, require_redraw=False, **kwargs):
        if "values" in kwargs:
            self._menu_values = list(kwargs.pop("values"))
            self._dropdown.configure(values=self._menu_values)
        if kwargs:
            super().configure(require_redraw=require_redraw, **kwargs)

    def cget(self, attribute_name: str):
        if attribute_name == "values":
            return list(self._menu_values)
        return super().cget(attribute_name)
