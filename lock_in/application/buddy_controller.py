"""
application/buddy_controller.py
===============================
Revice's buddy link, without the screen: pairing, sharing your timer,
and copying history.

The network part is lock_in/revice_link.py and the rules are
lock_in/revice_sync.py -- neither changed. This is the part that used to
live inside the window code: reading what the link heard, answering a
buddy's "Pull History", merging their history into yours, and sending
your timer about once a second. The Buddy page just shows `status` and
`message`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from .. import revice_sync
from ..history import HistoryStore
from ..revice_link import BuddyLink
from ..session import PomodoroSession
from .task_controller import TaskController

logger = logging.getLogger(__name__)


class BuddyController:
    def __init__(
        self,
        link: BuddyLink,
        session: PomodoroSession,
        history: HistoryStore,
        tasks: TaskController,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.link = link
        self.session = session
        self.history = history
        self.tasks = tasks
        self._clock = clock
        # What the Buddy page shows: the buddy's timer (None until one
        # arrives) and one line of words (empty when there's nothing to say).
        self.status: dict[str, Any] | None = None
        self.message = ""
        self._last_sent = 0.0

    # ---- The Buddy page's buttons ------------------------------------ #
    def share(self) -> None:
        self._clear()
        self.link.share()

    def receive(self, code: str) -> None:
        if not revice_sync.is_valid_code(code):
            self.message = revice_sync.MSG_TYPE_FOUR
            return
        self._clear()
        self.link.receive(code)

    def cancel(self) -> None:
        self._clear()
        self.link.close()

    def pull(self) -> None:
        if self.link.request_pull():
            self.message = ""

    # ---- Every timer tick -------------------------------------------- #
    def tick(self, active: bool) -> bool:
        """Read what the link heard and send our timer when it's due.

        `active` is False when Revice isn't the Rider any more (another
        Rider, or Standard Mode): then the link is closed straight away.
        Returns True if a buddy's tasks were added to yours (so the task
        pages need redrawing)."""
        if not active:
            if self.link.state != "idle":
                self.link.close()
            self.link.poll()
            self._clear()
            return False
        tasks_changed = False
        for event in self.link.poll():
            tasks_changed = self._handle(event) or tasks_changed
        now = self._clock()
        if (
            self.link.state == "paired"
            and now - self._last_sent >= revice_sync.STATUS_EVERY_SECONDS
        ):
            self._last_sent = now
            task = self.tasks.current_task()
            self.link.send_status(
                revice_sync.status_from_session(
                    self.session, task.name if task else None, self.link.name
                )
            )
        return tasks_changed

    def close(self) -> None:
        """Unpair and stop listening. Safe to call any time, and twice."""
        self.link.close()

    # ------------------------------------------------------------------ #
    def _clear(self) -> None:
        self.message = ""
        self.status = None

    def _handle(self, event: tuple) -> bool:
        kind = event[0]
        if kind == "paired":
            self._clear()
        elif kind == "status":
            self.status = revice_sync.clean_status(event[1])
        elif kind == "pull_request":
            sessions, task_list = revice_sync.pull_reply_payload(self.history, self.tasks.tasks)
            self.link.send_pull_reply(sessions, task_list)
        elif kind == "pull_reply":
            # The merge alone is wrapped (not the whole handler) so a
            # failure partway -- say sessions.jsonl locked by OneDrive --
            # still shows a message instead of leaving the page frozen.
            before = len(self.tasks.tasks.all())
            try:
                added = revice_sync.merge_pull(self.history, self.tasks.tasks, event[1], event[2])
                self.message = revice_sync.pull_result_text(*added)
            except Exception:
                logger.exception("Merging a buddy's history failed")
                self.message = revice_sync.MSG_PULL_FAILED
            # Redraw whenever a task actually got added, even if something
            # above failed partway through.
            return len(self.tasks.tasks.all()) != before
        elif kind == "pull_failed":
            self.message = revice_sync.MSG_PULL_FAILED
        elif kind == "left":
            self.message = revice_sync.MSG_BUDDY_LEFT
            self.status = None
        elif kind == "error":
            self.message = event[1]
        return False
