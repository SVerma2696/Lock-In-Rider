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

from collections.abc import Callable
from dataclasses import dataclass

from ..rider_effects import InteractionEffect, ProductivityEffect

# Tier 5's extra page: effect string (RiderTheme.tier5_effect) -> the
# words on its side bar button. A new Tier 5 Rider only needs a line here
# (and its builder in lock_in/tier5/__init__.py).
TIER5_ROUTE_LABELS: dict[str, str] = {
    ProductivityEffect.HOURS_TAB: "Hours",
    ProductivityEffect.TIMELINE_VIEW: "Timeline",
    ProductivityEffect.ANALYTICS_DASHBOARD: "Analytics",
    ProductivityEffect.HISTORY_EDITOR: "History",
    ProductivityEffect.KANBAN_BOARD: "Board",
    ProductivityEffect.WEEK_COMPARE: "Week",
    ProductivityEffect.GOAL_STREAK: "Goal",
    ProductivityEffect.BADGE_CARDS: "Badges",
    ProductivityEffect.PHASE_COMBO: "Combo",
    ProductivityEffect.PRIORITY_ORDER: "Priority",
}

# ...and the little picture next to those words.
TIER5_ROUTE_ICONS: dict[str, str] = {
    ProductivityEffect.HOURS_TAB: "clock",
    ProductivityEffect.TIMELINE_VIEW: "timeline",
    ProductivityEffect.ANALYTICS_DASHBOARD: "chart",
    ProductivityEffect.HISTORY_EDITOR: "history",
    ProductivityEffect.KANBAN_BOARD: "board",
    ProductivityEffect.WEEK_COMPARE: "calendar",
    ProductivityEffect.GOAL_STREAK: "flag",
    ProductivityEffect.BADGE_CARDS: "badge",
    ProductivityEffect.PHASE_COMBO: "layers",
    ProductivityEffect.PRIORITY_ORDER: "ordered",
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
    effect = str(effect)
    """The side bar words for a Tier 5 effect. A brand-new effect with
    no entry yet still gets readable words instead of an error."""
    return TIER5_ROUTE_LABELS.get(effect, effect.replace("_", " ").title())


def build_routes(
    tier5_effect: str = ProductivityEffect.NONE,
    tier6_effect: str = InteractionEffect.NONE,
    known_tier5_effects=None,
) -> list[Route]:
    """Every page, in the order the side bar shows them (top to bottom).

    `known_tier5_effects` is the set of Tier 5 effects that actually
    have a page builder. An effect missing from it gets no page, so a
    half-added Rider can never show a broken page. None means "trust
    the effect"."""
    routes = list(MAIN_ROUTES)
    if (
        tier5_effect
        and tier5_effect != ProductivityEffect.NONE
        and (known_tier5_effects is None or tier5_effect in known_tier5_effects)
    ):
        routes.append(
            Route(
                RIDER_ROUTE_ID,
                tier5_route_label(tier5_effect),
                TIER5_ROUTE_ICONS.get(tier5_effect, "star"),
                "rider",
            )
        )
    if tier6_effect == InteractionEffect.BUDDY_LINK:
        routes.append(Route(BUDDY_ROUTE_ID, "Buddy", "buddy", "rider"))
    routes.extend(BOTTOM_ROUTES)
    return routes


def route_ids(routes: list[Route]) -> list[str]:
    """Just the names, in side bar order. This is the list Wizard's
    gestures move along."""
    return [r.id for r in routes]


class Router:
    """Knows the pages and which one is showing. Showing and hiding is
    handed to two small functions the app gives it, so this class never
    touches the window itself."""

    def __init__(
        self,
        show: Callable[[str], None],
        hide: Callable[[str], None],
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        self._show = show
        self._hide = hide
        self._on_change = on_change
        self.routes: list[Route] = []
        self.active: str | None = None

    @property
    def ids(self) -> list[str]:
        return route_ids(self.routes)

    def has(self, route_id: str) -> bool:
        return route_id in self.ids

    def get(self, route_id: str) -> Route | None:
        for route in self.routes:
            if route.id == route_id:
                return route
        return None

    def set_routes(self, routes: list[Route], keep: str | None = None) -> str:
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


def labels_by_id(routes: list[Route]) -> dict[str, str]:
    return {r.id: r.label for r in routes}
