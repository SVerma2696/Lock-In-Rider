"""
ui/pages/activity.py
====================
The Activity page: every window Lock In saw during your focus blocks,
newest first, and whether it was blocked or allowed.

If Lock In guessed wrong, press "Was studying" or "Distraction" on that
row. The model learns from it right away (that part lives in the app,
in `_correct`). Red and green here only ever mean "blocked" and
"allowed".
"""

from __future__ import annotations

from ...classifier import DISTRACTION, STUDY
from ...enforcer import Reason
from .. import theme as t
from ..components import DangerButton, ModernCard, SecondaryButton, StatCard, StatusBadge
from ..components.box import Box
from .base import PAGE_PAD_X, Page


def describe_entry(entry: dict) -> str:
    """The small grey line under an app's name: time, why, how sure."""
    detail = f"{entry['time']} · {entry['reason'].value}"
    if entry["reason"] in (Reason.CLASSIFIER, Reason.CLAUDE):
        detail += f" {entry['confidence']:.0%}"
    if entry["count"] > 1:
        detail += f" · seen {entry['count']}×"
    if entry["corrected"]:
        detail += f" · you said: {entry['corrected']}"
    return detail


class ActivityPage(Page):
    route_id = "activity"

    def build(self) -> None:
        p = self.palette
        self.page_header(
            "Activity",
            "What you were on during focus blocks. Fix any wrong guess and Lock In learns from it.",
        )
        grid = self.grid_row(min_width=150, max_columns=3, pady=(0, t.SPACE_4))
        self.model_card = StatCard(
            grid, p, layout=self.layout, label="Learned model", icon=self.icon("spark")
        )
        self.seen_card = StatCard(
            grid, p, layout=self.layout, label="Windows seen", icon=self.icon("eye")
        )
        self.blocked_card = StatCard(
            grid, p, layout=self.layout, label="Blocked", icon=self.icon("blocking")
        )
        for card in (self.model_card, self.seen_card, self.blocked_card):
            grid.add(card)

        self.activity_frame = Box(self.body)
        self.pack(
            self.activity_frame, fill="both", expand=True, padx=PAGE_PAD_X, pady=(0, t.SPACE_6)
        )
        self.render()

    def on_show(self) -> None:
        self.app._update_model_stats()
        if self._signature() != getattr(self, "_drawn", None):
            self.render()

    def _signature(self) -> tuple:
        return tuple(
            (e["key"], e["count"], e["blocked"], e["corrected"]) for e in self.app.activity
        )

    def set_model_stats(self, value: str, detail: str) -> None:
        self.model_card.set(value, detail)

    def render(self) -> None:
        """Redraw the list from scratch. It's never longer than 40 rows."""
        p = self.palette
        app = self.app
        for child in self.activity_frame.winfo_children():
            child.destroy()
        self._drawn = self._signature()
        entries = app.activity
        blocked = sum(1 for e in entries if e.get("blocked"))
        self.seen_card.set(str(len(entries)), "Most recent 40 kept")
        self.blocked_card.set(
            str(blocked), "During this run", t.DANGER if blocked else p.text_primary
        )

        if not entries:
            empty = ModernCard(self.activity_frame, p, layout=self.layout, padding=t.SPACE_6)
            self.pack(empty, fill="x")
            self.pack(
                self.label(
                    empty.body,
                    "Nothing logged yet.",
                    size=t.FONT_SECTION,
                    bold=True,
                    anchor="center",
                ),
                fill="x",
            )
            self.pack(
                self.label(
                    empty.body,
                    "Start a focus block and this fills in.",
                    color=p.text_secondary,
                    anchor="center",
                ),
                fill="x",
            )
            return

        for entry in reversed(entries):
            is_blocked = bool(entry.get("blocked"))
            row = ModernCard(self.activity_frame, p, layout=self.layout, padding=t.SPACE_3)
            self.pack(row, fill="x", pady=(0, t.SPACE_2))
            line = Box(row.body)
            self.pack(line, fill="x")
            self.pack(
                StatusBadge(
                    line,
                    p,
                    text="Blocked" if is_blocked else "Allowed",
                    kind="danger" if is_blocked else "success",
                ),
                side="left",
                anchor="n",
                padx=(0, t.SPACE_3),
            )

            # These two buttons teach the model. A phone seen by the
            # camera has no window words to learn from (and "was studying"
            # would allow-list "your phone"), so camera rows don't get them.
            if entry["reason"] is not Reason.CAMERA:
                self.pack(
                    SecondaryButton(
                        line,
                        p,
                        text="Was studying",
                        width=104,
                        height=28,
                        font=t.font(size=t.FONT_SMALL + 1),
                        command=lambda e=entry: app._correct(e, STUDY),
                    ),
                    side="right",
                    padx=(t.SPACE_2, 0),
                )
                self.pack(
                    DangerButton(
                        line,
                        p,
                        text="Distraction",
                        width=96,
                        height=28,
                        font=t.font(size=t.FONT_SMALL + 1),
                        command=lambda e=entry: app._correct(e, DISTRACTION),
                    ),
                    side="right",
                )

            words = Box(line)
            self.pack(words, side="left", fill="x", expand=True)
            self.pack(self.label(words, entry["key"], bold=True, wrap=330), anchor="w", fill="x")
            self.pack(
                self.label(words, describe_entry(entry), size=t.FONT_SMALL, color=p.text_muted),
                anchor="w",
                fill="x",
            )
