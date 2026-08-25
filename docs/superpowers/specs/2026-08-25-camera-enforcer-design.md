# Lock In: Strict Camera Monitoring (opt-in phone detection)

Date: 2026-08-25
Status: Approved, ready for implementation plan

## Goal

An opt-in "hardcore" enforcer that watches your webcam during a focus
block and nudges you when it sees a phone in frame — the same
padlock-style friction the app already applies to blocked apps, aimed
at the one distraction a window-only monitor can never see.

One item, and nothing else: **Strict Camera Monitoring.**

## Why this isn't a Tier

Tiers 0-3 are all Kamen Rider flavor — optional workflow/visual
adjustments layered on a Rider theme, or (for Tier 0) the absence of
one. Camera monitoring has nothing to do with Rider theming: it's a
real-world enforcement capability, orthogonal to which Rider (or none,
under Standard Mode) is selected. It belongs next to `hard_mode` and
`claude_fallback_enabled` — core enforcement toggles that Standard
Mode already leaves untouched — not inside the Rider/Tier system.

Also deliberately **not** part of the app's baseline. Continuous
webcam capture plus object-detection inference is real, constant CPU
and battery cost, and an always-on camera is the kind of thing that
makes an app feel like it's watching you rather than helping you. Off
by default, one explicit switch, complete user agency.

## Architecture

A new `lock_in/camera_enforcer.py`, parallel to `enforcer.py`, with
two pieces:

**`PhoneWatcher`** — a background thread, same shape as `monitor.py`'s
`ActiveWindowMonitor` (`start()`/`stop()`/`pause()`/`resume()`, starts
paused). It loads the bundled detection model **once**, at
construction (or lazily on first `resume()`) — building the neural net
graph from disk has a real one-time cost, and there's no reason to pay
it more than once per app run. The camera hardware handle is a
separate lifecycle entirely:

- `resume()` (a focus block starts): opens `cv2.VideoCapture(0)` fresh.
- `pause()` (a break starts, the session stops, or the switch is
  turned off): calls `cap.release()` immediately and drops the handle.

This split matters: the model staying warm in memory costs nothing
observable to the user, but the physical webcam LED is a hardware
signal outside the app's control. If the camera stayed open in the
background through a 15-minute break to save a couple of seconds on
the next focus block, the LED would stay lit while the app's own
on-screen indicator (below) says monitoring is off — a direct
contradiction that breaks the trust this feature depends on.
Re-opening the camera every focus block (all off the main thread, so
the ~1-2s hardware init never freezes the UI) keeps the physical light
and the software state perfectly in sync, always.

