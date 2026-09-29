"""
ui/gestures.py
==============
Kamen Rider Wizard's mouse gestures. Hold the right mouse button and
draw on the window:

- a line to the left   -> the page above in the side bar
- a line to the right  -> the page below in the side bar
- a circle             -> the first page, Focus

The drawing math lives in lock_in/wizard_gestures.py and didn't change.
The only difference from before: gestures now move along the side bar's
list of pages (by their fixed names), not the old tab strip.
"""

from __future__ import annotations

import customtkinter as ctk

from ..rider_effects import InteractionEffect
from ..wizard_gestures import next_tab_name, recognize
from .host import AppHost


def gesture_target(route_ids, current, gesture):
    """Which page a finished gesture should open, or None to stay put.
    Plain function, so it's tested without a window."""
    return next_tab_name(list(route_ids), current, gesture)


class WizardGesturesMixin(AppHost):
    def _bind_wizard_gestures(self) -> None:
        # Bound once; each handler checks for itself whether Wizard is
        # picked and the switch is on, so changing Rider later needs no
        # re-binding. add="+" keeps any other binding working.
        self._wizard_points: list = []
        self._wizard_last_dot: tuple[int, int] | None = None
        self.bind("<ButtonPress-3>", self._on_wizard_press, add="+")
        self.bind("<B3-Motion>", self._on_wizard_motion, add="+")
        self.bind("<ButtonRelease-3>", self._on_wizard_release, add="+")

    def _wizard_listening(self, event) -> bool:
        """True only while Wizard is picked, the Settings switch is on,
        and the mouse press began in THIS window (not, say, the lockdown
        screen). It does not check where the mouse is now."""
        try:
            return (
                self.abilities.interaction is InteractionEffect.MOUSE_GESTURES
                and self.config_obj.mouse_gestures_enabled
                and event.widget.winfo_toplevel() is self
            )
        except Exception:
            return False

    def _wizard_inside_window(self, event) -> bool:
        """True if the mouse is over this window right now. Tk keeps
        sending drag and release events here even after the mouse leaves."""
        try:
            left, top = self.winfo_rootx(), self.winfo_rooty()
            return (
                left <= event.x_root < left + self.winfo_width()
                and top <= event.y_root < top + self.winfo_height()
            )
        except Exception:
            return False

    def _on_wizard_press(self, event) -> None:
        self._wizard_points = []
        self._wizard_last_dot = None
        if self._wizard_listening(event):
            self._wizard_points.append((event.x_root, event.y_root))

    def _on_wizard_motion(self, event) -> None:
        # An empty list means the press wasn't one we're listening to.
        if not self._wizard_points or not self._wizard_listening(event):
            return
        if not self._wizard_inside_window(event):
            return
        # Keep a point only when the mouse moved a few pixels. A slow swipe
        # sends hundreds of tiny moves, which would look too wobbly.
        last_x, last_y = self._wizard_points[-1]
        if abs(event.x_root - last_x) + abs(event.y_root - last_y) < 4:
            return
        self._wizard_points.append((event.x_root, event.y_root))
        self._wizard_draw_trail_dot(event)

    def _on_wizard_release(self, event) -> None:
        points, self._wizard_points = self._wizard_points, []
        if not points:
            return
        # Any surprise in here means "do nothing" -- a gesture is a
        # nice-to-have shortcut, never worth an error.
        try:
            if not self._wizard_listening(event):
                return
            if not self._wizard_inside_window(event):
                return
            target = gesture_target(self.router.ids, self.router.active, recognize(points))
            if target:
                self.navigate(target)
        except Exception:
            pass

    def _wizard_draw_trail_dot(self, event) -> None:
        """The little fading trail. Best-effort only: recognizing and
        switching pages never depend on it."""
        dot = None
        try:
            x = event.x_root - self.winfo_rootx()
            y = event.y_root - self.winfo_rooty()
            last = self._wizard_last_dot
            if last is not None and abs(x - last[0]) < 10 and abs(y - last[1]) < 10:
                return
            self._wizard_last_dot = (x, y)
            frame = ctk.CTkFrame(
                self, width=6, height=6, corner_radius=3, fg_color=self.color_focus
            )
            dot = frame
            frame.place(x=x - 3, y=y - 3)
            self._after(f"wizard_dot_{id(frame)}", 400, lambda: self._wizard_remove_dot(frame))
        except Exception:
            if dot is not None:
                self._wizard_remove_dot(dot)

    def _wizard_remove_dot(self, dot) -> None:
        try:
            dot.destroy()
        except Exception:
            pass
