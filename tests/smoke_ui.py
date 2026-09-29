"""
This is a "does the real app actually open and work?" test — it's separate
from the normal pytest tests.

It builds the real app window (using a fake, invisible display) and clicks
it through everything that only happens once the app is actually running:
building the window, the main loop, reading from the waiting lines, showing
blocked windows, correcting the model, and shutting down cleanly. This catches
mistakes that the regular tests structurally can't, like a typo in a widget's
setting, things being placed in the wrong order, or a timer trying to update
a window that's already been closed. It also walks the side bar: every
page, every Rider's own page, Revice's Buddy page, Ryuki's mirror (side
bar included), Wizard's page order, Standard Mode, and light/dark mode.

It SAVES settings and teaches the model as it goes, so point the app's
data folder at a throwaway folder first -- otherwise it changes yours.
.smoke-data is already in .gitignore for exactly this.

Run it with:  xvfb-run -a python tests/smoke_ui.py                (Linux)
         or, on Windows, three separate lines:
              set APPDATA=%CD%\\.smoke-data
              set PYTHONPATH=.
              python tests\\smoke_ui.py
"""

import sys
import time

from lock_in.application import WindowSeen
from lock_in.enforcer import WindowInfo
from lock_in.session import Phase
from lock_in.ui import LockInApp

failures = []
DISCORD = WindowInfo(process_name="discord.exe", title="general #chat", handle=0)


def check(label, condition):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")
    if not condition:
        failures.append(label)


print("building window...")
app = LockInApp()
app.config_obj.hard_mode = True  # turn this on so we can test the top two steps too
app.config_obj.lockdown_seconds = 1
app.update()

check("window built", app.winfo_exists())
check("timer shows a duration", ":" in app.time_label.cget("text"))
check("starts idle", app.session.phase is Phase.IDLE)

print("starting a focus block...")
app._on_toggle()
app.update()
check("entered focus", app.session.phase is Phase.FOCUS)
check("monitor resumed", app.monitor.is_active)
check("button flipped to Pause", app.start_button.cget("text") == "Pause")

print("injecting a blocked window...")
# The real window watcher would report whatever window is really in front
# on this computer (an allowed editor resets the warning ladder), so it's
# paused while the test sends its own windows.
app.monitor.pause()
app.controller.events.post(WindowSeen(DISCORD))
app.update()
app._dispatch_events()
app.update()
check("activity logged", len(app.activity) == 1)
check("logged the right app", "discord.exe" in app.activity[0]["key"])

print("driving the escalation ladder...")
seen = set()
for _ in range(6):
    app.enforcer._last_strike_at = None  # skip the "don't escalate too fast" wait
    app.enforcer._blocked_since = time.monotonic() - 60
    app.controller.events.post(WindowSeen(DISCORD))
    app._dispatch_events()
    app.update()
    seen.add(app.enforcer.strikes)
check("strikes accumulated", max(seen) >= 4)
check("lockdown overlay appeared", app._lockdown_window is not None)

app._close_lockdown()
app.update()
check("lockdown closes cleanly", app._lockdown_window is None)

print("de-duplication...")
before = len(app.activity)
for _ in range(5):
    app.controller.events.post(WindowSeen(DISCORD))
    app._dispatch_events()
app.update()
check("repeat hits collapse into one row", len(app.activity) == before)

print("observation recording...")
check("recorded the windows it saw", len(app.observations.all()) >= 1)
check(
    "recording captured the model's opinion", app.observations.all()[0].get("predicted") is not None
)

print("correcting the model...")
vocab_before = len(app.model.vocabulary)
app._correct(app.activity[0], "study")
app.update()
check("model learned", len(app.model.vocabulary) >= vocab_before)
check("process auto-allowlisted", "discord.exe" in app.config_obj.normalised_allowlist())
check("correction mirrored into training data", len(app.observations.labelled()) >= 1)
check(
    "labelled rows leave the pending queue",
    all(r.label is not None for r in app.observations.labelled()),
)

print("phase transitions...")
app._on_skip()
app.update()
check("skip moved to a break", app.session.phase.is_break)
check("monitor paused on break", not app.monitor.is_active)

app._on_skip()
app.update()
check("break -> focus", app.session.phase is Phase.FOCUS)

print("mirror-layout regression (issue #1: resurrecting hidden widgets)...")
# A Tier-1-shape Rider (this is also the app's default Rider) hides the
# plain progress bar in favor of its own custom shape. Before the fix,
# _sync_mirror_layout() ran unconditionally on every phase transition
# for every Rider and replayed the ORIGINAL pack_configure() call on
# every widget it had ever seen -- including this one, resurrecting the
# plain bar right below the buttons even though a different feature had
# deliberately pack_forget()-ten it.
app._on_reset()
app.update()
app._on_rider_theme_change("Kamen Rider (1971)")
app.update()
check("windmill shape shown before any phase transition", app.progress_shape.winfo_manager() != "")
check("plain progress bar hidden before any phase transition", app.progress.winfo_manager() == "")
app._on_skip()  # IDLE -> FOCUS: the exact "first phase transition" the bug hit
app.update()
check(
    "plain progress bar still hidden after a phase transition (issue #1)",
    app.progress.winfo_manager() == "",
)
check(
    "windmill shape still shown after a phase transition", app.progress_shape.winfo_manager() != ""
)

