"""Tests for the small pieces of the new screen code that need no
window: the icons, the Insights numbers, the Tasks page filters, the
Settings page's Rider rows, Ryuki's mirror helper, and Standard Mode
turning every Rider effect off."""

from datetime import date

import pytest

from lock_in.history import SessionRecord
from lock_in.rider_themes import RIDER_THEMES, STANDARD_THEME
from lock_in.tasks import Subtask, Task, TaskStatus
from lock_in.ui.icons import FALLBACK_ICON, ICON_NAMES, draw_icon
from lock_in.ui.insights_data import format_duration, summarize
from lock_in.ui.mirror import MirrorLayout, flip_grid_kwargs, mirrored_column
from lock_in.ui.router import TIER5_ROUTE_ICONS

# These page modules import customtkinter (installed with the app), but
# importing them never opens a window.
from lock_in.ui.pages.settings import TIER2_PRESET_ROWS, rider_power_parts
from lock_in.ui.pages.tasks import filter_tasks, step_progress


# ---------------------------------------------------------------------- #
# Icons
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize("name", sorted(ICON_NAMES))
def test_every_icon_draws_something_the_right_size(name):
    image = draw_icon(name, 36, "#ff0000")
    assert image.size == (36, 36)
    assert image.mode == "RGBA"
    assert image.getbbox() is not None       # not blank


def test_sidebar_and_rider_page_icons_all_exist():
    for name in ("focus", "tasks", "blocking", "activity", "insights",
                 "help", "settings", "buddy"):
        assert name in ICON_NAMES
    for name in TIER5_ROUTE_ICONS.values():
        assert name in ICON_NAMES


def test_unknown_icon_falls_back_instead_of_crashing():
    assert draw_icon("does-not-exist", 20, "#000000").tobytes() == \
        draw_icon(FALLBACK_ICON, 20, "#000000").tobytes()


def test_icon_uses_only_the_color_asked_for():
    image = draw_icon("tasks", 24, "#3366cc")
    raw = image.tobytes()
    pixels = [raw[i:i + 4] for i in range(0, len(raw), 4)]
    colors = {tuple(px[:3]) for px in pixels if px[3] > 250}
    assert colors == {(0x33, 0x66, 0xcc)}


# ---------------------------------------------------------------------- #
# Insights numbers
# ---------------------------------------------------------------------- #
def rec(start, seconds, completed=True, task=None):
    return SessionRecord(start=start, end=start, duration_seconds=seconds,
                         task_id=task, completed=completed)


def task(status, name="t"):
    return Task(id=name, name=name, status=status)


def test_insights_add_up_today_week_and_all_time():
    today = date(2026, 9, 25)
    records = [
        rec("2026-09-25T09:00:00", 1500),
        rec("2026-09-25T10:00:00", 600, completed=False),
        rec("2026-09-20T09:00:00", 1200),       # inside the last 7 days
        rec("2026-09-01T09:00:00", 3000),       # older
    ]
    n = summarize(records, [], today)
    assert n.today_seconds == 2100
    assert n.week_seconds == 3300
    assert n.all_time_seconds == 6300
    assert n.blocks_logged == 4
    assert n.blocks_finished == 3
    assert n.average_block_seconds == 6300 // 4
    assert n.active_days == 3
    assert n.finish_rate == pytest.approx(0.75)


def test_insights_count_tasks_by_status():
    tasks = [task(TaskStatus.TODO, "a"), task(TaskStatus.IN_PROGRESS, "b"),
             task(TaskStatus.DONE, "c"), task(TaskStatus.DONE, "d")]
    n = summarize([], tasks, date(2026, 9, 25))
    assert (n.tasks_open, n.tasks_in_progress, n.tasks_done) == (1, 1, 2)


def test_insights_empty_history_is_all_zero_not_an_error():
    n = summarize([], [], date(2026, 9, 25))
    assert n.all_time_seconds == 0 and n.average_block_seconds == 0
    assert n.finish_rate == 0.0


def test_insights_skip_a_broken_start_time():
    n = summarize([rec("not a date", 600)], [], date(2026, 9, 25))
    assert n.all_time_seconds == 0


def test_format_duration():
    assert format_duration(0) == "0m"
    assert format_duration(600) == "10m"
    assert format_duration(3900) == "1h 5m"


# ---------------------------------------------------------------------- #
# Tasks page helpers
# ---------------------------------------------------------------------- #
def test_task_filters():
    open_tasks, done_tasks = ["a", "b"], ["c"]
    assert filter_tasks(open_tasks, done_tasks, "All") == (["a", "b"], ["c"])
    assert filter_tasks(open_tasks, done_tasks, "Active") == (["a", "b"], [])
    assert filter_tasks(open_tasks, done_tasks, "Done") == ([], ["c"])


