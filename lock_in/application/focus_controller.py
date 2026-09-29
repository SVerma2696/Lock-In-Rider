"""
application/focus_controller.py
===============================
Writing each focus block into your history.

A focus block is timed from the moment you start working until it
finishes, is skipped, or is reset. This remembers when it began, and
writes one line into history when it ends -- "completed" if the timer
ran out, "cut short" if you skipped or reset. It never draws anything.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..history import HistoryStore, SessionRecord
from ..session import Phase, PomodoroSession
from .task_controller import TaskController


class FocusController:
    def __init__(
        self,
        session: PomodoroSession,
        history: HistoryStore,
        tasks: TaskController,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.session = session
        self.history = history
        self.tasks = tasks
        self._now = now
        # Set the instant a FOCUS phase begins, cleared once it's logged.
        # None means "no focus block is being timed right now".
        self.block_start: datetime | None = None
        self.block_planned_seconds: int = 0

    def phase_started(self) -> None:
        """Called whenever a new phase begins."""
        if self.session.phase is Phase.FOCUS:
            self.block_start = self._now()
            self.block_planned_seconds = self.session.total_seconds

    def work_resumed(self) -> bool:
        """Start (or Resume) was pressed during a focus block.

        A focus block is often entered, then sits paused until you press
        Start. History goes by the start time, so it's taken again at the
        real "began working" moment -- but only if nothing has counted
        down yet (not a resume in the middle of a block). The picked task
        becomes In progress. Returns True if a task changed."""
        if self.session.remaining_seconds >= self.block_planned_seconds:
            self.block_start = self._now()
        return self.tasks.mark_started()

    def log_block(self, completed: bool) -> SessionRecord | None:
        """Write one history line for the focus block being timed, if
        there is one, and return it. Called when a block finishes
        (completed=True), and on Skip and Reset (completed=False)."""
        if self.block_start is None:
            return None
        start, self.block_start = self.block_start, None
        if completed:
            duration = self.block_planned_seconds
        else:
            duration = max(0, self.block_planned_seconds - self.session.remaining_seconds)
            if duration == 0:
                # Entering FOCUS and skipping it without ever pressing Start
                # isn't a session you worked. Don't log a zero-second row.
                return None
        record = SessionRecord(
            start=start.isoformat(timespec="seconds"),
            end=self._now().isoformat(timespec="seconds"),
            duration_seconds=duration,
            task_id=self.tasks.current_task_id,
            completed=completed,
        )
        try:
            self.history.record(record)
        except OSError:
            # A disk problem (full disk, a locked file, cloud sync) must
            # never stop the clean-up that runs right after this. Only
            # OSError is swallowed -- a real bug still shows up.
            return None
        return record
