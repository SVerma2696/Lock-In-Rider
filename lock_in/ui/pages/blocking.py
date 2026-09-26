"""
ui/pages/blocking.py
====================
The Blocking page: which apps count as distractions, and how strict Lock
In is about them during a focus block.

At the top, four small cards sum things up. Below, the switches are
grouped into cards (Protection, Detection, Claude helper), then the two
app lists.

Every switch here is tied to the SAME on/off value as its twin on the
Settings page, so flipping one flips the other. The rules about what
gets blocked live in enforcer.py; this page only shows and changes the
settings.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import theme as t
from ..components.box import Box
from ...camera_enforcer import CAMERA_BACKEND_AVAILABLE
from ...monitor import BACKEND_AVAILABLE
from ..components import ModernCard, PrimaryButton, SettingRow, StatCard
from .base import PAGE_PAD_X, Page

CLAUDE_HELP_TEXT = (
    "Off by default. When the local model is unsure, sends just that one "
    "window's title to the Claude API instead of guessing. Confident local "
    "judgements never leave your machine."
)
NO_BACKEND_TEXT = (
    "App detection unavailable on this system. Install pywin32 + psutil on "
    "Windows to enable it. The timer works fine either way."
)
NO_CAMERA_TEXT = (
    "Strict Camera Monitoring needs opencv-python-headless and its bundled "
    "model file, and isn't available right now. Run: pip install opencv-python-headless"
)


def switch_rows(page: Page, card: ModernCard, rows, first_divider: bool = False) -> list:
    """Add (title, description, variable, command, icon) rows to a card,
    with thin lines between them. `first_divider` also puts a line above
    the first one, for when other rows came before. Returns the switches."""
    switches = []
    for index, (title, description, variable, command, icon) in enumerate(rows):
        holder = {}

        def make(master, v=variable, c=command):
            holder["switch"] = page.switch(master, v, c)
            return holder["switch"]

        row = SettingRow(card.body, page.palette, layout=page.layout, title=title,
                         description=description, icon=page.icon(icon) if icon else None,
                         control=make, divider=index > 0 or first_divider)
        page.pack(row, fill="x", pady=(0, t.SPACE_3))
        switches.append(holder["switch"])
    return switches


def claude_card(page: Page) -> ModernCard:
    """The Claude helper card. Used on both Blocking and Settings."""
    app = page.app
    card = ModernCard(page.body, page.palette, layout=page.layout, title="Claude helper",
                      subtitle=CLAUDE_HELP_TEXT, icon=page.icon("spark"))
    switch_rows(page, card, [
        ("Ask Claude about unclear windows", "Only for windows the local model isn't sure about.",
         app.claude_var, app._on_claude_toggle, None),
    ])
    status = page.label(card.body, "", size=t.FONT_SMALL + 1, color=page.palette.text_muted)
    page.pack(status, anchor="w")
    app._register_claude_status(status)
    return card


class BlockingPage(Page):
    route_id = "blocking"

    def build(self) -> None:
        app = self.app
        p = self.palette
        self.page_header("Blocking", "Pick which apps are distractions, and how strict "
                                     "Lock In is while you focus.")

        if not BACKEND_AVAILABLE:
            warn = ModernCard(self.body, p, layout=self.layout, border_color=t.WARNING)
            self.pack(warn, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_4))
            self.pack(self.label(warn.body, NO_BACKEND_TEXT, color=t.WARNING, wrap=560), fill="x")

        grid = self.grid_row(min_width=118, max_columns=4, pady=(0, t.SPACE_4))
        self.summary = {
            "apps": StatCard(grid, p, layout=self.layout, label="Apps blocked",
                             icon=self.icon("list")),
            "protection": StatCard(grid, p, layout=self.layout, label="Protection",
                                   icon=self.icon("blocking")),
            "camera": StatCard(grid, p, layout=self.layout, label="Camera",
                               icon=self.icon("camera")),
            "classifier": StatCard(grid, p, layout=self.layout, label="Smart check",
                                   icon=self.icon("eye")),
        }
        for card in self.summary.values():
            grid.add(card)

        protection = ModernCard(self.body, p, layout=self.layout, title="Protection",
                                icon=self.icon("blocking"))
        self.pack(protection, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_4))
        switch_rows(self, protection, [
            ("Block distracting apps during focus",
             "Warns you first, then gets stricter the longer you stay.",
             app.enforce_var, app._save_from_widgets, None),
            ("Hard mode", "Minimises distracting windows and shows the full-screen lockdown.",
             app.hard_var, app._save_from_widgets, None),
        ])

        detection = ModernCard(self.body, p, layout=self.layout, title="Detection",
                               icon=self.icon("eye"))
        self.pack(detection, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_4))
        switches = switch_rows(self, detection, [
            ("Use the learned model on unlisted apps",
             "Guesses about apps that aren't on either list.",
             app.classifier_var, app._save_from_widgets, None),
            ("Record windows for training", "Stays on this computer.",
             app.record_var, app._save_from_widgets, None),
            ("Strict Camera Monitoring", "Uses your webcam to catch phones during a focus block.",
             app.camera_var, app._on_camera_switch_toggled, None),
        ])
        self.camera_switch = switches[-1]
        if not CAMERA_BACKEND_AVAILABLE:
            self.camera_switch.configure(state="disabled")
            self.pack(self.label(detection.body, NO_CAMERA_TEXT, size=t.FONT_SMALL + 1,
                                 color=t.WARNING, wrap=540), fill="x")

        claude = claude_card(self)
        self.pack(claude, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_4))

        lists = ModernCard(self.body, p, layout=self.layout, title="App lists",
                           subtitle="One app name per line, like discord.exe.",
                           icon=self.icon("list"))
        self.pack(lists, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_6))
        columns = Box(lists.body)
        self.pack(columns, fill="x")
        columns.grid_columnconfigure((0, 1), weight=1, uniform="lists")

        def list_box(column: int, title: str, color, lines):
            holder = Box(columns)
            self.layout.grid(holder, total_columns=2, row=0, column=column, sticky="nsew",
                             padx=(0, t.SPACE_2) if column == 0 else (t.SPACE_2, 0))
            self.pack(self.label(holder, f"●  {title}", size=t.FONT_BODY, bold=True,
                                 color=color), anchor="w", pady=(0, t.SPACE_1))
            box = ctk.CTkTextbox(holder, height=150, border_width=1, corner_radius=t.CONTROL_RADIUS,
                                 fg_color=p.control_bg, border_color=p.card_border,
                                 text_color=p.text_primary, font=t.font())
            box.insert("1.0", "\n".join(lines))
            self.pack(box, fill="x")
            return box

        self.blocklist_box = list_box(0, "Blocked apps", t.DANGER, app.config_obj.blocklist)
        self.allowlist_box = list_box(1, "Always-allowed apps", t.SUCCESS, app.config_obj.allowlist)
        self.pack(PrimaryButton(lists.body, p, text="Save lists", height=36, width=130,
                                font_size=13, command=app._save_lists),
                  anchor="w", pady=(t.SPACE_3, 0))
        self.refresh_summary()

    def on_show(self) -> None:
        self.refresh_summary()

    def sync_list_boxes(self) -> None:
        """Put the saved lists back in the boxes after code changed them."""
        c = self.app.config_obj
        self.blocklist_box.delete("1.0", "end")
        self.blocklist_box.insert("1.0", "\n".join(c.blocklist))
        self.allowlist_box.delete("1.0", "end")
        self.allowlist_box.insert("1.0", "\n".join(c.allowlist))

    def refresh_summary(self) -> None:
        c = self.app.config_obj
        s = self.summary
        count = len(c.blocklist)
        s["apps"].set(str(count), f"{len(c.allowlist)} always allowed")
        if not BACKEND_AVAILABLE:
            s["protection"].set("Unavailable", "App detection isn't installed", t.WARNING)
        elif c.enforcement_enabled:
            s["protection"].set("Active", "Hard mode on" if c.hard_mode else "Warnings only",
                                t.SUCCESS)
        else:
            s["protection"].set("Off", "Nothing gets blocked", t.DANGER)
        if not CAMERA_BACKEND_AVAILABLE:
            s["camera"].set("Unavailable", "Needs OpenCV", self.palette.text_muted)
        elif c.camera_monitoring_enabled:
            s["camera"].set("On", "Only during focus", t.SUCCESS)
        else:
            s["camera"].set("Off", "Camera never opens", self.palette.text_primary)
        claude = "Claude helper on" if c.claude_fallback_enabled else "Claude helper off"
        s["classifier"].set("On" if c.use_classifier else "Off", claude,
                            t.SUCCESS if c.use_classifier else self.palette.text_primary)
