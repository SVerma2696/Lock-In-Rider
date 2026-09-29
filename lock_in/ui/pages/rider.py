"""
ui/pages/rider.py
=================
The extra page a Tier 5 Rider adds to the side bar (V3's Hours,
Decade's Analytics, and so on).

This page doesn't know what's on it. It asks lock_in/tier5/ for the
right builder (TIER5_BUILDERS) and hands it an empty frame, exactly like
the old tab did. Each Rider's own module draws its view and does its own
math -- nothing about those Riders changed.

The view is drawn fresh every time you open the page, and again when a
focus block ends, so it always shows your latest history.
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from ...tier5 import TIER5_BUILDERS
from .. import theme as t
from ..components.box import Box
from ..router import tier5_route_label
from .base import PAGE_PAD_X, Page, tasks_signature


class RiderPage(Page):
    route_id = "rider"
    # Every Tier 5 builder makes its own scrolling area, so this page
    # must not scroll too (two scroll bars inside each other).
    scrollable = False

    def build(self) -> None:
        app = self.app
        effect = app.abilities.productivity
        self.page_header(tier5_route_label(effect), app.config_obj.rider_theme)
        self.content = Box(self.body)
        self.pack(self.content, fill="both", expand=True, padx=PAGE_PAD_X - 4, pady=(0, t.SPACE_4))

    def on_show(self) -> None:
        # Drawn fresh whenever your history, tasks, goal, badges, or the
        # day changed since last time -- otherwise it's already right, and
        # the page keeps where you were (like the day Den-O was showing).
        if self._signature() != getattr(self, "_drawn", None):
            self.refresh()

    def _signature(self) -> tuple:
        app = self.app
        return (
            date.today(),
            tuple((r.id, r.task_id, r.duration_seconds, r.completed) for r in app.history.all()),
            tasks_signature(app.tasks.all()),
            app.config_obj.daily_goal_minutes,
            tuple(app.config_obj.badges_earned),
        )

    def refresh(self) -> None:
        """Clear the frame and let the Rider's builder draw it again."""
        app = self.app
        builder = TIER5_BUILDERS.get(app.abilities.productivity)
        if builder is None:
            return
        for child in self.content.winfo_children():
            child.destroy()
        builder(
            self.content,
            history=app.history,
            tasks=app.tasks,
            theme=app._current_rider_theme,
            appearance_mode=ctk.get_appearance_mode(),
            config=app.config_obj,
        )
        # Taken AFTER drawing: Gotchard may hand out a badge while drawing.
        self._drawn = self._signature()
