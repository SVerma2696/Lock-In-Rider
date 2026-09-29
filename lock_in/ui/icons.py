"""
ui/icons.py
===========
Small line pictures for the side bar and the setting rows: a target for
Focus, a check box for Tasks, a shield for Blocking, and so on.

They are drawn right here with Pillow (the picture library the app
already uses), not loaded from files and not made from emoji. Emoji
look different on every computer; these look the same everywhere.

How it works: each picture is drawn 4 times too big, then shrunk down.
Shrinking smooths the edges, so the lines look clean instead of jaggy.

`draw_icon()` makes a plain picture and needs no window, so it can be
tested. `icon_image()` wraps it for CustomTkinter, with one color for
light mode and one for dark mode, and remembers what it already made.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from PIL import Image, ImageDraw

_SCALE = 4  # draw this many times bigger, then shrink
_CANVAS = 24  # every icon is designed on a 24 x 24 grid
_STROKE = 1.9  # line thickness on that grid


def _rgba(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4)) + (255,)


class _Pen:
    """Draws on the 24 x 24 grid, scaled up. Keeps each icon's code short."""

    def __init__(self, draw: ImageDraw.ImageDraw, color: tuple) -> None:
        self.d = draw
        self.c = color
        self.w = max(1, round(_STROKE * _SCALE))

    def _p(self, *xy):
        return [v * _SCALE for v in xy]

    def line(self, *xy) -> None:
        self.d.line(self._p(*xy), fill=self.c, width=self.w, joint="curve")
        # Round the two ends, so lines don't end in hard squares.
        r = self.w / 2
        for x, y in ((xy[0], xy[1]), (xy[-2], xy[-1])):
            cx, cy = x * _SCALE, y * _SCALE
            self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=self.c)

    def circle(self, cx, cy, r, fill=False) -> None:
        box = self._p(cx - r, cy - r, cx + r, cy + r)
        if fill:
            self.d.ellipse(box, fill=self.c)
        else:
            self.d.ellipse(box, outline=self.c, width=self.w)

    def rect(self, x0, y0, x1, y1, radius=2, fill=False) -> None:
        box = self._p(x0, y0, x1, y1)
        if fill:
            self.d.rounded_rectangle(box, radius=radius * _SCALE, fill=self.c)
        else:
            self.d.rounded_rectangle(box, radius=radius * _SCALE, outline=self.c, width=self.w)

    def arc(self, x0, y0, x1, y1, start, end) -> None:
        self.d.arc(self._p(x0, y0, x1, y1), start=start, end=end, fill=self.c, width=self.w)

    def polygon(self, points, fill=False) -> None:
        scaled = [(x * _SCALE, y * _SCALE) for x, y in points]
        if fill:
            self.d.polygon(scaled, fill=self.c)
        else:
            self.d.line(scaled + [scaled[0]], fill=self.c, width=self.w, joint="curve")


# ---------------------------------------------------------------------- #
# One small function per picture
# ---------------------------------------------------------------------- #
def _focus(p: _Pen) -> None:  # a target
    p.circle(12, 12, 9)
    p.circle(12, 12, 5)
    p.circle(12, 12, 1.6, fill=True)


def _tasks(p: _Pen) -> None:  # a check box
    p.rect(3.5, 3.5, 20.5, 20.5, radius=4)
    p.line(7.5, 12.5, 10.5, 15.5, 16.5, 8.5)


def _blocking(p: _Pen) -> None:  # a shield
    p.polygon([(12, 2.8), (19.5, 5.8), (19, 12.5), (12, 21.2), (5, 12.5), (4.5, 5.8)])


def _activity(p: _Pen) -> None:  # a heartbeat line
    p.line(2.5, 12.5, 7, 12.5, 9.5, 5.5, 14, 19, 16.5, 12.5, 21.5, 12.5)


def _insights(p: _Pen) -> None:  # a bar chart
    p.line(3.5, 20.5, 20.5, 20.5)
    p.line(7, 17, 7, 12)
    p.line(12, 17, 12, 6)
    p.line(17, 17, 17, 9.5)


def _settings(p: _Pen) -> None:  # a gear
    p.circle(12, 12, 3.2)
    p.circle(12, 12, 6.8)
    for i in range(8):
        a = math.radians(i * 45)
        p.line(
            12 + 7.2 * math.cos(a),
            12 + 7.2 * math.sin(a),
            12 + 9.6 * math.cos(a),
            12 + 9.6 * math.sin(a),
        )


