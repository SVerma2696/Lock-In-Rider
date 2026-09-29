"""
ui/revice.py
============
Kamen Rider Revice's buddy link, from the window's side: the Buddy
page's buttons, and redrawing that page on every timer tick.

What the link actually does (pairing, sharing your timer, copying
history) lives in lock_in/application/buddy_controller.py. This file
only passes button presses to it and shows what it says.
"""

from __future__ import annotations

import logging
import time

from ..rider_effects import InteractionEffect
from .host import AppHost

logger = logging.getLogger(__name__)


class ReviceMixin(AppHost):
    def _on_buddy_share(self) -> None:
        self._buddy_action("share", self.controller.buddy.share)

    def _on_buddy_receive(self, code: str) -> None:
        self._buddy_action("receive", lambda: self.controller.buddy.receive(code))

    def _on_buddy_cancel(self) -> None:
        self._buddy_action("cancel", self.controller.buddy.cancel)

    def _on_buddy_pull(self) -> None:
        self._buddy_action("pull history", self.controller.buddy.pull)

    def _buddy_action(self, name: str, action) -> None:
        # A network problem must never reach the window. It's logged (no
        # history or task names are written to the log).
        try:
            action()
        except Exception:
            logger.exception("Buddy link %s failed", name)

    @property
    def _buddy_status(self):
        return self.controller.buddy.status

    @property
    def _buddy_message(self) -> str:
        return self.controller.buddy.message

    @property
    def _buddy_tab(self):
        """The Buddy page's screens, if that page has been drawn."""
        page = self.pages.get("buddy") if hasattr(self, "pages") else None
        return getattr(page, "tab", None)

    def _drain_buddy_link(self) -> None:
        """Called every tick from _pump(). Lets the buddy controller read
        what the link heard and send our timer, then redraws the Buddy
        page. The link closes as soon as Revice isn't the Rider any more
        (another Rider, or Standard Mode). Never lets an error reach the
        timer."""
        try:
            buddy = self.controller.buddy
            active = self.abilities.interaction is InteractionEffect.BUDDY_LINK
            if buddy.tick(active):
                self._render_tasks()
                self._refresh_current_task_picker()
            tab = self._buddy_tab
            if active and tab is not None:
                tab.show(buddy.link, buddy.status, buddy.message, time.monotonic())
        except Exception:
            logger.exception("Buddy link tick failed")
