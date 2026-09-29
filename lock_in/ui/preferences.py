"""
ui/preferences.py
=================
What happens when you change a setting: flipping a switch, picking a
Rider, turning Standard Mode on, saving timer lengths, and so on.

The rules are the same as before -- only where the switches live
changed (they're on the Blocking and Settings pages now). Every switch
is tied to one shared on/off value made once by the app, so the same
switch on two pages always agrees.
"""

from __future__ import annotations

import customtkinter as ctk

from ..classifier import NaiveBayesClassifier
from ..config import MODEL_PATH
from ..presets import GAVV_MICRO_SPRINT, TimerPreset
from ..session import Phase
from . import theme as t


class PreferencesMixin:
    # ------------------------------------------------------------------ #
    # Shared on/off values
    # ------------------------------------------------------------------ #
    def _make_setting_vars(self) -> None:
        c = self.config_obj
        self.enforce_var = ctk.BooleanVar(value=c.enforcement_enabled)
        self.hard_var = ctk.BooleanVar(value=c.hard_mode)
        self.camera_var = ctk.BooleanVar(value=c.camera_monitoring_enabled)
        self.classifier_var = ctk.BooleanVar(value=c.use_classifier)
        self.record_var = ctk.BooleanVar(value=c.record_observations)
        self.claude_var = ctk.BooleanVar(value=c.claude_fallback_enabled)
        self.autobreak_var = ctk.BooleanVar(value=c.auto_start_breaks)
        self.autofocus_var = ctk.BooleanVar(value=c.auto_start_focus)
        self.sound_var = ctk.BooleanVar(value=c.sound_enabled)
        self.toast_var = ctk.BooleanVar(value=c.toast_enabled)
        self.check_updates_var = ctk.BooleanVar(value=c.check_for_updates)
        self.gestures_var = ctk.BooleanVar(value=c.mouse_gestures_enabled)

    def _save_from_widgets(self) -> None:
        """These switches save themselves right away — no separate save step needed."""
        c = self.config_obj
        c.enforcement_enabled = self.enforce_var.get()
        c.hard_mode = self.hard_var.get()
        c.use_classifier = self.classifier_var.get()
        c.record_observations = self.record_var.get()
        c.auto_start_breaks = self.autobreak_var.get()
        c.auto_start_focus = self.autofocus_var.get()
        c.sound_enabled = self.sound_var.get()
        c.toast_enabled = self.toast_var.get()
        c.check_for_updates = self.check_updates_var.get()
        c.mouse_gestures_enabled = self.gestures_var.get()
        c.save()
        self._refresh_summaries()

    # ------------------------------------------------------------------ #
    # Appearance, Rider, Standard Mode, wording
    # ------------------------------------------------------------------ #
    def _on_appearance_change(self, value: str) -> None:
        ctk.set_appearance_mode(value)
        self.config_obj.appearance = value
        self.config_obj.save()
        # Every color on screen is a (light, dark) pair, so CustomTkinter
        # repaints everything by itself -- no need to rebuild any page.

    def _on_rider_theme_change(self, value: str) -> None:
        """Called when you pick a new Kamen Rider in Settings. It shows up
        right away -- no need to save, restart, or wait for a new session.

        Standard Mode hides every Rider's colors, so picking a Rider while
        it's on used to change nothing you could see. Picking a Rider is a
        clear "I want to see this one", so Standard Mode turns off."""
        self.config_obj.rider_theme = value
        if self.config_obj.standard_mode:
            self.config_obj.standard_mode = False
            self._after_standard_mode_change()
            self._show_banner(f"Standard Mode is off now, so you can see {value}.", "low")
            return
        self.config_obj.save()
        self._apply_theme_everywhere()

    def _on_standard_mode_toggled(self) -> None:
        """Called when you flip the Standard Mode switch in Settings."""
        page = self.pages.get("settings")
        if page is not None:
            self.config_obj.standard_mode = bool(page.standard_mode_switch.get())
        self._after_standard_mode_change()

    def _after_standard_mode_change(self) -> None:
        """Saves Standard Mode's new on/off and switches everything over."""
        self.config_obj.save()
        self._apply_theme_everywhere()
        # Standard Mode changes current_tier3_effect too (see
        # _apply_rider_theme). Gaim's always-on-top lock and Amazon's
        # zero-grace mode normally only change when a phase starts or
        # ends -- so if Standard Mode is flipped mid-block, work both out
        # again right now instead of leaving them stuck.
        self.attributes("-topmost", self.current_tier3_effect == "lock_overlay"
                        and self.session.phase is Phase.FOCUS)
        self.config_obj.zero_grace_mode = (
            self.current_tier3_effect == "zero_ui" and self.session.phase is Phase.FOCUS
        )
        self.config_obj.save()

    def _apply_theme_everywhere(self) -> None:
        """After a Rider or Standard Mode change: new colors, new side bar
        pages, and every Rider gimmick switched over -- without a restart."""
        self._apply_rider_theme()
        self._rebuild_pages()
        # Switching away from Amazon mid-block would leave the Focus page
        # stuck hidden; switching TO it should hide things right away.
        self._sync_zero_ui_visibility()
        # Switching away from Hibiki mid-focus would leave its sound
        # playing; switching to it should start it.
        self.ambient.stop()
        if self.session.phase is Phase.FOCUS and self.session.is_running:
            self.ambient.start_if_applicable()
        self._sync_mirror_layout()
        self._sync_mirror_divider()

    def _on_terminology_switch_toggled(self) -> None:
        """Called when you click the Wording switch itself."""
        page = self.pages.get("settings")
        on = bool(page.terminology_switch.get()) if page is not None else False
        self._on_terminology_change("Tokusatsu" if on else "Professional")

    def _on_terminology_change(self, value: str) -> None:
        """Wording changes words in many places at once, so the simplest
        way to update them all together is to redraw the pages."""
        self.config_obj.terminology = value.lower()
        self.config_obj.save()
        self._rebuild_pages()

    # ------------------------------------------------------------------ #
    # Blocking-related switches
    # ------------------------------------------------------------------ #
    def _on_claude_toggle(self) -> None:
        """
        Turning this switch on is a real decision — confusing window titles
        will start being sent to Claude — so it gets its own handler
        instead of quietly sharing one with all the other switches.
        """
        self.config_obj.claude_fallback_enabled = self.claude_var.get()
        self.config_obj.save()
        self.claude.clear_cache()          # an old "unavailable" answer shouldn't stick around
        self._refresh_claude_status()
        self._refresh_summaries()

    def _on_camera_switch_toggled(self) -> None:
        """
        Applies right away, even in the middle of a focus block: turning
        Strict Camera Monitoring off stops the camera immediately, and
        turning it on mid-block starts it immediately too.
        """
        self.config_obj.camera_monitoring_enabled = self.camera_var.get()
        self.config_obj.save()
        if self.config_obj.camera_monitoring_enabled:
            if self.session.phase is Phase.FOCUS and self.session.is_running:
                self.camera_watcher.resume()
        else:
            self.camera_watcher.pause()
        self._sync_camera_indicator()
        self._refresh_summaries()

    def _register_claude_status(self, label) -> None:
        """The Claude status line shows on two pages; keep both up to date."""
        self._claude_status_labels.append(label)
        self._refresh_claude_status()

    def _refresh_claude_status(self) -> None:
        status = self.claude.status
        colour = t.SUCCESS if status.startswith("ready") else self.palette.text_muted
        alive = []
        for label in self._claude_status_labels:
            try:
                if label.winfo_exists():
                    label.configure(text=f"status: {status}", text_color=colour)
                    alive.append(label)
            except Exception:
                pass
        self._claude_status_labels = alive

    def _refresh_summaries(self) -> None:
        page = self.pages.get("blocking")
        if page is not None:
            try:
                page.refresh_summary()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Tier 2: presets and Gavv / Black RX switches
    # ------------------------------------------------------------------ #
    def _apply_timer_preset(self, preset: TimerPreset) -> None:
        """
        Copies one preset's 4 numbers into Config, updates the number
        boxes on screen so they show what just happened, and saves --
        exactly like typing the numbers in yourself.
        """
        self.config_obj.focus_minutes = preset.focus_minutes
        self.config_obj.short_break_minutes = preset.short_break_minutes
        self.config_obj.long_break_minutes = preset.long_break_minutes
        self.config_obj.blocks_until_long_break = preset.blocks_until_long_break
        self.config_obj.save()

        page = self.pages.get("settings")
        spinners = page.spinners if page is not None else {}
        for key, value in (
            ("focus_minutes", preset.focus_minutes),
            ("short_break_minutes", preset.short_break_minutes),
            ("long_break_minutes", preset.long_break_minutes),
            ("blocks_until_long_break", preset.blocks_until_long_break),
        ):
            if key in spinners:
                spinners[key].delete(0, "end")
                spinners[key].insert(0, str(value))

        name = preset.name_tokusatsu if self._is_tokusatsu() else preset.name_professional
        self._show_banner(
            f"Applied: {name} — {preset.focus_minutes}m focus. "
            "New times start with the next focus block or break.",
            "low",
        )

    def _on_blackrx_toggled(self) -> None:
        """Called when you click the Manual Break Mode switch itself."""
        page = self.pages.get("settings")
        if page is None or page.blackrx_switch is None:
            return
        self.config_obj.blackrx_manual_breaks = page.blackrx_switch.get() == 1
        self.config_obj.save()

    def _on_micro_sprint_toggled(self) -> None:
        """Called when you click the Micro-Sprint switch itself."""
        page = self.pages.get("settings")
        if page is None or page.micro_sprint_switch is None:
            return
        self.config_obj.micro_sprint_mode = page.micro_sprint_switch.get() == 1
        self.config_obj.save()
        name = GAVV_MICRO_SPRINT.name_tokusatsu if self._is_tokusatsu() else GAVV_MICRO_SPRINT.name_professional
        state = "on" if self.config_obj.micro_sprint_mode else "off"
        self._show_banner(f"{name}: {state}. Starts with the next focus block or break.", "low")

    # ------------------------------------------------------------------ #
    # Saving
    # ------------------------------------------------------------------ #
    def _save_lists(self) -> None:
        """Reads the two app lists into clean lists, and saves them."""
        page = self._page("blocking")

        def parse(box) -> list:
            raw = box.get("1.0", "end").splitlines()
            # This trick removes duplicate lines while keeping your original order.
            return list(dict.fromkeys(line.strip().lower() for line in raw if line.strip()))

        self.config_obj.blocklist = parse(page.blocklist_box)
        self.config_obj.allowlist = parse(page.allowlist_box)
        self.config_obj.save()
        self._refresh_summaries()
        self._show_banner("Lists saved.", "low")

    def _save_settings(self) -> None:
        """Checks and saves the number boxes; tells you clearly if something's wrong."""
        page = self._page("settings")
        problems = []
        changed = False
        for key, entry in page.spinners.items():
            try:
                value = int(entry.get())
                if value < 1:
                    raise ValueError
                changed = changed or getattr(self.config_obj, key) != value
                setattr(self.config_obj, key, value)
            except ValueError:
                problems.append(key.replace("_", " "))

        self._save_from_widgets()

        if problems:
            self._show_banner(f"Ignored invalid values: {', '.join(problems)}", "high")
        elif changed:
            # Only the number boxes wait: a timer that's already running
            # keeps its length. Colors, Rider, and switches never wait.
            self._show_banner("Saved. New times start with the next focus block or break.", "low")
        else:
            self._show_banner("Saved.", "low")

    def _reset_model(self) -> None:
        """
        Rebuilds the model from the starter examples plus everything you've
        labelled. Every correction is also saved to observations.jsonl, so
        nothing you taught it is lost -- this just cleans up double
        counting. Same thing as `train.py rebuild`.
        """
        pairs = self.observations.training_pairs()
        self.model = NaiveBayesClassifier.load_seed()
        for text, label in pairs:
            self.model.learn(text, label)
        self.model.save(MODEL_PATH)
        self._update_model_stats()
        self._show_banner(f"Rebuilt from seed + {len(pairs)} of your labels.", "low")
