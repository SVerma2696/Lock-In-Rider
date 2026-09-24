# Lock In: Tier 6 Rider #1 — Wizard, mouse gestures

Date: 2026-09-23
Status: Draft, awaiting review

## Goal

The first of Tier 6's two Riders, and the first Rider whose gimmick is
neither a color, a setting, an enforcement tweak, nor a read-only tab:
it listens to the mouse. When Kamen Rider Wizard (2012) is the picked
Rider, you can hold the **right mouse button** and draw a shape on the
Lock In window to move between tabs, the way a wizard draws a
magic circle.

It is deliberately small and safe:

- **Only inside the Lock In window.** Nothing watches the mouse anywhere
  else on your computer. No system-wide hook, no new Windows permission,
  no new library.
- **Only tab navigation.** A gesture can never start, pause, skip, or end
  a focus session. A misread gesture costs one second of looking at the
  wrong tab, never a lost focus block.
- **No learning, no downloads.** The shapes are recognized with
  plain geometry from Python's built-in `math` module. It gives the same
  answer for the same stroke every time.

## The gestures

Decided during brainstorming. Hold the right button, drag, let go.

| You draw | What happens |
|---|---|
| A line to the **left** | Go to the previous tab |
| A line to the **right** | Go to the next tab |
| A **circle** | Go to the first tab (Tasks) |

- The timer is not a tab (it sits above the tabs), so "circle" goes to
  **Tasks**, the first tab.
- Swiping left on the first tab, or right on the last tab, does nothing.
  Tabs do not wrap around.
- "Next" and "previous" follow the tab order on screen, including a
  Rider's extra tab if one exists.
- A right-click with almost no movement does nothing, so it never
  interferes with normal clicking. Any stroke that is too short, too
  wobbly, too diagonal, or otherwise unclear also does nothing, silently.
  There is no error message and no sound for a gesture the app didn't
  understand.

## The rule for turning points into a gesture

All in one pure function that never touches the window. It receives the
list of `(x, y)` points collected while the right button was down and
returns `"left"`, `"right"`, `"circle"`, or `None`.

Steps, in order:

1. **Too few points or too small?** Fewer than a small minimum number of
   points, or the whole stroke fits inside a tiny box (under
   `MIN_STROKE_PIXELS`): return `None`.
