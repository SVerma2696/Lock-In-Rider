"""
tier5/
======
One module per Tier 5 Rider (V3, Decade, W, OOO, Den-O, Zi-O, Gotchard,
Geats, Blade, MY-TH). Each module exposes a single `build(parent, *,
history, tasks, theme, appearance_mode)` function that populates an
empty page frame with that Rider's view -- see
docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md for why
this is a package of small modules instead of more methods on the app
itself. lock_in/ui/pages/rider.py hands each builder its empty frame.

Every builder also accepts `config` (the app's settings). Geats uses it
to read and save the daily goal, and Gotchard uses it to read the goal
and to read and save the badge list; the others ignore it.

TIER5_BUILDERS grows one entry per Rider as each one is built.
"""

from ..rider_effects import ProductivityEffect
from . import blade, decade, den_o, geats, gotchard, my_th, ooo, v3, w, zi_o

TIER5_BUILDERS = {
    ProductivityEffect.HOURS_TAB: v3.build,
    ProductivityEffect.TIMELINE_VIEW: den_o.build,
    ProductivityEffect.ANALYTICS_DASHBOARD: decade.build,
    ProductivityEffect.HISTORY_EDITOR: zi_o.build,
    ProductivityEffect.KANBAN_BOARD: blade.build,
    ProductivityEffect.WEEK_COMPARE: w.build,
    ProductivityEffect.GOAL_STREAK: geats.build,
    ProductivityEffect.BADGE_CARDS: gotchard.build,
    ProductivityEffect.PHASE_COMBO: ooo.build,
    ProductivityEffect.PRIORITY_ORDER: my_th.build,
}
