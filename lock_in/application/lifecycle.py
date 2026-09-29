"""
application/lifecycle.py
========================
Starting and stopping the app's background helpers, the same way every
time.

Every helper that runs on its own (the window watcher, the camera
watcher, Hibiki's sound, Revice's buddy link) can be started and
stopped. When the app closes, every one of them must stop -- even if
stopping an earlier one went wrong. `ShutdownSteps` makes sure of that:
it runs every step, notes any failure in the log, and never runs twice.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

logger = logging.getLogger(__name__)


class Service(Protocol):
    """Anything that runs in the background and can be started and stopped.
    Stopping must be safe to call more than once."""

    def start(self) -> None: ...

    def stop(self) -> None: ...


class ShutdownSteps:
    """A list of clean-up steps, run in order, each one on its own.

    A step that fails is written to the log and the next step still
    runs. Calling run() a second time does nothing, so closing the app
    twice (say, the window's X and a Restart at the same moment) is safe.
    """

    def __init__(self) -> None:
        self._steps: list[tuple[str, Callable[[], object]]] = []
        self._done = False

    def add(self, name: str, step: Callable[[], object]) -> None:
        self._steps.append((name, step))

    def run(self) -> list[str]:
        """Run every step. Returns the names of the steps that failed."""
        if self._done:
            return []
        self._done = True
        failed: list[str] = []
        for name, step in self._steps:
            try:
                step()
            except Exception:
                failed.append(name)
                logger.exception("Shutdown step %r failed", name)
        return failed

    @property
    def done(self) -> bool:
        return self._done
