# Strict Camera Monitoring (opt-in phone detection) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in "Strict Camera Monitoring" enforcer that watches the webcam during a focus block and runs the existing WARN/NAG/MINIMIZE/LOCKDOWN escalation ladder against phone sightings, exactly the way it already runs against blocked apps.

**Architecture:** A new `lock_in/camera_enforcer.py` module with three pieces — `PhoneDetector` (wraps one loaded OpenCV DNN network, frame in, phone-seen bool out), `PhoneWatcher` (a background thread, same shape as `monitor.py`'s `ActiveWindowMonitor`, that owns the camera hardware lifecycle and samples every 4s), and `CameraEnforcer` (wraps a second, independent `enforcer.Enforcer` instance, feeding it a synthetic `Verdict` so the whole existing action ladder — including `message_for()` — is reused untouched). `ui.py` wires `PhoneWatcher`'s samples through a `queue.Queue` into `CameraEnforcer`, draining it from the existing `_pump()` tick loop, mirroring exactly how `ActiveWindowMonitor` already feeds `Enforcer`.

**Tech Stack:** Python 3, `opencv-python-headless` (new dependency), a bundled pre-trained SSD MobileNet v2 (COCO) TensorFlow model loaded through OpenCV's `cv2.dnn` module — no PyTorch, no TensorFlow runtime, no GPU.

## Global Constraints

- One new `Config` field only: `camera_monitoring_enabled: bool = False`. Every other threshold (`grace_seconds`, `strike_interval_seconds`, `strike_decay_seconds`, `hard_mode`) is reused as-is from the existing window-blocking settings — no new Config fields for them.
- `standard_mode` (Tier 0 / Standard Mode) must not read or override `camera_monitoring_enabled` — Standard Mode strips Rider theme/wording flavor only, never real enforcement toggles (same precedent as `hard_mode`, `claude_fallback_enabled`).
- Sample interval (`SAMPLE_INTERVAL_SECONDS = 4.0`), detection confidence threshold (`DETECTION_CONFIDENCE_THRESHOLD = 0.5`), and camera device (always index `0`) are fixed module-level constants — not Config fields, not UI settings.
- A video frame is never written to disk, displayed, or sent over any network. The feature makes zero network calls, ever — the model is bundled, not downloaded at runtime.
- The camera hardware handle (`cv2.VideoCapture`) must be released (`cap.release()`) the instant monitoring pauses (break, idle, session end, or the Settings switch being turned off) — the physical webcam LED must never stay lit after the on-screen "Camera monitoring active" indicator disappears. The loaded DNN model network is a separate lifecycle: built once per `PhoneWatcher` instance (construction or first sample) and kept warm in memory across every pause/resume — only the hardware capture opens and closes each time.
- Every OpenCV/model/camera call is wrapped in `try/except`; any failure (missing `cv2`, missing model file, camera locked by another app, a frame read failing) degrades to "feature unavailable" — it never crashes the app or the main enforcement loop.
- `opencv-python-headless` is added to `requirements.txt` unconditionally (not platform-guarded like `pywin32`), matching how `anthropic` is already listed unconditionally even though its feature is off by default — this keeps it installed in the dev/test environment so the test suite can exercise real `cv2` calls (blob preprocessing, checksum-verified model files) without needing camera hardware.
- Version: v2.3.1. No git commit, push, or other git state change is executed as part of any task in this plan — the final task hands the exact commands to the user to run themselves.

---

### Task 1: `Config.camera_monitoring_enabled` field

**Files:**
- Modify: `lock_in/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config.camera_monitoring_enabled: bool` (default `False`), used by every later task via `self.config_obj.camera_monitoring_enabled`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py` (near the existing `test_standard_mode_defaults_to_off` / `test_standard_mode_round_trips_through_save_and_load` tests, same file):

```python
def test_camera_monitoring_enabled_defaults_to_off():
    assert Config().camera_monitoring_enabled is False


def test_camera_monitoring_enabled_round_trips_through_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    Config(camera_monitoring_enabled=True).save(path)
    assert Config.load(path).camera_monitoring_enabled is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -k camera_monitoring_enabled -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'camera_monitoring_enabled'`

- [ ] **Step 3: Add the field**

In `lock_in/config.py`, inside the `Config` dataclass, directly below the existing `standard_mode: bool = False` field (and its comment block):

```python
    # Strict Camera Monitoring: off unless you turn it on yourself. When
    # it's on, PhoneWatcher (camera_enforcer.py) samples your webcam
    # roughly every 4 seconds during a focus block, and a phone in frame
    # feeds the exact same WARN/NAG/MINIMIZE/LOCKDOWN ladder Enforcer
    # already runs for blocked apps. Nothing about a frame is ever saved,
    # shown, or sent anywhere -- it's judged and thrown away immediately.
    camera_monitoring_enabled: bool = False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -k camera_monitoring_enabled -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full test suite to confirm nothing else broke**

Run: `pytest tests/test_config.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add lock_in/config.py tests/test_config.py
git commit -m "Add Config.camera_monitoring_enabled field for Strict Camera Monitoring"
```

---

### Task 2: `Reason.CAMERA` and `CameraEnforcer` (reuses the existing ladder)

**Files:**
- Modify: `lock_in/enforcer.py`
- Create: `lock_in/camera_enforcer.py`
- Test: `tests/test_enforcer.py`, `tests/test_camera_enforcer.py`

**Interfaces:**
- Consumes: `enforcer.Action`, `enforcer.Enforcer`, `enforcer.Reason`, `enforcer.Verdict`, `enforcer.WindowInfo`, `enforcer.message_for()` (all already defined in `lock_in/enforcer.py`).
- Produces: `enforcer.Reason.CAMERA` (new enum member). `camera_enforcer.CameraEnforcer` — class with `__init__(self, config, clock: Callable[[], float] = time.monotonic)`, `.update(phone_seen: bool) -> Action`, `.reset() -> None`, `.seconds_on_phone -> float` property, and class attribute `CameraEnforcer.PHONE_WINDOW: WindowInfo` (used by Task 5's `ui.py` wiring as the synthetic window passed to `_perform()`/`_log_activity()`).

- [ ] **Step 1: Write the failing test for `Reason.CAMERA`**

Add to `tests/test_enforcer.py` (anywhere near the other `Reason`-adjacent tests):

```python
def test_reason_camera_exists():
    assert Reason.CAMERA.value == "camera"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_enforcer.py -k test_reason_camera_exists -v`
Expected: FAIL — `AttributeError: CAMERA`

- [ ] **Step 3: Add `Reason.CAMERA`**

In `lock_in/enforcer.py`, inside the `Reason` enum (currently `ALLOWLIST`, `BLOCKLIST`, `CLASSIFIER`, `CLAUDE`, `UNKNOWN`, `NOT_FOCUSING`), add:

```python
    CAMERA = "camera"
```

- [ ] **Step 4: Run it to verify it passes**

Run: `pytest tests/test_enforcer.py -k test_reason_camera_exists -v`
Expected: PASS

- [ ] **Step 5: Write the failing tests for `CameraEnforcer`**

Create `tests/test_camera_enforcer.py`:

```python
"""Tests for CameraEnforcer -- the pure logic that feeds phone-sighting
samples through the same escalation ladder Enforcer already applies to
blocked apps. No real camera or model involved anywhere in this file."""

import pytest

from lock_in.config import Config
from lock_in.enforcer import Action, message_for
from lock_in.camera_enforcer import CameraEnforcer


class FakeClock:
    def __init__(self) -> None:
        self.now = 500.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def config() -> Config:
    return Config(grace_seconds=8, strike_interval_seconds=10,
                  strike_decay_seconds=30, hard_mode=False)


@pytest.fixture
def camera_enforcer(config, clock) -> CameraEnforcer:
    return CameraEnforcer(config, clock=clock)


def test_no_phone_seen_is_action_none(camera_enforcer):
    assert camera_enforcer.update(False) is Action.NONE


def test_grace_period_stays_silent(camera_enforcer, clock):
    assert camera_enforcer.update(True) is Action.NONE
    clock.advance(7)
    assert camera_enforcer.update(True) is Action.NONE


def test_first_strike_after_grace_is_a_warning(camera_enforcer, clock):
    camera_enforcer.update(True)
    clock.advance(9)
    assert camera_enforcer.update(True) is Action.WARN


def test_hard_mode_minimizes_then_locks_down(config, clock):
    config.hard_mode = True
    ce = CameraEnforcer(config, clock=clock)
    ce.update(True)
    clock.advance(9)
    assert ce.update(True) is Action.MINIMIZE
    clock.advance(11)
    assert ce.update(True) is Action.LOCKDOWN


def test_no_longer_seeing_a_phone_resets_the_grace_timer(camera_enforcer, clock):
    camera_enforcer.update(True)
    clock.advance(9)
    camera_enforcer.update(True)          # strike 1 (WARN)
    clock.advance(2)
    assert camera_enforcer.update(False) is Action.NONE
    assert camera_enforcer.seconds_on_phone == 0.0


def test_reset_clears_strikes_and_the_grace_period_starts_over(camera_enforcer, clock):
    camera_enforcer.update(True)
    clock.advance(9)
    camera_enforcer.update(True)          # strike 1 (WARN)
    camera_enforcer.reset()
    assert camera_enforcer.update(True) is Action.NONE   # back in grace period


def test_phone_window_reads_naturally_in_the_existing_messages():
    title, body = message_for(
        Action.WARN, app=CameraEnforcer.PHONE_WINDOW.display,
        remaining="20:00", seconds=5, lockdown=15,
    )
    assert "your phone" in body
```

- [ ] **Step 6: Run them to verify they fail**

Run: `pytest tests/test_camera_enforcer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lock_in.camera_enforcer'`

- [ ] **Step 7: Create `lock_in/camera_enforcer.py` with `CameraEnforcer`**

```python
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
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `pytest tests/test_camera_enforcer.py tests/test_enforcer.py -v`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add lock_in/enforcer.py lock_in/camera_enforcer.py tests/test_enforcer.py tests/test_camera_enforcer.py
git commit -m "Add Reason.CAMERA and CameraEnforcer, reusing the existing escalation ladder"
```

---

### Task 3: Bundle the detection model into `lock_in/assets/`

**Files:**
- Create: `lock_in/assets/phone_detector.pb`, `lock_in/assets/phone_detector.pbtxt`
- Create: `.gitattributes`
- Modify: `requirements.txt`
- Modify: `lock_in/camera_enforcer.py`
- Test: `tests/test_camera_enforcer.py`

**Interfaces:**
- Produces: `camera_enforcer.MODEL_PB_PATH: Path`, `camera_enforcer.MODEL_PBTXT_PATH: Path`, `camera_enforcer.CAMERA_BACKEND_AVAILABLE: bool`, `camera_enforcer.PHONE_CLASS_ID: int` (`77`), `camera_enforcer.DETECTION_CONFIDENCE_THRESHOLD: float` (`0.5`), `camera_enforcer.DETECTION_INPUT_SIZE: tuple` (`(300, 300)`), `camera_enforcer.SAMPLE_INTERVAL_SECONDS: float` (`4.0`) -- all consumed by Task 4 (`PhoneDetector`), Task 5 (`PhoneWatcher`), and Task 6 (`ui.py`'s disabled-switch fallback).

The model is SSD MobileNet v2, COCO-trained (2018-03-29 TensorFlow Object Detection API release), Apache-2.0 licensed. Two files are needed, verified reachable and byte-exact during plan authoring:

| File | Source | Bytes | SHA-256 |
|---|---|---|---|
| `phone_detector.pb` | extracted from `http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz`, member `ssd_mobilenet_v2_coco_2018_03_29/frozen_inference_graph.pb` | 69,688,296 | `2a8d8a89d695842e60d8c6d144181100555563e21acf2fa1e8f561fec5c3c6ad` |
| `phone_detector.pbtxt` | `https://raw.githubusercontent.com/opencv/opencv_extra/master/testdata/dnn/ssd_mobilenet_v2_coco_2018_03_29.pbtxt` | 115,601 | `cfbecf9447c384403ef5cf695f4cd0bb4840c1312938280350639a9a8e82d303` |

"cell phone" is COCO class id `77` in this model's label space (confirmed against `mscoco_label_map.pbtxt` from the TensorFlow models repo).

- [ ] **Step 1: Write the failing checksum test**

Add to `tests/test_camera_enforcer.py`:

```python
import hashlib

from lock_in.camera_enforcer import CAMERA_BACKEND_AVAILABLE, MODEL_PB_PATH, MODEL_PBTXT_PATH

EXPECTED_PB_SHA256 = "2a8d8a89d695842e60d8c6d144181100555563e21acf2fa1e8f561fec5c3c6ad"
EXPECTED_PBTXT_SHA256 = "cfbecf9447c384403ef5cf695f4cd0bb4840c1312938280350639a9a8e82d303"


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_bundled_model_files_exist_with_the_expected_checksum():
    assert MODEL_PB_PATH.exists(), "run the model-download step from the implementation plan"
    assert MODEL_PBTXT_PATH.exists(), "run the model-download step from the implementation plan"
    assert _sha256(MODEL_PB_PATH) == EXPECTED_PB_SHA256
    assert _sha256(MODEL_PBTXT_PATH) == EXPECTED_PBTXT_SHA256


def test_camera_backend_available_is_true_once_cv2_and_the_model_are_present():
    assert CAMERA_BACKEND_AVAILABLE is True
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_camera_enforcer.py -k "bundled_model or backend_available" -v`
Expected: FAIL — `ImportError: cannot import name 'CAMERA_BACKEND_AVAILABLE'`

- [ ] **Step 3: Download and verify the two files**

Run (from the repo root, Bash):

```bash
mkdir -p lock_in/assets
curl -sL -o /tmp/ssd_v2.tar.gz "http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz"
tar -xzf /tmp/ssd_v2.tar.gz -C /tmp ssd_mobilenet_v2_coco_2018_03_29/frozen_inference_graph.pb
mv /tmp/ssd_mobilenet_v2_coco_2018_03_29/frozen_inference_graph.pb lock_in/assets/phone_detector.pb
curl -sL -o lock_in/assets/phone_detector.pbtxt "https://raw.githubusercontent.com/opencv/opencv_extra/master/testdata/dnn/ssd_mobilenet_v2_coco_2018_03_29.pbtxt"
sha256sum lock_in/assets/phone_detector.pb lock_in/assets/phone_detector.pbtxt
```

Verify the two printed hashes match the table above exactly before continuing. If they don't match, delete both files and re-download — do not proceed with a mismatched file.

- [ ] **Step 4: Prevent Windows line-ending conversion from corrupting the files**

`phone_detector.pbtxt` is a text-format protobuf; without this, git's line-ending handling (already seen elsewhere in this repo converting LF to CRLF) could silently corrupt it on commit. Create `.gitattributes` at the repo root:

```
lock_in/assets/phone_detector.pb binary
lock_in/assets/phone_detector.pbtxt binary
```

- [ ] **Step 5: Add the dependency**

In `requirements.txt`, add (after the `Pillow` block, before the `pywin32`/`psutil` block):

```
# This lets the app look at your webcam and recognize a phone in frame,
# for the opt-in "Strict Camera Monitoring" switch in the Blocking tab.
# Not required for anything else -- the app works fully without it, that
# one switch just can't turn on. -headless because nothing here ever
# opens a window with OpenCV's own GUI code.
opencv-python-headless>=4.8.0
```

- [ ] **Step 6: Install it and add the path/availability constants**

Run: `pip install opencv-python-headless>=4.8.0`

In `lock_in/camera_enforcer.py`, add near the top, right after the module docstring and before the `CameraEnforcer` class:

```python
from pathlib import Path

try:
    import cv2  # type: ignore
except ImportError:  # pragma: no cover - depends on install
    cv2 = None

_ASSETS_DIR = Path(__file__).parent / "assets"
MODEL_PB_PATH = _ASSETS_DIR / "phone_detector.pb"
MODEL_PBTXT_PATH = _ASSETS_DIR / "phone_detector.pbtxt"

# True only once everything Strict Camera Monitoring needs -- the
# opencv-python-headless package AND both bundled model files -- is
# actually present. ui.py disables the Settings switch (with an
# explanation) whenever this is False, the same treatment monitor.py's
# BACKEND_AVAILABLE already gets for window detection.
CAMERA_BACKEND_AVAILABLE = (
    cv2 is not None and MODEL_PB_PATH.exists() and MODEL_PBTXT_PATH.exists()
)

PHONE_CLASS_ID = 77                     # COCO's class id for "cell phone"
DETECTION_CONFIDENCE_THRESHOLD = 0.5
DETECTION_INPUT_SIZE = (300, 300)
SAMPLE_INTERVAL_SECONDS = 4.0
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pytest tests/test_camera_enforcer.py -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add lock_in/assets/phone_detector.pb lock_in/assets/phone_detector.pbtxt .gitattributes requirements.txt lock_in/camera_enforcer.py tests/test_camera_enforcer.py
git commit -m "Bundle the SSD MobileNet v2 phone-detection model, add opencv-python-headless"
```

---

### Task 4: `PhoneDetector` (one loaded model, frame in, phone-seen bool out)

**Files:**
- Modify: `lock_in/camera_enforcer.py`
- Test: `tests/test_camera_enforcer.py`

**Interfaces:**
- Consumes: `cv2`, `PHONE_CLASS_ID`, `DETECTION_CONFIDENCE_THRESHOLD`, `DETECTION_INPUT_SIZE`, `MODEL_PB_PATH`, `MODEL_PBTXT_PATH` (Task 3).
- Produces: `camera_enforcer.PhoneDetector` — `PhoneDetector(net)` (takes an already-loaded `cv2.dnn` network, or any object with matching `.setInput()`/`.forward()` methods -- this is what makes it testable without a real model), classmethod `PhoneDetector.from_files(pb_path, pbtxt_path) -> PhoneDetector`, and `.detect(frame) -> bool`. Consumed by Task 5's `PhoneWatcher`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_camera_enforcer.py`:

```python
import numpy as np

from lock_in.camera_enforcer import PhoneDetector


class FakeNet:
    """Stands in for a real cv2.dnn network -- returns a canned detection
    array shaped like the real SSD output, (1, 1, N, 7):
    [batchId, classId, confidence, left, top, right, bottom]."""

    def __init__(self, detections) -> None:
        self._output = np.array([[detections]], dtype=np.float32)
        self.last_input = None

    def setInput(self, blob) -> None:
        self.last_input = blob

    def forward(self):
        return self._output


def test_detects_a_confident_phone():
    net = FakeNet([[0.0, 77.0, 0.9, 0.1, 0.1, 0.5, 0.5]])
    detector = PhoneDetector(net)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    assert detector.detect(frame) is True


def test_ignores_a_confident_non_phone_class():
    net = FakeNet([[0.0, 1.0, 0.95, 0.1, 0.1, 0.5, 0.5]])   # class 1 = "person"
    detector = PhoneDetector(net)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    assert detector.detect(frame) is False


def test_ignores_a_low_confidence_phone():
    net = FakeNet([[0.0, 77.0, 0.2, 0.1, 0.1, 0.5, 0.5]])
    detector = PhoneDetector(net)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    assert detector.detect(frame) is False


def test_no_detections_at_all_is_false():
    net = FakeNet([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    detector = PhoneDetector(net)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    assert detector.detect(frame) is False
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_camera_enforcer.py -k PhoneDetector -v`
Expected: FAIL — `ImportError: cannot import name 'PhoneDetector'`

(the four `test_detects_a_confident_phone` etc. tests will also fail to collect for the same reason)

- [ ] **Step 3: Implement `PhoneDetector`**

Add to `lock_in/camera_enforcer.py`, after the constants from Task 3, before `CameraEnforcer`:

```python
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
    def from_files(cls, pb_path: Path, pbtxt_path: Path) -> "PhoneDetector":
        net = cv2.dnn.readNetFromTensorflow(str(pb_path), str(pbtxt_path))
        return cls(net)

    def detect(self, frame) -> bool:
        """One frame in, one answer out: was a phone visible, confidently, anywhere in it?"""
        blob = cv2.dnn.blobFromImage(frame, size=DETECTION_INPUT_SIZE, swapRB=True, crop=False)
        self._net.setInput(blob)
        output = self._net.forward()
        for detection in output[0, 0]:
            class_id = int(detection[1])
            confidence = float(detection[2])
            if class_id == PHONE_CLASS_ID and confidence >= DETECTION_CONFIDENCE_THRESHOLD:
                return True
        return False
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_camera_enforcer.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add lock_in/camera_enforcer.py tests/test_camera_enforcer.py
git commit -m "Add PhoneDetector: one loaded model, a frame in, a phone-seen bool out"
```

---

### Task 5: `PhoneWatcher` (the background thread that owns the camera)

**Files:**
- Modify: `lock_in/camera_enforcer.py`
- Test: `tests/test_camera_enforcer.py`

**Interfaces:**
- Consumes: `PhoneDetector`, `MODEL_PB_PATH`, `MODEL_PBTXT_PATH`, `CAMERA_BACKEND_AVAILABLE`, `SAMPLE_INTERVAL_SECONDS`, `cv2` (all from Tasks 3-4).
- Produces: `camera_enforcer.PhoneWatcher` — `PhoneWatcher(callback: Callable[[bool], None], detector=None, camera_factory=None, interval: float = SAMPLE_INTERVAL_SECONDS)`, with `.start()`, `.stop()`, `.resume()`, `.pause()`, all no-argument, matching `monitor.ActiveWindowMonitor`'s exact method names and shapes. Consumed by Task 6's `ui.py`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_camera_enforcer.py`:

```python
from lock_in.camera_enforcer import PhoneWatcher


class FakeCapture:
    def __init__(self, frame=None) -> None:
        self.released = False
        self._frame = frame if frame is not None else np.zeros((2, 2, 3), dtype=np.uint8)

    def read(self):
        return True, self._frame

    def release(self) -> None:
        self.released = True


class FakeDetector:
    def __init__(self, result: bool = False) -> None:
        self.result = result
        self.calls = 0

    def detect(self, frame) -> bool:
        self.calls += 1
        return self.result


def test_camera_stays_closed_until_resumed():
    opened = []

    def factory():
        opened.append(1)
        return FakeCapture()

    watcher = PhoneWatcher(callback=lambda seen: None, detector=FakeDetector(),
                            camera_factory=factory)
    watcher._step()
    assert opened == []           # never resumed -- must not touch the camera at all

    watcher.resume()
    watcher._step()
    assert opened == [1]


def test_pausing_releases_the_camera_handle():
    cap = FakeCapture()
    watcher = PhoneWatcher(callback=lambda seen: None, detector=FakeDetector(),
                            camera_factory=lambda: cap)
    watcher.resume()
    watcher._step()
    assert cap.released is False

    watcher.pause()
    assert cap.released is True


def test_a_detected_phone_reaches_the_callback():
    seen = []
    watcher = PhoneWatcher(callback=seen.append, detector=FakeDetector(result=True),
                            camera_factory=lambda: FakeCapture())
    watcher.resume()
    watcher._step()
    assert seen == [True]


def test_no_phone_also_reaches_the_callback():
    seen = []
    watcher = PhoneWatcher(callback=seen.append, detector=FakeDetector(result=False),
                            camera_factory=lambda: FakeCapture())
    watcher.resume()
    watcher._step()
    assert seen == [False]


def test_a_camera_that_fails_to_open_never_crashes_a_step():
    def broken_factory():
        raise RuntimeError("camera is in use by another app")

    watcher = PhoneWatcher(callback=lambda seen: None, detector=FakeDetector(),
                            camera_factory=broken_factory)
    watcher.resume()
    watcher._step()   # must not raise
    watcher._step()   # must not raise a second time either
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_camera_enforcer.py -k PhoneWatcher -v`
Expected: FAIL — `ImportError: cannot import name 'PhoneWatcher'`

- [ ] **Step 3: Implement `PhoneWatcher`**

Add to `lock_in/camera_enforcer.py`, after `PhoneDetector`. This uses `threading` and `Optional`, which aren't imported yet — Step 5 below adds them to the file's top-level imports in one pass, alongside everything else this file needs; don't add a separate `import threading` here.

```python
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
        detector: Optional[PhoneDetector] = None,
        camera_factory: Optional[Callable[[], object]] = None,
        interval: float = SAMPLE_INTERVAL_SECONDS,
    ) -> None:
        self._callback = callback
        self._detector = detector
        self._detector_unavailable = detector is None and not CAMERA_BACKEND_AVAILABLE
        self._camera_factory = camera_factory or (lambda: cv2.VideoCapture(0))
        self.interval = interval

        self._cap = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._paused.set()   # start paused -- nothing to check until a focus block begins

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
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def _ensure_detector(self) -> None:
        if self._detector is None and not self._detector_unavailable:
            try:
                self._detector = PhoneDetector.from_files(MODEL_PB_PATH, MODEL_PBTXT_PATH)
            except Exception:
                self._detector_unavailable = True

    def _step(self) -> None:
        """One sample: open the camera if needed, read one frame, judge it, report it."""
        if self._paused.is_set():
            return
        self._ensure_detector()
        if self._detector is None:
            return
        if self._cap is None:
            try:
                self._cap = self._camera_factory()
            except Exception:
                self._cap = None
                return
        try:
            ok, frame = self._cap.read()
            if not ok:
                return
            self._callback(self._detector.detect(frame))
        except Exception:
            pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._step()
            except Exception:
                # A camera or model hiccup must not silently kill the
                # background thread -- the next sample, a few seconds
                # later, deserves a fresh chance to work.
                pass
            self._stop.wait(self.interval)
```

- [ ] **Step 4: Add `threading` and `Optional` to the file's top-level imports**

`lock_in/camera_enforcer.py` should have exactly one set of imports, at the very top of the file, in this order (standard library, then relative) — replace whatever import block is there now (from Tasks 2-3) with this complete one:

```python
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .enforcer import Action, Enforcer, Reason, Verdict, WindowInfo
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_camera_enforcer.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add lock_in/camera_enforcer.py tests/test_camera_enforcer.py
git commit -m "Add PhoneWatcher: background camera sampling, release-on-pause hardware lifecycle"
```

---

### Task 6: Wire it into `ui.py`

**Files:**
- Modify: `lock_in/ui.py`

**Interfaces:**
- Consumes: `camera_enforcer.CAMERA_BACKEND_AVAILABLE`, `camera_enforcer.CameraEnforcer`, `camera_enforcer.PhoneWatcher` (Tasks 2-5); `enforcer.Verdict` (already exists).
- Produces: `LockInApp.camera_enforcer`, `LockInApp.camera_watcher`, `LockInApp._camera_queue`, `LockInApp._drain_camera_queue()`, `LockInApp._on_camera_switch_toggled()`, `LockInApp._sync_camera_indicator()` — internal to `ui.py`, nothing external depends on these names.

This task is UI wiring with no automated test (same as every other Settings-tab switch in this codebase) — verified manually in Task 8.

- [ ] **Step 1: Import the new names**

In `lock_in/ui.py`, change:

```python
from .enforcer import Action, Enforcer, Reason, WindowInfo, judge, lockdown_label_for, message_for
from .monitor import BACKEND_AVAILABLE, ActiveWindowMonitor, minimize_window
```

to:

```python
from .camera_enforcer import CAMERA_BACKEND_AVAILABLE, CameraEnforcer, PhoneWatcher
from .enforcer import Action, Enforcer, Reason, Verdict, WindowInfo, judge, lockdown_label_for, message_for
from .monitor import BACKEND_AVAILABLE, ActiveWindowMonitor, minimize_window
```

- [ ] **Step 2: Construct `camera_enforcer` and `camera_watcher` in `__init__`**

In `lock_in/ui.py`, right after `self.enforcer = Enforcer(self.config_obj)` (around line 140):

```python
        self.enforcer = Enforcer(self.config_obj)
        self.camera_enforcer = CameraEnforcer(self.config_obj)
```

Right after `self._window_queue: "queue.Queue[WindowInfo]" = queue.Queue()` (around line 145):

```python
        self._window_queue: "queue.Queue[WindowInfo]" = queue.Queue()
        self._camera_queue: "queue.Queue[bool]" = queue.Queue()
```

Right after the `self.monitor = ActiveWindowMonitor(...)` block (around line 149-152):

```python
        self.monitor = ActiveWindowMonitor(
            callback=self._window_queue.put,
            interval=1.0,
        )
        self.camera_watcher = PhoneWatcher(callback=self._camera_queue.put)
```

Right after `self.monitor.start()` (around line 183):

```python
        self.monitor.start()
        self.camera_watcher.start()
```

- [ ] **Step 3: Add the Settings switch and disabled-state fallback**

In `_build_blocking_tab`, right after the "Hard mode" switch block (after the line ending `.pack(anchor="w", pady=6)` for `hard_var`, around line 639):

```python
        self.camera_var = ctk.BooleanVar(value=self.config_obj.camera_monitoring_enabled)
        self.camera_switch = ctk.CTkSwitch(
            frame, text="Strict Camera Monitoring (uses your webcam to catch phones)",
            variable=self.camera_var, progress_color=COLOR_DANGER,
            command=self._on_camera_switch_toggled,
        )
        self.camera_switch.pack(anchor="w", pady=6)
        if not CAMERA_BACKEND_AVAILABLE:
            self.camera_switch.configure(state="disabled")
            ctk.CTkLabel(
                frame,
                text=("Strict Camera Monitoring needs opencv-python-headless "
                      "and its bundled model file, and isn't available right "
                      "now. Run: pip install opencv-python-headless"),
                text_color=COLOR_WARN, justify="left", wraplength=440,
            ).pack(anchor="w", pady=(0, 6))
```

- [ ] **Step 4: Add the toggle handler (applies instantly, even mid-block)**

Add this method near `_on_claude_toggle` (search for `def _on_claude_toggle` in `lock_in/ui.py` and add this right after that method ends):

```python
    def _on_camera_switch_toggled(self) -> None:
        """
        Applies right away, even in the middle of a focus block -- same
        reasoning that already applies to every other enforcement switch
        in this app: turning Strict Camera Monitoring off should stop
        the camera immediately, not wait for the next focus block to
        start. Turning it ON mid-block starts it immediately too.
        """
        self.config_obj.camera_monitoring_enabled = self.camera_var.get()
        self.config_obj.save()
        if self.config_obj.camera_monitoring_enabled:
            if self.session.phase is Phase.FOCUS and self.session.is_running:
                self.camera_watcher.resume()
        else:
            self.camera_watcher.pause()
        self._sync_camera_indicator()
```

- [ ] **Step 5: Wire `resume()`/`pause()` into every place `monitor.resume()`/`monitor.pause()` already appears**

In `_on_phase_started` (around line 1285-1289), change:

```python
        if phase is Phase.FOCUS and self.session.is_running:
            self.monitor.resume()
        else:
            self.monitor.pause()
            self._close_lockdown()
```

to:

```python
        if phase is Phase.FOCUS and self.session.is_running:
            self.monitor.resume()
            if self.config_obj.camera_monitoring_enabled:
                self.camera_watcher.resume()
        else:
            self.monitor.pause()
            self.camera_watcher.pause()
            self._close_lockdown()
```

In `_on_phase_ended` (around line 1304-1305), change:

```python
    def _on_phase_ended(self) -> None:
        self.monitor.pause()
```

to:

```python
    def _on_phase_ended(self) -> None:
        self.monitor.pause()
        self.camera_watcher.pause()
```

In `_do_toggle` (around line 1338-1342), change:

```python
        if not was_running and self.session.is_running:
            if self.session.phase is Phase.FOCUS:
                self.monitor.resume()
        else:
            self.monitor.pause()
```

to:

```python
        if not was_running and self.session.is_running:
            if self.session.phase is Phase.FOCUS:
                self.monitor.resume()
                if self.config_obj.camera_monitoring_enabled:
                    self.camera_watcher.resume()
        else:
            self.monitor.pause()
            self.camera_watcher.pause()
```

In `_on_reset` (around line 1394-1397), change:

```python
    def _on_reset(self) -> None:
        self.session.reset()
        self.enforcer.reset()
        self.monitor.pause()
```

to:

```python
    def _on_reset(self) -> None:
        self.session.reset()
        self.enforcer.reset()
        self.camera_enforcer.reset()
        self.monitor.pause()
        self.camera_watcher.pause()
```

In `_on_close` (around line 2049-2057), change:

```python
        finally:
            self.monitor.stop()
            self.destroy()
```

to:

```python
        finally:
            self.monitor.stop()
            self.camera_watcher.stop()
            self.destroy()
```

Also reset `camera_enforcer` alongside `enforcer` in `_on_phase_started` -- change the very first line of that method (around line 1263):

```python
    def _on_phase_started(self) -> None:
        """Turn on watching for FOCUS, turn it off for everything else."""
        self.enforcer.reset()
```

to:

```python
    def _on_phase_started(self) -> None:
        """Turn on watching for FOCUS, turn it off for everything else."""
        self.enforcer.reset()
        self.camera_enforcer.reset()
```

- [ ] **Step 6: Add `_drain_camera_queue()` and call it from `_pump()`**

In `_pump()` (around line 1024-1026), change:

```python
            self._drain_window_queue()
            self._drain_claude_queue()
            self._drain_banner_queue()
```

to:

```python
            self._drain_window_queue()
            self._drain_camera_queue()
            self._drain_claude_queue()
            self._drain_banner_queue()
```

Add the new method right after `_drain_window_queue()` ends (search for `def _drain_claude_queue` and add this method directly above it):

```python
    def _drain_camera_queue(self) -> None:
        """Look at every phone-sighting sample PhoneWatcher noticed, and act on it."""
        while True:
            try:
                phone_seen = self._camera_queue.get_nowait()
            except queue.Empty:
                return

            # PhoneWatcher only ever samples while resumed, but a sample
            # can still be sitting in the queue from the instant before
            # a pause/toggle-off took effect -- skip it rather than act
            # on a stale reading, same guard _drain_window_queue already
            # applies to window samples.
            if self.session.phase is not Phase.FOCUS or not self.session.is_running:
                continue
            if not self.config_obj.camera_monitoring_enabled:
                continue

            verdict = Verdict(phone_seen, Reason.CAMERA, 1.0)
            action = self.camera_enforcer.update(phone_seen)
            self._log_activity(CameraEnforcer.PHONE_WINDOW, verdict)
            if action is not Action.NONE:
                self._perform(action, CameraEnforcer.PHONE_WINDOW)
```

- [ ] **Step 7: Add the on-screen "camera monitoring active" indicator**

In `_build_header()`, right after `self.watch_label.pack(pady=(12, 0))` (around line 588):

```python
        self.watch_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=11), text_color=COLOR_IDLE,
            wraplength=480,
        )
        self.watch_label.pack(pady=(12, 0))

        # Only ever shown while a focus block is actually running AND the
        # switch is on -- i.e. exactly whenever PhoneWatcher genuinely has
        # the camera open. Gone the instant either stops being true, on
        # top of whatever your webcam's own hardware light already shows.
        self.camera_indicator_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=11), text_color=COLOR_ENFORCE_ACCENT,
        )
        self.camera_indicator_label.pack(pady=(4, 0))