While running, `PhoneWatcher` samples one frame roughly every 4
seconds (a module-level constant, not a user setting — sampling every
frame would be the CPU/battery/fan cost this whole design exists to
avoid; a phone glance doesn't need split-second detection), runs it
through the model, and reports back a single `bool` — phone seen in
that frame, yes or no. The frame array is discarded immediately after
inference: never written to disk, never displayed, never sent
anywhere. Every OpenCV/model call is wrapped in try/except, matching
`monitor.py`'s existing philosophy — if the camera is grabbed by
another app (Zoom, Teams), a driver hiccups, or `cv2` isn't installed
at all, the feature quietly becomes unavailable rather than crashing
the app or silently pretending to work.

**Reuses the existing `Enforcer`/`Action` ladder** — a second,
independent `Enforcer(config)` instance (the exact class already
defined in `enforcer.py`) is fed a synthetic verdict whenever a phone
is seen, sharing your existing `grace_seconds` /
`strike_interval_seconds` / `strike_decay_seconds` / `hard_mode`
numbers — the same grace period you'd want before Discord earning a
strike applies naturally to a phone glance. This gets WARN → NAG →
(hard mode) MINIMIZE/LOCKDOWN for free, through the exact code path
already used for blocked apps, including `message_for()` — called with
`app="your phone"`, so existing message templates read naturally
("your phone isn't part of your focus block") with zero new message
tables to write.

## Threading / data flow

`PhoneWatcher`'s callback never touches Tkinter state directly — it
puts the `bool` sample onto a `queue.Queue`, exactly like
`ActiveWindowMonitor` already does with `WindowInfo`. A new
`_drain_camera_queue()` in `ui.py`, called from `_pump()` next to the
existing `_drain_window_queue()`, drains it on the main thread each
tick: builds a synthetic `WindowInfo` (`process_name="phone"`,
`title="Phone"`), wraps the sample into a `Verdict(blocked=<bool>,
reason=Reason.CAMERA)`, feeds it to the camera `Enforcer`, and calls
the existing `_perform()` if the result isn't `Action.NONE` — so
WARN/NAG/LOCKDOWN rendering is 100% shared code, not reimplemented.
`Reason.CAMERA` is a new `enforcer.Reason` enum member, purely so the
Activity tab can say *why* a strike happened.

`PhoneWatcher.resume()`/`.pause()` are called in lockstep with
`ActiveWindowMonitor.resume()`/`.pause()` (focus start/break/pause),
but only actually take effect — i.e., only open the physical camera —
when `config.camera_monitoring_enabled` is `True`. The camera is never
opened at all otherwise.

## Config

One new field:

```python
camera_monitoring_enabled: bool = False
```

Nothing else new — grace/strike/decay/hard_mode are all reused as-is.
Standard Mode (`standard_mode`) does **not** read or override this
field, same as it already leaves `hard_mode`/`claude_fallback_enabled`
alone — Standard Mode strips Rider flavor, not enforcement behavior.

## Settings UI

- New switch in the **Blocking** tab, directly below "Hard mode":
  *"Strict Camera Monitoring (uses your webcam to catch phones)"*, off
  by default, styled like the existing Claude-fallback blurb (a short
  description + the switch). Disabled with explanatory text — same
  treatment `monitor.py`'s `BACKEND_AVAILABLE` already gets — if
  OpenCV, the model file, or a webcam aren't available.
- A small on-screen label near the timer, e.g. *"📷 Camera monitoring
  active"* — visible only while the switch is on **and** a focus block
  is actively running (i.e., exactly whenever `PhoneWatcher` actually
  has the camera open). Gone during breaks/idle, gone the instant the
  switch is turned off. This is the app's own explicit confirmation of
  what the hardware LED is also showing — never watching without
  saying so.

## Model & dependencies

- `opencv-python-headless` (no GUI bindings needed, smaller than full
  `opencv-python`) — new line in `requirements.txt`, marked optional
  the same way `pywin32`/`winotify` already are: the app works
  perfectly without it, this one switch just can't turn on.
- A small pre-trained SSD MobileNet v2 object-detection model
  (COCO-trained, 80 classes including "cell phone" at class id 77,
  Apache-2.0 licensed, ~66MB frozen graph + a 113KB config file),
  bundled into `lock_in/assets/` — same pattern as the existing app
  icon. Fully offline: no first-run download, no network call, ever.
  `build.bat` already ships everything under `lock_in/assets/` via
  `--add-data`, so no packaging changes needed. The implementation
  plan pins the exact source URLs and checksums.

## Error handling

Camera unavailable, model missing, `cv2` not installed, device locked
by another app, a frame read failing mid-session — all of these
degrade to "feature unavailable" (switch disabled with an explanation,
or if it fails mid-block, quietly stops sampling until the next focus
block) and never crash the app or the main enforcement loop. Treating
the webcam as a volatile peripheral that can vanish at any moment,
not a guaranteed resource.

## Testing

- `tests/test_camera_enforcer.py`, mirroring `test_enforcer.py`: pure
  logic only — feeding `bool` samples through the synthetic-verdict →
  `Enforcer` → `Action` wiring, and `Reason.CAMERA` plumbing. No real
  camera or model involved.
- `PhoneWatcher`'s actual OpenCV/thread/hardware plumbing is not
  covered by automated tests, same as `monitor.py`'s OS-specific calls
  today — existing project precedent, not a new gap.
- `Config`: `camera_monitoring_enabled` defaults to `False`, round-
  trips through `load`/`save`, same shape as the other boolean flags.
- `ui.py` wiring (switch, indicator label, disabled-state fallback):
  screenshot-driven manual verification of the running app, same
  approach every prior tier used.

## Docs

- `README.md`: a new section mirroring the existing "Claude fallback
  (optional, off by default)" section — what it does, what actually
  happens to a frame (in, judged, discarded — nothing stored or sent),
  how it stays out of the way, why it's split into its own module. Also
  one line in "Known limits" (default webcam only, needs a working
  `cv2` install).
- Help tab: one short paragraph alongside the other enforcement
  settings, describing what it does and exactly how to turn it on.
- `.gitignore`: no new entries. The model ships committed in
  `lock_in/assets/`, same as the app icon; nothing about this feature
  writes generated files to the working tree.

## Out of scope for this pass

- Any UI to change the sample interval, confidence threshold, or
  camera index — module-level constants, not settings, per YAGNI.
- Multi-camera support — always the default device (index 0).
- Any form of frame display, recording, or snapshot capability.
- Face recognition, presence/attention detection, or anything beyond
  a binary "is a phone visible" signal.
- A first-run model downloader — the model is bundled, not fetched.
- Any git/GitHub action — every command runs manually, at the end.

## File-by-file change list

- New: `lock_in/camera_enforcer.py`, bundled model file(s) under
  `lock_in/assets/`.
- Edit: `lock_in/config.py` (`camera_monitoring_enabled` field),
  `lock_in/enforcer.py` (`Reason.CAMERA`), `lock_in/ui.py` (switch,
  indicator label, `_drain_camera_queue()`, `PhoneWatcher` lifecycle
  wiring), `requirements.txt`.
- New: `tests/test_camera_enforcer.py`.
- Edit: `tests/test_config.py`, `tests/test_enforcer.py`.
- Edit: `README.md`, Help tab in `lock_in/ui.py`.
- Version: v2.3.1.
