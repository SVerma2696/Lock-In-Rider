"""
ui/router.py
============
The list of pages in the side bar, and which one is showing.

Every page has a fixed name made for the app, like "focus" or
"settings" (its `id`). The app only ever uses those names to move
around -- never the words printed on the button, because those words
can change (for example, "Hours" vs "Analytics").

The list is built fresh from the picked Rider:

    Focus, Tasks, Blocking, Activity, Insights     (always)
    one Rider page                                 (Tier 5 Riders only)
    Buddy                                          (Revice only)
    Help, Settings                                 (always, at the bottom)

`build_routes()` and `Router` don't touch the window at all, so they are
tested without one (tests/test_ui_router.py). The window side lives in
components/sidebar.py and app.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

# Tier 5's extra page: effect string (RiderTheme.tier5_effect) -> the
# words on its side bar button. A new Tier 5 Rider only needs a line here
# (and its builder in lock_in/tier5/__init__.py).
TIER5_ROUTE_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
    "history_editor": "History", "kanban_board": "Board", "week_compare": "Week",
    "goal_streak": "Goal", "badge_cards": "Badges", "phase_combo": "Combo",
    "priority_order": "Priority",
}

# ...and the little picture next to those words.
TIER5_ROUTE_ICONS = {
    "hours_tab": "clock", "timeline_view": "timeline", "analytics_dashboard": "chart",
    "history_editor": "history", "kanban_board": "board", "week_compare": "calendar",
    "goal_streak": "flag", "badge_cards": "badge", "phase_combo": "layers",
    "priority_order": "ordered",
}

RIDER_ROUTE_ID = "rider"
BUDDY_ROUTE_ID = "buddy"
FIRST_ROUTE_ID = "focus"


@dataclass(frozen=True)
class Route:
    id: str
    label: str
    icon: str
    # "main" sits at the top of the side bar, "rider" under it (with a
    # small heading), "bottom" is pinned at the bottom.
    section: str = "main"


MAIN_ROUTES = (
    Route("focus", "Focus", "focus"),
    Route("tasks", "Tasks", "tasks"),
    Route("blocking", "Blocking", "blocking"),
    Route("activity", "Activity", "activity"),
    Route("insights", "Insights", "insights"),
)

BOTTOM_ROUTES = (
    Route("help", "Help", "help", "bottom"),
    Route("settings", "Settings", "settings", "bottom"),
)


def tier5_route_label(effect: str) -> str:
    """The side bar words for a Tier 5 effect. A brand-new effect with
    no entry yet still gets readable words instead of an error."""
    return TIER5_ROUTE_LABELS.get(effect, effect.replace("_", " ").title())


def build_routes(tier5_effect: str = "none", tier6_effect: str = "none",
                 known_tier5_effects=None) -> List[Route]:
    """Every page, in the order the side bar shows them (top to bottom).

    `known_tier5_effects` is the set of Tier 5 effects that actually
    have a page builder. An effect missing from it gets no page, so a
    half-added Rider can never show a broken page. None means "trust
    the effect"."""
    routes = list(MAIN_ROUTES)
    if tier5_effect and tier5_effect != "none" and (
            known_tier5_effects is None or tier5_effect in known_tier5_effects):
        routes.append(Route(
            RIDER_ROUTE_ID, tier5_route_label(tier5_effect),
            TIER5_ROUTE_ICONS.get(tier5_effect, "star"), "rider",
        ))
    if tier6_effect == "buddy_link":
        routes.append(Route(BUDDY_ROUTE_ID, "Buddy", "buddy", "rider"))
    routes.extend(BOTTOM_ROUTES)
    return routes


def route_ids(routes: List[Route]) -> List[str]:
    """Just the names, in side bar order. This is the list Wizard's
    gestures move along."""
    return [r.id for r in routes]


class Router:
    """Knows the pages and which one is showing. Showing and hiding is
    handed to two small functions the app gives it, so this class never
    touches the window itself."""

    def __init__(self, show: Callable[[str], None], hide: Callable[[str], None],
                 on_change: Optional[Callable[[str], None]] = None) -> None:
        self._show = show
        self._hide = hide
        self._on_change = on_change
        self.routes: List[Route] = []
        self.active: Optional[str] = None

    @property
    def ids(self) -> List[str]:
        return route_ids(self.routes)

    def has(self, route_id: str) -> bool:
        return route_id in self.ids

    def get(self, route_id: str) -> Optional[Route]:
        for route in self.routes:
            if route.id == route_id:
                return route
        return None

    def set_routes(self, routes: List[Route], keep: Optional[str] = None) -> str:
        """Swap in a new page list (after a Rider change). Stays on
        `keep` (or the current page) if it still exists, otherwise goes
        back to Focus. Returns the page it ended up on."""
        wanted = keep or self.active
        self.routes = list(routes)
        self.active = None
        target = wanted if wanted in self.ids else FIRST_ROUTE_ID
        self.navigate(target)
        return target

    def navigate(self, route_id: str) -> bool:
        """Show one page and hide the one before it. An unknown name
        does nothing and returns False."""
        if route_id not in self.ids:
            return False
        if route_id == self.active:
            return True
        previous = self.active
        if previous is not None:
            self._hide(previous)
        self.active = route_id
        self._show(route_id)
        if self._on_change is not None:
            self._on_change(route_id)
        return True


def labels_by_id(routes: List[Route]) -> Dict[str, str]:
    return {r.id: r.label for r in routes}
