"""
This is a "does the real app actually open and work?" test — it's separate
from the normal pytest tests.

It builds the real app window (using a fake, invisible display) and clicks
it through everything that only happens once the app is actually running:
building the window, the main loop, reading from the waiting lines, showing
blocked windows, correcting the model, and shutting down cleanly. This catches
mistakes that the regular tests structurally can't, like a typo in a widget's
setting, things being placed in the wrong order, or a timer trying to update
a window that's already been closed.

Run it with:  xvfb-run -a python tests/smoke_ui.py
"""

import sys
import time

from lock_in.enforcer import Action, WindowInfo
from lock_in.session import Phase
from lock_in.ui import LockInApp

failures = []


def check(label, condition):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")
    if not condition:
        failures.append(label)


print("building window...")
app = LockInApp()
app.config_obj.hard_mode = True          # turn this on so we can test the top two steps too
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
app._window_queue.put(WindowInfo(process_name="discord.exe", title="general #chat", handle=0))
app.update()
app._drain_window_queue()
app.update()
check("activity logged", len(app.activity) == 1)
check("logged the right app", "discord.exe" in app.activity[0]["key"])

print("driving the escalation ladder...")
seen = set()
for _ in range(6):
    app.enforcer._last_strike_at = None      # skip the "don't escalate too fast" wait
    app.enforcer._blocked_since = time.monotonic() - 60
    app._window_queue.put(WindowInfo(process_name="discord.exe", title="general #chat", handle=0))
    app._drain_window_queue()
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
    app._window_queue.put(WindowInfo(process_name="discord.exe", title="general #chat", handle=0))
    app._drain_window_queue()
app.update()
check("repeat hits collapse into one row", len(app.activity) == before)

print("observation recording...")
check("recorded the windows it saw", len(app.observations.all()) >= 1)
check("recording captured the model's opinion",
      app.observations.all()[0].get("predicted") is not None)

print("correcting the model...")
vocab_before = len(app.model.vocabulary)
app._correct(app.activity[0], "study")
app.update()
check("model learned", len(app.model.vocabulary) >= vocab_before)
check("process auto-allowlisted", "discord.exe" in app.config_obj.normalised_allowlist())
check("correction mirrored into training data", len(app.observations.labelled()) >= 1)
check("labelled rows leave the pending queue",
      all(r.label is not None for r in app.observations.labelled()))

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
check("windmill shape shown before any phase transition",
      app.progress_shape.winfo_manager() != "")
check("plain progress bar hidden before any phase transition",
      app.progress.winfo_manager() == "")
app._on_skip()   # IDLE -> FOCUS: the exact "first phase transition" the bug hit
app.update()
check("plain progress bar still hidden after a phase transition (issue #1)",
      app.progress.winfo_manager() == "")
check("windmill shape still shown after a phase transition",
      app.progress_shape.winfo_manager() != "")

print("mirror-layout regression (Ryuki still flips correctly)...")
# The fix adds a guard that makes _sync_mirror_layout() a no-op for
# every Rider except Ryuki -- confirm it does NOT also break the one
# Rider it's supposed to keep working.
app._on_reset()
app.update()
app._on_rider_theme_change("Kamen Rider Ryuki (2002)")
app.update()
check("start button unmirrored before any break",
      int(app.start_button.grid_info()["column"]) == 0)
check("reset button unmirrored before any break",
      int(app.reset_button.grid_info()["column"]) == 2)
app._on_skip()   # IDLE -> FOCUS (still unmirrored -- FOCUS isn't a break)
app.update()
check("buttons still unmirrored entering focus",
      int(app.start_button.grid_info()["column"]) == 0)
app._on_skip()   # FOCUS -> break (mirrored)
app.update()
check("start button mirrors to column 2 on break",
      int(app.start_button.grid_info()["column"]) == 2)
check("reset button mirrors to column 0 on break",
      int(app.reset_button.grid_info()["column"]) == 0)
app._on_skip()   # break -> FOCUS (un-mirrored again)
app.update()
check("start button un-mirrors back to column 0",
      int(app.start_button.grid_info()["column"]) == 0)
check("reset button un-mirrors back to column 2",
      int(app.reset_button.grid_info()["column"]) == 2)

app._on_reset()
app.update()
app._on_rider_theme_change("Kamen Rider (1971)")   # back to the default Rider
app.update()

print("tabs...")
for tab in ("Blocking", "Activity", "Settings"):
    app.tabs.set(tab)
    app.update()
check("all tabs render", True)

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
print()
if failures:
    print(f"{len(failures)} FAILURES: {failures}")
    sys.exit(1)
print("smoke test passed")