"""
ui/pages/settings.py
====================
The Settings page, laid out like Windows Settings: one card per topic,
one row per setting, words on the left and the switch or box on the
right.

    Focus          timer lengths, auto-start
    Rider power    only for Riders with an extra setting (presets, etc.)
    Blocking       how fast Lock In gets stricter
    Detection      the model, recording, the camera
    Claude helper  asking Claude about unclear windows
    Appearance     light/dark, Standard Mode, Rider, wording
    Notifications  sounds and pop-ups
    Updates        checking for a newer Lock In

Switches save the moment you flip them. The number boxes save when you
press "Save settings". What each setting DOES is unchanged -- the
handlers are the same ones the app always used.
"""

from __future__ import annotations

import customtkinter as ctk

from ... import __version__
from ...presets import GAVV_MICRO_SPRINT, KUUGA_PRESETS, SUPER1_PRESETS
from ...rider_effects import DisplayEffect, InteractionEffect, PresetEffect
from ...rider_themes import RIDER_THEMES
from .. import theme as t
from ..components import (
    DangerButton,
    MenuButton,
    ModernCard,
    PrimaryButton,
    SecondaryButton,
    SettingRow,
)
from ..components.box import Box
from .base import PAGE_PAD_X, Page
from .blocking import NO_CAMERA_TEXT, claude_card, switch_rows

# Tier 2 quick-pick buttons: effect -> (presets, tokusatsu heading, plain heading).
TIER2_PRESET_ROWS = {
    PresetEffect.INTERVAL_PRESETS: (KUUGA_PRESETS, "Kuuga presets", "Interval presets"),
    PresetEffect.TASK_PRESETS: (SUPER1_PRESETS, "Super-1's Five Hands", "Task-type presets"),
}

APPEARANCE_CHOICES = {"Light": "light", "Dark": "dark", "System": "system"}


def rider_power_parts(theme) -> list:
    """Which extra Rider rows the Settings page shows for this theme, in
    order. Standard Mode's theme has no effects, so it always gets []."""
    parts = []
    if theme.tier2_effect in TIER2_PRESET_ROWS:
        parts.append("presets")
    if theme.tier2_effect == PresetEffect.MICRO_SPRINT:
        parts.append("micro_sprint")
    if theme.tier4_effect == DisplayEffect.MANUAL_BREAK_TOGGLE:
        parts.append("manual_breaks")
    if theme.tier6_effect == InteractionEffect.MOUSE_GESTURES:
        parts.append("gestures")
    return parts