```

Add the sync method anywhere near `_refresh_timer_widgets` (e.g. directly above it):

```python
    def _sync_camera_indicator(self) -> None:
        active = (
            self.config_obj.camera_monitoring_enabled
            and self.session.phase is Phase.FOCUS
            and self.session.is_running
        )
        self.camera_indicator_label.configure(
            text="\U0001F4F7 Camera monitoring active" if active else ""
        )
```

Call it from `_refresh_timer_widgets()` -- add as the last line of that method (it's already called every `_pump()` tick, every 200ms, so the indicator tracks phase/running changes automatically without any extra wiring):

```python
        self.title(f"{self.session.format_remaining()} · {label} — Lock In")
        self._sync_camera_indicator()
```

- [ ] **Step 8: Run the full test suite**

Run: `pytest -v`
Expected: all PASS (no test in this task, but every earlier task's tests must still pass after these edits)

- [ ] **Step 9: Commit**

```bash
git add lock_in/ui.py
git commit -m "Wire Strict Camera Monitoring into ui.py: switch, indicator, phase lifecycle"
```

---

### Task 7: Docs and version bump

**Files:**
- Modify: `README.md`
- Modify: `lock_in/ui.py` (Help tab only)
- Modify: `lock_in/__init__.py` (or wherever the version string currently lives -- check first)

**Interfaces:** none (documentation only).

- [ ] **Step 1: Find the current version string**

Run: `grep -rn "2\.3\.0" lock_in/ main.py 2>/dev/null`

Expected: shows exactly where the version string(s) currently live (likely `lock_in/__init__.py` and/or a window-title constant). Update whatever this finds to `2.3.1`, following the exact same pattern the `v2.3.0` bump used (check `git show d67f28b --stat` if the location isn't obvious).

- [ ] **Step 2: Add the README section**

In `README.md`, add a new section directly after the existing "## Claude fallback (optional, off by default)" section (after its final `pytest` / `xvfb-run` code block, before "## 🔧 Config"):

```markdown
## Strict Camera Monitoring (optional, off by default)

