"""Tests for ui/router.py: which pages the side bar shows, in what order,
and moving between them. No window is opened anywhere in this file."""

import pytest

from lock_in.rider_themes import RIDER_THEMES, STANDARD_THEME
from lock_in.tier5 import TIER5_BUILDERS
from lock_in.ui.gestures import gesture_target
from lock_in.ui.router import (
    BUDDY_ROUTE_ID, RIDER_ROUTE_ID, TIER5_ROUTE_LABELS, Router, build_routes, route_ids,
    tier5_route_label,
)

MAIN = ["focus", "tasks", "blocking", "activity", "insights"]
BOTTOM = ["help", "settings"]


def routes_for(theme):
    return build_routes(theme.tier5_effect, theme.tier6_effect,
                        known_tier5_effects=TIER5_BUILDERS)


def test_plain_rider_gets_just_the_permanent_pages_in_order():
    ids = route_ids(build_routes())
    assert ids == MAIN + BOTTOM


def test_help_and_settings_are_pinned_at_the_bottom():
    routes = build_routes("hours_tab", "buddy_link")
    assert [r.id for r in routes if r.section == "bottom"] == BOTTOM
    assert route_ids(routes)[-2:] == BOTTOM


def test_tier5_rider_adds_one_rider_page_after_the_main_pages():
    ids = route_ids(build_routes("hours_tab"))
    assert ids == MAIN + [RIDER_ROUTE_ID] + BOTTOM


def test_revice_adds_the_buddy_page():
    ids = route_ids(build_routes("none", "buddy_link"))
    assert ids == MAIN + [BUDDY_ROUTE_ID] + BOTTOM


def test_wizard_adds_no_page():
    assert route_ids(build_routes("none", "mouse_gestures")) == MAIN + BOTTOM


def test_route_ids_are_unique_and_stable_not_labels():
    routes = build_routes("analytics_dashboard", "buddy_link")
    ids = route_ids(routes)
    assert len(ids) == len(set(ids))
    rider = next(r for r in routes if r.id == RIDER_ROUTE_ID)
    assert rider.label == "Analytics"          # the words can change...
    assert rider.id == "rider"                 # ...the name never does


@pytest.mark.parametrize("effect,label", sorted(TIER5_ROUTE_LABELS.items()))
def test_every_tier5_effect_has_its_page_label(effect, label):
    routes = build_routes(effect)
    assert next(r for r in routes if r.id == RIDER_ROUTE_ID).label == label


def test_all_ten_tier5_effects_have_a_builder_and_a_label():
    assert set(TIER5_ROUTE_LABELS) == set(TIER5_BUILDERS)
    assert len(TIER5_BUILDERS) == 10


def test_unknown_future_effect_still_gets_readable_words():
    assert tier5_route_label("brand_new_thing") == "Brand New Thing"


def test_effect_without_a_builder_gets_no_page():
    ids = route_ids(build_routes("not_built_yet", known_tier5_effects=TIER5_BUILDERS))
    assert RIDER_ROUTE_ID not in ids


@pytest.mark.parametrize("name", list(RIDER_THEMES))
def test_every_rider_gets_the_right_pages(name):
    theme = RIDER_THEMES[name]
    ids = route_ids(routes_for(theme))
    assert (RIDER_ROUTE_ID in ids) == (theme.tier5_effect != "none")
    assert (BUDDY_ROUTE_ID in ids) == (theme.tier6_effect == "buddy_link")
    assert ids[:5] == MAIN and ids[-2:] == BOTTOM


def test_standard_mode_gets_no_rider_or_buddy_page():
    assert route_ids(routes_for(STANDARD_THEME)) == MAIN + BOTTOM


# ---------------------------------------------------------------------- #
# The Router itself
# ---------------------------------------------------------------------- #
class Recorder:
    def __init__(self):
        self.calls = []

    def show(self, rid):
        self.calls.append(("show", rid))

    def hide(self, rid):
        self.calls.append(("hide", rid))


def make_router():
    rec = Recorder()
    changes = []
    router = Router(rec.show, rec.hide, on_change=changes.append)
    return router, rec, changes


def test_first_set_routes_opens_focus():
    router, rec, changes = make_router()
    assert router.set_routes(build_routes()) == "focus"
    assert router.active == "focus"
    assert rec.calls == [("show", "focus")]
    assert changes == ["focus"]


def test_navigate_hides_the_old_page_and_shows_the_new_one():
    router, rec, _ = make_router()
    router.set_routes(build_routes())
    rec.calls.clear()
    assert router.navigate("tasks")
    assert rec.calls == [("hide", "focus"), ("show", "tasks")]


def test_navigate_to_the_same_page_does_nothing():
    router, rec, _ = make_router()
    router.set_routes(build_routes())
    rec.calls.clear()
    assert router.navigate("focus")
    assert rec.calls == []


def test_navigate_to_an_unknown_page_is_refused():
    router, rec, _ = make_router()
    router.set_routes(build_routes())
    assert not router.navigate("nope")
    assert router.active == "focus"


def test_rider_change_keeps_the_page_you_were_on():
    router, _, _ = make_router()
    router.set_routes(build_routes("hours_tab"))
    router.navigate("settings")
    assert router.set_routes(build_routes("kanban_board")) == "settings"


def test_rider_change_removes_the_old_rider_page_and_falls_back_to_focus():
    router, _, _ = make_router()
    router.set_routes(build_routes("hours_tab"))
    router.navigate(RIDER_ROUTE_ID)
    assert router.set_routes(build_routes()) == "focus"
    assert not router.has(RIDER_ROUTE_ID)


def test_leaving_revice_removes_the_buddy_page():
    router, _, _ = make_router()
    router.set_routes(build_routes("none", "buddy_link"))
    router.navigate(BUDDY_ROUTE_ID)
    assert router.set_routes(build_routes()) == "focus"
    assert not router.has(BUDDY_ROUTE_ID)


# ---------------------------------------------------------------------- #
# Wizard's gestures move along the side bar's page names
# ---------------------------------------------------------------------- #
def test_wizard_line_right_goes_to_the_next_page():
    ids = route_ids(build_routes())
    assert gesture_target(ids, "tasks", "right") == "blocking"


def test_wizard_line_left_goes_to_the_page_above():
    ids = route_ids(build_routes())
    assert gesture_target(ids, "tasks", "left") == "focus"


def test_wizard_circle_goes_to_focus():
    ids = route_ids(build_routes("hours_tab"))
    assert gesture_target(ids, "settings", "circle") == "focus"


def test_wizard_never_wraps_around():
    ids = route_ids(build_routes())
    assert gesture_target(ids, "focus", "left") is None
    assert gesture_target(ids, "settings", "right") is None


def test_wizard_unsure_gesture_does_nothing():
    ids = route_ids(build_routes())
    assert gesture_target(ids, "tasks", None) is None
