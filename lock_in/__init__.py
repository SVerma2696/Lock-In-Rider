"""
Lock In — a Pomodoro timer that actually keeps you off the fun apps.

Package layout
--------------
    application/     everything that isn't drawing: AppController,
                     the event mailbox, focus/task/blocking/buddy
                     controllers, clean shutdown, update checks   (no screen code)
    storage/         crash-safe saving (whole files and JSON lines) (no deps)
    config.py        settings + JSON persistence            (no deps)
    config_validation.py  one rule per setting in config.json  (no deps)
    rider_effects.py the typed names of every Rider power   (no deps, pure data)
    diagnostics.py   the small private log file             (no deps)
    update_verify.py SHA-256 fingerprint check for updates  (no deps)
    task_picker.py   the Focus page's task menu words        (no deps, pure logic)
    session.py       the Pomodoro state machine             (no deps, pure logic)
    classifier.py    Naive Bayes study/distraction model     (no deps, pure logic)
    enforcer.py      judgement + escalation ladder           (no deps, pure logic)
    rider_themes.py  Kamen Rider color palettes              (no deps, pure data)
    wizard_gestures.py  mouse-gesture recognizer for Wizard  (no deps, pure logic)
    revice_sync.py   Revice's buddy-link rules and merge     (no deps, pure logic)
    revice_link.py   Revice's local-network connection       (stdlib sockets)
    revice_tab.py    Revice's Buddy screens                  (customtkinter)
    presets.py       saved timer-length preset bundles       (no deps, pure data)
    visuals.py       fonts and generated glow/background art (Pillow)
    monitor.py       foreground-window polling               (pywin32/psutil, osascript, xdotool)
    notifier.py      toasts and sounds                       (winotify/winsound, osascript/afplay, notify-send/paplay)
    ui/              the window: side bar, pages, cards      (customtkinter)
        app.py         the main window and its heartbeat
        effects.py     the Rider pictures (glow, era strip, shapes)
        host.py        what the window's add-on parts may use (types only)
        theme.py       every color, size, and space           (no deps)
        router.py      the side bar's list of pages           (no deps)
        mirror.py      Ryuki's left-right flip helpers        (no deps)
        icons.py       small line pictures, drawn with Pillow (Pillow)
        components/    cards, buttons, badges, the timer
        pages/         Focus, Tasks, Blocking, Activity, Insights,
                       Help, Settings, the Rider page, Buddy

The modules marked (no deps) import nothing outside the standard library, which
is why the whole behavioural core is unit-tested without a display server.
"""

__version__ = "3.0.4"
__all__ = ["__version__"]
