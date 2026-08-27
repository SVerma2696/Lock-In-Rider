"""
ambient.py
==========
Hibiki's one gimmick: a soft ambient sound loop that plays for as long
as a focus block runs, and stops the instant it doesn't. Same OS-glue-
only shape as notifier.py and monitor.py -- this file makes no
decisions about WHETHER to play beyond "is Hibiki selected, is
Standard Mode off, is sound turned on" -- everything else about WHEN
lives in ui.py, calling start_if_applicable()/stop() at the same
phase-transition points the camera-monitoring feature's
resume()/pause() already use.

No new dependency. Windows uses winsound (already in the standard
library) with its own loop flag. macOS/Linux keep re-invoking whatever
sound-playing program notifier.py already detected on this machine --
not a perfectly seamless loop, but close enough for ambient background
texture, and consistent with this app's existing "Windows first-class,
Mac/Linux best-effort" treatment of sound.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

from .rider_themes import DEFAULT_RIDER_THEME, RIDER_THEMES

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

_winsound = None
if IS_WINDOWS:
    try:
        import winsound as _winsound  # type: ignore
    except ImportError:  # pragma: no cover - depends on install
        _winsound = None

_AMBIENT_PATH = Path(__file__).parent / "assets" / "hibiki_ambient.wav"


class AmbientPlayer:
    """Plays Hibiki's ambient loop, and only Hibiki's."""

    def __init__(self, config) -> None:
        self.config = config
        self._loop_thread: "threading.Thread | None" = None
        self._stop_event = threading.Event()

    def start_if_applicable(self) -> None:
        """Call this whenever a focus block begins. Does nothing unless
        Hibiki is selected, Standard Mode is off, and sound is on."""
        theme = RIDER_THEMES.get(self.config.rider_theme, RIDER_THEMES[DEFAULT_RIDER_THEME])
        if theme.tier4_effect != "ambient_loop":
            return
        if self.config.standard_mode:
            return
        if not self.config.effective_sound_enabled():
            return
        self._play_loop()

    def stop(self) -> None:
        """Call this whenever a focus block ends -- always safe to call,
        even if nothing is currently playing."""
        self._stop_loop()

    # ------------------------------------------------------------------ #
    def _play_loop(self) -> None:
        try:
            if IS_WINDOWS and _winsound is not None:
                _winsound.PlaySound(
                    str(_AMBIENT_PATH),
                    _winsound.SND_FILENAME | _winsound.SND_LOOP | _winsound.SND_ASYNC,
                )
                return
            player = "afplay" if IS_MACOS else "paplay"
            self._stop_event.clear()
            self._loop_thread = threading.Thread(
                target=self._repeat_subprocess, args=(player,), daemon=True,
            )
            self._loop_thread.start()
        except Exception:
            pass

    def _repeat_subprocess(self, player: str) -> None:
        while not self._stop_event.is_set():
            try:
                subprocess.run([player, str(_AMBIENT_PATH)], timeout=25)
            except Exception:
                return

    def _stop_loop(self) -> None:
        try:
            if IS_WINDOWS and _winsound is not None:
                _winsound.PlaySound(None, _winsound.SND_PURGE)
            self._stop_event.set()
        except Exception:
            pass