def test_step_progress():
    t = Task(id="x", name="x")
    assert step_progress(t) == ""
    t.subtasks = [Subtask(id="1", text="a", done=True)]
    assert step_progress(t) == "1/1 step"
    t.subtasks.append(Subtask(id="2", text="b"))
    assert step_progress(t) == "1/2 steps"


# ---------------------------------------------------------------------- #
# Tier 2 and other Rider rows on the Settings page
# ---------------------------------------------------------------------- #
def test_tier2_effects_are_on_exactly_kuuga_super1_and_gavv():
    with_tier2 = {name: th.tier2_effect for name, th in RIDER_THEMES.items()
                  if th.tier2_effect != "none"}
    assert with_tier2 == {
        "Kamen Rider Kuuga (2000)": "interval_presets",
        "Kamen Rider Super-1 (1980)": "task_presets",
        "Kamen Rider Gavv (2024)": "micro_sprint",
    }


def test_rider_power_rows():
    assert rider_power_parts(RIDER_THEMES["Kamen Rider Kuuga (2000)"]) == ["presets"]
    assert rider_power_parts(RIDER_THEMES["Kamen Rider Super-1 (1980)"]) == ["presets"]
    assert rider_power_parts(RIDER_THEMES["Kamen Rider Gavv (2024)"]) == ["micro_sprint"]
    assert rider_power_parts(RIDER_THEMES["Kamen Rider Black RX (1988)"]) == ["manual_breaks"]
    assert rider_power_parts(RIDER_THEMES["Kamen Rider Wizard (2012)"]) == ["gestures"]
    assert rider_power_parts(RIDER_THEMES["Kamen Rider (1971)"]) == []


def test_kuuga_has_four_presets_and_super1_five():
    assert len(TIER2_PRESET_ROWS["interval_presets"][0]) == 4
    assert len(TIER2_PRESET_ROWS["task_presets"][0]) == 5


def test_standard_mode_has_no_rider_rows_and_no_effects_at_all():
    assert rider_power_parts(STANDARD_THEME) == []
    for tier in (1, 2, 3, 4, 5, 6):
        assert getattr(STANDARD_THEME, f"tier{tier}_effect") == "none"


# ---------------------------------------------------------------------- #
# Ryuki's mirror helpers
# ---------------------------------------------------------------------- #
def test_grid_padding_swaps_ends_when_mirrored():
    assert flip_grid_kwargs(True, 2, {"column": 0, "padx": (0, 8)}) == {"column": 1, "padx": (8, 0)}


def test_side_bar_and_page_area_swap_columns():
    assert flip_grid_kwargs(True, 2, {"column": 0})["column"] == 1   # side bar
    assert flip_grid_kwargs(True, 2, {"column": 1})["column"] == 0   # page area
    # The top bar spans both columns, so it stays put.
    assert flip_grid_kwargs(True, 2, {"column": 0, "columnspan": 2})["column"] == 0


def test_mirrored_column():
    assert mirrored_column(False, 2, 1) == 1
    assert mirrored_column(True, 2, 1) == 0


class FakeWidget:
    """Just enough of a Tk widget for MirrorLayout."""

    def __init__(self, name):
        self.name = name
        self.calls = []
        self.alive = True
        self.managed = True

    def __str__(self):
        return self.name

    def pack(self, **kw):
        self.calls.append(("pack", kw))

    def grid(self, **kw):
        self.calls.append(("grid", kw))

    def place(self, **kw):
        self.calls.append(("place", kw))

    def winfo_exists(self):
        return self.alive

    def winfo_manager(self):
        return "pack" if self.managed else ""


def test_mirror_layout_flips_everything_on_sync():
    state = {"mirrored": False}
    layout = MirrorLayout(lambda: state["mirrored"])
    w = FakeWidget(".a")
    layout.pack(w, side="left")
    assert w.calls[-1] == ("pack", {"side": "left"})
    state["mirrored"] = True
    layout.sync()
    assert w.calls[-1] == ("pack", {"side": "right"})


def test_mirror_layout_never_brings_back_a_hidden_widget():
    state = {"mirrored": False}
    layout = MirrorLayout(lambda: state["mirrored"])
    w = FakeWidget(".hidden")
    layout.pack(w, side="left")
    w.managed = False                  # another feature hid it on purpose
    state["mirrored"] = True
    before = len(w.calls)
    layout.sync()
    assert len(w.calls) == before


def test_mirror_layout_forgets_closed_widgets():
    layout = MirrorLayout(lambda: False)
    w = FakeWidget(".gone")
    layout.grid(w, total_columns=2, column=0)
    assert len(layout) == 1
    w.alive = False
    layout.sync()
    assert len(layout) == 0


def test_mirror_layout_replaces_instead_of_piling_up():
    layout = MirrorLayout(lambda: False)
    w = FakeWidget(".same")
    layout.pack(w, side="left")
    layout.pack(w, side="right")
    assert len(layout) == 1