def _help(p: _Pen) -> None:  # a question mark in a circle
    p.circle(12, 12, 9.2)
    p.arc(8.8, 6.2, 15.2, 12.6, 190, 400)
    p.line(12, 12.6, 12, 14.2)
    p.circle(12, 17.3, 1.2, fill=True)


def _buddy(p: _Pen) -> None:  # two people
    p.circle(9, 8.5, 3.3)
    p.arc(3, 14, 15, 25, 200, 340)
    p.circle(16.5, 9.5, 2.6)
    p.arc(13, 15.5, 22, 24, 220, 340)


def _clock(p: _Pen) -> None:
    p.circle(12, 12, 9)
    p.line(12, 7, 12, 12, 15.5, 14)


def _chart(p: _Pen) -> None:  # a line chart going up
    p.line(3.5, 20.5, 20.5, 20.5)
    p.line(3.5, 3.5, 3.5, 20.5)
    p.line(6.5, 16, 10.5, 11, 13.5, 13.5, 19.5, 6.5)


def _calendar(p: _Pen) -> None:
    p.rect(3.5, 5, 20.5, 20.5, radius=3)
    p.line(3.5, 9.5, 20.5, 9.5)
    p.line(8, 3, 8, 6.5)
    p.line(16, 3, 16, 6.5)


def _layers(p: _Pen) -> None:  # three stacked layers
    p.polygon([(12, 3.5), (21, 8), (12, 12.5), (3, 8)])
    p.line(3, 12, 12, 16.5, 21, 12)
    p.line(3, 16, 12, 20.5, 21, 16)


def _timeline(p: _Pen) -> None:  # dots on a line
    p.line(6, 3.5, 6, 20.5)
    p.circle(6, 6.5, 2, fill=True)
    p.circle(6, 12, 2, fill=True)
    p.circle(6, 17.5, 2, fill=True)
    p.line(10, 6.5, 20, 6.5)
    p.line(10, 12, 18, 12)
    p.line(10, 17.5, 16, 17.5)


def _history(p: _Pen) -> None:  # a clock with a back arrow
    p.arc(3.5, 3.5, 20.5, 20.5, 200, 520)
    p.line(3.8, 6.5, 4.5, 10.5, 8.5, 9.8)
    p.line(12, 8, 12, 12, 15, 14)


def _badge(p: _Pen) -> None:  # a medal
    p.circle(12, 9.5, 6)
    p.line(8.5, 14.5, 7, 21, 12, 18.5, 17, 21, 15.5, 14.5)


def _flag(p: _Pen) -> None:
    p.line(5, 21, 5, 3.5)
    p.polygon([(5, 4), (19, 4), (16, 8.5), (19, 13), (5, 13)])


def _board(p: _Pen) -> None:  # three columns
    p.rect(3, 4, 21, 20, radius=3)
    p.line(9, 4, 9, 20)
    p.line(15, 4, 15, 20)


def _ordered(p: _Pen) -> None:  # a numbered list
    p.line(10, 6.5, 20.5, 6.5)
    p.line(10, 12, 20.5, 12)
    p.line(10, 17.5, 20.5, 17.5)
    p.circle(5, 6.5, 1.6, fill=True)
    p.circle(5, 12, 1.6, fill=True)
    p.circle(5, 17.5, 1.6, fill=True)


def _star(p: _Pen) -> None:
    pts = []
    for i in range(10):
        r = 9 if i % 2 == 0 else 4
        a = math.radians(-90 + i * 36)
        pts.append((12 + r * math.cos(a), 12.5 + r * math.sin(a)))
    p.polygon(pts)


def _camera(p: _Pen) -> None:
    p.rect(3, 7, 21, 19, radius=3)
    p.line(8.5, 7, 10, 4.5, 14, 4.5, 15.5, 7)
    p.circle(12, 13, 3.3)


def _eye(p: _Pen) -> None:
    p.arc(2.5, 5, 21.5, 23, 205, 335)
    p.arc(2.5, 1, 21.5, 19, 25, 155)
    p.circle(12, 12, 2.8)


def _palette(p: _Pen) -> None:  # a paint drop / appearance
    p.circle(12, 12, 9)
    p.circle(8, 10, 1.4, fill=True)
    p.circle(12, 7.2, 1.4, fill=True)
    p.circle(16, 10, 1.4, fill=True)
    p.circle(15, 15.5, 2.2)