A separate opt-in extra, unrelated to Claude fallback: while turned on,
Lock In watches your webcam during a focus block and runs the exact
same WARN → NAG → (hard mode) MINIMIZE → LOCKDOWN ladder it already
runs for blocked apps -- just aimed at a phone in frame.

### Setup

**1. Install OpenCV.**

```bat
pip install opencv-python-headless
```

**2. Turn it on.** Blocking tab → "Strict Camera Monitoring (uses your
webcam to catch phones)". If the switch is greyed out, the message
underneath tells you exactly what's missing.

### What actually happens to a frame

Roughly every 4 seconds during a focus block, one frame is grabbed from
your default webcam, checked against a small bundled object-detection
model for a phone, and thrown away immediately. Nothing is ever saved
to disk, shown on screen, or sent over a network -- there is no network
call anywhere in this feature, the model ships inside the app itself.

### How it stays out of the way

- **Off by default, one switch, your call entirely.**
- **Only runs during an active focus block.** Paused on every break,
  on idle, and the instant the session ends -- exactly like the window
  monitor that blocks distracting apps.
- **The camera closes the moment monitoring pauses.** The detection
  model stays loaded in memory (so turning it back on doesn't have to
  reload anything), but the actual webcam handle is released
  immediately on every break/pause/toggle-off, so the hardware light on
  your laptop always matches what the app's own on-screen "Camera
  monitoring active" label says -- never lit when the label isn't
  showing.