2. **Circle check.** The stroke counts as a circle when all of these hold:
   - its end comes back close to its start (within a fraction of the
     stroke's overall size),
   - its bounding box is roughly square (neither side more than about
     twice the other), and
   - it is long enough overall compared with its size, meaning it really
     went around instead of out and back.
3. **Swipe check.** Otherwise, take the straight line from the first point
   to the last. The stroke counts as a swipe when it is:
   - mostly horizontal (the sideways part is clearly larger than the
     up-and-down part, so a diagonal is ignored),
   - long enough (at least `MIN_SWIPE_PIXELS` sideways), and
   - mostly straight (the path length is not much longer than the straight
     distance, so a squiggle is ignored).
   Left or right is then just the sign of the sideways movement.
4. Anything else: `None`.

The exact numbers (`MIN_STROKE_PIXELS`, `MIN_SWIPE_PIXELS`, the closing
distance, the squareness limit, the straightness limit) are plain named
constants at the top of the file so they can be tuned in one place, and
each one has a comment saying what it means in plain words. They are
picked in the implementation plan and checked against the tests below.

The classic "$1 Unistroke Recognizer" was considered and not used: it
rotates every stroke to a standard angle first, so it cannot tell a left
swipe from an up swipe, and left versus right is the whole point here.

## The Settings switch

- New setting **`mouse_gestures_enabled: bool = True`** in `config.py`,
  next to `camera_monitoring_enabled`.
- A **"Mouse gestures"** switch in the Settings tab, under "Behavior &
  notifications", **shown only while Wizard is the picked Rider**. Other
  Riders' Settings tabs look exactly as they do today.
- Off means the app does not react to right-button drags at all.
- The switch only matters for Wizard. No other Rider ever gets gestures,
  whatever the setting says, the same "the effect string decides" gating
  every other Rider effect uses. Picking another Rider leaves the saved
  value alone, so coming back to Wizard remembers your choice.
- Standard Mode (the neutral, no-Rider mode) turns Wizard's gestures off
  along with every other Rider effect, through the existing mechanism.
- The setting is read fresh on each gesture, so flipping the switch takes
  effect immediately, with no restart.

## The fading trail

While you drag, a thin line follows the mouse and fades away shortly after
you let go, in Wizard's `primary` color, so you can see that the app is
"listening."

**This is a best-effort visual.** Tkinter has no window-wide transparent
drawing layer that safely sits above every button, frame, and tab, and a
line drawn across nested frames can be clipped, hidden behind a widget, or
render differently on other operating systems. So:

- Recognition and tab switching never depend on the trail. They work from
  the collected points alone.
- If drawing the trail raises any error, it is swallowed and the gesture
  still works.
- If the trail proves too glitchy when checked by eye in the running app
  (clipped at frame edges, flicker, wrong z-order), it is **dropped from
  this release** rather than patched with hacks, and the feature ships
  without it. The spec's core is the recognition and the tab switching.

## New code

### `lock_in/wizard_gestures.py` (new)

Only `math`. No Tk, no `customtkinter`, no config, so it is fully testable
without a display.

- **`recognize(points: list[tuple[float, float]]) -> str | None`**
  The rule above.
- Named constants for every threshold.
- **`next_tab_name(tab_names: list[str], current: str, gesture: str) -> str | None`**
  Given the tab names in on-screen order, the current tab, and a gesture,
  returns the tab to switch to, or `None` if nothing should happen (first
  tab + left, last tab + right, an unknown current tab, an unknown
  gesture). `"circle"` returns the first name in the list.
  Pulled out so the edge rules are unit-tested the same way every other
  small piece of logic in the project is.

### `lock_in/ui.py` (small)

- `<ButtonPress-3>`, `<B3-Motion>`, and `<ButtonRelease-3>` bound on the
  main window (only points inside the Lock In window are ever seen; that
  is the entire scope of this feature). On press, start a fresh point
  list; on motion, append the point; on release, call `recognize()`, then
  `next_tab_name()`, then switch the tab.
- All three handlers return immediately when the picked Rider's
  `tier6_effect` is not `"mouse_gestures"` or when
  `config.mouse_gestures_enabled` is off. The handlers are always bound
  once at startup, so picking Wizard mid-session needs no rebind.
- The whole release handler sits inside a `try/except` that does nothing
  on error, the app's usual fail-silent posture for extras.
- The Settings switch, added and removed as the Rider changes (the
  Settings tab already rebuilds when the Rider changes).
- Help tab: one Wizard bullet.

### `lock_in/rider_themes.py`

- New field **`tier6_effect: str = "none"`**, with a comment in the same
  style as `tier1_effect` through `tier5_effect`.
- `Kamen Rider Wizard (2012)` gets `tier6_effect="mouse_gestures"`.

### `lock_in/config.py`

- `mouse_gestures_enabled: bool = True`, with a plain-words comment. Loading
  an old settings file that lacks it uses the default, as every other
  setting already does.

## Error handling

- Any exception while recognizing, choosing the tab, switching the tab, or
  drawing the trail is swallowed. Worst case: nothing happens.
- A stroke with zero or one point, or points that are all identical:
  `recognize()` returns `None`, no division by zero.
- Releasing the right button outside the window, or the window losing
  focus mid-drag: the stroke is discarded, nothing happens.
- A right-click on something that has its own right-click behavior is not
  interfered with; Wizard only reads the points and never swallows or
  cancels the event.
- Gestures during Hard-mode lockdown: the lockdown screen is a separate
  window and receives no gesture. Gestures only ever apply to the main
  window.

## Testing

- `tests/test_wizard_gestures.py` (new), no Tk and no display:
  - `recognize()` on hand-built point lists: a clean left line, a clean
    right line, a clean circle (both directions of drawing), each return
    the right answer.
  - Ignored: an empty list, one point, all-identical points, a tiny
    stroke, a diagonal stroke, a vertical stroke, a wobbly zig-zag, an
    out-and-back line, a half-circle that doesn't close.
  - A slightly tilted left/right swipe still counts (real hands are not
    ruler-straight).
  - `next_tab_name()`: left/right move one step; left on the first and
    right on the last return `None`; circle returns the first tab; an
    unknown gesture or unknown current tab returns `None`; a list with a
    Rider's extra tab on the end includes it in the order.
- `tests/test_rider_themes.py` *(grows)*: a check that exactly one Rider
  (Wizard) has `tier6_effect="mouse_gestures"` and every other Rider has
  `"none"`.
- `tests/test_config.py` *(grows)*: `mouse_gestures_enabled` defaults to
  `True`; it round-trips through save/load; a settings file without it
  loads with `True`.
- **Manual, in the running app** (same as every other UI piece, no
  automated GUI test): pick Wizard, and the Mouse gestures switch appears
  in Settings; swipe left/right moves one tab; a circle goes to Tasks; a
  plain right-click does nothing; switching the switch off stops
  gestures instantly; picking another Rider hides the switch and stops
  gestures; the trail follows the mouse and fades (or, if it glitches, is
  removed as described above); light and dark mode both read clearly.

## Docs, version, and repo hygiene

- `README.md`: a **Wizard** bullet in plain words, a short "Tier 6"
  heading noting this is the first of two, and the Settings switch
  mentioned. It says clearly that gestures only work inside the Lock In
  window and never watch the rest of your computer.
- `lock_in/ui.py`, Help tab: as above.
- `__version__`: **2.6.0**.
- `.gitignore`: Wizard creates no new file on disk, so no change is
  expected. It is re-checked when this ships.
- Project files describe the software only: nothing about who or what
  wrote them, and commit messages carry no trailer or credit line.
- Committing, pushing, and tagging are done by the project owner. The
  exact commands are handed over at the end, with a plain commit message.

## Out of scope for this pass

- Any gesture that starts, pauses, skips, or ends a session, or touches
  tasks, blocking, or settings.
- Watching the mouse outside the Lock In window.
- More shapes (up, down, diagonal, letters), custom gestures, or
  remapping which shape does what.
- A left-handed or middle-button option.
- The second Tier 6 Rider, Revice (local-network sync), which gets its own
  design conversation.

## File-by-file change list

**New**
- `lock_in/wizard_gestures.py`: `recognize()`, `next_tab_name()`, constants.
- `tests/test_wizard_gestures.py`.
- `docs/superpowers/plans/2026-09-23-tier6-wizard-mouse-gestures.md`: the
  implementation plan (written after this spec is approved).

**Edit**
- `lock_in/rider_themes.py`: `tier6_effect` field; Wizard's value.
- `lock_in/config.py`: `mouse_gestures_enabled`.
- `lock_in/ui.py`: mouse bindings and handlers, Settings switch, Help
  bullet, optional trail.
- `lock_in/__init__.py`: version 2.6.0.
- `tests/test_rider_themes.py`, `tests/test_config.py`: as above.
- `README.md`: Wizard bullet and Tier 6 note.