def _spark(p: _Pen) -> None:  # a spark, for the Claude helper
    p.polygon(
        [(12, 2.5), (14, 10), (21.5, 12), (14, 14), (12, 21.5), (10, 14), (2.5, 12), (10, 10)]
    )


def _refresh(p: _Pen) -> None:  # a circle arrow, for updates
    p.arc(4, 4, 20, 20, 300, 600)
    p.line(20, 4.5, 20, 9.2, 15.3, 9.2)


def _bell(p: _Pen) -> None:
    p.arc(5.5, 4, 18.5, 17, 180, 360)
    p.line(5.5, 10.5, 5.5, 16, 3.5, 18, 20.5, 18, 18.5, 16, 18.5, 10.5)
    p.line(10, 21, 14, 21)


def _timer(p: _Pen) -> None:  # a stopwatch
    p.circle(12, 13.5, 7.8)
    p.line(10, 2.8, 14, 2.8)
    p.line(12, 9.5, 12, 13.5)


def _list(p: _Pen) -> None:
    p.line(4, 6.5, 20, 6.5)
    p.line(4, 12, 20, 12)
    p.line(4, 17.5, 14, 17.5)


def _lock(p: _Pen) -> None:
    p.rect(5, 10.5, 19, 20.5, radius=2.5)
    p.arc(8, 3.5, 16, 14, 180, 360)
    p.line(8, 8.8, 8, 10.5)
    p.line(16, 8.8, 16, 10.5)


def _plus(p: _Pen) -> None:
    p.line(12, 5, 12, 19)
    p.line(5, 12, 19, 12)


def _chevron_down(p: _Pen) -> None:
    p.line(6.5, 9.5, 12, 15, 17.5, 9.5)


def _chevron_right(p: _Pen) -> None:
    p.line(9.5, 6.5, 15, 12, 9.5, 17.5)


def _hand(p: _Pen) -> None:  # a pointer swipe, for gestures
    p.line(4, 12, 20, 12)
    p.line(15, 7, 20, 12, 15, 17)


_ICONS: dict[str, Callable[[_Pen], None]] = {
    "focus": _focus,
    "tasks": _tasks,
    "blocking": _blocking,
    "activity": _activity,
    "insights": _insights,
    "settings": _settings,
    "help": _help,
    "buddy": _buddy,
    "clock": _clock,
    "chart": _chart,
    "calendar": _calendar,
    "layers": _layers,
    "timeline": _timeline,
    "history": _history,
    "badge": _badge,
    "flag": _flag,
    "board": _board,
    "ordered": _ordered,
    "star": _star,
    "camera": _camera,
    "eye": _eye,
    "palette": _palette,
    "spark": _spark,
    "refresh": _refresh,
    "bell": _bell,
    "timer": _timer,
    "list": _list,
    "lock": _lock,
    "plus": _plus,
    "chevron_down": _chevron_down,
    "chevron_right": _chevron_right,
    "gesture": _hand,
}

ICON_NAMES = frozenset(_ICONS)
FALLBACK_ICON = "star"


def draw_icon(name: str, size: int, color: str) -> Image.Image:
    """Make one icon as a see-through picture, `size` pixels square, in
    one color. An unknown name gets the star, never an error."""
    painter = _ICONS.get(name, _ICONS[FALLBACK_ICON])
    big = _CANVAS * _SCALE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    painter(_Pen(ImageDraw.Draw(image, "RGBA"), _rgba(color)))
    # Box averaging keeps the color exact (Lanczos overshoots at edges).
    return image.resize((size, size), Image.Resampling.BOX)


_cache: dict = {}


def icon_image(name: str, color_pair: tuple, size: int = 18):
    """A CustomTkinter picture of one icon: the first color in light
    mode, the second in dark mode. Made once, then reused."""
    import customtkinter as ctk

    key = (name, tuple(color_pair), size)
    image = _cache.get(key)
    if image is None:
        # Drawn at 2x and shown at `size`, so it stays sharp on a
        # high-resolution screen too.
        image = ctk.CTkImage(
            light_image=draw_icon(name, size * 2, color_pair[0]),
            dark_image=draw_icon(name, size * 2, color_pair[1]),
            size=(size, size),
        )
        _cache[key] = image
    return image
