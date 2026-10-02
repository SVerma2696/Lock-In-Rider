"""Tests for the window watcher's pause. On a Mac, asking "which window
is in front?" can take up to 2 seconds. If the watcher is paused while
it's asking, the answer must be thrown away, not sent."""

import threading
import time

from lock_in import monitor
from lock_in.enforcer import WindowInfo
from lock_in.monitor import ActiveWindowMonitor

DISCORD = WindowInfo(process_name="discord.exe", title="general #chat")


def wait_until(condition, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_sends_windows_while_watching(monkeypatch):
    monkeypatch.setattr(monitor, "get_active_window", lambda: DISCORD)
    seen = []
    watcher = ActiveWindowMonitor(seen.append, interval=0.01)
    watcher.start()
    try:
        watcher.resume()
        assert wait_until(lambda: len(seen) > 0)
        assert seen[0] == DISCORD
    finally:
        watcher.stop()


def test_slow_answer_after_pause_is_thrown_away(monkeypatch):
    asking = threading.Event()
    answer_now = threading.Event()

    def slow_lookup():
        # Like a slow Mac: start asking, then wait before answering.
        asking.set()
        answer_now.wait(5)
        return DISCORD

    monkeypatch.setattr(monitor, "get_active_window", slow_lookup)
    seen = []
    watcher = ActiveWindowMonitor(seen.append, interval=0.01)
    watcher.start()
    try:
        watcher.resume()
        assert asking.wait(5)  # the watcher is in the middle of asking...
        watcher.pause()  # ...when the focus block ends
        answer_now.set()  # now the slow answer arrives
        time.sleep(0.2)
        assert seen == []  # and it was thrown away
    finally:
        answer_now.set()
        watcher.stop()


def test_nothing_is_sent_while_paused(monkeypatch):
    monkeypatch.setattr(monitor, "get_active_window", lambda: DISCORD)
    seen = []
    watcher = ActiveWindowMonitor(seen.append, interval=0.01)
    watcher.start()
    try:
        time.sleep(0.1)  # starts paused
        assert seen == []
    finally:
        watcher.stop()
