"""
ui/mirror.py
============
Kamen Rider Ryuki's gimmick: during a break, the WHOLE window flips
left-to-right, like looking in a mirror. The side bar jumps to the
right, words that sat on the left move to the right, and so on. When
focus starts again, everything flips back.

How: every time the app puts a widget on the screen, it goes through
`MirrorLayout` instead of calling Tk's .pack()/.grid()/.place() itself.
`MirrorLayout` writes down what was asked for. When a break starts or
ends, `sync()` puts every widget down again -- flipped or not.

The three `flip_*_kwargs` functions do the actual flipping. They take
the settings you were about to use and hand back the flipped ones. They
never touch a window, so they are tested on their own
(tests/test_ui_mirror.py).
"""

from __future__ import annotations

from collections.abc import Callable


def _flip_side(side):
    return {"left": "right", "right": "left"}.get(side, side)


def _flip_anchor_or_sticky(value):
    """Swaps every 'w' for 'e' and vice versa inside an anchor/sticky
    string (e.g. 'nw' -> 'ne'), leaving n/s/center parts untouched."""
    if value is None:
        return value
    return "".join({"w": "e", "e": "w"}.get(c, c) for c in value)


def _flip_asymmetric_padding(value):
    """A 2-tuple padx/ipadx like (10, 0) means (left, right) -- when
    `side` flips, the padding has to swap ends too, or the gap ends up
    on the wrong edge of the mirrored row. A single number (equal
    padding on both sides) is unaffected either way."""
    if isinstance(value, tuple) and len(value) == 2:
        return (value[1], value[0])
    return value


def flip_pack_kwargs(mirrored: bool, kwargs: dict) -> dict:
    """Given the kwargs you were about to pass to .pack(), return the
    kwargs to actually use -- flipped if `mirrored` is True, exactly
    as given otherwise."""
    if not mirrored:
        return dict(kwargs)
    result = dict(kwargs)
    if "side" in result:
        result["side"] = _flip_side(result["side"])
    if "anchor" in result:
        result["anchor"] = _flip_anchor_or_sticky(result["anchor"])
    if "padx" in result:
        result["padx"] = _flip_asymmetric_padding(result["padx"])
    if "ipadx" in result:
        result["ipadx"] = _flip_asymmetric_padding(result["ipadx"])
    return result


def flip_place_kwargs(mirrored: bool, kwargs: dict) -> dict:
    if not mirrored:
        return dict(kwargs)
    result = dict(kwargs)
    if "relx" in result:
        # round() sidesteps binary-float artifacts like 1 - 0.18 landing
        # on 0.8200000000000001 instead of 0.82.
        result["relx"] = round(1 - result["relx"], 10)
    if "anchor" in result:
        result["anchor"] = _flip_anchor_or_sticky(result["anchor"])
    return result


def flip_grid_kwargs(mirrored: bool, total_columns: int, kwargs: dict) -> dict:
    if not mirrored:
        return dict(kwargs)
    result = dict(kwargs)
    if "column" in result:
        columnspan = result.get("columnspan", 1)
        result["column"] = total_columns - result["column"] - columnspan
    if "sticky" in result:
        result["sticky"] = _flip_anchor_or_sticky(result["sticky"])
    if "padx" in result:
        result["padx"] = _flip_asymmetric_padding(result["padx"])
    return result


def mirrored_column(mirrored: bool, total_columns: int, column: int) -> int:
    """Which grid column a column ends up in once flipped. Used to move
    the "this column stretches" setting along with the widgets."""
    return total_columns - 1 - column if mirrored else column


class MirrorLayout:
    """Puts widgets on the screen and remembers how, so Ryuki's flip can
    redo them all at once. `is_mirrored` is asked fresh every time."""

    def __init__(self, is_mirrored: Callable[[], bool]) -> None:
        self._is_mirrored = is_mirrored
        # Keyed by Tk's own widget name, so putting the same widget down
        # twice replaces its old entry instead of piling up duplicates.
        self._widgets: dict = {}

    @property
    def mirrored(self) -> bool:
        return bool(self._is_mirrored())

    def pack(self, widget, **kwargs) -> None:
        widget.pack(**flip_pack_kwargs(self.mirrored, kwargs))
        self._widgets[str(widget)] = ("pack", widget, None, kwargs)

    def place(self, widget, **kwargs) -> None:
        widget.place(**flip_place_kwargs(self.mirrored, kwargs))
        self._widgets[str(widget)] = ("place", widget, None, kwargs)

    def grid(self, widget, total_columns: int = 1, **kwargs) -> None:
        widget.grid(**flip_grid_kwargs(self.mirrored, total_columns, kwargs))
        self._widgets[str(widget)] = ("grid", widget, total_columns, kwargs)

    def __len__(self) -> int:
        return len(self._widgets)

    def sync(self) -> None:
        """Put every remembered widget down again, flipped or not, to
        match right now. Widgets that were closed are forgotten.
        Widgets another feature hid on purpose stay hidden."""
        mirrored = self.mirrored
        dead_keys = []
        for key, (manager, widget, total_columns, kwargs) in list(self._widgets.items()):
            try:
                if not widget.winfo_exists():
                    dead_keys.append(key)
                    continue
                if not widget.winfo_manager():
                    # Hidden on purpose (pack_forget()/grid_remove()) --
                    # don't bring it back.
                    continue
                # Deliberately .pack()/.place()/.grid() here, NOT the
                # _configure() variants: CTkScrollableFrame overrides
                # .pack()/.place()/.grid() to move its outer frame, but
                # leaves pack_configure() alone -- calling that form would
                # start pack-managing the inner, canvas-embedded widget
                # itself and break its scrolling.
                if manager == "pack":
                    widget.pack(**flip_pack_kwargs(mirrored, kwargs))
                elif manager == "place":
                    widget.place(**flip_place_kwargs(mirrored, kwargs))
                else:
                    widget.grid(**flip_grid_kwargs(mirrored, total_columns, kwargs))
            except Exception:
                # A Tk error re-placing one widget must never stop the rest.
                pass
        for key in dead_keys:
            del self._widgets[key]