- **Fails silent, not broken.** No webcam, `opencv-python-headless`
  not installed, the camera locked by another app -- all of it
  degrades to "feature unavailable," never a crash, never a lockdown
  UI you can't explain.
```

- [ ] **Step 3: Add one line to "Known limits"**

Find the "## Known limits" section in `README.md` and add one bullet, matching the style of the existing bullets there:

```markdown
- Strict Camera Monitoring only checks your default webcam (device
  index 0) -- no multi-camera picker, and no way to change the sample
  interval or confidence threshold from the UI.
```

- [ ] **Step 4: Add a Help tab paragraph**

In `lock_in/ui.py`'s `_build_help_tab` method, add a new numbered section right after the existing `heading("3. Some heroes have a secret extra power", ...)` block ends (right after the `body(...)` call that reads "Everything else — the timer, the blocking rules, and the learning — works exactly the same no matter which hero you pick. The hero is just for fun.", and before the `_build_settings_tab` method begins):

```python
        # --- Strict Camera Monitoring ------------------------------------ #
        heading("4. Strict Camera Monitoring (optional)", COLOR_ENFORCE_ACCENT)
        body(
            "A separate opt-in extra, nothing to do with heroes: turn it "
            "on in the Blocking tab and Lock In checks your webcam every "
            "few seconds during a focus block for a phone in frame, "
            "using the exact same warn-then-escalate ladder as blocked "
            "apps. Off by default. Only runs during an actual focus "
            "block, and the camera turns off the instant a break starts "
            "or you flip the switch back off -- watch for the little "
            "\"Camera monitoring active\" label under the timer; the "
            "camera is only ever on when that's showing."
        )
