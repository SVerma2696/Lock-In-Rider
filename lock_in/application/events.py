"""
application/events.py
=====================
The one mailbox every background helper uses to tell the app something.

Some jobs run on their own background helper: watching which window
you're in, the camera, the Claude helper, the update check. The screen
toolkit is NOT safe to touch from those helpers. So a helper never
changes the screen itself -- it drops a small note ("event") in this
mailbox, and the app's heartbeat reads the notes on the screen's own
thread, where it's safe.

Before, each helper had its own mailbox (five of them). Now there's one,
and each kind of note is its own small, named type, so the code that
reads them can't mix them up.

    post()              any thread: drop a note in the mailbox
    subscribe()         say which function handles which kind of note
    dispatch_pending()  the screen's thread only: hand every waiting note
                        to its handlers
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from ..claude_fallback import ClaudeVerdict
    from ..enforcer import WindowInfo
    from ..updater import CheckResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WindowSeen:
    """The window watcher saw you on this window."""

    window: WindowInfo


@dataclass(frozen=True)
class PhoneSample:
    """The camera took one look. `seen` is True if a phone was in view."""

    seen: bool


@dataclass(frozen=True)
class BannerRequested:
    """Something wants a short message shown at the top of the window."""

    title: str
    body: str
    urgency: str


@dataclass(frozen=True)
class ClaudeAnswered:
    """The optional Claude helper answered about one window title."""

    text: str
    verdict: ClaudeVerdict


@dataclass(frozen=True)
class UpdateChecked:
    """The update check finished. `extracted_path` is the unpacked new
    version, when there is one ready to swap in."""

    result: CheckResult
    extracted_path: Path | None


AppEvent = WindowSeen | PhoneSample | BannerRequested | ClaudeAnswered | UpdateChecked

E = TypeVar("E")


class EventBus:
    """A thread-safe mailbox with handlers, one list per kind of note."""

    def __init__(self) -> None:
        self._queue: queue.SimpleQueue[Any] = queue.SimpleQueue()
        self._handlers: dict[type, list[Callable[[Any], None]]] = {}
        self._closed = threading.Event()

    def post(self, event: AppEvent) -> None:
        """Safe from any thread. Notes posted after close() are dropped,
        so a helper finishing late can't reach a closed window."""
        if not self._closed.is_set():
            self._queue.put(event)

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """`handler` is called (on the screen's thread) for every note of
        exactly this type, in the order they arrived."""
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch_pending(self, limit: int | None = None) -> int:
        """Hand every waiting note to its handlers. Screen thread only.

        A handler that fails is logged and skipped: one bad note must
        never stop the heartbeat or the notes after it. `limit` caps how
        many notes one call handles, so a flood can't freeze the window.
        Returns how many notes were handled."""
        handled = 0
        while not self._closed.is_set() and (limit is None or handled < limit):
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                break
            handled += 1
            for handler in self._handlers.get(type(event), ()):
                try:
                    handler(event)
                except Exception:
                    logger.exception("Handling %s failed", type(event).__name__)
        return handled

    def pending(self) -> int:
        """Roughly how many notes are waiting (for tests)."""
        return self._queue.qsize()

    def close(self) -> None:
        """Stop taking and handing out notes, and throw away what's waiting."""
        self._closed.set()
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    @property
    def closed(self) -> bool:
        return self._closed.is_set()
