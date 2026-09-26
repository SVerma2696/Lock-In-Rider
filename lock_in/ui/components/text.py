"""
ui/components/text.py
=====================
`Text`: a plain label for words -- titles, descriptions, numbers.

A CustomTkinter label (CTkLabel) is really a little drawing canvas with
a label inside it, which is what lets it have rounded corners and a
picture. Plain words need none of that, and pages have a LOT of plain
words (the Help and Settings pages have about 80 labels each). A normal
Tk label draws about twice as fast, so pages open quicker.

It still acts like the rest of the app:

- its colors are (light, dark) pairs and it switches with light/dark
  mode, using CustomTkinter's own mode tracker;
- its background is taken from whatever it sits on (a card, the page);
- it understands `configure(text=..., text_color=...)` and
  `cget("text")`, like the CTkLabels it replaces.
"""

from __future__ import annotations

import tkinter

from customtkinter.windows.widgets.appearance_mode import CTkAppearanceModeBaseClass

from .. import theme as t


def background_of(widget):
    """The (light, dark) color of the nearest thing behind `widget` that
    actually has a color -- see-through holders are skipped."""
    while widget is not None:
        try:
            color = widget.cget("fg_color")
        except Exception:
            color = None
        if color is not None and color != "transparent":
            return color
        widget = getattr(widget, "master", None)
    return t.APP_BG


class Text(tkinter.Label, CTkAppearanceModeBaseClass):
    def __init__(self, master, text: str = "", *, text_color=t.TEXT_PRIMARY, font=None,
                 anchor: str = "w", justify: str = "left", wraplength: int = 0,
                 pady: int = 2) -> None:
        self._text_color = text_color
        self._background = background_of(master)
        tkinter.Label.__init__(
            self, master, text=text, font=font or t.font(), anchor=anchor, justify=justify,
            wraplength=wraplength, bd=0, highlightthickness=0, padx=0, pady=pady,
        )
        CTkAppearanceModeBaseClass.__init__(self)
        self._recolor()

    def _recolor(self) -> None:
        tkinter.Label.configure(
            self,
            fg=self._apply_appearance_mode(self._text_color),
            bg=self._apply_appearance_mode(self._background),
        )

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        self._recolor()

    def configure(self, cnf=None, **kwargs):
        recolor = False
        if "text_color" in kwargs:
            self._text_color = kwargs.pop("text_color")
            recolor = True
        kwargs.pop("fg_color", None)   # a Text never has its own box color
        if cnf or kwargs:
            tkinter.Label.configure(self, cnf, **kwargs)
        if recolor:
            self._recolor()

    config = configure

    def cget(self, key: str):
        if key == "text_color":
            return self._text_color
        return tkinter.Label.cget(self, key)

    def destroy(self) -> None:
        CTkAppearanceModeBaseClass.destroy(self)
        tkinter.Label.destroy(self)
