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

import importlib.util
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .diagnostics import log_once
from .enforcer import Action, Enforcer, Reason, Verdict, WindowInfo

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).parent / "assets"
MODEL_PB_PATH = _ASSETS_DIR / "phone_detector.pb"
MODEL_PBTXT_PATH = _ASSETS_DIR / "phone_detector.pbtxt"

# True only once everything Strict Camera Monitoring needs -- the
# opencv-python-headless package AND both bundled model files -- is
# actually present. ui.py disables the Settings switch (with an
# explanation) whenever this is False, the same treatment monitor.py's
# BACKEND_AVAILABLE already gets for window detection.
#
# This only asks "is OpenCV installed?" -- it doesn't load it. OpenCV is
# big (tens of MB of memory), and most people never turn the camera on,
# so it's loaded by _cv2() the first time the camera is really used.
CAMERA_BACKEND_AVAILABLE = (
    importlib.util.find_spec("cv2") is not None
    and MODEL_PB_PATH.exists()
    and MODEL_PBTXT_PATH.exists()
)


def _cv2():
    """Load OpenCV the first time it's needed (Python remembers it after)."""
    import cv2

    return cv2


PHONE_CLASS_ID = 77  # COCO's class id for "cell phone"
DETECTION_CONFIDENCE_THRESHOLD = 0.5
DETECTION_INPUT_SIZE = (300, 300)
SAMPLE_INTERVAL_SECONDS = 4.0


class PhoneDetector:
    """
    Wraps one loaded OpenCV DNN network. Construction (`from_files`) is
    the slow part -- reading the model off disk and building the graph
    -- so `PhoneWatcher` (next task) builds exactly one of these and
    keeps it warm in memory for as long as the app runs, regardless of
    how many times the camera itself opens and closes.
    """

    def __init__(self, net) -> None:
        self._net = net

    @classmethod
    def from_files(cls, pb_path: Path, pbtxt_path: Path) -> PhoneDetector:
        net = _cv2().dnn.readNetFromTensorflow(str(pb_path), str(pbtxt_path))
        return cls(net)

    def detect(self, frame) -> bool:
        """One frame in, one answer out: was a phone visible, confidently, anywhere in it?"""
        blob = _cv2().dnn.blobFromImage(frame, size=DETECTION_INPUT_SIZE, swapRB=True, crop=False)
        self._net.setInput(blob)
        output = self._net.forward()
        for detection in output[0, 0]:
            class_id = int(detection[1])
            confidence = float(detection[2])
            if class_id == PHONE_CLASS_ID and confidence >= DETECTION_CONFIDENCE_THRESHOLD:
                return True
        return False


class PhoneWatcher:
    """
    Checks the webcam for a phone, on its own background thread --
    same shape as monitor.py's ActiveWindowMonitor (start/stop/pause/
    resume, starts paused, calls back with one plain value each sample).

    The model (`PhoneDetector`) is built once, lazily, on the first
    sample -- and then kept warm in memory for as long as this object
    lives, no matter how many times the camera itself opens and closes.
    The camera hardware handle is a completely separate lifecycle:
    resume() opens it fresh, pause() releases it immediately. That
    split matters -- the physical webcam LED is outside this app's
    control, and it must never stay lit after monitoring has visibly
    stopped, even though re-loading the ~66MB model on every single
    focus block would be wasteful and pointless.

    `detector` and `camera_factory` are constructor arguments (not
    hardcoded) purely so this class can be unit tested without a real
    camera or model file -- see tests/test_camera_enforcer.py.
    """

    def __init__(
        self,
        callback: Callable[[bool], None],
        detector: PhoneDetector | None = None,
        camera_factory: Callable[[], object] | None = None,
        interval: float = SAMPLE_INTERVAL_SECONDS,
    ) -> None:
        self._callback = callback
        self._detector = detector
        self._detector_unavailable = detector is None and not CAMERA_BACKEND_AVAILABLE
        self._camera_factory = camera_factory or (lambda: _cv2().VideoCapture(0))
        self.interval = interval

        self._cap: Any = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._paused.set()  # start paused -- nothing to check until a focus block begins
        self._cam_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Start the background thread. Safe to call more than once."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="phone-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Tell the background thread to stop, wait a moment, and release the camera."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._release_camera()

    def resume(self) -> None:
        """Start sampling again (called when a focus block begins, if the switch is on)."""
        self._paused.clear()

    def pause(self) -> None:
        """
        Stop sampling and immediately let go of the physical camera --
        called on a break, on idle, on session end, or the instant the
        Settings switch is turned off. The hardware LED must go dark
        exactly when this runs, not whenever the model next happens to
        be garbage collected.
        """
        self._paused.set()
        self._release_camera()

    # ------------------------------------------------------------------ #
    def _release_camera(self) -> None:
        with self._cam_lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    log_once(logger, "camera-release", "Letting go of the camera failed")
                self._cap = None

    def _ensure_detector(self) -> None:
        if self._detector is None and not self._detector_unavailable:
            try:
                self._detector = PhoneDetector.from_files(MODEL_PB_PATH, MODEL_PBTXT_PATH)
            except Exception:
                logger.warning("The phone detector couldn't load", exc_info=True)
                self._detector_unavailable = True

    @property
    def is_capturing(self) -> bool:
        """True only while a real camera handle is actually open right now."""
        return self._cap is not None

    def _step(self) -> None:
        """One sample: open the camera if needed, read one frame, judge it, report it."""
        if self._paused.is_set():
            return
        self._ensure_detector()
        if self._detector is None:
            return
        with self._cam_lock:
            if self._paused.is_set():  # a pause landed while we were setting up
                return
            if self._cap is None:
                try:
                    self._cap = self._camera_factory()
                except Exception:
                    log_once(logger, "camera-open", "The camera couldn't be opened")
                    self._cap = None
                    return
            try:
                ok, frame = self._cap.read()
            except Exception:
                return
        if not ok:
            return
        try:
            self._callback(self._detector.detect(frame))
        except Exception:
            pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._step()
            except Exception:
                log_once(logger, "camera-step", "A camera check failed")
                # A camera or model hiccup must not silently kill the
                # background thread -- the next sample, a few seconds
                # later, deserves a fresh chance to work.
                pass
            self._stop.wait(self.interval)


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