```

- [ ] **Step 5: Run the full test suite once more**

Run: `pytest -v`
Expected: all PASS (docs-only changes, but confirms nothing was accidentally broken)

- [ ] **Step 6: Commit**

```bash
git add README.md lock_in/ui.py lock_in/__init__.py
git commit -m "v2.3.1: document Strict Camera Monitoring, bump version"
```

(adjust the last `git add` path if Step 1 found the version string somewhere other than `lock_in/__init__.py`)

---

### Task 8: Manual verification, then hand off to the user

**Files:** none (verification only).

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: all tests pass, including every test added in Tasks 1-5.

- [ ] **Step 2: Launch the real app and verify by hand**

Run: `python main.py`

Check, in order:
1. Blocking tab shows the "Strict Camera Monitoring" switch, off by default.
2. Turn it on, start a focus block. Within ~4 seconds, the "📷 Camera monitoring active" label appears under the timer, and your webcam's hardware light turns on.
3. Hold a phone up to the camera. Within the grace period plus one more sample, a WARN notification appears (or MINIMIZE/LOCKDOWN if Hard mode is also on), same visual style as an app being blocked.
4. Skip to a break, or press Reset. The "Camera monitoring active" label disappears, and the webcam's hardware light turns off within a couple of seconds.
5. Start another focus block, then flip the Strict Camera Monitoring switch off *while the block is running*. Confirm the label disappears and the hardware light turns off immediately, without needing to end the block.
6. Open the Activity tab. Confirm a "your phone" entry appears in the list when a phone was detected, styled the same as a blocked app entry.
7. If `opencv-python-headless` is uninstalled (`pip uninstall opencv-python-headless -y`, test, then `pip install opencv-python-headless` again to restore it), confirm the switch is greyed out with the explanatory text, and the rest of the app still works normally.

- [ ] **Step 3: Give the user the commands to review and push**

Do not run any of these — print them for the user to run themselves:

```bash
git log --oneline main..HEAD
git push origin main
```

(or, if this work happened on a separate branch/worktree per the user's usual workflow, the equivalent branch push + PR commands instead.)
