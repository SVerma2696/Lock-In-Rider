"""
application/enforcement_controller.py
=====================================
Deciding what to do about the window you're on, or a phone the camera
saw -- and learning from your corrections.

For every window the watcher reports during a running focus block:
  1. judge it (block list, allow list, the learned model, maybe Claude),
  2. step the warning ladder (warn -> nag -> minimize -> lockdown),
  3. write it down for training, and add it to the Activity list.
It hands back a `Decision`; the window code then shows the warning or
minimizes the window. Nothing here draws anything, so all of it can be
tested without opening a window.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..camera_enforcer import CameraEnforcer
from ..classifier import STUDY, NaiveBayesClassifier
from ..claude_fallback import ClaudeFallback, ClaudeVerdict
from ..config import Config
from ..enforcer import Action, Enforcer, Reason, Verdict, WindowInfo, judge
from ..observations import ObservationStore

# The Activity list keeps only this many rows.
ACTIVITY_LIMIT = 40
# Never block someone just for looking at Lock In itself.
OWN_WINDOW_WORDS = "lock in"


@dataclass(frozen=True)
class Decision:
    """What to do about one window (or the phone). `seconds` is how long
    you've been on it, for the warning's words. `new_activity_row` says
    the Activity list got a new row (so that page needs redrawing)."""

    window: WindowInfo
    verdict: Verdict
    action: Action
    seconds: float
    new_activity_row: bool = False


class ActivityLog:
    """The Activity page's list: every window seen during focus, newest
    last, with a repeat of the same app folded into the row above."""

    def __init__(self, limit: int = ACTIVITY_LIMIT, now: Callable[[], datetime] = datetime.now):
        self.entries: list[dict[str, Any]] = []
        self.limit = limit
        self._now = now

    def add(self, window: WindowInfo, verdict: Verdict) -> bool:
        """Add a window. Returns True if a new row was added (False when
        it was folded into the row above)."""
        key = window.display
        if self.entries and self.entries[-1]["key"] == key:
            last = self.entries[-1]
            last["count"] += 1
            last["blocked"] = verdict.blocked
            last["reason"] = verdict.reason
            last["confidence"] = verdict.confidence
            return False
        self.entries.append(
            {
                "key": key,
                "text": window.text,
                "time": self._now().strftime("%H:%M"),
                "reason": verdict.reason,
                "confidence": verdict.confidence,
                "blocked": verdict.blocked,
                "count": 1,
                "corrected": None,
            }
        )
        del self.entries[: -self.limit]
        return True


class EnforcementController:
    def __init__(
        self,
        config: Config,
        model: NaiveBayesClassifier,
        claude: ClaudeFallback,
        observations: ObservationStore,
        model_path: Path,
        on_claude_answer: Callable[[str, ClaudeVerdict], None],
        enforcer: Enforcer | None = None,
        camera_enforcer: CameraEnforcer | None = None,
    ) -> None:
        self.config = config
        self.model = model
        self.claude = claude
        self.observations = observations
        self.model_path = model_path
        self._on_claude_answer = on_claude_answer
        self.enforcer = enforcer or Enforcer(config)
        self.camera_enforcer = camera_enforcer or CameraEnforcer(config)
        self.activity = ActivityLog()

    # ------------------------------------------------------------------ #
    def reset(self) -> None:
        """A new phase: start the warning ladders from the bottom again."""
        self.enforcer.reset()
        self.camera_enforcer.reset()

    def judge_window(self, window: WindowInfo, focus_running: bool) -> Decision | None:
        """Judge one window. None means "not judged" (no running focus
        block, blocking is off, or it's Lock In itself)."""
        if not focus_running or not self.config.enforcement_enabled:
            return None
        if OWN_WINDOW_WORDS in (window.title or "").lower():
            return None

        verdict = judge(window, self.config, self.model, self.claude)
        action = self.enforcer.update(verdict, window)

        # If our own model isn't sure, quietly ask Claude in the
        # background. The answer is ready by the next check.
        if (
            self.config.claude_fallback_enabled
            and verdict.reason is Reason.CLASSIFIER
            and verdict.confidence < self.config.classifier_threshold
        ):
            self.claude.judge_async(window.text, self._on_claude_answer)

        # Write down EVERY window, not just the blocked ones, so
        # train.py can also show the distractions that slipped past.
        if self.config.record_observations:
            predicted, confidence = self.model.predict(window.text)
            self.observations.record(
                text=window.text,
                process=window.process_name,
                title=window.title,
                predicted=predicted,
                confidence=confidence,
                blocked=verdict.blocked,
            )
        new_row = self.activity.add(window, verdict)
        return Decision(window, verdict, action, self.enforcer.seconds_on_blocked_app, new_row)

    def judge_phone(self, phone_seen: bool, focus_running: bool) -> Decision | None:
        """Judge one camera sample. A sample can still be waiting from the
        instant before a pause or switch-off; that one is skipped."""
        if not focus_running:
            return None
        if not self.config.camera_monitoring_enabled or not self.config.enforcement_enabled:
            return None
        window = CameraEnforcer.PHONE_WINDOW
        verdict = Verdict(phone_seen, Reason.CAMERA, 1.0)
        action = self.camera_enforcer.update(phone_seen)
        new_row = self.activity.add(window, verdict) if phone_seen else False
        return Decision(window, verdict, action, self.camera_enforcer.seconds_on_phone, new_row)

    def learn_from_claude(self, text: str, verdict: ClaudeVerdict) -> bool:
        """Every real, fresh Claude answer also goes into the training
        data, so over time the local model needs to ask less. Errors and
        "couldn't ask" results teach nothing. Returns True if it learned."""
        if verdict.source != "claude":
            return False
        self.observations.record(text=text, predicted=verdict.label, confidence=verdict.confidence)
        self.observations.label_by_text(text, verdict.label)
        self.observations.save()
        return True

    def correct(self, entry: dict[str, Any], label: str) -> str | None:
        """Teach the model from one click on the Activity page, and save it
        straight away -- the very next check already uses it.

        "This was studying" is a strong hint the app should always be
        allowed, so it's added to the allow list too. Returns that
        program's name when it was allow-listed, otherwise None."""
        self.model.learn(entry["text"], label)
        self.model.save(self.model_path)
        entry["corrected"] = label
        # So train.py doesn't ask about a window you already corrected here.
        self.observations.label_by_text(entry["text"], label)
        self.observations.save()

        process = entry["key"].split(" — ")[0].strip().lower()
        if label == STUDY and process and process not in self.config.normalised_allowlist():
            self.config.allowlist.append(process)
            self.config.save()
            return process
        return None
