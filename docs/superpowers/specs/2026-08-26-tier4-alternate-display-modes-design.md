# Lock In: Tier 4 — Alternate display modes

Date: 2026-08-26
Status: Approved, ready for implementation plan

## Goal

Tier 4 of the larger 38-Rider project (Tiers 0-3 shipped in v2.2.0-v2.3.1).
Nine Riders, each getting a distinct "alternate display mode" — a bigger,
more varied grab-bag than any prior tier, spanning window layout, audio,
input handling, and reskins, rather than one shared pattern.

**Black RX** (manual-break toggle), **Ryuki** (full window mirror on
break), **Kabuto** (hidden timer, hover to reveal), **Ex-Aid** (pixel
font + an 8-bit-style alert sound), **Hibiki** (looping ambient sound
during focus), **Zero-One** (dashboard-card reskin), **Ghost** (a
floating always-on-top mini widget), and **Zeztz** (in-window keyboard
shortcuts) all get a new `tier4_effect` field on `RiderTheme`. **Saber**
turns out not to belong here at all — see below — and ships as a Tier 1
progress-bar shape instead.

## Why this isn't one pattern

Tier 1's nine Riders were all the same shape: a different progress-bar
renderer, one architecture, one file (`visuals.py`) doing all the work.
Tier 4 was pitched the same way ("bounded rendering modes") but turned
out not to be — the nine items span at least four genuinely different
kinds of change: window geometry (Ryuki), a brand new looping-audio
subsystem (Hibiki), a second floating window (Ghost), and keyboard
input handling (Zeztz), alongside smaller reactive UI swaps (Black RX,
Kabuto, Ex-Aid, Zero-One). Two scope decisions came out of that:

- **Saber was reclassified into Tier 1.** "E-reader bookmark mode" is,
  on inspection, just a new progress-bar shape — a ribbon that fills
  top-to-bottom — which is exactly what Tier 1's `SHAPE_EFFECTS`/
  `render_progress()` architecture already exists to hold. Building it
  as a `tier4_effect` would have meant inventing a second way to draw
  a custom progress shape next to the one that already works. It ships
  with `tier1_effect="bookmark"`, not `tier4_effect`.
