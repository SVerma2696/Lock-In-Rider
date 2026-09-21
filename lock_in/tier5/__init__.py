"""
tier5/
======
One module per Tier 5 Rider (V3, Decade, W, OOO, Den-O, Zi-O, Gotchard,
Geats, Blade, MY-TH). Each module exposes a single `build(parent, *,
history, tasks, theme, appearance_mode)` function that populates an
empty tab frame with that Rider's view -- see
docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md for why
this is a package of small modules instead of more methods on ui.py's
already-large LockInApp.

TIER5_BUILDERS grows one entry per Rider as each one is built.
"""

from . import blade, decade, den_o, v3, w, zi_o

TIER5_BUILDERS = {
    "hours_tab": v3.build,
    "timeline_view": den_o.build,
    "analytics_dashboard": decade.build,
    "history_editor": zi_o.build,
    "kanban_board": blade.build,
    "week_compare": w.build,
}