print("mirror-layout regression (Ryuki still flips correctly)...")
# Guarded so it only runs for Ryuki -- confirm it does NOT break the one
# Rider it's supposed to flip. Skip and Reset share a row (Start spans
# both columns above them), and the side bar swaps sides too.
app._on_reset()
app.update()
app._on_rider_theme_change("Kamen Rider Ryuki (2002)")
app.update()
check("skip button unmirrored before any break", int(app.skip_button.grid_info()["column"]) == 0)
check("reset button unmirrored before any break", int(app.reset_button.grid_info()["column"]) == 1)
check("side bar on the left before any break", int(app.sidebar.grid_info()["column"]) == 0)
app._on_skip()  # IDLE -> FOCUS (still unmirrored -- FOCUS isn't a break)
app.update()
check("buttons still unmirrored entering focus", int(app.skip_button.grid_info()["column"]) == 0)
app._on_skip()  # FOCUS -> break (mirrored)
app.update()
check("skip button mirrors to column 1 on break", int(app.skip_button.grid_info()["column"]) == 1)
check("reset button mirrors to column 0 on break", int(app.reset_button.grid_info()["column"]) == 0)
check("side bar moves to the right on break", int(app.sidebar.grid_info()["column"]) == 1)
check("page area moves to the left on break", int(app.content.grid_info()["column"]) == 0)
# Leaving Ryuki in the middle of a break must flip everything back, and
# coming back must flip it again (this used to leave the window half-flipped).
app._on_rider_theme_change("Kamen Rider (1971)")
app.update()
check(
    "switching away from Ryuki mid-break un-flips the side bar",
    int(app.sidebar.grid_info()["column"]) == 0,
)
check(
    "switching away from Ryuki mid-break un-flips the top bar",
    app.brand_label.master.pack_info()["side"] == "left",
)
app._on_rider_theme_change("Kamen Rider Ryuki (2002)")
app.update()
check("switching back to Ryuki mid-break flips again", int(app.sidebar.grid_info()["column"]) == 1)
app._on_skip()  # break -> FOCUS (un-mirrored again)
app.update()
check("skip button un-mirrors back to column 0", int(app.skip_button.grid_info()["column"]) == 0)
check("side bar back on the left", int(app.sidebar.grid_info()["column"]) == 0)

app._on_reset()
app.update()
app._on_rider_theme_change("Kamen Rider (1971)")  # back to the default Rider
app.update()

print("pages...")
for route in ("tasks", "blocking", "activity", "insights", "help", "settings", "focus"):
    check(f"navigate to {route}", app.navigate(route))
    app.update()
check("no bottom tab strip any more", not hasattr(app, "tabs"))
check("default Rider has no Rider page", not app.router.has("rider"))

print("Tier 5 and Tier 6 pages...")
from lock_in.rider_themes import RIDER_THEMES

for name, theme in RIDER_THEMES.items():
    app._on_rider_theme_change(name)
    app.update()
    if theme.tier5_effect != "none":
        check(f"{name}: Rider page listed", app.router.has("rider"))
        check(f"{name}: Rider page opens", app.navigate("rider"))
        app.update()
        check(
            f"{name}: Rider page drew something",
            len(app.pages["rider"].content.winfo_children()) > 0,
        )
    else:
        check(f"{name}: no Rider page", not app.router.has("rider"))
    check(
        f"{name}: Buddy page only for Revice",
        app.router.has("buddy") == (theme.tier6_effect == "buddy_link"),
    )
    app.navigate("focus")
    app.update()
app._on_rider_theme_change("Kamen Rider Revice (2021)")
app.update()
check("Buddy page opens", app.navigate("buddy"))
app._pump()
app.update()
check("Buddy page shows its start screen", app.pages["buddy"].tab._screen == "start")

print("Wizard's gestures move along the side bar...")
app._on_rider_theme_change("Kamen Rider Wizard (2012)")
app.update()
app.navigate("tasks")
from lock_in.ui.gestures import gesture_target

check(
    "line right goes to the next page",
    gesture_target(app.router.ids, app.router.active, "right") == "blocking",
)
check(
    "circle goes to Focus", gesture_target(app.router.ids, app.router.active, "circle") == "focus"
)

print("Standard Mode strips every gimmick...")
app.config_obj.standard_mode = True
app._apply_theme_everywhere()
app.update()
check("standard: plain progress bar", app.progress.winfo_manager() != "")
check("standard: no Rider page", not app.router.has("rider"))
check("standard: no Buddy page", not app.router.has("buddy"))
check(
    "standard: no Tier effects",
    all(getattr(app, f"current_tier{n}_effect") == "none" for n in (1, 2, 3, 4, 5, 6)),
)
app.config_obj.standard_mode = False
app._apply_theme_everywhere()
app._on_rider_theme_change("Kamen Rider (1971)")
app.update()

print("appearance switch...")
app._on_appearance_change("light")
app.update()
app._on_appearance_change("dark")
app.update()
check("appearance switches rebuild cleanly", app.winfo_exists())

print("saving from widgets...")
app._save_lists()
app._save_settings()
app.update()
check("saves without error", True)

print("reset + shutdown...")
app._on_reset()
app.update()
check("reset returns to idle", app.session.phase is Phase.IDLE)

app._on_close()
check("every helper shut down", app.controller.is_shut_down)
check("the mailbox is closed", app.controller.events.closed)
check("the camera is let go", not app.camera_watcher.is_capturing)
app._on_close()  # a second close must be harmless
check("closing twice is safe", True)
print()
if failures:
    print(f"{len(failures)} FAILURES: {failures}")
    sys.exit(1)
print("smoke test passed")