- **Zeztz's scope was narrowed.** "Hotkey-driven terminal UI" could
  have meant a real second interface reachable via global,
  window-independent hotkeys (a genuine new input subsystem, roughly
  Tier 6-scale: an OS-permission-hungry global-hotkey library, conflict
  risk with other apps' shortcuts). Scoped down to in-window keyboard
  shortcuts instead — Tkinter's own `bind_all()`, active only while the
  Lock In window has focus. No new dependency, no OS permission
  prompts, genuinely bounded.

Everything else here (Black RX, Ryuki, Kabuto, Ex-Aid, Hibiki, Zero-One,
Ghost, Zeztz) shares one dispatch mechanism — a new `tier4_effect: str
= "none"` field on `RiderTheme`, set on exactly these eight already-
existing Riders (none of the eight currently has a Tier 1 or Tier 3
gimmick, so this is purely additive — no overlapping-state risk). `ui.py`
gets a `self.current_tier4_effect` attribute, read the same way
`current_tier1_effect`/`current_tier3_effect` already are.

## Black RX — manual-break toggle

Originally pitched as "Robo/Bio" modes (an unpausable, maximum-lockdown
mode vs. a fluid/adaptive one). Rejected: an unpausable timer directly
violates the "friction, not force" ethos this app already committed to
in Tier 3 (Gaim, X) — every enforcement step, even the full-screen
lockdown, always has a visible way out. Replaced with something that
keeps the spirit (two switchable interaction modes) without the
hostility: a **manual-break toggle**.

A new `Config.blackrx_manual_breaks: bool = False` field — same shape
as Gavv's `micro_sprint_mode`. A switch appears in the Settings tab,
shown only when Black RX is the selected Rider (the same pattern
Kuuga/Super-1/Gavv's Tier 2 preset buttons already use). When it's on,
breaks never auto-start, regardless of the global "Auto-start breaks"
setting — you always press Start yourself.

Mechanically, this is the same non-destructive read-side-override
pattern `effective_grace_seconds()` already established: `Config`
gains `effective_auto_start_breaks() -> bool`, and `session.py`'s
`_advance()` (currently `auto = self.config.auto_start_breaks` at the
line that decides whether a break starts on its own) calls
`self.config.effective_auto_start_breaks()` instead — a one-line
change to the pure-logic session module, which stays completely
unaware that a UI-level override exists. The real `auto_start_breaks`
setting is never touched, so switching Riders away restores it
instantly.

## Ryuki — full window mirror on break

The whole window's layout mirrors left-to-right during a break —
every tab, not just the header — and reverts the instant focus starts
again.

A literal per-widget mirror was chosen deliberately over the cheaper
alternative (mirroring only the rendered background art). It's a much
larger change — roughly 107 `.pack()`/`.place()`/`.grid()` call sites
across `ui.py` are candidates — so the mechanism is built once and
reused everywhere, rather than duplicating flip logic per call site:

- Three wrapper methods on `LockInApp` — `_mpack(widget, side=None,
  anchor=None, **kwargs)`, `_mplace(widget, relx=None, anchor=None,
  **kwargs)`, `_mgrid(widget, column=None, columnspan=None,
  total_columns=None, sticky=None, **kwargs)` — replace every direct
  `.pack()`/`.place()`/`.grid()` call in the file. Each flips its
  relevant argument when mirroring is active (`side` left↔right,
  `relx` to `1 - relx`, `column` to `total_columns - 1 - column -
  (columnspan - 1)`, and the w/e parts of `anchor`/`sticky`) and calls
  the real geometry method with the (possibly flipped) arguments.
  `_mgrid` takes `total_columns` as an explicit argument — Tkinter
  doesn't expose a grid's column count cleanly, so it isn't inferred.
- Each wrapper also records `(widget, manager, original kwargs)` in
  `self._mirror_managed_widgets`. A new `_sync_mirror_layout()` walks
  that list and re-applies every widget's geometry (via
  `pack_configure`/`place_configure`/`grid_configure`) against the
  *current* mirror state. This is the only place a flip actually
  happens — called once from `_on_phase_started`/`_on_phase_ended`
  whenever the phase crosses into or out of a break, not on every tick.
- `self._is_mirrored` is computed fresh each time (`current_tier4_effect
  == "mirror_flip" and self.session.phase.is_break`), never stored —
  so there's no separate state to keep in sync with reality.
- The Pillow-rendered images (background wallpaper, divider strip,
  glows) get `ImageOps.mirror()`'d through the same swap
  `_apply_rider_theme()` already does for other Tier 1 gimmicks.

Two accepted limitations, both deliberate scope boundaries rather than
oversights: **text content itself never mirrors** — labels, button
text, and paragraphs keep reading left-to-right, since mirroring
English text into unreadable glyphs would be a genuine UX failure, not
a fun gimmick, for a productivity tool. And **the native
`ctk.CTkProgressBar`'s fill direction stays left-to-right** even while
everything around it flips — this toolkit doesn't expose a reverse-fill
option, and building a custom canvas renderer just to flip one bar's
fill direction for a break-only cosmetic gimmick would be real
over-engineering.

## Kabuto — hidden timer, hover to reveal

Text-swap only — the underlying countdown in `session.py` is never
touched, so there's no risk of desyncing block durations or
accidentally pausing anything. `_refresh_timer_widgets()` (already
called every `_pump()` tick) decides what string goes in
`self.time_label`:

```python
if self.current_tier4_effect == "hidden_timer" and phase is Phase.FOCUS and not self._kabuto_revealed:
    self.time_label.configure(text="--:--")
else:
    self.time_label.configure(text=self.session.format_remaining())
```

`self._kabuto_revealed` is a plain instance flag, flipped by two event
bindings added once in `_build_header()` (`<Enter>`/`<Leave>` on
`self.time_label`) — harmless no-ops for every other Rider, since
they're only consulted when `current_tier4_effect == "hidden_timer"`.
The handler calls `_refresh_timer_widgets()` immediately on both
events, so the peek feels instant rather than waiting for the next
200ms tick.

Masking only applies during an actual focus block — idle and break
screens always show the real countdown. The progress bar is never
masked either way, so there's always an ambient sense of how far along
the block is, even with the digits hidden.

## Ex-Aid — pixel font + 8-bit alert

**Sound** needs no new audio infrastructure at all. `notifier.py`
already synthesizes its chimes as pure Beep-tone sequences per era
(`_WINDOWS_CHIME_TONES`/`_WINDOWS_ALERT_TONES`, keyed `"Showa"` /
`"Heisei"` / `"Reiwa"`) — no sound files involved on Windows at all,
and a Beep-tone sequence already sounds distinctly "8-bit" by nature
(it's a square wave). Ex-Aid adds one more tone sequence, checked
first when the current Rider's `tier4_effect` is `"chiptune_alert"`,
falling back to the era table otherwise. Same shape on Mac/Linux — one
more entry in the existing `_MAC_CHIME_SOUND`/`_LINUX_CHIME_CANDIDATES`
tables, still all built-in OS sounds, no bundled audio file.

**Font**: one small (~17KB), freely-licensed pixel font ("Press Start
2P" or equivalent, SIL Open Font License) bundled into `lock_in/assets/`.
On Windows, loaded in-process via `ctypes`' `AddFontResourceExW` with
the `FR_PRIVATE` flag — registers the font for this process only, no
system install, no admin rights, and Windows cleans it up automatically
when the process exits. On macOS/Linux, falls back to a plain
monospace system font instead of the real pixel font (e.g. `"Menlo"` /
`"Noto Sans Mono"`) — the same "reduced feature set on non-Windows"
shape `monitor.py`'s own docs already describe for window detection.
Applied only to the timer digits and phase label while Ex-Aid is
selected; every other label keeps the normal `DISPLAY_FONT`.

## Hibiki — ambient sound loop

The one genuinely new subsystem in this tier. Rather than adding a
real audio library (e.g. pygame, tens of MB) for one Rider's gimmick,
this reuses what each OS already provides, matching the app's existing
"Windows first-class, Mac/Linux best-effort via already-installed
tools" shape:

- **Windows**: `winsound.PlaySound(path, winsound.SND_LOOP |
  winsound.SND_ASYNC)` — stdlib, zero new dependency, genuinely loops
  a small bundled ambient `.wav` for as long as it's playing.
- **macOS/Linux**: a small background thread repeatedly re-invokes
  `afplay` / `paplay` (already detected via `shutil.which` in
  `notifier.py` today) back-to-back for the duration of the block —
  not a true seamless loop, but close enough for ambient background
  texture, and consistent with the existing best-effort treatment of
  these platforms elsewhere in the app.

One small new `ambient.py` module — same OS-glue-only shape as
`notifier.py`/`monitor.py`, no decisions made there, just playback.
Starts the instant a Hibiki focus block begins, stops the instant it
ends (mirrors `PhoneWatcher`'s resume/pause lifecycle from the camera
feature: paired start/stop calls at the exact same phase-transition
call sites `monitor.resume()`/`.pause()` already use). Respects
`effective_sound_enabled()` — muting sound globally mutes this too, no
separate on/off switch needed.

## Zero-One — dashboard cards

No new data and no new `Config` field — purely a different arrangement
of numbers the app already shows today (time remaining, sessions
complete, streak, the active Rider name). When
`current_tier4_effect == "dashboard_cards"`, `_build_header()` lays
those same values out as bordered, boxy "cards" with small caption
labels above each value ("Status" / "Time Remaining" / "Sessions
Complete" / "Active Profile") instead of the centered timer stack —
the same kind of whole-header visual swap Amazon's zero-UI reskin
(Tier 3) already does based on `tier3_effect`. Real history/task data
doesn't exist yet (that's Tier 5) — this dashboard only ever shows
numbers the app already tracks, restyled, not new metrics.

## Saber — reclassified into Tier 1 (not a `tier4_effect`)

Built exactly like Fourze/Build/every other Tier 1 custom shape: a new
`"bookmark"` entry in `visuals.py`'s `SHAPE_EFFECTS`, and a
`render_progress()` branch that draws a vertical ribbon (like a
bookmark hanging from the top edge) filling top-to-bottom as progress
increases, using the same primary/secondary Rider colors and
light/dark variants every other shape already handles. Saber's
`RiderTheme` entry gets `tier1_effect="bookmark"`. Documented
explicitly in the Help tab and README as living in the Tier 1 list,
so it isn't confusing later that a "Tier 4" Rider shows up there
instead.

## Ghost — floating always-on-top mini widget

A small borderless (`overrideredirect(True)`), always-on-top
(`attributes("-topmost", True)`) `Toplevel` window — just the
countdown digits and a thin 4px progress strip, no title bar, no
buttons. Draggable by click-and-drag (`<B1-Motion>` repositions it); a
single click anywhere on it restores the main window.

When `current_tier4_effect == "ghost_widget"` and a focus block starts
running, `_on_phase_started` calls `self.iconify()` on the main window
and creates/shows the mini widget; the block ending (or switching
Riders away from Ghost) reverses both. Self-contained in its own small
group of methods — doesn't touch Ryuki's geometry-wrapper mechanism or
Hibiki's audio, and doesn't persist any new `Config` state (purely
phase-driven, like Amazon's zero-UI visibility sync already is).

## Zeztz — in-window keyboard shortcuts

Plain `self.bind_all(...)` calls added once, in `_build_header()` or
`__init__`: Space starts/pauses, `S` skips, `R` resets — each handler
checks `self.current_tier4_effect == "hotkeys"` before doing anything,
so switching Riders away just makes the handler a no-op rather than
needing to bind/unbind anything dynamically. Reset fires immediately
on keypress, same immediacy as the existing Reset button (no separate
confirmation step invented just for the hotkey). No new dependency, no
OS permission prompts, and — deliberately, per the scope decision
above — never a global hotkey; these only fire while the Lock In
window itself has focus.

## Standard Mode stays free

Every one of the eight `tier4_effect` Riders (all but Saber, which is
Tier 1) is silenced by Standard Mode's existing `current_tier4_effect =
"none"` force in `_apply_rider_theme()` — the same intercept that
already zeroes out `current_tier1_effect`/`current_tier3_effect`. No
new teardown code needed per gimmick, matching the zero-cost property
established since Tier 0.

## Docs

- Help tab: one more numbered section (`"5. Nine more heroes have
  their own display trick"` or similar), same `heading()`/`body()`/
  `bullet()` pattern already used for Tier 1/3, listing all nine —
  including a note that Saber's bookmark shape actually lives under
  the Tier 1 heading above it.
- `README.md`: one-line feature mention for Tier 4 matching how Tiers
  1-3 were each documented, plus Saber's cross-reference note.

## Testing

- `Config`: `blackrx_manual_breaks` defaults to `False`, round-trips
  through `load`/`save`, same shape as `micro_sprint_mode`'s existing
  tests. `effective_auto_start_breaks()` tested the same way
  `effective_grace_seconds()` already is.
- `visuals.py`: the new `"bookmark"` shape tested the same way every
  other `render_progress()` branch already is (returns an image of
  the requested size, fill grows with progress).
- `rider_themes.py`: the eight new `tier4_effect` values and Saber's
  `tier1_effect="bookmark"` pass the same completeness/contrast checks
  `tests/test_rider_themes.py` already runs across every Rider.
- `session.py`: `_advance()` picking up `effective_auto_start_breaks()`
  tested with a fake config, same style as existing session tests.
- `notifier.py`: Ex-Aid's tone-sequence lookup and Hibiki's
  start/stop calls tested with the sound backend faked out, matching
  how the existing era-based chime tests already avoid touching a
  real speaker.
- `ambient.py`: pure logic (which backend to call, start/stop
  lifecycle) tested with the actual `winsound`/`subprocess` calls
  faked out — no real audio playback in the test suite, same
  philosophy as `monitor.py`'s OS calls not being unit-tested today.
- `ui.py` wiring (Ryuki's mirror mechanism, Kabuto's hover reveal,
  Zero-One's card layout, Ghost's floating widget, Zeztz's hotkeys):
  screenshot-driven manual verification of the real running app, same
  approach every prior tier used — no automated GUI test.

## Out of scope for this pass

- Any change to Tiers 0-3's own behavior.
- A true global (window-independent) hotkey system for Zeztz —
  explicitly scoped down to in-window shortcuts.
- A real analytics dashboard with actual task/history data for
  Zero-One — that needs Tier 5's data model, which doesn't exist yet.
- Bundling a real pixel font or ambient-loop audio for anything beyond
  Ex-Aid/Hibiki specifically.
- Reverse-fill support for the native progress bar under Ryuki's
  mirror.
- Any git/GitHub action — every command runs manually, at the end.

## File-by-file change list

- Edit: `lock_in/rider_themes.py` (`tier4_effect` field, eight Rider
  entries, Saber's `tier1_effect="bookmark"`), `lock_in/config.py`
  (`blackrx_manual_breaks` field, `effective_auto_start_breaks()`),
  `lock_in/session.py` (`_advance()`'s one-line change),
  `lock_in/visuals.py` (`"bookmark"` shape + `SHAPE_EFFECTS` entry),
  `lock_in/notifier.py` (Ex-Aid tone/sound tables), `lock_in/ui.py`
  (`current_tier4_effect`, the `_mpack`/`_mplace`/`_mgrid`/
  `_sync_mirror_layout()` mechanism and every geometry call-site
  routed through it, Kabuto's hover binding, Zero-One's card layout,
  Ghost's floating widget, Zeztz's hotkey bindings, Help tab section).
- New: `lock_in/ambient.py`, one small pixel font file and one small
  ambient loop audio file under `lock_in/assets/`.
- Edit: `tests/test_config.py`, `tests/test_rider_themes.py`,
  `tests/test_visuals.py`, `tests/test_session.py`,
  `tests/test_notifier.py`.
- New: `tests/test_ambient.py`.
- Edit: `README.md`.
- Version: v2.4.0.