class SettingsPage(Page):
    route_id = "settings"

    def build(self) -> None:
        app = self.app
        p = self.palette
        self.spinners: dict = {}
        self.micro_sprint_switch: ctk.CTkSwitch | None = None
        self.blackrx_switch: ctk.CTkSwitch | None = None

        self.page_header(
            "Settings",
            "Colors, Riders, and switches change right away. Number boxes "
            "save when you press Save settings, and start with the next "
            "focus block or break.",
            trailing=lambda m: PrimaryButton(
                m,
                p,
                text="Save settings",
                height=36,
                width=130,
                font_size=13,
                command=app._save_settings,
            ),
        )

        # ---- Focus ----------------------------------------------------- #
        focus = self._card("Focus", "How long focus blocks and breaks last.", "timer")
        c = app.config_obj
        self._number(
            focus,
            "focus_minutes",
            "Focus length",
            "Minutes per focus block.",
            c.focus_minutes,
            first=True,
        )
        self._number(focus, "short_break_minutes", "Short break", "Minutes.", c.short_break_minutes)
        self._number(focus, "long_break_minutes", "Long break", "Minutes.", c.long_break_minutes)
        self._number(
            focus,
            "blocks_until_long_break",
            "Blocks before a long break",
            "Focus blocks in a row before the big break.",
            c.blocks_until_long_break,
        )
        switch_rows(
            self,
            focus,
            [
                (
                    "Auto-start breaks",
                    "A break begins by itself when focus ends.",
                    app.autobreak_var,
                    app._save_from_widgets,
                    None,
                ),
                (
                    "Auto-start next focus block",
                    "Otherwise you press Start to work again.",
                    app.autofocus_var,
                    app._save_from_widgets,
                    None,
                ),
            ],
            first_divider=True,
        )

        # ---- Rider power (only for some Riders) ------------------------ #
        parts = rider_power_parts(app._current_rider_theme)
        if parts:
            name = app.config_obj.rider_theme
            power = self._card(
                "Rider power" if not app._is_tokusatsu() else "Rider Gear",
                f"Extra settings for {name}.",
                "star",
            )
            for part in parts:
                getattr(self, f"_build_{part}")(power)

        # ---- Blocking --------------------------------------------------- #
        blocking = self._card("Blocking", "How quickly Lock In gets stricter.", "blocking")
        self._number(
            blocking,
            "grace_seconds",
            "Grace period",
            "Free seconds on a blocked app before anything happens.",
            c.grace_seconds,
            first=True,
        )
        self._number(
            blocking,
            "strike_interval_seconds",
            "Seconds between escalations",
            "How often it gets stricter while you stay.",
            c.strike_interval_seconds,
        )
        self._number(
            blocking,
            "lockdown_seconds",
            "Lockdown length",
            "Seconds the full-screen lockdown stays up.",
            c.lockdown_seconds,
        )
        switch_rows(
            self,
            blocking,
            [
                (
                    "Block distracting apps during focus",
                    "The main on/off for blocking.",
                    app.enforce_var,
                    app._save_from_widgets,
                    None,
                ),
                (
                    "Hard mode",
                    "Minimise windows and show the lockdown screen.",
                    app.hard_var,
                    app._save_from_widgets,
                    None,
                ),
            ],
            first_divider=True,
        )

        # ---- Detection --------------------------------------------------- #
        from ...camera_enforcer import CAMERA_BACKEND_AVAILABLE

        detection = self._card("Detection", "How Lock In tells work from distraction.", "eye")
        switches = switch_rows(
            self,
            detection,
            [
                (
                    "Use the learned model on unlisted apps",
                    "Guesses about apps on neither list.",
                    app.classifier_var,
                    app._save_from_widgets,
                    None,
                ),
                (
                    "Record windows for training",
                    "Stays on this computer.",
                    app.record_var,
                    app._save_from_widgets,
                    None,
                ),
                (
                    "Strict Camera Monitoring",
                    "Uses your webcam to catch phones during focus.",
                    app.camera_var,
                    app._on_camera_switch_toggled,
                    None,
                ),
            ],
        )
        if not CAMERA_BACKEND_AVAILABLE:
            switches[-1].configure(state="disabled")
            self.pack(
                self.label(
                    detection.body, NO_CAMERA_TEXT, size=t.FONT_SMALL + 1, color=t.WARNING, wrap=540
                ),
                fill="x",
                pady=(0, t.SPACE_3),
            )
        self._row(
            detection,
            "Rebuild model from labels",
            "Starts the model over from the starter examples plus every label you gave. "
            "Nothing you taught it is lost.",
            lambda m: DangerButton(m, p, text="Rebuild", width=96, command=app._reset_model),
            divider=True,
        )

        # ---- Claude helper ------------------------------------------------ #
        claude = claude_card(self)
        self.pack(claude, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_4))

        # ---- Appearance ----------------------------------------------------- #
        look = self._card("Appearance", "Colors, Rider, and words.", "palette")

        def appearance_control(master):
            chooser = self.segmented(
                master,
                APPEARANCE_CHOICES,
                lambda v: app._on_appearance_change(APPEARANCE_CHOICES[v]),
            )
            current = next(
                (k for k, v in APPEARANCE_CHOICES.items() if v == app.config_obj.appearance), "Dark"
            )
            chooser.set(current)
            self.appearance_menu = chooser
            return chooser

        self._row(look, "Mode", "Light, dark, or match your computer.", appearance_control)

        def standard_control(master):
            self.standard_mode_switch = self.switch(master, None, app._on_standard_mode_toggled)
            if app.config_obj.standard_mode:
                self.standard_mode_switch.select()
            else:
                self.standard_mode_switch.deselect()
            return self.standard_mode_switch

        self._row(
            look,
            "Standard Mode",
            "Strips every Rider's color, art, and gimmick for a plain, fast, "
            "distraction-free look, and switches Wording to plain Professional while "
            "it's on. Your Rider pick and Wording setting are remembered and come "
            "right back when you turn this off. Picking a Rider below turns it off too.",
            standard_control,
            divider=True,
        )

        def rider_control(master):
            self.rider_menu = MenuButton(
                master,
                p,
                values=list(RIDER_THEMES.keys()),
                width=250,
                command=app._on_rider_theme_change,
            )
            self.rider_menu.set(app.config_obj.rider_theme)
            return self.rider_menu

        rider_row = self._row(
            look,
            app._rider_row_label_text(),
            "Changes the colors. Some Riders also add a special power.",
            rider_control,
            divider=True,
        )
        self.rider_row_label = rider_row.title_label

        def wording_control(master):
            box = Box(master)
            self.pack(
                self.label(box, "Professional", size=t.FONT_SMALL + 1, color=p.text_secondary),
                side="left",
                padx=(0, t.SPACE_2),
            )
            self.terminology_switch = self.switch(box, None, app._on_terminology_switch_toggled)
            # Shows the SAVED value on purpose: while Standard Mode is on,
            # the words on screen are always plain, but the switch should
            # still show what you picked.
            if app.config_obj.terminology == "tokusatsu":
                self.terminology_switch.select()
            else:
                self.terminology_switch.deselect()
            self.pack(self.terminology_switch, side="left")
            self.pack(
                self.label(box, "Tokusatsu", size=t.FONT_SMALL + 1, color=p.text_secondary),
                side="left",
            )
            return box

        self._row(
            look,
            "Wording",
            'Plain words ("Focus", "Start"), or Kamen Rider hero talk ("Henshin", "Off Mission").',
            wording_control,
            divider=True,
        )

        # ---- Notifications ------------------------------------------------- #
        notes = self._card("Notifications", "Sounds and pop-up messages.", "bell")
        switch_rows(
            self,
            notes,
            [
                (
                    "Sounds",
                    "A short chime when a phase changes.",
                    app.sound_var,
                    app._save_from_widgets,
                    None,
                ),
                (
                    "Desktop notifications",
                    "Pop-up messages from Lock In.",
                    app.toast_var,
                    app._save_from_widgets,
                    None,
                ),
            ],
        )

        # ---- Updates -------------------------------------------------------- #
        updates = self._card("Updates", f"You're running Lock In v{__version__}.", "refresh")
        switch_rows(
            self,
            updates,
            [
                (
                    "Automatically check for updates",
                    "Checks once, a moment after Lock In opens.",
                    app.check_updates_var,
                    app._save_from_widgets,
                    None,
                ),
            ],
        )
        holder = Box(updates.body)
        self.pack(holder, fill="x")
        # Works even with the switch above off -- it's the "ask right now,
        # just once" version of the same check.
        self.update_check_button = SecondaryButton(
            holder,
            p,
            text="Check for updates now",
            width=180,
            command=app._on_check_updates_clicked,
        )
        self.pack(self.update_check_button, anchor="w")
        self.update_check_status = self.label(
            holder, "", size=t.FONT_SMALL + 1, color=p.text_secondary, wrap=520
        )
        self.pack(self.update_check_status, anchor="w", fill="x", pady=(t.SPACE_1, 0))
        app._restore_update_check_state()

        self.pack(
            PrimaryButton(
                self.body,
                p,
                text="Save settings",
                height=36,
                width=130,
                font_size=13,
                command=app._save_settings,
            ),
            anchor="w",
            padx=PAGE_PAD_X,
            pady=(0, t.SPACE_7),
        )

    # ------------------------------------------------------------------ #
    def _card(self, title: str, subtitle: str, icon: str) -> ModernCard:
        card = ModernCard(
            self.body,
            self.palette,
            layout=self.layout,
            title=title,
            subtitle=subtitle,
            icon=self.icon(icon),
        )
        self.pack(card, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_4))
        return card

    def _row(self, card, title, description, control, divider=False) -> SettingRow:
        row = SettingRow(
            card.body,
            self.palette,
            layout=self.layout,
            title=title,
            description=description,
            control=control,
            divider=divider,
        )
        self.pack(row, fill="x", pady=(0, t.SPACE_3))
        return row

    def _number(self, card, key, title, description, value, first=False) -> None:
        p = self.palette

        def make(master):
            entry = ctk.CTkEntry(
                master,
                width=76,
                height=32,
                justify="center",
                border_width=1,
                fg_color=p.control_bg,
                border_color=p.card_border,
                text_color=p.text_primary,
                corner_radius=t.CONTROL_RADIUS,
                font=t.font(),
            )
            entry.insert(0, str(value))
            self.spinners[key] = entry
            return entry

        self._row(card, title, description, make, divider=not first)

    # ---- Rider power rows ------------------------------------------------ #
    def _build_presets(self, card) -> None:
        app = self.app
        presets, toku, plain = TIER2_PRESET_ROWS[app._current_rider_theme.tier2_effect]
        self.pack(
            self.label(card.body, toku if app._is_tokusatsu() else plain, bold=True), anchor="w"
        )
        self.pack(
            self.label(
                card.body,
                "Click one to fill in your timer lengths.",
                size=t.FONT_SMALL + 1,
                color=self.palette.text_muted,
            ),
            anchor="w",
        )
        row = Box(card.body)
        self.pack(row, fill="x", pady=(t.SPACE_2, t.SPACE_3))
        for preset in presets:
            name = preset.name_tokusatsu if app._is_tokusatsu() else preset.name_professional
            column = Box(row)
            self.pack(column, side="left", padx=(0, t.SPACE_2), anchor="n")
            self.pack(
                SecondaryButton(
                    column,
                    self.palette,
                    text=name,
                    width=96,
                    height=32,
                    command=lambda pr=preset: app._apply_timer_preset(pr),
                )
            )
            if preset.description:
                self.pack(
                    self.label(
                        column,
                        preset.description,
                        size=10,
                        color=self.palette.text_muted,
                        wrap=96,
                        anchor="center",
                        justify="center",
                    ),
                    pady=(2, 0),
                )

    def _build_micro_sprint(self, card) -> None:
        app = self.app
        heading = "Bite-Sized Mode" if app._is_tokusatsu() else "Micro-Sprint Mode"

        def make(master):
            switch = self.switch(master, None, app._on_micro_sprint_toggled)
            if app.config_obj.micro_sprint_mode:
                switch.select()
            else:
                switch.deselect()
            self.micro_sprint_switch = switch
            return switch

        self._row(
            card,
            heading,
            f"{GAVV_MICRO_SPRINT.focus_minutes}m focus / "
            f"{GAVV_MICRO_SPRINT.short_break_minutes}m break, repeating. Overrides your "
            "timer lengths until you turn it off.",
            make,
        )

    def _build_manual_breaks(self, card) -> None:
        app = self.app
        heading = "Manual Recovery" if app._is_tokusatsu() else "Manual Break Mode"

        def make(master):
            switch = self.switch(master, None, app._on_blackrx_toggled)
            if app.config_obj.blackrx_manual_breaks:
                switch.select()
            else:
                switch.deselect()
            self.blackrx_switch = switch
            return switch

        self._row(
            card,
            heading,
            "Never auto-start breaks -- always wait for you to press "
            "Start. Overrides Auto-start breaks until you turn it off.",
            make,
        )

    def _build_gestures(self, card) -> None:
        app = self.app
        self._row(
            card,
            "Mouse gestures",
            "Hold the right mouse button and draw: a line left or right moves one page "
            "up or down the side bar, a circle goes to Focus.",
            lambda m: self.switch(m, app.gestures_var, app._save_from_widgets),
        )
