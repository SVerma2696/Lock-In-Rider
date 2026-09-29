"""
ui/pages/base.py
================
What every page has in common: a big title at the top, a short line
under it, and room below that scrolls if the window is too short.

Each real page (Focus, Tasks, Blocking...) is a small class that fills
in `build()`. Pages only DRAW things. When you click something, the page
asks the app to do it (for example `app._on_toggle()`), so the rules
about timers and blocking stay in one place.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import theme as t
from ..components.box import Box
from ..components.scroll_area import ScrollArea
from ..components.text import Anchor, Justify, Text

PAGE_PAD_X = t.SPACE_7 - 4  # the gap on the left and right of every page


def tasks_signature(tasks) -> tuple:
    """A short summary of every task that changes whenever anything a
    page shows changes. Pages compare it to skip redrawing when nothing
    is new."""
    return tuple(
        (t.id, t.name, t.status, tuple(t.phases), tuple((s.id, s.text, s.done) for s in t.subtasks))
        for t in tasks
    )


class ResponsiveGrid(Box):
    """A row of cards that wraps onto more lines when the window gets
    narrow. `min_width` is how thin one card is allowed to get."""

    def __init__(
        self, master, layout, *, min_width: int = 170, max_columns: int = 4, gap: int = t.SPACE_3
    ) -> None:
        super().__init__(master)
        self._layout = layout
        self._min_width = min_width
        self._max_columns = max_columns
        self._gap = gap
        self._items: list = []
        self._columns = 0
        self.bind("<Configure>", self._on_resize, add="+")

    def add(self, widget) -> None:
        self._items.append(widget)
        self._regrid(self._columns or min(self._max_columns, len(self._items)), force=True)

    def _on_resize(self, event) -> None:
        width = max(1, event.width)
        columns = max(
            1, min(self._max_columns, len(self._items) or 1, width // (self._min_width + self._gap))
        )
        self._regrid(columns)

    def _regrid(self, columns: int, force: bool = False) -> None:
        columns = max(1, columns)
        if columns == self._columns and not force:
            return
        self._columns = columns
        for c in range(self._max_columns):
            self.grid_columnconfigure(
                c, weight=1 if c < columns else 0, uniform="card" if c < columns else ""
            )
        half = self._gap // 2
        for index, widget in enumerate(self._items):
            row, column = divmod(index, columns)
            self._layout.grid(
                widget,
                total_columns=columns,
                row=row,
                column=column,
                sticky="nsew",
                padx=half,
                pady=half,
            )


class Page:
    route_id = ""
    scrollable = True

    def __init__(self, app, host) -> None:
        self.app = app
        self.palette: t.Palette = app.palette
        self.layout = app.layout
        self.frame = Box(host)
        self.scroll_area = None
        if self.scrollable:
            self.scroll_area = ScrollArea(
                self.frame,
                layout=self.layout,
                scrollbar_color=self.palette.control_bg,
                scrollbar_hover_color=self.palette.control_hover,
            )
            self.layout.pack(self.scroll_area, fill="both", expand=True)
            self.body = self.scroll_area.inner
        else:
            self.body = self.frame
        self.build()

    # ------------------------------------------------------------------ #
    def build(self) -> None:  # filled in by each page
        pass

    def on_show(self) -> None:  # runs each time the page opens
        pass

    def destroy(self) -> None:
        try:
            self.frame.destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Small helpers every page uses
    # ------------------------------------------------------------------ #
    def pack(self, widget, **kwargs):
        self.layout.pack(widget, **kwargs)
        return widget

    def page_header(self, title: str, subtitle: str = "", trailing=None) -> ctk.CTkFrame:
        head = Box(self.body)
        self.pack(head, fill="x", padx=PAGE_PAD_X, pady=(t.SPACE_6, t.SPACE_4))
        if trailing is not None:
            widget = trailing(head)
            self.pack(widget, side="right", anchor="s")
        words = Box(head)
        self.pack(words, side="left", fill="x", expand=True)
        self.title_label = Text(
            words,
            text=title,
            anchor="w",
            text_color=self.palette.text_primary,
            font=t.font(size=t.FONT_PAGE_TITLE, weight="bold"),
        )
        self.pack(self.title_label, anchor="w")
        if subtitle:
            self.subtitle_label = Text(
                words,
                text=subtitle,
                anchor="w",
                justify="left",
                wraplength=420 if trailing is not None else 560,
                text_color=self.palette.text_secondary,
                font=t.font(size=t.FONT_BODY),
            )
            self.pack(self.subtitle_label, anchor="w", fill="x")
        return head

    def section(self, **kwargs) -> ctk.CTkFrame:
        """A full-width holder with the page's side gaps."""
        frame = Box(self.body)
        pady = kwargs.pop("pady", (0, t.SPACE_4))
        self.pack(frame, fill="x", padx=PAGE_PAD_X, pady=pady, **kwargs)
        return frame

    def grid_row(
        self, min_width: int = 170, max_columns: int = 4, pady=(0, t.SPACE_3)
    ) -> ResponsiveGrid:
        grid = ResponsiveGrid(self.body, self.layout, min_width=min_width, max_columns=max_columns)
        # The grid adds half a gap around each card, so take that back off
        # the outer edge to line up with everything else on the page.
        self.pack(grid, fill="x", padx=PAGE_PAD_X - t.SPACE_3 // 2, pady=pady)
        return grid

    def label(
        self,
        master,
        text: str,
        *,
        size: int = t.FONT_BODY,
        color=None,
        bold: bool = False,
        wrap: int | None = None,
        anchor: Anchor = "w",
        justify: Justify = "left",
    ) -> Text:
        return Text(
            master,
            text,
            anchor=anchor,
            justify=justify,
            text_color=color or self.palette.text_primary,
            font=t.font(size=size, weight="bold" if bold else "normal"),
            wraplength=wrap or 0,
        )

    def switch(self, master, variable, command) -> ctk.CTkSwitch:
        """A switch in the Rider's color, with no words of its own (the
        row next to it already says what it does)."""
        return ctk.CTkSwitch(
            master,
            text="",
            variable=variable,
            command=command,
            width=46,
            progress_color=self.palette.accent_strong,
            button_color=t.SWITCH_KNOB,
            button_hover_color=t.SWITCH_KNOB_HOVER,
            fg_color=t.SWITCH_OFF,
            font=t.font(),
        )

    def segmented(self, master, values, command) -> ctk.CTkSegmentedButton:
        """A row of joined choices, like Light | Dark | System. Kept grey
        on purpose: the words must stay readable for every Rider, even
        ones whose color is almost white."""
        p = self.palette
        return ctk.CTkSegmentedButton(
            master,
            values=list(values),
            command=command,
            height=32,
            selected_color=t.SEGMENT_SELECTED,
            selected_hover_color=t.SEGMENT_SELECTED,
            unselected_color=p.control_bg,
            unselected_hover_color=p.control_hover,
            fg_color=p.control_bg,
            text_color=p.text_primary,
            font=t.font(size=t.FONT_BODY),
        )

    def icon(self, name: str, color=None):
        from ..icons import icon_image

        return icon_image(name, color or self.palette.text_secondary, t.ICON_SIZE)
