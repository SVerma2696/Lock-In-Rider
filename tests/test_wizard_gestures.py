import math
import random

from lock_in.wizard_gestures import CIRCLE, LEFT, RIGHT, next_tab_name, recognize


def line(x0, y0, x1, y1, n=20, jitter=0.0):
    """Evenly spaced dots from one spot to another, optionally shaken a bit."""
    rng = random.Random(1)
    return [
        (
            x0 + (x1 - x0) * i / (n - 1) + rng.uniform(-jitter, jitter),
            y0 + (y1 - y0) * i / (n - 1) + rng.uniform(-jitter, jitter),
        )
        for i in range(n)
    ]


def circle(cx, cy, r, n=30, clockwise=True, turns=1.0):
    """Dots around a circle. `turns` below 1 leaves it open."""
    sign = 1 if clockwise else -1
    return [
        (
            cx + r * math.cos(sign * 2 * math.pi * turns * i / (n - 1)),
            cy + r * math.sin(sign * 2 * math.pi * turns * i / (n - 1)),
        )
        for i in range(n)
    ]


# --- recognize(): things that should be understood ------------------------ #

def test_clean_left_line_is_left():
    assert recognize(line(300, 100, 100, 100)) == LEFT


def test_clean_right_line_is_right():
    assert recognize(line(100, 100, 300, 100)) == RIGHT


def test_slightly_tilted_left_line_still_counts():
    assert recognize(line(300, 100, 100, 160)) == LEFT


def test_slightly_shaky_right_line_still_counts():
    assert recognize(line(100, 100, 300, 70, jitter=4)) == RIGHT


def test_clockwise_circle_is_circle():
    assert recognize(circle(200, 200, 60)) == CIRCLE


def test_counter_clockwise_circle_is_circle():
    assert recognize(circle(200, 200, 60, clockwise=False)) == CIRCLE


def test_circle_that_does_not_quite_close_still_counts():
    assert recognize(circle(200, 200, 60, turns=0.95)) == CIRCLE


# --- recognize(): things that should be ignored --------------------------- #

def test_empty_and_single_point_do_nothing():
    assert recognize([]) is None
    assert recognize([(1, 1)]) is None


def test_all_identical_points_do_nothing():
    assert recognize([(5, 5)] * 10) is None


def test_tiny_stroke_does_nothing():
    assert recognize(line(100, 100, 110, 105)) is None


def test_short_line_does_nothing():
    assert recognize(line(100, 100, 140, 100)) is None


def test_diagonal_does_nothing():
    assert recognize(line(100, 100, 250, 250)) is None


def test_vertical_line_does_nothing():
    assert recognize(line(100, 100, 100, 300)) is None


def test_zigzag_does_nothing():
    zigzag = [(100 + i * 10, 100 + (40 if i % 2 else 0)) for i in range(20)]
    assert recognize(zigzag) is None


def test_out_and_back_line_does_nothing():
    out_and_back = line(100, 100, 300, 100, 10) + line(300, 100, 110, 102, 10)
    assert recognize(out_and_back) is None


def test_half_circle_does_nothing():
    assert recognize(circle(200, 200, 60, turns=0.5)) is None


def test_very_small_circle_does_nothing():
    assert recognize(circle(200, 200, 20)) is None


# --- next_tab_name() ------------------------------------------------------- #

TABS = ["Tasks", "Blocking", "Activity", "Settings", "Help"]


def test_left_moves_to_previous_tab():
    assert next_tab_name(TABS, "Activity", LEFT) == "Blocking"


def test_right_moves_to_next_tab():
    assert next_tab_name(TABS, "Activity", RIGHT) == "Settings"


def test_left_on_first_tab_does_nothing():
    assert next_tab_name(TABS, "Tasks", LEFT) is None


def test_right_on_last_tab_does_nothing():
    assert next_tab_name(TABS, "Help", RIGHT) is None


def test_circle_goes_to_first_tab():
    assert next_tab_name(TABS, "Settings", CIRCLE) == "Tasks"


def test_extra_rider_tab_at_the_end_counts_as_a_tab():
    tabs = TABS + ["Priority"]
    assert next_tab_name(tabs, "Help", RIGHT) == "Priority"
    assert next_tab_name(tabs, "Priority", RIGHT) is None


def test_unknown_gesture_or_tab_does_nothing():
    assert next_tab_name(TABS, "Activity", None) is None
    assert next_tab_name(TABS, "Activity", "up") is None
    assert next_tab_name(TABS, "Nope", LEFT) is None
    assert next_tab_name([], "Tasks", LEFT) is None
