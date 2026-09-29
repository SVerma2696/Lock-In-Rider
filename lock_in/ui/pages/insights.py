"""
ui/pages/insights.py
====================
The Insights page: simple totals about your focus time and tasks, added
up from what Lock In already saves. The adding up happens in
ui/insights_data.py; this page just shows the numbers in cards.

Charts, rankings, and streaks stay on the Rider pages that own them
(V3, Decade, W, Geats...), so those Riders keep their own special thing.
"""

from __future__ import annotations

from datetime import date

from .. import theme as t
from ..components import ModernCard, StatCard
from ..insights_data import format_duration, summarize
from .base import PAGE_PAD_X, Page


class InsightsPage(Page):
    route_id = "insights"

    def build(self) -> None:
        p = self.palette
        self.page_header(
            "Insights", "Your focus time, added up. Every focus block counts, finished or not."
        )
        time_grid = self.grid_row(min_width=150, max_columns=3)
        self.cards = {}
        for key, label, icon in (
            ("today", "Today", "clock"),
            ("week", "Last 7 days", "calendar"),
            ("all", "All time", "timer"),
            ("blocks", "Focus blocks", "focus"),
            ("average", "Average block", "chart"),
            ("days", "Days with focus", "flag"),
        ):
            card = StatCard(time_grid, p, layout=self.layout, label=label, icon=self.icon(icon))
            time_grid.add(card)
            self.cards[key] = card

        self.pack(
            self.label(self.body, "Tasks and this session", size=t.FONT_SECTION, bold=True),
            anchor="w",
            padx=PAGE_PAD_X,
            pady=(t.SPACE_4, t.SPACE_2),
        )
        task_grid = self.grid_row(min_width=150, max_columns=3)
        for key, label, icon in (
            ("open", "Tasks to do", "tasks"),
            ("progress", "In progress", "layers"),
            ("session", "This session", "star"),
        ):
            card = StatCard(task_grid, p, layout=self.layout, label=label, icon=self.icon(icon))
            task_grid.add(card)
            self.cards[key] = card

        if not self.app.config_obj.standard_mode:
            tip = ModernCard(self.body, p, layout=self.layout, padding=t.SPACE_3)
            self.pack(tip, fill="x", padx=PAGE_PAD_X, pady=(t.SPACE_3, t.SPACE_6))
            self.pack(
                self.label(
                    tip.body,
                    "Want charts and streaks? Some Riders add their "
                    "own page to the side bar: V3 (Hours), Decade "
                    "(Analytics), W (Week), and Geats (Goal).",
                    size=t.FONT_SMALL + 1,
                    color=p.text_secondary,
                    wrap=560,
                ),
                fill="x",
            )
        self.refresh()

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        app = self.app
        n = summarize(app.history.all(), app.tasks.all(), date.today())
        c = self.cards
        c["today"].set(format_duration(n.today_seconds), "Focused so far today")
        c["week"].set(format_duration(n.week_seconds), "Today and the 6 days before")
        c["all"].set(format_duration(n.all_time_seconds), "Since you started")
        c["blocks"].set(
            str(n.blocks_logged),
            f"{n.blocks_finished} finished ({n.finish_rate:.0%})"
            if n.blocks_logged
            else "None yet",
        )
        c["average"].set(format_duration(n.average_block_seconds), "Per focus block")
        c["days"].set(str(n.active_days), "Days you focused at all")
        c["open"].set(str(n.tasks_open + n.tasks_in_progress), f"{n.tasks_done} done")
        c["progress"].set(str(n.tasks_in_progress), "Started, not finished")
        done = app.session.completed_focus_blocks
        c["session"].set(str(done), "Blocks since Lock In opened")
