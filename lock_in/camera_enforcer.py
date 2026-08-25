"""
camera_enforcer.py
===================
An opt-in, off-by-default extra: while "Strict Camera Monitoring" is
turned on in Settings, this watches your webcam during a focus block and
runs the exact same WARN / NAG / MINIMIZE / LOCKDOWN ladder `enforcer.py`
already runs for blocked apps -- just aimed at a phone in frame instead
of a blocked window.

This file has two halves, kept separate on purpose, same split as the
enforcer.py / monitor.py boundary elsewhere in this app:

  - `CameraEnforcer` (below) is pure decision-making: a `bool` ("was a
    phone visible just now?") goes in, an `Action` comes out. It touches
    no camera, no thread, no OpenCV -- just a second, independent
    `enforcer.Enforcer` instance, fed a synthetic verdict. That's what
    makes it directly unit-testable with no hardware involved.
  - `PhoneDetector` and `PhoneWatcher` (added in later tasks) are the
    half that actually touches the webcam and the model.
"""

from __future__ import annotations

import time
from typing import Callable

from .enforcer import Action, Enforcer, Reason, Verdict, WindowInfo


class CameraEnforcer:
    """
    Feeds phone-sighting samples through the same escalation ladder
    `Enforcer` already applies to blocked apps -- see enforcer.py's
    `Enforcer` class for the actual grace/strike/decay/hard-mode logic,
    all of which is reused here unchanged.
    """

    # A phone in your hand isn't a window, so there's nothing to
    # minimize -- but reusing WindowInfo (and therefore message_for(),
    # via .display) means every existing message template just works,
    # reading naturally: "your phone isn't part of your focus block."
    PHONE_WINDOW = WindowInfo(title="your phone", process_name="")

    def __init__(self, config, clock: Callable[[], float] = time.monotonic) -> None:
        self._enforcer = Enforcer(config, clock=clock)

    def reset(self) -> None:
        """Forget everything and start over -- call this whenever the phase changes."""
        self._enforcer.reset()

    def update(self, phone_seen: bool) -> Action:
        """Move the ladder forward by one sample and return what to do right now."""
        verdict = Verdict(phone_seen, Reason.CAMERA, 1.0)
        return self._enforcer.update(verdict, self.PHONE_WINDOW)

    @property
    def seconds_on_phone(self) -> float:
        """How many seconds a phone has been continuously visible, this one sighting."""
        return self._enforcer.seconds_on_blocked_app
