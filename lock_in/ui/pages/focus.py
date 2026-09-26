"""
ui/pages/focus.py
=================
The Focus page: the big clock, the bar under it, which task you're on,
the Start (or Henshin) button, and small cards saying whether blocking
and the camera are on.

A few Riders change how this page looks. The page has ONE method that
puts everything in order, `restack()`, and the app tells it which look
to use:

- normal:    the clock, the bar, the task picker, the buttons, the cards
- dashboard: Zero-One -- the clock becomes a row of four data cards
- zero_ui:   Amazon during a focus block -- only a green tank that
             drains, and three tiny buttons

The page never decides WHEN to change. The app does, and calls
`restack()`.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import theme as t
from ..components.box import Box
from ..components import (
    MenuButton, ModernCard, PrimaryButton, ProgressArea, SecondaryButton, StatCard,
    TimerDisplay,
)
from .base import PAGE_PAD_X, Page, ResponsiveGrid


class FocusPage(Page):
    route_id = "focus"

    def build(self) -> None:
        app = self.app
        p = self.palette

        # ---- the hero card: clock + bar ---------------------------------- #
        self.hero = ModernCard(self.body, p, layout=self.layout, padding=t.SPACE_4)
        self.caption = self.label(self.hero.body, "FOCUS SESSION", size=t.FONT_SMALL,
                                  color=p.text_muted, bold=True, anchor="center")
        self.timer = TimerDisplay(self.hero.body, p, layout=self.layout,
                                  font_family=app._active_display_font,
                                  label_font_family=app.display_font)
        self.timer.time_label.bind("<Enter>", lambda e: app._set_kabuto_revealed(True))
        self.timer.time_label.bind("<Leave>", lambda e: app._set_kabuto_revealed(False))
        # Zero-One's cards, shown INSTEAD of the clock words (not beside them).
        self.dashboard = ResponsiveGrid(self.hero.body, self.layout, min_width=120, max_columns=4)
        self.dashboard_cards = {}
        for key, label in (("status", "Status"), ("time", "Time Remaining"),
                           ("streak", "Sessions Complete"), ("profile", "Active Profile")):
            card = StatCard(self.dashboard, p, layout=self.layout, label=label, elevated=True,
                            value_size=15, value_wrap=120)
            self.dashboard.add(card)
            self.dashboard_cards[key] = card
        self.progress_area = ProgressArea(self.hero.body, p, layout=self.layout)

        # ---- current task (inside the hero, like the mockup) ------------ #
        self.task_card = Box(self.hero.body)
        self.pack(self.label(self.task_card, "Current task", size=t.FONT_SMALL + 1,
                             color=p.text_muted, anchor="center"), pady=(0, t.SPACE_1))
        self.current_task_menu = MenuButton(
            self.task_card, p, values=["No task"], width=300, height=34, anchor="center",
            font=t.font(size=t.FONT_BODY + 1, weight="bold"),
            command=app._on_current_task_selected,
        )
        self.pack(self.current_task_menu)

        # ---- the buttons: one big main button, two small ones ------------ #
        self.controls = Box(self.hero.body)
        self.start_button = PrimaryButton(
            self.controls, p, text=app._henshin_word(), command=app._on_toggle,
            width=260, height=44, font_family=app.display_font, font_size=16,
        )
        self.layout.grid(self.start_button, total_columns=2, row=0, column=0, columnspan=2,
                         pady=(0, t.SPACE_2))
        self.skip_button = SecondaryButton(self.controls, p, text="Skip", width=124, height=32,
                                           command=app._on_skip)
        self.layout.grid(self.skip_button, total_columns=2, row=1, column=0,
                         padx=(0, t.SPACE_1), sticky="e")
        self.reset_button = SecondaryButton(self.controls, p, text="Reset", width=124, height=32,
                                            command=app._on_reset)
        self.layout.grid(self.reset_button, total_columns=2, row=1, column=1,
                         padx=(t.SPACE_1, 0), sticky="w")

        # ---- small live status cards --------------------------------------- #
        self.status_grid = ResponsiveGrid(self.body, self.layout, min_width=160, max_columns=3)
        self.blocking_card = StatCard(self.status_grid, p, layout=self.layout,
                                      label="Blocking", icon=self.icon("blocking"))
        self.camera_card = StatCard(self.status_grid, p, layout=self.layout,
                                    label="Phone check", icon=self.icon("camera"))
        # Window names can be long, so this one's value is smaller and wraps.
        self.watch_card = StatCard(self.status_grid, p, layout=self.layout,
                                   label="Watching", icon=self.icon("eye"),
                                   value_size=14, value_wrap=190)
        for card in (self.blocking_card, self.camera_card, self.watch_card):
            self.status_grid.add(card)
        # The camera card's detail line. It reads "Camera monitoring active"
        # ONLY while the camera is really on -- same promise as before.
        self.camera_indicator_label = self.camera_card.detail
        self.watch_label = self.watch_card.detail

        self._stack = None
        self.restack("normal", "bar")

    def on_show(self) -> None:
        self.app._on_focus_page_shown()

    # ------------------------------------------------------------------ #
    def restack(self, look: str, progress_mode: str) -> None:
        """Put the page's pieces on screen in the right order for `look`
        ("normal", "dashboard", or "zero_ui"). `progress_mode` is "bar"
        or "shape". Does nothing if that's already what's showing, so the
        app can call this on every tick."""
        wanted = (look, progress_mode)
        if wanted == self._stack:
            return
        self._stack = wanted

        for widget in (self.hero, self.task_card, self.controls, self.status_grid,
                       self.caption, self.timer, self.dashboard, self.progress_area):
            widget.pack_forget()

        self.pack(self.hero, fill="x", padx=PAGE_PAD_X, pady=(t.SPACE_4, t.SPACE_3))
        if look == "zero_ui":
            self.progress_area.show("zero_ui")
            self.pack(self.progress_area)
            self.pack(self.controls, pady=(t.SPACE_2, 0))
            for button in (self.start_button, self.skip_button, self.reset_button):
                button.configure(width=56)
            return

        self.start_button.configure(width=260)
        self.skip_button.configure(width=124)
        self.reset_button.configure(width=124)
        self.pack(self.caption)
        if look == "dashboard":
            self.pack(self.dashboard, fill="x", pady=(t.SPACE_2, 0))
        else:
            self.pack(self.timer)
        self.progress_area.show(progress_mode)
        self.pack(self.progress_area)
        self.pack(self.task_card, pady=(0, t.SPACE_3))
        self.pack(self.controls)
        self.pack(self.status_grid, fill="x", pady=(0, t.SPACE_5),
                  padx=PAGE_PAD_X - t.SPACE_3 // 2)

    @property
    def look(self):
        return self._stack[0] if self._stack else None
