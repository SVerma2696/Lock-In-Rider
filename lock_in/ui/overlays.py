"""
ui/overlays.py
==============
The windows that pop up on top of Lock In:

- the full-screen lockdown (Hard mode's last step)
- Kamen Rider X's "what are you working on?" screen
- Kamen Rider Ghost's tiny floating clock

These are exactly the same as before, just moved into their own file.
They are part of `LockInApp` (it "mixes in" this class), so they can
use the timer and settings directly.
"""

from __future__ import annotations

import customtkinter as ctk

from . import theme as t
from ..enforcer import lockdown_label_for


class OverlaysMixin:
    # ------------------------------------------------------------------ #
    def _raise_self(self) -> None:
        """
        Bring the timer window to the front, without keeping it pinned there
        forever.

        Quickly turning "always on top" on and then back off is the reliable
        trick to actually raise a window — just asking nicely often doesn't
        work, because Windows has its own rules about that.
        """
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(400, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # The lockdown screen
    # ------------------------------------------------------------------ #
    def _show_lockdown(self) -> None:
        """
        Covers the whole screen for `lockdown_seconds`.

        There's always a visible way out ("End session"), on purpose. An app
        that can trap you is an app you'd delete the first time it messes up
        at a moment that actually mattered.
        """
        if self._lockdown_window is not None:
            return

        overlay = ctk.CTkToplevel(self)
        overlay.attributes("-topmost", True)
        try:
            overlay.attributes("-fullscreen", True)
        except Exception:
            overlay.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        overlay.configure(fg_color=t.OVERLAY_BG)
        overlay.protocol("WM_DELETE_WINDOW", lambda: None)   # the X button on this window does nothing
        self._lockdown_window = overlay
        pack = self.layout.pack

        pack(
            ctk.CTkLabel(overlay, text=lockdown_label_for(self.current_era, self._effective_terminology()),
                         font=t.font(size=54, weight="bold"),
                         text_color=self.color_lockdown_text),
            pady=(220, 10),
        )

        remaining_word = "mission" if self._is_tokusatsu() else "session"
        pack(
            ctk.CTkLabel(overlay, text=f"{self.session.format_remaining()} left in this {remaining_word}",
                         font=t.font(size=20), text_color=t.OVERLAY_TEXT)
        )

        countdown = ctk.CTkLabel(overlay, text="", font=t.font(size=16),
                                 text_color=t.OVERLAY_MUTED)
        pack(countdown, pady=26)

        if self.current_tier3_effect == "code_unlock":
            code_entry = ctk.CTkEntry(overlay, width=140, justify="center",
                                      font=t.font(size=16))
            pack(code_entry, pady=(4, 4))
            code_hint = ctk.CTkLabel(overlay, text="Enter code to unlock early",
                                     font=t.font(size=11), text_color=t.OVERLAY_MUTED)
            pack(code_hint, pady=(0, 12))

            def check_code(event=None) -> None:
                if code_entry.get().strip() == "555":
                    self._close_lockdown()
                else:
                    code_entry.delete(0, "end")
                    code_hint.configure(text="Incorrect code", text_color=t.DANGER[1])

            code_entry.bind("<Return>", check_code)

        end_button_text = "Abort Mission" if self._is_tokusatsu() else "End Session"
        pack(
            ctk.CTkButton(overlay, text=end_button_text, width=200,
                          fg_color="transparent", border_width=1,
                          text_color=t.OVERLAY_MUTED, hover_color=t.OVERLAY_HOVER,
                          command=self._end_session_from_lockdown, font=t.font())
        )

        remaining = {"value": self.config_obj.lockdown_seconds}

        def step() -> None:
            """Count down the lockdown screen's own timer, then close itself."""
            if self._lockdown_window is None:
                return
            if remaining["value"] <= 0:
                self._close_lockdown()
                return
            countdown.configure(text=f"unlocks in {remaining['value']}s")
            remaining["value"] -= 1
            overlay.after(1000, step)

        step()
        try:
            overlay.focus_force()
        except Exception:
            pass

    def _close_lockdown(self) -> None:
        if self._lockdown_window is not None:
            try:
                self._lockdown_window.destroy()
            except Exception:
                pass
            self._lockdown_window = None

    def _end_session_from_lockdown(self) -> None:
        """The way out: stops the whole session, not just closes the lockdown screen."""
        self._close_lockdown()
        self._on_reset()

    # ------------------------------------------------------------------ #
    # Kamen Rider X's goal gate
    # ------------------------------------------------------------------ #
    def _show_goal_gate(self) -> None:
        """
        X's gimmick: before you can even start, you have to say what
        you're working on. Same full-screen cover as the lockdown, but
        this one asks a question instead of making you wait -- no
        countdown, no timeout, just a text box.
        """
        overlay = ctk.CTkToplevel(self)
        overlay.attributes("-topmost", True)
        try:
            overlay.attributes("-fullscreen", True)
        except Exception:
            overlay.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        overlay.configure(fg_color=t.OVERLAY_BG)
        overlay.protocol("WM_DELETE_WINDOW", lambda: None)
        pack = self.layout.pack

        title = "DEEP SETUP" if self._is_tokusatsu() else "Set your goal"
        pack(
            ctk.CTkLabel(overlay, text=title, font=t.font(size=40, weight="bold"),
                         text_color=self.color_lockdown_text),
            pady=(220, 20),
        )
        pack(
            ctk.CTkLabel(overlay, text="What are you working on this block?",
                         font=t.font(size=16), text_color=t.OVERLAY_TEXT),
            pady=(0, 16),
        )

        entry = ctk.CTkEntry(overlay, width=420, height=44, font=t.font(size=15))
        pack(entry, pady=(0, 8))
        entry.focus_set()

        hint = ctk.CTkLabel(overlay, text="", font=t.font(size=12), text_color=t.DANGER[1])
        pack(hint)

        def submit(event=None) -> None:
            text = entry.get().strip()
            if not text:
                hint.configure(text="Type something before you begin.")
                return
            self.current_goal_text = text
            overlay.destroy()
            self._do_toggle()

        entry.bind("<Return>", submit)
        begin_word = "Begin" if self._is_tokusatsu() else "Start"
        pack(ctk.CTkButton(overlay, text=begin_word, width=200, height=40,
                           fg_color=self.palette.accent, hover_color=self.palette.accent_hover,
                           text_color=self.palette.accent_on, command=submit, font=t.font()), pady=20)

    # ------------------------------------------------------------------ #
    # Kamen Rider Ghost's floating clock
    # ------------------------------------------------------------------ #
    def _show_ghost_widget(self) -> None:
        if self._ghost_widget is not None:
            return
        widget = ctk.CTkToplevel(self)
        widget.overrideredirect(True)
        widget.attributes("-topmost", True)
        widget.configure(fg_color=t.OVERLAY_BG)
        widget.geometry("140x50+80+80")

        self._ghost_time_label = ctk.CTkLabel(
            widget, text=self.session.format_remaining(),
            font=t.font(family=self.display_font, size=22, weight="bold"),
            text_color=self.color_focus_text,
        )
        self._ghost_time_label.pack(pady=(6, 2))

        self._ghost_progress = ctk.CTkProgressBar(widget, height=4, corner_radius=2,
                                                  progress_color=self.palette.accent)
        self._ghost_progress.set(self.session.progress)
        self._ghost_progress.pack(fill="x", padx=8, pady=(0, 6))

        def restore(event=None) -> None:
            self._hide_ghost_widget()

        def start_drag(event) -> None:
            widget._drag_start = (event.x, event.y)
            widget._dragged = False

        def do_drag(event) -> None:
            dx = event.x - widget._drag_start[0]
            dy = event.y - widget._drag_start[1]
            if abs(dx) > 3 or abs(dy) > 3:
                widget._dragged = True
            x = widget.winfo_x() + dx
            y = widget.winfo_y() + dy
            widget.geometry(f"+{x}+{y}")

        def end_click_or_drag(event) -> None:
            if not getattr(widget, "_dragged", False):
                restore()

        widget.bind("<ButtonPress-1>", start_drag)
        widget.bind("<B1-Motion>", do_drag)
        widget.bind("<ButtonRelease-1>", end_click_or_drag)
        self._ghost_time_label.bind("<ButtonPress-1>", start_drag)
        self._ghost_time_label.bind("<B1-Motion>", do_drag)
        self._ghost_time_label.bind("<ButtonRelease-1>", end_click_or_drag)

        self._ghost_widget = widget
        self.iconify()

    def _hide_ghost_widget(self) -> None:
        # This is called on every phase change, for every Rider -- not
        # just Ghost. Only bring the window back when this call is really
        # undoing Ghost's hide; otherwise it would force open a window YOU
        # minimized by hand.
        had_widget = self._ghost_widget is not None
        if self._ghost_widget is not None:
            try:
                self._ghost_widget.destroy()
            except Exception:
                pass
            self._ghost_widget = None
        if had_widget:
            self.deiconify()

    def _refresh_ghost_widget(self) -> None:
        if self._ghost_widget is None:
            return
        self._ghost_time_label.configure(text=self.session.format_remaining())
        self._ghost_progress.set(self.session.progress)
