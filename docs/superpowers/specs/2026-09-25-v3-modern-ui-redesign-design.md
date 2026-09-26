# v3.0.0 — Modern look (side bar, cards, one Rider color)

## In one sentence

Lock In gets a new, calm, modern look — a side bar instead of bottom
tabs, clean cards, and one Rider color used with care — while every
feature and every Rider gimmick keeps working exactly as before.

## What changed for people using the app

- **Side bar navigation.** Focus, Tasks, Blocking, Activity, Insights at
  the top; Help and Settings pinned at the bottom. A Tier 5 Rider's page
  and Revice's Buddy page appear in between, under a small "Rider"
  heading, only while that Rider is picked.
- **Window** starts at 960 × 680 (smallest 820 × 600).
- **Focus page:** one card with the phase, the big timer, the progress
  bar (or the Rider's own shape), the current-task menu, one big
  Start/Henshin button, and smaller Skip and Reset. Under it, three small
  cards: Blocking, Phone check, and Watching.
- **Tasks page:** add box, All / Active / Done filter, one card per task
  with a tick box, a status badge, step progress, and a fold-open list of
  steps.
- **Blocking page:** four summary cards, then Protection, Detection,
  Claude helper, and the two app lists.
- **Activity page:** three summary cards and one card per window with a
  Blocked/Allowed badge and the two teach-the-model buttons.
- **Insights page (new):** plain totals worked out from the history and
  tasks already saved. No charts or rankings — those stay special to V3,
  Decade, W, and Geats.
- **Settings page:** Windows-Settings-style cards (Focus, Rider power,
  Blocking, Detection, Claude helper, Appearance, Notifications,
  Updates). Each row has words on the left and the control on the right.
- **Help page:** the same guide, split into cards, with "tab" wording
  changed to "page".
- **Colors:** calm base colors for light and dark mode
  (`lock_in/ui/theme.py`). One Rider color marks the main button, the
  progress bar, the page you're on, and switches. Green/amber/red only
  mean allowed/careful/blocked. The old per-section colors are gone.
- **MY-TH:** light mode is normal MY-TH (blue `#0f4a8f`, silver
  `#78909c`); dark mode is MY-TH ORIGIN (red `#ef5350`, gunmetal
  `#616161`). Still one entry in the Rider list.

## What did NOT change

- `config.json`, `tasks.json`, `sessions.jsonl`, `observations.jsonl`,
  and `model.json` keep exactly the same shape. No new saved settings.
- Enforcement, the session timer, the classifier, Claude fallback, the
  camera watcher, the updater, and Revice's network code are untouched.
- Every Tier 1–6 gimmick keeps its behavior. The Tier 5 builders in
  `lock_in/tier5/` are called exactly as before; only the frame they draw
  into moved from a tab to a page. (Three of them had "Tasks tab" in a
  sentence, now "Tasks page".)
- Background threads still only talk to the screen through queues.
- `ctk.deactivate_automatic_dpi_awareness()` stays, for the same reason
  as before (it stops the window going see-through when moved between
  screens with different scaling).

## How the code is split

`lock_in/ui.py` (one 3,600-line file) became the `lock_in/ui/` package.
`from lock_in.ui import LockInApp, run, flip_*_kwargs,
build_task_picker_entries, _TIER5_TAB_LABELS` all still work.

| File | Job |
|---|---|
| `app.py` | The window, the heartbeat, timer and enforcement handling |
| `theme.py` | Base colors, sizes, spacing; `resolve_palette(theme)` |
| `router.py` | `Route`, `build_routes()`, `Router` — no window needed |
| `mirror.py` | Ryuki's flip helpers and `MirrorLayout` |
| `icons.py` | Line icons drawn with Pillow |
| `overlays.py`, `updates.py`, `gestures.py`, `revice.py`, `preferences.py` | Behavior moved out of the old file unchanged, as mixins on `LockInApp` |
| `components/` | `ModernCard`, `StatCard`, buttons, `StatusBadge`, `SettingRow`, `Sidebar`, `TimerDisplay` |
| `pages/` | One class per page; `PAGE_CLASSES` maps route ids to them |

Pages only draw. Clicks call the same app methods as before
(`_on_toggle`, `_save_settings`, `_correct`, ...).

## Rider compatibility notes

- **Tier 2** is now read from a new `RiderTheme.tier2_effect` field
  (`interval_presets`, `task_presets`, `micro_sprint`) instead of
  comparing Rider names. Standard Mode's theme has none, as before.
- **Ryuki** mirrors the top bar and side bar too. The app now tracks
  which way the widgets are flipped and re-syncs whenever that changes —
  including Reset during a break and switching away from Ryuki while
  flipped, which used to leave the header half-flipped.
- **Wizard** moves along the side bar's route ids. A circle goes to Focus.
- **Zeztz** shortcuts are bound on the window as before.
- **Amazon** hides the side bar during a focus block and brings back the
  page you were on afterwards.
- **Zero-One** uses `StatCard`s for its four dashboard cards.
- **Stronger, Kiva, Gaim** paint onto a picture behind the page area; it
  shows in the gap around the page. Gaim also shows a "Locked on top"
  badge in the top bar during focus.
- **Black** gets a stricter dark palette (pure black background, brighter
  grey words).
- **Ghost's** floating clock is its own window, unchanged.
- **Revice's** link object lives on the app, so rebuilding pages never
  drops a connection.

## Speed and memory

Measured on the development laptop, before → after this work:

| | Before | After |
|---|---|---|
| Memory after opening every page | ~125 MB | ~87 MB |
| Timer tick (Stronger, Kiva, Gaim, Ryuki) | 75–130 ms | ~3–8 ms |
| Switching to a page already opened | 0.5–0.9 s | ~0.2 s |
| First open of Settings | ~4.6 s | ~1.8 s |
| Picking a new Rider | 8–9 s | ~2.8 s |
| Light/dark switch | 8–9 s | ~2 s |

What changed, and why:

- **OpenCV loads only when the camera is used** (`camera_enforcer._cv2()`).
  Checking "is it installed?" no longer loads it. The update checker's
  web code also loads on its background helper, not at launch.
- **The background picture is small and only redrawn when it changes.**
  It used to be redrawn at 900×1200 five times a second for four Riders.
- **Tier 1 shapes and Amazon's drain are redrawn only when they move.**
- **Pages stay drawn and are raised to the front** instead of being taken
  off the screen and put back. The four most recently used pages (plus
  Focus) stay ready; older ones are put away to save memory.
- **Old pages are taken apart a little at a time** after a Rider change,
  so the new page shows up first.
- **The Focus page is drawn when it's next opened** after a Rider change,
  not while you're still on Settings.
- **Light/dark needs no rebuild** — every color is a (light, dark) pair.
- **Lighter building blocks:** `Box` (invisible holders that don't draw
  a rounded shape), `Text` (plain-word labels, about twice as fast as
  CTkLabel), `ScrollArea` (its scrollbar doesn't force the whole window
  to lay out again, and it hides when a page fits), `MenuButton`
  (CTkOptionMenu forced a full layout on every draw), and fonts shared
  app-wide instead of one per label.
- **Pages only redraw when something changed** (Tasks, Activity, the
  Rider page).

## Testing

- All existing tests still pass.
- New: `tests/test_ui_theme.py`, `tests/test_ui_router.py`,
  `tests/test_ui_logic.py` (tokens, every Rider's palette, MY-TH's two
  looks, route lists for every Rider, the Router, Wizard targets, icons,
  Insights totals, task filters, Settings' Rider rows, `MirrorLayout`).
- `tests/smoke_ui.py` now also walks every page, every Rider's page, the
  Buddy page, Ryuki's mirror with the side bar, Standard Mode, and
  light/dark. Run it with a throwaway data folder (`.smoke-data/`).
