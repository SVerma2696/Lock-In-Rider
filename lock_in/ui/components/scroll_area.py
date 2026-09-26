"""
ui/components/scroll_area.py
============================
`ScrollArea`: the part of a page that scrolls when the page is taller
than the window. Put widgets in `area.inner`.

Why not CustomTkinter's CTkScrollableFrame? Its scrollbar makes the
whole window lay itself out again every single time it draws -- even
while it's first being made. That was one of the biggest reasons pages
and Rider changes felt slow. This version:

- uses a scrollbar that draws without forcing that extra layout
  (`CalmScrollbar`), so Tk lays things out once, when it's ready;
- hides the scrollbar when everything already fits, and shows it again
  when it doesn't;
- scrolls with the mouse wheel on Windows, macOS, and Linux.

The inner area is always as wide as the visible area, so pages lay out
exactly as before.
"""

from __future__ import annotations

import sys
import tkinter
import weakref

import customtkinter as ctk

from .box import Box


class CalmScrollbar(ctk.CTkScrollbar):
    """A CTkScrollbar that doesn't force the whole window to lay itself
    out every time it redraws (the library does that on purpose, but it
    isn't needed here and it's slow on busy pages)."""

    def _draw(self, no_color_updates: bool = False) -> None:
        canvas = getattr(self, "_canvas", None)
        if canvas is not None and "update_idletasks" not in canvas.__dict__:
            canvas.update_idletasks = lambda: None
        super()._draw(no_color_updates)


# Every scroll area on screen, so ONE mouse-wheel handler can find the one
# under the mouse. Weak, so closed pages are forgotten automatically.
_AREAS: "weakref.WeakSet[ScrollArea]" = weakref.WeakSet()
_WHEEL_BOUND = False


def _area_under(widget):
    """The scroll area that contains `widget`, if any. Tk widget names
    are paths like '.!box.!canvas.!box3', so "inside" means "starts with"."""
    name = str(widget)
    best = None
    for area in list(_AREAS):
        try:
            prefix = str(area.canvas)
        except Exception:
            continue
        if name == prefix or name.startswith(prefix + "."):
            # The deepest match wins (a scroll area inside another one).
            if best is None or len(prefix) > len(str(best.canvas)):
                best = area
    return best


def _on_wheel(event) -> None:
    area = _area_under(event.widget)
    if area is None:
        return
    if getattr(event, "num", None) == 4:
        steps = -1
    elif getattr(event, "num", None) == 5:
        steps = 1
    elif sys.platform == "darwin":
        steps = -event.delta
    else:
        steps = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
    area.scroll(steps)


class ScrollArea(Box):
    def __init__(self, master, *, layout, scrollbar_color, scrollbar_hover_color) -> None:
        super().__init__(master)
        global _WHEEL_BOUND
        self._layout = layout
        self._canvas_bg = None
        self.canvas = tkinter.Canvas(self, highlightthickness=0, bd=0)
        self.scrollbar = CalmScrollbar(
            self, orientation="vertical", width=12, command=self.canvas.yview,
            button_color=scrollbar_color, button_hover_color=scrollbar_hover_color,
            fg_color="transparent",
        )
        self._scrollbar_shown = False
        layout.pack(self.canvas, side="left", fill="both", expand=True)

        # The canvas is a plain Tk widget with one fixed color, so the
        # inner box is told the real (light, dark) pair outright -- that way
        # everything inside still follows light and dark mode.
        self.inner = Box(self.canvas, fg_color=self._bg_color, bg_color=self._bg_color)
        self._window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll_moved)
        self.inner.bind("<Configure>", self._on_inner_resized, add="+")
        self.canvas.bind("<Configure>", self._on_canvas_resized, add="+")
        self._paint_canvas()

        _AREAS.add(self)
        if not _WHEEL_BOUND:
            root = self.winfo_toplevel()
            root.bind_all("<MouseWheel>", _on_wheel, add="+")
            root.bind_all("<Button-4>", _on_wheel, add="+")
            root.bind_all("<Button-5>", _on_wheel, add="+")
            _WHEEL_BOUND = True

    # ------------------------------------------------------------------ #
    def _paint_canvas(self) -> None:
        """The canvas is a plain Tk widget, so it gets the background
        color of whatever this area sits on, for the current mode."""
        color = self._apply_appearance_mode(self._bg_color)
        if color != self._canvas_bg:
            self._canvas_bg = color
            self.canvas.configure(bg=color)

    def _draw(self, no_color_updates: bool = False) -> None:
        super()._draw(no_color_updates)
        if hasattr(self, "canvas"):
            self._paint_canvas()

    def _on_inner_resized(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resized(self, event) -> None:
        # Keep the inner area exactly as wide as what you can see.
        self.canvas.itemconfigure(self._window, width=event.width)

    def _on_scroll_moved(self, first, last) -> None:
        first, last = float(first), float(last)
        needed = first > 0.0 or last < 1.0
        if needed and not self._scrollbar_shown:
            self._layout.pack(self.scrollbar, side="right", fill="y", before=self.canvas)
            self._scrollbar_shown = True
        elif not needed and self._scrollbar_shown:
            self.scrollbar.pack_forget()
            self._scrollbar_shown = False
        if self._scrollbar_shown:
            self.scrollbar.set(first, last)

    def scroll(self, steps: int) -> None:
        if self._scrollbar_shown:
            self.canvas.yview_scroll(steps, "units")

    def scroll_to(self, fraction: float) -> None:
        self.canvas.yview_moveto(fraction)

    def destroy(self) -> None:
        _AREAS.discard(self)
        super().destroy()
