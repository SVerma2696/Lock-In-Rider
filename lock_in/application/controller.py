"""
application/controller.py
=========================
Everything the app does that isn't drawing: the timer, your tasks and
history, blocking, the camera, the Claude helper, notifications, Revice's
buddy link -- built once, wired together, and shut down cleanly.

The window (lock_in/ui/app.py) makes one `AppController` and asks it for
things. It doesn't own each of these parts itself any more.

    events       the one mailbox background helpers post notes to
    tasks_ctl    which task the next focus block is for
    focus        writing each focus block into history
    enforcement  judging windows and phones, the Activity list
    buddy        Revice's buddy link

Background helpers never touch the window. The window watcher, camera,
Claude helper, and notifier only ever `events.post(...)` a note; the
window's heartbeat hands the notes out on its own thread.
"""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from pathlib import Path

from ..ambient import AmbientPlayer
from ..camera_enforcer import PhoneWatcher
from ..classifier import NaiveBayesClassifier
from ..claude_fallback import ClaudeFallback
from ..config import (
    CONFIG_PATH,
    LOG_PATH,
    MODEL_PATH,
    OBSERVATIONS_PATH,
    TASKS_PATH,
    Config,
)
from ..history import HistoryStore
from ..monitor import ActiveWindowMonitor
from ..notifier import Notifier
from ..observations import ObservationStore
from ..revice_link import BuddyLink
from ..session import Phase, PomodoroSession
from ..tasks import TaskStore
from .buddy_controller import BuddyController
from .enforcement_controller import EnforcementController
from .events import BannerRequested, ClaudeAnswered, EventBus, PhoneSample, WindowSeen
from .focus_controller import FocusController
from .lifecycle import ShutdownSteps
from .task_controller import TaskController

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppPaths:
    """Where each saved file lives. Tests pass a throwaway folder."""

    config: Path = CONFIG_PATH
    model: Path = MODEL_PATH
    history: Path = LOG_PATH
    observations: Path = OBSERVATIONS_PATH
    tasks: Path = TASKS_PATH

    @classmethod
    def inside(cls, folder: Path) -> AppPaths:
        return cls(
            config=folder / "config.json",
            model=folder / "model.json",
            history=folder / "sessions.jsonl",
            observations=folder / "observations.jsonl",
            tasks=folder / "tasks.json",
        )


class AppController:
    def __init__(
        self,
        paths: AppPaths | None = None,
        *,
        monitor_interval: float = 1.0,
        buddy_name: str | None = None,
    ) -> None:
        self.paths = paths or AppPaths()
        self.events = EventBus()

        # ---- What you've saved ------------------------------------------ #
        self.config = Config.load(self.paths.config)
        self.model = NaiveBayesClassifier.load(self.paths.model)
        self.observations = ObservationStore(self.paths.observations)
        self.tasks = TaskStore(self.paths.tasks)
        self.history = HistoryStore(self.paths.history)

        # ---- The timer and what it drives ------------------------------- #
        self.session = PomodoroSession(self.config)
        self.tasks_ctl = TaskController(self.tasks)
        self.focus = FocusController(self.session, self.history, self.tasks_ctl)
        self.claude = ClaudeFallback(self.config)
        self.enforcement = EnforcementController(
            self.config,
            self.model,
            self.claude,
            self.observations,
            self.paths.model,
            on_claude_answer=lambda text, verdict: self.events.post(ClaudeAnswered(text, verdict)),
        )
        self.notifier = Notifier(self.config)
        self.notifier.banner_callback = lambda title, body, urgency: self.events.post(
            BannerRequested(title, body, urgency)
        )
        self.ambient = AmbientPlayer(self.config)

        # ---- Background helpers: they only ever post notes -------------- #
        self.monitor = ActiveWindowMonitor(
            callback=lambda window: self.events.post(WindowSeen(window)),
            interval=monitor_interval,
        )
        self.camera_watcher = PhoneWatcher(
            callback=lambda seen: self.events.post(PhoneSample(seen))
        )
        # Made once for the app's whole life, so redrawing the pages never
        # drops the connection. No network until Share or Receive is pressed.
        self.buddy = BuddyController(
            BuddyLink(buddy_name or socket.gethostname() or "Buddy"),
            self.session,
            self.history,
            self.tasks_ctl,
        )

        self._shutdown = ShutdownSteps()
        self._shutdown.add("save settings", self.config.save)
        self._shutdown.add("save model", lambda: self.model.save(self.paths.model))
        self._shutdown.add("save observations", self.observations.save)
        self._shutdown.add("close buddy link", self.buddy.close)
        self._shutdown.add("stop window watcher", self.monitor.stop)
        self._shutdown.add("stop sound", self.ambient.stop)
        self._shutdown.add("stop camera", self.camera_watcher.stop)
        self._shutdown.add("close mailbox", self.events.close)

    # ------------------------------------------------------------------ #
    # Starting and stopping
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Start the background helpers. They begin paused: nothing is
        watched until a focus block runs."""
        self.monitor.start()
        self.camera_watcher.start()

    def shutdown(self) -> list[str]:
        """Save everything and stop every helper. Every step runs even if
        one fails, and a second call does nothing. Returns the steps that
        failed."""
        return self._shutdown.run()

    @property
    def is_shut_down(self) -> bool:
        return self._shutdown.done

    # ------------------------------------------------------------------ #
    # Watching, on and off
    # ------------------------------------------------------------------ #
    @property
    def focus_running(self) -> bool:
        return self.session.phase is Phase.FOCUS and self.session.is_running

    def resume_watching(self) -> None:
        """A focus block is running: watch windows, and the camera if it's on."""
        self.monitor.resume()
        if self.config.camera_monitoring_enabled:
            self.camera_watcher.resume()

    def pause_watching(self) -> None:
        """Not in a running focus block: stop watching, stop the sound."""
        self.monitor.pause()
        self.camera_watcher.pause()
        self.ambient.stop()

    def save_all(self) -> None:
        self.config.save()
        self.model.save(self.paths.model)
        self.observations.save()
