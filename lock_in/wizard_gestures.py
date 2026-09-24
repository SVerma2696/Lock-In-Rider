"""
wizard_gestures.py
===================
Kamen Rider Wizard's whole trick, in plain math. While you hold the right
mouse button and drag on the Lock In window, the app writes down where the
mouse went. When you let go, this file looks at that list of dots and
decides: did you draw a line to the left, a line to the right, a circle,
or just wiggle around?

Nothing in here touches the window, the mouse, or the disk. It gets a list
of (x, y) dots in and hands one word back. That is on purpose: it means
every rule below can be tested without opening the app.

There is no magic here, only measurements using Python's built-in `math`,
so the same drawing always gets the same answer.

The numbers below are in "pixels" (the tiny dots on your screen). Each
one has a comment saying what it means in plain words, so you can change
one and see what happens.
"""

from __future__ import annotations

import math

# A drawing needs at least this many dots before we even look at it.
MIN_POINTS = 5
# If the whole drawing fits in a box smaller than this on both sides, it
# was just a wiggle or a click, so we ignore it.
MIN_STROKE_PIXELS = 30

# A left/right line has to go at least this far sideways.
MIN_SWIPE_PIXELS = 60
# How much up-and-down is allowed, compared with sideways. 0.5 means "up
# to half as much up-and-down as sideways": a slightly tilted line is
# fine, a diagonal is not.
MAX_SWIPE_SLOPE = 0.5
# How wobbly a line may be. The path the mouse walked may be at most this
# many times longer than the straight distance from start to end.
MAX_SWIPE_WIGGLE = 1.3

# A circle's box must be at least this big on both sides.
MIN_CIRCLE_PIXELS = 50
# The end of a circle has to come back near its start: at most this
# fraction of the drawing's biggest side away.
CIRCLE_CLOSE_FRACTION = 0.35
# A circle's box is roughly square: the longer side may be at most this
# many times the shorter side.
CIRCLE_MAX_ASPECT = 2.0
# A circle really went around: the path walked must be at least this many
# times the drawing's biggest side. (A perfect circle is about 3.1 times.)
CIRCLE_MIN_PATH_RATIO = 2.5

LEFT = "left"
RIGHT = "right"
CIRCLE = "circle"


def _path_length(points) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def recognize(points) -> str | None:
    """
    Turn the dots you drew into "left", "right", "circle", or None.

    None means "not sure" -- and when the app isn't sure it does nothing
    at all, so a wobbly drag never causes a surprise.
    """
    if len(points) < MIN_POINTS:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    biggest = max(width, height)
    smallest = min(width, height)
    if biggest < MIN_STROKE_PIXELS:
        return None

    path = _path_length(points)
    start, end = points[0], points[-1]

    # Circle: comes back near where it started, roughly square, went around.
    if (
        smallest >= MIN_CIRCLE_PIXELS
        and math.dist(start, end) <= CIRCLE_CLOSE_FRACTION * biggest
        and biggest <= CIRCLE_MAX_ASPECT * smallest
        and path >= CIRCLE_MIN_PATH_RATIO * biggest
    ):
        return CIRCLE

    # Swipe: mostly sideways, long enough, and mostly straight.
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if (
        abs(dx) >= MIN_SWIPE_PIXELS
        and abs(dy) <= MAX_SWIPE_SLOPE * abs(dx)
        and path <= MAX_SWIPE_WIGGLE * math.hypot(dx, dy)
    ):
        return LEFT if dx < 0 else RIGHT

    return None


def next_tab_name(tab_names, current, gesture) -> str | None:
    """
    Given the tabs in the order they're shown, which tab you're on, and
    what you drew, say which tab to go to -- or None to stay put.

    Left and right move one tab and never wrap around. A circle goes to
    the first tab.
    """
    if not tab_names or current not in tab_names:
        return None
    index = tab_names.index(current)
    if gesture == CIRCLE:
        return tab_names[0]
    if gesture == LEFT:
        return tab_names[index - 1] if index > 0 else None
    if gesture == RIGHT:
        return tab_names[index + 1] if index < len(tab_names) - 1 else None
    return None
