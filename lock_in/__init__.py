"""
Lock In — a Pomodoro timer that actually keeps you off the fun apps.

Package layout
--------------
    config.py        settings + JSON persistence            (no deps)
    session.py       the Pomodoro state machine             (no deps, pure logic)
    classifier.py    Naive Bayes study/distraction model     (no deps, pure logic)
    enforcer.py      judgement + escalation ladder           (no deps, pure logic)
    rider_themes.py  Kamen Rider color palettes              (no deps, pure data)
    wizard_gestures.py  mouse-gesture recognizer for Wizard  (no deps, pure logic)
    revice_sync.py   Revice's buddy-link rules and merge     (no deps, pure logic)
    revice_link.py   Revice's local-network connection       (stdlib sockets)
    revice_tab.py    Revice's Buddy tab                      (customtkinter)
    presets.py       saved timer-length preset bundles       (no deps, pure data)
    visuals.py       fonts and generated glow/background art (Pillow)
    monitor.py       foreground-window polling               (pywin32/psutil, osascript, xdotool)
    notifier.py      toasts and sounds                       (winotify/winsound, osascript/afplay, notify-send/paplay)
    ui.py            CustomTkinter front end                 (customtkinter)

The modules marked (no deps) import nothing outside the standard library, which
is why the whole behavioural core is unit-tested without a display server.
"""

__version__ = "2.6.1"
__all__ = ["__version__"]
