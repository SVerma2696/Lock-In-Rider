"""
ui.py
=====
This file draws the actual window you see and click on. It's the only file
in the whole app that touches the screen-drawing toolkit directly.

How the background thread and the screen work together (important!)
-------------------------------------------------------------------------
`ActiveWindowMonitor` checks your active window on its own background
thread. The screen-drawing toolkit isn't safe to touch from another thread,
so that background thread does exactly one simple thing:
`queue.put(window_info)` — it drops the info into a safe waiting line. The
main screen thread picks things up from that line on a timer loop, and it's
the only place that makes decisions or updates anything you see.

What the window looks like
------------------------------
    ┌───────────────────────────────┐
    │ banner (short pop-up message) │
    ├───────────────────────────────┤
    │  FOCUS                        │
    │        24:31                  │
    │  ▓▓▓▓▓░░░░░░░░░░░░            │
    │  [Start] [Skip] [Reset]       │
    ├───────────────────────────────┤
    │ Timer │ Blocking │ Activity │ Settings │ Help │
    └───────────────────────────────┘
"""

from __future__ import annotations

import dataclasses
import queue
import sys
import time
from datetime import datetime
from typing import List, Optional

import customtkinter as ctk
from PIL import ImageOps, ImageTk

# customtkinter's own automatic per-monitor DPI handling briefly makes the
# whole window ~85% transparent (window.attributes("-alpha", 0.15)) every
# time it detects the window moved to a monitor with different display
# scaling, while it rescales every widget/image/font -- by the library's
# own design, not a bug here. This trades that flash away: the window
# renders at a fixed pixel size instead of automatically adjusting per
# monitor, so it can look too small/large on a monitor whose scaling
# differs from the one the app started on. Must run before any CTk
# window is created, so it's placed immediately after the import.
ctk.deactivate_automatic_dpi_awareness()

from .classifier import DISTRACTION, STUDY, NaiveBayesClassifier
from .claude_fallback import ClaudeFallback
from .config import Config, MODEL_PATH, OBSERVATIONS_PATH, TASKS_PATH, LOG_PATH, app_data_dir
from .observations import ObservationStore
from .tasks import Task, TaskStatus, TaskStore
from .history import HistoryStore, SessionRecord
from .tier5 import TIER5_BUILDERS
from .camera_enforcer import CAMERA_BACKEND_AVAILABLE, CameraEnforcer, PhoneWatcher
from .enforcer import Action, Enforcer, Reason, Verdict, WindowInfo, judge, lockdown_label_for, message_for
from .ambient import AmbientPlayer
from .monitor import BACKEND_AVAILABLE, ActiveWindowMonitor, minimize_window
from .notifier import Notifier
from .session import Event, Phase, PomodoroSession, label_for
from .presets import GAVV_MICRO_SPRINT, KUUGA_PRESETS, SUPER1_PRESETS, TimerPreset
from .rider_themes import DEFAULT_RIDER_THEME, RIDER_THEMES, STANDARD_THEME, desaturate
from .visuals import (
    SHAPE_EFFECTS,
    apply_gaim_lock_overlay,
    apply_tier1_background_effect,
    display_font_family,
    ease_drive_progress,
    interpolate_agito_color,
    load_app_icon,
    load_pixel_font,
    make_background_texture,
    make_flat_fill,
    make_glow,
    make_panel_divider,
    render_amazon_drain,
    render_progress,
)

# Our color choices, kept in one spot — so changing the theme means
# changing a few lines here, not hunting through the whole file.
# (The focus color isn't here anymore — it now comes from whichever
# Kamen Rider is picked in Settings. See _apply_rider_theme.)
COLOR_BREAK = "#2f9e5f"      # green — means it's okay to relax
COLOR_IDLE = "#5a6472"
COLOR_WARN = "#e0a800"
COLOR_DANGER = "#c0392b"

# A few extra accent colors, so each tab/section has its own bit of
# personality instead of everything being the same grey. Each one is a
# (light-mode color, dark-mode color) pair — CustomTkinter automatically
# picks the right half depending on which theme is active, so these stay
# easy to read no matter which mode you're in.
COLOR_BLOCKING_ACCENT = ("#c2255c", "#ff6b9d")   # rose pink — Blocking tab
COLOR_ACTIVITY_ACCENT = ("#e8590c", "#ffa94d")   # orange — Activity tab
COLOR_TIMER_ACCENT = ("#1c7ed6", "#4dabf7")      # blue — timer-length settings
COLOR_ENFORCE_ACCENT = ("#e03131", "#ff8787")    # red — enforcement settings
COLOR_LOOK_ACCENT = ("#0ca678", "#63e6be")       # teal — sound/notification/look settings
COLOR_CLAUDE_ACCENT = ("#9c36b5", "#e599f7")     # purple — the Claude fallback feature

# The nicer-looking font for the timer digits and headings. Picked once
# per computer in visuals.py — see that file for why.
DISPLAY_FONT = display_font_family()

# The background wallpaper picture is made bigger than the window's
# starting size, so shrinking the window down never looks blurry — only
# growing it a lot past this would.
BG_TEXTURE_WIDTH = 900
BG_TEXTURE_HEIGHT = 1200

# The thin strip between the timer panel and the tab panel. Made wider
# than the window starts at, same reasoning as the background above.
DIVIDER_WIDTH = 900
DIVIDER_HEIGHT = 14

# The size of the picture used for the 4 Tier 1 Riders with their own
# custom progress SHAPE (windmill, rising bar, constellation, vials).
# Fixed on purpose -- unlike the background/divider above, this picture
# doesn't stretch when you resize the window, it just stays centered.
PROGRESS_SHAPE_WIDTH = 340
PROGRESS_SHAPE_HEIGHT = 48

# Amazon's zero-UI picture is bigger than the other progress pictures
# on purpose -- it's meant to dominate the header, not sit in a thin strip.
ZERO_UI_WIDTH = 340
ZERO_UI_HEIGHT = 120

# Tier 5's dynamic 6th tab: effect string (RiderTheme.tier5_effect) ->
# what the tab is called. Grows one entry per Rider as each one ships.
_TIER5_TAB_LABELS = {
    "hours_tab": "Hours", "timeline_view": "Timeline", "analytics_dashboard": "Analytics",
}


def _flip_side(side):
    return {"left": "right", "right": "left"}.get(side, side)


def _flip_anchor_or_sticky(value):
    """Swaps every 'w' for 'e' and vice versa inside an anchor/sticky
    string (e.g. 'nw' -> 'ne'), leaving n/s/center parts untouched."""
    if value is None:
        return value
    return "".join({"w": "e", "e": "w"}.get(c, c) for c in value)


def _flip_asymmetric_padding(value):
    """A 2-tuple padx/ipadx like (10, 0) means (left, right) -- when
    `side` flips, the padding has to swap ends too, or the gap ends up
    on the wrong edge of the mirrored row. A single number (equal
    padding on both sides) is unaffected either way."""
    if isinstance(value, tuple) and len(value) == 2:
        return (value[1], value[0])
    return value


def flip_pack_kwargs(mirrored: bool, kwargs: dict) -> dict:
    """Given the kwargs you were about to pass to .pack(), return the
    kwargs to actually use -- flipped if `mirrored` is True, exactly
    as given otherwise."""
    if not mirrored:
        return dict(kwargs)
    result = dict(kwargs)
    if "side" in result:
        result["side"] = _flip_side(result["side"])
    if "anchor" in result:
        result["anchor"] = _flip_anchor_or_sticky(result["anchor"])
    if "padx" in result:
        result["padx"] = _flip_asymmetric_padding(result["padx"])
    if "ipadx" in result:
        result["ipadx"] = _flip_asymmetric_padding(result["ipadx"])
    return result


def flip_place_kwargs(mirrored: bool, kwargs: dict) -> dict:
    if not mirrored:
        return dict(kwargs)
    result = dict(kwargs)
    if "relx" in result:
        # round() sidesteps binary-float artifacts like 1 - 0.18 landing
        # on 0.8200000000000001 instead of 0.82.
        result["relx"] = round(1 - result["relx"], 10)
    if "anchor" in result:
        result["anchor"] = _flip_anchor_or_sticky(result["anchor"])
    return result


def flip_grid_kwargs(mirrored: bool, total_columns: int, kwargs: dict) -> dict:
    if not mirrored:
        return dict(kwargs)
    result = dict(kwargs)
    if "column" in result:
        columnspan = result.get("columnspan", 1)
        result["column"] = total_columns - result["column"] - columnspan
    if "sticky" in result:
        result["sticky"] = _flip_anchor_or_sticky(result["sticky"])
    return result


def build_task_picker_entries(open_tasks: List[Task]) -> "tuple[List[str], dict]":
    """Turns a list of open tasks into (dropdown values, label -> id map)
    for the current-task picker.

    `TaskStore.add()` has no uniqueness check on `name`, so two open
    tasks can legitimately share the same display name (e.g. "Reading"
    typed twice for two different sessions). A dict keyed by name alone
    would silently collapse those into whichever one was inserted last,
    so picking either one from the dropdown would resolve to the wrong
    task id. To keep the label -> id lookup unambiguous, a name that
    collides among the currently-open tasks gets a "(2)", "(3)", ...
    counter suffix appended to its displayed label -- the id mapping is
    otherwise untouched, and TaskStore itself is never involved.

    That generated suffix can itself collide with a DIFFERENT open task's
    literal name (nothing stops you naming a task "Reading (1)" by hand
    alongside two tasks both called "Reading"), so every label is checked
    against the ones already handed out and the counter keeps climbing
    until it lands on one nobody is using.

    Kept free of Tk (like flip_pack_kwargs et al. above) so it can be
    unit tested directly without a live LockInApp/Tk instance."""
    name_counts: dict = {}
    for t in open_tasks:
        name_counts[t.name] = name_counts.get(t.name, 0) + 1

    seen_so_far: dict = {}
    task_menu_ids: dict = {}
    values = ["No task"]
    for t in open_tasks:
        if name_counts[t.name] > 1:
            seen_so_far[t.name] = seen_so_far.get(t.name, 0) + 1
            counter = seen_so_far[t.name]
            label = f"{t.name} ({counter})"
        else:
            counter = 0
            label = t.name
        # Whether the label came out of the suffix branch or is a plain
        # name, it only goes in the map once it's provably unused --
        # otherwise the later task would silently overwrite the earlier
        # one's entry and the dropdown would resolve to the wrong id.
        while label in task_menu_ids:
            counter += 1
            label = f"{t.name} ({counter})"
        task_menu_ids[label] = t.id
        values.append(label)
    return values, task_menu_ids


class LockInApp(ctk.CTk):
    """The main app window — everything you see lives inside this."""

    UI_TICK_MS = 200      # how often we redraw the countdown, in milliseconds
    BANNER_MS = 6000      # how long a pop-up banner stays on screen, in milliseconds

    def __init__(self) -> None:
        super().__init__()

        # ---------------- The main pieces of the app -------------------- #
        self.config_obj = Config.load()
        # The session has to exist BEFORE _apply_rider_theme(), because
        # that method now also has to check what phase we're in (for
        # Stronger/Kiva's Tier 1 background effect).
        self.session = PomodoroSession(self.config_obj)
        self._apply_rider_theme()
        # X's goal-entry gate stores what you typed here -- in-memory
        # only, same rule as Fourze's constellation state: it resets
        # every time the app restarts, no save file needed.
        self.current_goal_text = ""
        # Kabuto's hidden-timer gimmick: True only while you're hovering
        # over the digits to peek at the real time. Resets every time
        # you move the mouse away -- never saved, never persisted.
        self._kabuto_revealed = False
        self.model = NaiveBayesClassifier.load(MODEL_PATH)
        self.observations = ObservationStore(OBSERVATIONS_PATH)
        self.tasks = TaskStore(TASKS_PATH)
        self.history = HistoryStore(LOG_PATH)
        # The task selected in the Home header's "current task" picker --
        # None means an untagged block, exactly like today's behavior
        # with no task system at all. Never saved to config.json; it's
        # meant to change often and doesn't need to survive a restart.
        self.current_task_id: Optional[str] = None
        # Set the instant a FOCUS phase begins, cleared once it's logged
        # to history (whether it finished naturally, was skipped, or was
        # reset). None means "no focus block is currently being timed" --
        # used to tell a FOCUS phase ending from a BREAK phase ending,
        # since by the time _on_phase_ended() runs, self.session.phase
        # has already moved on to whatever comes next.
        self._focus_block_start: Optional[datetime] = None
        self._focus_block_planned_seconds: int = 0
        self.claude = ClaudeFallback(self.config_obj)
        self.enforcer = Enforcer(self.config_obj)
        self.camera_enforcer = CameraEnforcer(self.config_obj)
        self.notifier = Notifier(self.config_obj)
        self.notifier.banner_callback = self._queue_banner
        self.ambient = AmbientPlayer(self.config_obj)

        # Safe mailboxes for passing messages between threads.
        self._window_queue: "queue.Queue[WindowInfo]" = queue.Queue()
        self._camera_queue: "queue.Queue[bool]" = queue.Queue()
        self._banner_queue: "queue.Queue[tuple]" = queue.Queue()
        self._claude_queue: "queue.Queue[tuple]" = queue.Queue()

        self.monitor = ActiveWindowMonitor(
            callback=self._window_queue.put,   # safe to call from any thread — does nothing fancy
            interval=1.0,
        )
        self.camera_watcher = PhoneWatcher(callback=self._camera_queue.put)

        # The activity list: dicts of {time, text, blocked, reason, label}
        self.activity: List[dict] = []
        self._lockdown_window: Optional[ctk.CTkToplevel] = None
        self._ghost_widget: Optional[ctk.CTkToplevel] = None
        self._banner_after_id: Optional[str] = None

        # ---------------- The window frame ------------------------------ #
        ctk.set_appearance_mode(self.config_obj.appearance)
        ctk.set_default_color_theme(self.config_obj.accent)

        self.title("Lock In")
        self.geometry("560x720")
        self.minsize(500, 640)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_app_icon()

        # This picture sits behind absolutely everything else. It has to
        # be made FIRST, before any other button or label — in this
        # screen-drawing toolkit, whatever gets made first sits at the
        # very back, like the bottom of a stack of papers.
        self._bg_label = ctk.CTkLabel(self, text="", image=self._bg_image)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        # Whenever you resize the window, stretch the picture to match —
        # otherwise it would stay one fixed size and leave a bare edge.
        self.bind("<Configure>", self._on_window_resized)

        # Keyed by str(widget) (Tk's own widget path) instead of a plain
        # list -- re-registering the same widget (e.g. a Settings tab
        # rebuild) replaces its old entry instead of piling up a
        # duplicate, so this self-heals during normal operation instead
        # of growing without bound across a long session.
        self._mirror_managed_widgets: dict = {}
        self._dashboard_built = False

        self._build_header()
        self._build_divider()
        self._build_tabs()
        self._refresh_current_task_picker()

        self.bind_all("<space>", self._on_zeztz_space)
        self.bind_all("s", self._on_zeztz_skip)
        self.bind_all("r", self._on_zeztz_reset)

        self.monitor.start()
        self.camera_watcher.start()
        self._sync_progress_widget_visibility()
        self._pump()          # start the UI heartbeat
        self._refresh_timer_widgets()
        # Wait a moment before showing this, so the window is fully drawn
        # and visible first — a banner on a window that isn't on screen yet
        # would just be missed.
        self.after(400, self._warn_if_app_detection_unavailable)

    def _set_app_icon(self) -> None:
        """
        Puts the app's own picture in the title bar and the taskbar.

        If the picture is missing or broken, `load_app_icon()` just
        gives back `None` instead of raising an error — so we quietly
        skip this and the window keeps the toolkit's plain default
        icon instead of crashing.
        """
        icon = load_app_icon()
        if icon is None:
            return
        # Tkinter only understands its own kind of picture object, so we
        # convert to that here. We also keep a copy on `self` — if we
        # didn't, the toolkit could throw the picture away too early and
        # the icon would quietly vanish a moment after it appeared.
        self._icon_image = ImageTk.PhotoImage(icon)
        self.iconphoto(True, self._icon_image)

        # Windows' own title bar and taskbar don't reliably pick up the
        # picture from the line above -- on Windows specifically, they
        # need a real ".ico" file handed to them a different way. We
        # save one, once, in the app's own settings folder (the same
        # place config.json lives), so we're not trying to write into
        # the program's own install folder, which might not be allowed.
        if sys.platform == "win32":
            try:
                ico_path = app_data_dir() / "app_icon.ico"
                if not ico_path.exists():
                    icon.save(
                        ico_path, format="ICO",
                        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
                    )
                self.iconbitmap(default=str(ico_path))
            except Exception:
                pass

    # ================================================================== #
    # Picking words: "professional" (the normal voice) or "tokusatsu"
    # (the Kamen Rider-flavored voice you turn on in Settings)
    # ================================================================== #
    def _is_tokusatsu(self) -> bool:
        # Standard Mode always reads as Professional, no matter what the
        # Wording switch itself says -- the switch's real value is never
        # overwritten, so it's back the instant Standard Mode is off.
        return self.config_obj.terminology == "tokusatsu" and not self.config_obj.standard_mode

    def _effective_terminology(self) -> str:
        """The wording value to hand to label_for()/message_for()/lockdown_label_for()
        -- the same Standard Mode override _is_tokusatsu() applies to display
        copy, as the plain string those functions expect instead of a bool."""
        return "tokusatsu" if self._is_tokusatsu() else "professional"

    def _henshin_word(self) -> str:
        """What the main Start/Henshin button says when it's not running."""
        return "Henshin" if self._is_tokusatsu() else "Start"

    def _rider_row_label_text(self) -> str:
        """What the color-theme picker's row is called in Settings."""
        return "Kamen Rider theme" if self._is_tokusatsu() else "Color theme"

    def _driver_label_text(self) -> str:
        """What the name label under the timer digits should say right now."""
        if self.config_obj.standard_mode:
            return "STANDARD MODE"
        return self.config_obj.rider_theme.upper()

    def _apply_rider_theme(self) -> None:
        """
        Look up which Kamen Rider is picked in settings, and remember
        that Rider's two colors so the rest of the app can use them.

        Also redraws the three Rider-colored pictures (the background
        wallpaper, and the two soft glows) to match. The very first time
        this runs, the pictures don't exist yet, so we make brand-new
        ones; every time after that (when you pick a different Rider),
        we just update the ones already on screen instead.

        If we don't understand the saved name for some reason, we just
        use the first Rider instead of crashing.
        """
        theme = STANDARD_THEME if self.config_obj.standard_mode else RIDER_THEMES.get(
            self.config_obj.rider_theme, RIDER_THEMES[DEFAULT_RIDER_THEME]
        )
        # ZX's whole gimmick is going monochrome. Swapping in a
        # desaturated copy of the theme HERE, before anything below
        # reads theme.primary_pair/surface_pair/etc, means every one of
        # those (which all derive from primary/secondary) comes out
        # grey automatically -- no separate grayscale step needed
        # anywhere else, for widgets OR the Pillow-rendered art.
        if theme.tier3_effect == "stealth_mute":
            theme = dataclasses.replace(
                theme,
                primary=(desaturate(theme.primary[0]), desaturate(theme.primary[1])),
                secondary=(desaturate(theme.secondary[0]), desaturate(theme.secondary[1])),
            )
        self.color_focus = theme.primary_pair
        self.color_rider_accent = theme.secondary_pair
        # A panel-background color tinted by the Rider's primary color —
        # pale in light mode, near-black in dark mode, same hue either
        # way. This is what makes the header and tabs themselves change
        # color, not just a button and a label.
        self.color_surface = theme.surface_pair
        # These are for WORDS specifically, not fills or bars — they're
        # always readable on top of whatever they're meant to sit on,
        # even for a Rider whose own color is almost white or almost
        # black. Without these, a Rider like Fourze (pure white) would
        # have text that's the exact same color as its own background —
        # invisible.
        self.color_focus_text = theme.primary_text_pair
        self.color_driver_text = theme.secondary_text_pair
        self.color_button_text = theme.button_text_pair
        # The lockdown screen's cover is always dark, no matter which
        # appearance mode you're in, so its words just need to always be
        # bright — one plain color, not a light/dark pair. The dark-mode
        # half of primary is already hand-picked to pop against a dark
        # background, so it's used as-is here, no extra lightening.
        self.color_lockdown_text = theme.primary[1]
        # Which era this Rider is from (Showa/Heisei/Reiwa) — this also
        # picks the notification wording, the lockdown screen's big
        # words, the background pattern shape, and the sound cues.
        self.current_era = theme.era

        # Which Tier 1 gimmick (if any) this Rider has, and the two
        # (light, dark) color pairs some of those gimmicks need directly
        # (not the text/surface pairs above -- Agito's color shift and
        # Stronger's glow both work from the Rider's real colors).
        self.current_tier1_effect = theme.tier1_effect
        # Which Tier 3 gimmick (if any) this Rider has -- read by the
        # goal-gate, zero-UI, lock-overlay, and code-unlock code later
        # in this file.
        self.current_tier3_effect = theme.tier3_effect
        # Which Tier 4 gimmick (if any) this Rider has -- read by the
        # mirror-flip, hidden-timer, dashboard-cards, ghost-widget, and
        # hotkey code later in this file.
        self.current_tier4_effect = theme.tier4_effect
        # Which Tier 5 gimmick (if any) this Rider has -- read by
        # _build_tabs() to decide whether a 6th tab exists at all.
        self.current_tier5_effect = theme.tier5_effect
        # The resolved RiderTheme itself (after ZX's desaturation, if
        # that applied above) -- _build_tier5_tab() needs the actual
        # theme object, not just the derived colors already unpacked
        # onto self above.
        self._current_rider_theme = theme
        if self.current_tier4_effect == "chiptune_alert":
            self._active_display_font = load_pixel_font()
        else:
            self._active_display_font = DISPLAY_FONT
        if hasattr(self, "time_label"):
            self.time_label.configure(
                font=ctk.CTkFont(family=self._active_display_font, size=76, weight="bold"))
            self.phase_label.configure(
                font=ctk.CTkFont(family=self._active_display_font, size=16, weight="bold"))
        self.rider_primary_pair = theme.primary
        self.rider_secondary_pair = theme.secondary
        # Stronger's glow uses the Rider's own primary (already a red);
        # Kiva's night wash uses the secondary (the amber gold). Every
        # other Rider never reads this, so the value doesn't matter for them.
        self.color_tier1_effect_pair = (
            theme.primary if theme.tier1_effect == "border_glow" else theme.secondary
        )

        primary_light, primary_dark = theme.primary
        secondary_light, secondary_dark = theme.secondary
        if self.config_obj.standard_mode:
            # No glow, and a flat fill instead of an era pattern -- a
            # solid-color fill is what actually makes this "bypass the
            # Pillow art": virtually free to draw, versus a
            # procedurally-generated texture.
            surface_light, surface_dark = self.color_surface
            timer_glow_light = make_flat_fill(300, 120, primary_light, alpha=0)
            timer_glow_dark = make_flat_fill(300, 120, primary_dark, alpha=0)
            button_glow_light = make_flat_fill(170, 70, secondary_light, alpha=0)
            button_glow_dark = make_flat_fill(170, 70, secondary_dark, alpha=0)
            bg_dark = make_flat_fill(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, surface_dark)
            bg_light = make_flat_fill(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, surface_light)
            divider_light = make_flat_fill(DIVIDER_WIDTH, DIVIDER_HEIGHT, surface_light)
            divider_dark = make_flat_fill(DIVIDER_WIDTH, DIVIDER_HEIGHT, surface_dark)
        else:
            timer_glow_light = make_glow(300, 120, primary_light)
            timer_glow_dark = make_glow(300, 120, primary_dark)
            button_glow_light = make_glow(170, 70, secondary_light)
            button_glow_dark = make_glow(170, 70, secondary_dark)
            bg_dark = make_background_texture(
                BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, primary_dark, secondary_dark,
                dark=True, era=theme.era,
            )
            bg_light = make_background_texture(
                BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, primary_light, secondary_light,
                dark=False, era=theme.era,
            )
            divider_light = make_panel_divider(
                DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_light, secondary_light, era=theme.era,
            )
            divider_dark = make_panel_divider(
                DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_dark, secondary_dark, era=theme.era,
            )
        # Keep the PLAIN pattern around separately from whatever ends up
        # on screen -- Stronger/Kiva's effect gets painted fresh on top
        # of this every tick, so we always need the untouched original
        # to start from, not last tick's already-tinted result.
        self._base_bg_dark = bg_dark
        self._base_bg_light = bg_light
        self._base_divider_dark = divider_dark
        self._base_divider_light = divider_light

        if hasattr(self, "_timer_glow_image"):
            self._timer_glow_image.configure(light_image=timer_glow_light, dark_image=timer_glow_dark)
            self._button_glow_image.configure(light_image=button_glow_light, dark_image=button_glow_dark)
            self._bg_image.configure(light_image=bg_light, dark_image=bg_dark)
            self._divider_image.configure(light_image=divider_light, dark_image=divider_dark)
        else:
            self._timer_glow_image = ctk.CTkImage(
                light_image=timer_glow_light, dark_image=timer_glow_dark, size=(300, 120)
            )
            self._button_glow_image = ctk.CTkImage(
                light_image=button_glow_light, dark_image=button_glow_dark, size=(170, 70)
            )
            self._bg_image = ctk.CTkImage(
                light_image=bg_light, dark_image=bg_dark,
                size=(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT),
            )
            self._divider_image = ctk.CTkImage(
                light_image=divider_light, dark_image=divider_dark,
                size=(DIVIDER_WIDTH, DIVIDER_HEIGHT),
            )

        # Re-apply Stronger/Kiva's effect (if this Rider has one) right
        # away -- otherwise switching themes mid-focus-block would show
        # the plain, untinted background for a moment.
        self._refresh_background_effect(self.session.progress)

    def _refresh_background_effect(self, progress_fraction: float) -> None:
        """
        Redraw the background picture's Stronger-glow or Kiva-wash (if
        this Rider has one) and push it onto the picture already on
        screen. Both effects only show up DURING a focus block and
        disappear the moment it ends -- that's what `in_focus` is for.
        Riders without either effect just get the plain picture back,
        unchanged.
        """
        in_focus = self.session.phase is Phase.FOCUS
        active_effect = self.current_tier1_effect if in_focus else "none"
        effect_color_light, effect_color_dark = self.color_tier1_effect_pair
        bg_light = apply_tier1_background_effect(
            self._base_bg_light, active_effect, effect_color_light, progress_fraction,
        )
        bg_dark = apply_tier1_background_effect(
            self._base_bg_dark, active_effect, effect_color_dark, progress_fraction,
        )

        if self.current_tier3_effect == "lock_overlay":
            bg_light = apply_gaim_lock_overlay(bg_light, in_focus)
            bg_dark = apply_gaim_lock_overlay(bg_dark, in_focus)

        if self._is_mirrored:
            bg_light = ImageOps.mirror(bg_light)
            bg_dark = ImageOps.mirror(bg_dark)

        self._bg_image.configure(light_image=bg_light, dark_image=bg_dark)

    def _sync_mirror_divider(self) -> None:
        """The divider strip has no per-tick refresh path the way the
        background wallpaper does, so Ryuki's mirror needs this one
        small explicit call instead -- see _sync_mirror_layout() for
        why phase transitions (not every tick) are the right moment."""
        if not hasattr(self, "_base_divider_light"):
            return
        if self._is_mirrored:
            self._divider_image.configure(
                light_image=ImageOps.mirror(self._base_divider_light),
                dark_image=ImageOps.mirror(self._base_divider_dark),
            )
        else:
            self._divider_image.configure(
                light_image=self._base_divider_light, dark_image=self._base_divider_dark,
            )

    def _on_window_resized(self, event) -> None:
        """
        Stretch the background picture to match whenever the window
        changes size.

        This fires a LOT while you're actively dragging the window's
        edge, so we skip the work unless the size actually changed —
        otherwise we'd be resizing the same picture to the same size
        over and over for no reason.
        """
        if event.widget is not self:
            return
        new_size = (max(event.width, 1), max(event.height, 1))
        if self._bg_image.cget("size") != new_size:
            self._bg_image.configure(size=new_size)

        # The divider strip spans the same width as the header/tabs
        # panels above and below it (the window's width, minus the
        # padx=20 gap on each side) — keep it in sync as the window
        # changes size, same idea as the background picture above.
        divider_width = max(event.width - 40, 1)
        if self._divider_image.cget("size") != (divider_width, DIVIDER_HEIGHT):
            self._divider_image.configure(size=(divider_width, DIVIDER_HEIGHT))

    def _warn_if_app_detection_unavailable(self) -> None:
        """
        Puts up an obvious on-screen warning if blocking can't work at all.

        `main.py` already prints this same warning to the console — but
        `run.bat` launches with `pythonw.exe` specifically so no console
        window shows up, which also means that printed warning is thrown
        away and nobody ever sees it. Someone could easily use the app for
        weeks thinking blocking is on, when it's silently doing nothing.
        This banner (and the note already on the Blocking tab) make sure
        that's visible right on the main screen instead.
        """
        if not BACKEND_AVAILABLE:
            self._show_banner(
                "Blocking isn't working: pywin32 and psutil aren't "
                "installed, so the app can't see which window you're in. "
                "Run: pip install pywin32 psutil",
                "high", duration_ms=20000,
            )

    # ------------------------------------------------------------------ #
    # Ryuki's mirror mechanism -- see flip_pack_kwargs/flip_place_kwargs/
    # flip_grid_kwargs above for the actual flipping logic. These three
    # wrappers are drop-in replacements for .pack()/.place()/.grid():
    # same arguments, but every geometry call in this file goes through
    # one of these instead of calling the real method directly, so a
    # single _sync_mirror_layout() call can re-flip everything at once
    # when a break starts or ends.
    # ------------------------------------------------------------------ #
    @property
    def _is_mirrored(self) -> bool:
        return self.current_tier4_effect == "mirror_flip" and self.session.phase.is_break

    def _mpack(self, widget, **kwargs) -> None:
        flipped = flip_pack_kwargs(self._is_mirrored, kwargs)
        widget.pack(**flipped)
        self._mirror_managed_widgets[str(widget)] = ("pack", widget, None, kwargs)

    def _mplace(self, widget, **kwargs) -> None:
        flipped = flip_place_kwargs(self._is_mirrored, kwargs)
        widget.place(**flipped)
        self._mirror_managed_widgets[str(widget)] = ("place", widget, None, kwargs)

    def _mgrid(self, widget, total_columns: int, **kwargs) -> None:
        flipped = flip_grid_kwargs(self._is_mirrored, total_columns, kwargs)
        widget.grid(**flipped)
        self._mirror_managed_widgets[str(widget)] = ("grid", widget, total_columns, kwargs)

    def _sync_mirror_layout(self) -> None:
        """Re-applies every registered widget's geometry against the
        CURRENT mirror state. Call this whenever the phase crosses into
        or out of a break -- that's the only moment anything should
        actually flip.

        Only Ryuki ever needs this at all -- for every other Rider it's
        a no-op, on purpose, so it never has a chance to disturb
        whatever some OTHER feature has already pack_forget()-ten (the
        Tier 1 shape Riders' plain progress bar, Amazon's normal header
        content, etc.)."""
        if self.current_tier4_effect != "mirror_flip":
            return
        dead_keys = []
        for key, (manager, widget, total_columns, kwargs) in self._mirror_managed_widgets.items():
            if not widget.winfo_exists():
                # Destroyed since it was registered (e.g. a rebuilt
                # Settings tab) -- drop it so the registry doesn't pin a
                # dead widget reference forever.
                dead_keys.append(key)
                continue
            if not widget.winfo_manager():
                # Deliberately hidden by another feature (pack_forget()
                # / place_forget()) -- don't resurrect it.
                continue
            try:
                # Deliberately .pack()/.place()/.grid() here, NOT the
                # _configure() variants. They're equivalent re-apply calls
                # for an ordinary widget already under that manager -- but
                # CTkScrollableFrame overrides .pack()/.place()/.grid() to
                # delegate to its internal _parent_frame (the actual
                # widget lives embedded in its own scrolling canvas, via
                # canvas.create_window(), reported as winfo_manager()
                # "canvas") while leaving pack_configure()/etc. un-
                # overridden. Calling the _configure() form directly on
                # one of those literally starts pack-managing the inner,
                # canvas-embedded widget itself -- confirmed by testing
                # against the real widget: its winfo_manager() flips from
                # "canvas" to "pack" the instant pack_configure() is
                # called on it, corrupting both its layout and the
                # canvas's own scroll tracking. The five CTkScrollableFrame
                # tabs (Tasks/Blocking/Activity/Settings/Help) are all
                # registered here via _mpack, so this bit the whole app,
                # not just one tab, and only once Ryuki's mirror actually
                # ran this method for the first time.
                if manager == "pack":
                    widget.pack(**flip_pack_kwargs(self._is_mirrored, kwargs))
                elif manager == "place":
                    widget.place(**flip_place_kwargs(self._is_mirrored, kwargs))
                else:
                    widget.grid(**flip_grid_kwargs(self._is_mirrored, total_columns, kwargs))
            except Exception:
                # Belt-and-braces: any other Tk error re-applying this
                # widget's geometry shouldn't crash the sync.
                pass
        for key in dead_keys:
            del self._mirror_managed_widgets[key]

    # ================================================================== #
    # Building the pieces you see on screen
    # ================================================================== #
    def _build_dashboard_cards(self, parent) -> None:
        """Zero-One's reskin: the same values normal_header_content
        already shows, laid out as bordered corporate-looking cards
        instead of the centered timer stack. No new data -- just a
        different arrangement of what's already tracked."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        self._mpack(row, fill="x", pady=(8, 4))

        def card(label: str, value_getter) -> ctk.CTkLabel:
            box = ctk.CTkFrame(row, border_width=1, border_color=self.color_rider_accent)
            self._mpack(box, side="left", expand=True, fill="both", padx=4)
            self._mpack(ctk.CTkLabel(box, text=label, font=ctk.CTkFont(size=10),
                                      text_color=COLOR_IDLE), pady=(6, 0))
            value_label = ctk.CTkLabel(box, text=value_getter(),
                                        font=ctk.CTkFont(size=16, weight="bold"))
            self._mpack(value_label, pady=(0, 6))
            return value_label

        self._dashboard_status_value = card("Status", lambda: label_for(
            self.session.phase, self._effective_terminology()))
        self._dashboard_time_value = card("Time Remaining", self.session.format_remaining)
        self._dashboard_streak_value = card(
            "Sessions Complete", lambda: str(self.session.completed_focus_blocks))
        self._dashboard_profile_value = card("Active Profile", self._driver_label_text)

    def _build_header(self) -> None:
        """Builds the top area: banner, phase name, countdown, progress bar, and buttons."""
        header = ctk.CTkFrame(self, corner_radius=16, fg_color=self.color_surface)
        self._mpack(header, fill="x", padx=20, pady=(16, 4))
        # Kept so `_on_rider_theme_change` can re-tint this panel later
        # without having to rebuild the whole header from scratch.
        self.header_frame = header

        # A short pop-up message banner. Starts hidden; _show_banner reveals it.
        self.banner = ctk.CTkLabel(
            header, text="", corner_radius=8, height=44,
            font=ctk.CTkFont(size=13), wraplength=480, justify="left",
        )

        # A soft glow sits right behind the timer digits. It has to be
        # made before EVERY other label in this header, including the
        # phase name above it — whatever gets made first is stacked at
        # the back, so this makes sure the glow never paints over words.
        self._timer_glow_label = ctk.CTkLabel(header, text="", image=self._timer_glow_image)
        self._mplace(self._timer_glow_label, relx=0.5, rely=0.33, anchor="center")

        # Wrapped in one frame so Amazon's zero-UI mode can hide all 4
        # of these at once, safely, instead of hiding and restoring
        # each one individually. Not packed here -- self.controls
        # doesn't exist yet at this point in the method, so packing
        # happens a little further down, right after self.controls is
        # created.
        self.normal_header_content = ctk.CTkFrame(header, fg_color="transparent")

        self.phase_label = ctk.CTkLabel(
            self.normal_header_content, text="Standing By",
            font=ctk.CTkFont(family=self._active_display_font, size=16, weight="bold"),
            text_color=COLOR_IDLE,
        )
        self._mpack(self.phase_label, pady=(4, 0))

        self.time_label = ctk.CTkLabel(
            self.normal_header_content, text="25:00",
            font=ctk.CTkFont(family=self._active_display_font, size=76, weight="bold"),
        )
        self._mpack(self.time_label, pady=(0, 4))
        self.time_label.bind("<Enter>", lambda e: self._set_kabuto_revealed(True))
        self.time_label.bind("<Leave>", lambda e: self._set_kabuto_revealed(False))

        self.streak_label = ctk.CTkLabel(
            self.normal_header_content, text="0 blocks done", font=ctk.CTkFont(size=12),
            text_color=COLOR_IDLE,
        )
        self._mpack(self.streak_label)

        self.driver_label = ctk.CTkLabel(
            self.normal_header_content, text=self._driver_label_text(),
            font=ctk.CTkFont(family=DISPLAY_FONT, size=10, weight="bold"),
            text_color=self.color_driver_text,
        )
        self._mpack(self.driver_label, pady=(2, 0))

        # Deliberately a child of `header`, NOT of normal_header_content:
        # Zero-One's dashboard-card reskin swaps normal_header_content out
        # wholesale, and the current-task picker is real functionality, not
        # part of the centered-timer arrangement the cards replace. Keeping
        # it one level up means it survives that swap. (Amazon's zero-UI is
        # the one deliberate exception -- see _sync_zero_ui_visibility,
        # which hides this row along with everything else on purpose.)
        # Packed just below normal_header_content and just above the
        # progress bar, exactly where it used to sit inside it.
        self.task_row = ctk.CTkFrame(header, fg_color="transparent")
        self.current_task_menu = ctk.CTkOptionMenu(
            self.task_row, values=["No task"], width=220,
            command=self._on_current_task_selected,
        )
        self._mpack(self.current_task_menu, side="left")

        self.progress = ctk.CTkProgressBar(header, height=8, corner_radius=4)
        self.progress.set(0)
        self._mpack(self.progress, fill="x", pady=(12, 14))

        # A second, picture-based widget -- only shown INSTEAD of the
        # plain bar above, and only for the 4 Riders with their own
        # custom shape (see _sync_progress_widget_visibility). Every
        # other Rider never sees this at all; the plain bar above just
        # keeps working exactly like it always has.
        self.progress_shape = ctk.CTkLabel(header, text="", image=None)

        # Amazon's "zero UI" picture -- only shown instead of everything
        # else in the header, and only during an actual focus block
        # (see _sync_zero_ui_visibility). Not packed yet on purpose.
        self.zero_ui_label = ctk.CTkLabel(header, text="", image=None)

        self.controls = ctk.CTkFrame(header, fg_color="transparent")
        self._mpack(self.controls)
        # normal_header_content and task_row were created earlier in this
        # method (before the progress bar), but weren't packed yet until
        # now -- pack() needs self.controls to already be managed for
        # `before=` to place them correctly, right where they visually
        # belong: above the progress bar. task_row goes in first so the
        # final stack reads content, picker, progress, controls.
        self._mpack(self.task_row, pady=(6, 0), before=self.progress)
        self._mpack(self.normal_header_content, before=self.task_row)

        # Zero-One's dashboard-card reskin -- same values as
        # normal_header_content, just arranged as bordered cards.
        # Not packed yet on purpose; visibility is decided in
        # _refresh_timer_widgets(), matching zero_ui_label above.
        self._dashboard_cards_frame = ctk.CTkFrame(header, fg_color="transparent")

        controls = self.controls

        # Same trick as the timer glow: made first, so it sits behind the
        # Henshin button that gets made right after it.
        self._button_glow_label = ctk.CTkLabel(controls, text="", image=self._button_glow_image)
        self._mplace(self._button_glow_label, relx=0.18, rely=0.5, anchor="center")

        self.start_button = ctk.CTkButton(
            controls, text=self._henshin_word(), width=140, height=40,
            font=ctk.CTkFont(family=DISPLAY_FONT, size=15, weight="bold"), command=self._on_toggle,
            fg_color=self.color_rider_accent, text_color=self.color_button_text,
        )
        self._mgrid(self.start_button, total_columns=3, row=0, column=0, padx=6)

        self.skip_button = ctk.CTkButton(
            controls, text="Skip", width=80, height=40,
            fg_color="transparent", border_width=2,
            border_color=COLOR_TIMER_ACCENT, text_color=COLOR_TIMER_ACCENT,
            hover_color=("#d0ebff", "#173a5e"),
            command=self._on_skip,
        )
        self._mgrid(self.skip_button, total_columns=3, row=0, column=1, padx=6)

        self.reset_button = ctk.CTkButton(
            controls, text="Reset", width=80, height=40,
            fg_color="transparent", border_width=2,
            border_color=COLOR_ENFORCE_ACCENT, text_color=COLOR_ENFORCE_ACCENT,
            hover_color=("#ffe3e3", "#4a1414"),
            command=self._on_reset,
        )
        self._mgrid(self.reset_button, total_columns=3, row=0, column=2, padx=6)

        # Shows, live, what window we currently think you're looking at.
        self.watch_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=11), text_color=COLOR_IDLE,
            wraplength=480,
        )
        self._mpack(self.watch_label, pady=(12, 0))

        # Only ever shown while a focus block is actually running AND the
        # switch is on -- i.e. exactly whenever PhoneWatcher genuinely has
        # the camera open. Gone the instant either stops being true, on
        # top of whatever your webcam's own hardware light already shows.
        self.camera_indicator_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=11), text_color=COLOR_ENFORCE_ACCENT,
        )
        self._mpack(self.camera_indicator_label, pady=(4, 0))

    def _refresh_current_task_picker(self) -> None:
        """Rebuilds the dropdown's options from the current open-task
        list. Called after any add/complete in the Tasks tab (Task 4),
        so a newly-added task shows up here without restarting the app.
        Label -> id mapping (including collision-safe disambiguation
        when two open tasks share a name) is delegated to
        build_task_picker_entries() so that logic stays unit-testable
        without a live Tk instance."""
        open_tasks = self.tasks.open()
        values, self._task_menu_ids = build_task_picker_entries(open_tasks)
        self.current_task_menu.configure(values=values)

        if self.current_task_id not in {t.id for t in open_tasks}:
            # The selected task was completed or deleted out from under
            # the picker -- fall back to "No task" rather than pointing
            # at a task that's no longer open.
            self.current_task_id = None
            self.current_task_menu.set("No task")

    def _on_current_task_selected(self, name: str) -> None:
        self.current_task_id = self._task_menu_ids.get(name)  # None for "No task"

    def _build_divider(self) -> None:
        """
        Builds the thin, decorated strip that sits in the gap between
        the timer panel above and the tab panel below — so even that
        little gap looks like it belongs to whichever Kamen Rider era
        is picked, instead of just being empty space.
        """
        self._divider_label = ctk.CTkLabel(self, text="", image=self._divider_image)
        self._mpack(self._divider_label, fill="x", padx=20, pady=(0, 4))

    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(
            self, height=340,
            fg_color=self.color_surface,
            segmented_button_selected_color=self.color_rider_accent,
            text_color=self.color_button_text,
        )
        self._mpack(self.tabs, fill="both", expand=True, padx=20, pady=(0, 16))

        for name in ("Tasks", "Blocking", "Activity", "Settings", "Help"):
            self.tabs.add(name)
        if self.current_tier5_effect != "none":
            self.tabs.add(_TIER5_TAB_LABELS[self.current_tier5_effect])

        self._build_tasks_tab(self.tabs.tab("Tasks"))
        self._build_blocking_tab(self.tabs.tab("Blocking"))
        self._build_activity_tab(self.tabs.tab("Activity"))
        self._build_settings_tab(self.tabs.tab("Settings"))
        self._build_help_tab(self.tabs.tab("Help"))
        if self.current_tier5_effect != "none":
            self._build_tier5_tab()

    def _build_tier5_tab(self) -> None:
        """Fills in whichever Tier 5 tab `_build_tabs()` just added, by
        looking up this Rider's builder in TIER5_BUILDERS. Safe to call
        again later (e.g. from _on_phase_ended) to refresh the tab's
        content in place without rebuilding the other five tabs."""
        label = _TIER5_TAB_LABELS[self.current_tier5_effect]
        frame = self.tabs.tab(label)
        for child in frame.winfo_children():
            child.destroy()
        TIER5_BUILDERS[self.current_tier5_effect](
            frame, history=self.history, tasks=self.tasks,
            theme=self._current_rider_theme, appearance_mode=ctk.get_appearance_mode(),
        )

    # ------------------------------------------------------------------ #
    def _build_blocking_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._mpack(frame, fill="both", expand=True)

        if not BACKEND_AVAILABLE:
            self._mpack(ctk.CTkLabel(
                frame,
                text=("App detection unavailable on this system.\n"
                      "Install pywin32 + psutil on Windows to enable it.\n"
                      "The timer works fine either way."),
                text_color=COLOR_WARN, justify="left",
            ), anchor="w", pady=(0, 10))

        self.enforce_var = ctk.BooleanVar(value=self.config_obj.enforcement_enabled)
        self._mpack(ctk.CTkSwitch(frame, text="Block distracting apps during focus",
                      variable=self.enforce_var, progress_color=COLOR_ENFORCE_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=6)

        self.hard_var = ctk.BooleanVar(value=self.config_obj.hard_mode)
        self._mpack(ctk.CTkSwitch(frame, text="Hard mode (minimise windows, lockdown screen)",
                      variable=self.hard_var, progress_color=COLOR_DANGER,
                      command=self._save_from_widgets), anchor="w", pady=6)

        self.camera_var = ctk.BooleanVar(value=self.config_obj.camera_monitoring_enabled)
        self.camera_switch = ctk.CTkSwitch(
            frame, text="Strict Camera Monitoring (uses your webcam to catch phones)",
            variable=self.camera_var, progress_color=COLOR_DANGER,
            command=self._on_camera_switch_toggled,
        )
        self._mpack(self.camera_switch, anchor="w", pady=6)
        if not CAMERA_BACKEND_AVAILABLE:
            self.camera_switch.configure(state="disabled")
            self._mpack(ctk.CTkLabel(
                frame,
                text=("Strict Camera Monitoring needs opencv-python-headless "
                      "and its bundled model file, and isn't available right "
                      "now. Run: pip install opencv-python-headless"),
                text_color=COLOR_WARN, justify="left", wraplength=440,
            ), anchor="w", pady=(0, 6))

        self.classifier_var = ctk.BooleanVar(value=self.config_obj.use_classifier)
        self._mpack(ctk.CTkSwitch(frame, text="Use the learned model on unlisted apps",
                      variable=self.classifier_var, progress_color=COLOR_TIMER_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=6)

        self.record_var = ctk.BooleanVar(value=self.config_obj.record_observations)
        self._mpack(ctk.CTkSwitch(frame, text="Record windows for training (stays on this PC)",
                      variable=self.record_var, progress_color=COLOR_LOOK_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=6)

        # --- The Claude helper -------------------------------------------- #
        self._mpack(ctk.CTkLabel(frame, text=""), pady=2)
        self._mpack(ctk.CTkLabel(frame, text="Claude fallback", text_color=COLOR_CLAUDE_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")), anchor="w")
        self._mpack(ctk.CTkLabel(
            frame,
            text=("Off by default. When the local model is unsure, sends "
                  "just that one window's title to the Claude API instead "
                  "of guessing. Confident local judgements never leave "
                  "your machine."),
            text_color=COLOR_IDLE, justify="left", wraplength=440,
        ), anchor="w", pady=(0, 6))

        self.claude_var = ctk.BooleanVar(value=self.config_obj.claude_fallback_enabled)
        self._mpack(ctk.CTkSwitch(frame, text="Enable Claude fallback for ambiguous windows",
                      variable=self.claude_var, progress_color=COLOR_CLAUDE_ACCENT,
                      command=self._on_claude_toggle), anchor="w", pady=4)

        self.claude_status = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=11),
                                          text_color=COLOR_IDLE)
        self._mpack(self.claude_status, anchor="w", pady=(0, 4))
        self._refresh_claude_status()

        self._mpack(ctk.CTkLabel(frame, text="Blocked apps (one process name per line)",
                     text_color=COLOR_ENFORCE_ACCENT,
                     font=ctk.CTkFont(size=12, weight="bold")), anchor="w", pady=(16, 4))
        self.blocklist_box = ctk.CTkTextbox(frame, height=120, border_width=2,
                                            border_color=COLOR_ENFORCE_ACCENT)
        self.blocklist_box.insert("1.0", "\n".join(self.config_obj.blocklist))
        self._mpack(self.blocklist_box, fill="x")

        self._mpack(ctk.CTkLabel(frame, text="Always-allowed apps", text_color=COLOR_BREAK,
                     font=ctk.CTkFont(size=12, weight="bold")), anchor="w", pady=(16, 4))
        self.allowlist_box = ctk.CTkTextbox(frame, height=120, border_width=2,
                                            border_color=COLOR_BREAK)
        self.allowlist_box.insert("1.0", "\n".join(self.config_obj.allowlist))
        self._mpack(self.allowlist_box, fill="x")

        self._mpack(ctk.CTkButton(frame, text="Save lists",
                      command=self._save_lists), anchor="w", pady=14)

    # ------------------------------------------------------------------ #
    def _build_tasks_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._mpack(frame, fill="both", expand=True)

        add_row = ctk.CTkFrame(frame, fg_color="transparent")
        self._mpack(add_row, fill="x", pady=(0, 12))
        self.new_task_entry = ctk.CTkEntry(add_row, placeholder_text="Add a task...")
        self._mpack(self.new_task_entry, side="left", fill="x", expand=True, padx=(0, 8))
        self.new_task_entry.bind("<Return>", lambda e: self._on_add_task())
        self._mpack(ctk.CTkButton(add_row, text="Add", width=60, command=self._on_add_task), side="left")

        self.tasks_list_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._mpack(self.tasks_list_frame, fill="both", expand=True)

        self._render_tasks()

    def _on_add_task(self) -> None:
        name = self.new_task_entry.get().strip()
        if not name:
            return
        self.tasks.add(name)
        self.new_task_entry.delete(0, "end")
        self._render_tasks()
        self._refresh_current_task_picker()

    def _render_tasks(self) -> None:
        """Redraws the whole task list from scratch -- same pattern
        _render_activity() already uses for the Activity tab."""
        for child in self.tasks_list_frame.winfo_children():
            child.destroy()

        open_tasks = self.tasks.open()
        done_tasks = self.tasks.done()

        if not open_tasks and not done_tasks:
            self._mpack(ctk.CTkLabel(self.tasks_list_frame, text="No tasks yet.",
                         text_color=COLOR_IDLE), anchor="w", pady=20)
            return

        for task in open_tasks:
            self._render_one_task(task)

        if done_tasks:
            self._mpack(ctk.CTkLabel(
                self.tasks_list_frame, text=f"Done ({len(done_tasks)})",
                text_color=COLOR_IDLE, font=ctk.CTkFont(size=11, weight="bold"),
            ), anchor="w", pady=(14, 4))
            for task in done_tasks:
                self._render_one_task(task)

    def _render_one_task(self, task: Task) -> None:
        row = ctk.CTkFrame(self.tasks_list_frame, fg_color="transparent")
        self._mpack(row, fill="x", pady=4)

        header_row = ctk.CTkFrame(row, fg_color="transparent")
        self._mpack(header_row, fill="x")

        status_text = {"todo": "○", "in_progress": "◐", "done": "●"}[task.status.value]
        self._mpack(ctk.CTkLabel(header_row, text=status_text, width=20), side="left")
        self._mpack(ctk.CTkLabel(header_row, text=task.name, anchor="w"),
                     side="left", fill="x", expand=True)

        if task.status != TaskStatus.DONE:
            self._mpack(ctk.CTkButton(
                header_row, text="Done", width=50, height=24,
                command=lambda t=task: self._on_complete_task(t.id),
            ), side="right")

        for subtask in task.subtasks:
            sub_row = ctk.CTkFrame(row, fg_color="transparent")
            self._mpack(sub_row, fill="x", padx=(28, 0))
            var = ctk.BooleanVar(value=subtask.done)
            self._mpack(ctk.CTkCheckBox(
                sub_row, text=subtask.text, variable=var,
                command=lambda t=task, s=subtask: self._on_toggle_subtask(t.id, s.id),
            ), side="left", anchor="w", pady=2)

        add_sub_row = ctk.CTkFrame(row, fg_color="transparent")
        self._mpack(add_sub_row, fill="x", padx=(28, 0), pady=(2, 0))
        entry = ctk.CTkEntry(add_sub_row, placeholder_text="Add a step...", height=26)
        self._mpack(entry, side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e, t=task, ent=entry: self._on_add_subtask(t.id, ent))

    def _on_complete_task(self, task_id: str) -> None:
        self.tasks.complete(task_id)
        self._render_tasks()
        self._refresh_current_task_picker()

    def _on_toggle_subtask(self, task_id: str, subtask_id: str) -> None:
        self.tasks.toggle_subtask(task_id, subtask_id)
        self._render_tasks()

    def _on_add_subtask(self, task_id: str, entry) -> None:
        text = entry.get().strip()
        if not text:
            return
        self.tasks.add_subtask(task_id, text)
        self._render_tasks()

    # ------------------------------------------------------------------ #
    def _build_activity_tab(self, parent) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        self._mpack(header, fill="x", pady=(0, 6))

        self._mpack(ctk.CTkLabel(header, text="What you were on during focus blocks.",
                     text_color=COLOR_ACTIVITY_ACCENT,
                     font=ctk.CTkFont(size=12, weight="bold")), side="left")

        self.model_stats = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=11),
                                        text_color=COLOR_IDLE)
        self._mpack(self.model_stats, side="right")

        self.activity_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._mpack(self.activity_frame, fill="both", expand=True)

        self.activity_empty = ctk.CTkLabel(
            self.activity_frame,
            text="Nothing logged yet.\nStart a focus block and this fills in.",
            text_color=COLOR_IDLE, justify="left",
        )
        self._mpack(self.activity_empty, anchor="w", pady=20)
        self._update_model_stats()

    # ------------------------------------------------------------------ #
    def _build_help_tab(self, parent) -> None:
        """A full, plain-language "how do I use this thing" guide — written
        so a total beginner (or a five-year-old) can follow it without
        knowing anything about the app already."""
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._mpack(frame, fill="both", expand=True)

        def heading(text: str, color) -> None:
            self._mpack(ctk.CTkLabel(
                frame, text=text, text_color=color,
                font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
            ), anchor="w", pady=(16, 4), fill="x")

        def body(text: str) -> None:
            self._mpack(ctk.CTkLabel(
                frame, text=text, justify="left", wraplength=460, anchor="w",
            ), anchor="w", pady=3, fill="x")

        def bullet(text: str) -> None:
            body(f"•  {text}")

        self._mpack(ctk.CTkLabel(
            frame, text="How to use Lock In", text_color=COLOR_LOOK_ACCENT,
            font=ctk.CTkFont(size=15, weight="bold"),
        ), anchor="w", pady=(0, 6))
        body(
            "Lock In is a timer that helps you get work done by making "
            "distracting apps annoying to open while you're focusing. "
            "Here's everything it can do, and exactly how to turn each "
            "part on."
        )

        # --- Quick start ---------------------------------------------- #
        start_word = self._henshin_word()
        heading("1. The quick start", COLOR_LOOK_ACCENT)
        steps = [
            "Go to the Settings tab and set how many minutes a focus "
            "block and a break should last.",
            "Go to the Blocking tab. Type apps that distract you (like a "
            "game) under \"Blocked apps\", and apps you trust under "
            "\"Always-allowed apps\" — one app name per line.",
            f'Press "{start_word}" to begin a focus block.',
            "Stay off blocked apps while the timer runs. Opening one "
            "warns you first, then gets stricter the longer you stay on "
            "it.",
            "When the block ends, open the Activity tab and tell the app "
            "if it guessed right or wrong about any app — it gets "
            "smarter every time you correct it.",
        ]
        for i, step in enumerate(steps, start=1):
            body(f"{i}. {step}")

        # --- Look and voice --------------------------------------------- #
        heading("2. Change how it looks and talks", COLOR_CLAUDE_ACCENT)
        body(
            "Both of these are in the Settings tab, and change instantly "
            "— nothing to save."
        )
        bullet(
            "\"Wording\" is a switch. Off keeps every word plain and "
            "simple (\"Focus\", \"Start\"). On switches to fun Kamen "
            "Rider hero talk (\"Henshin\", \"Off Mission\")."
        )
        bullet(
            "Right below it, click the theme dropdown (it says "
            "\"Kamen Rider theme\" when Wording is on, or \"Color "
            "theme\" when it's off) and pick any of the 38 heroes. The "
            "whole app instantly changes color — this is purely for "
            "looks and never changes how blocking or timers work."
        )
        bullet(
            "Want zero Rider flavor at all? Flip \"Standard Mode\" on, "
            "right above the theme dropdown — it strips every color, "
            "glow, and gimmick down to a plain grey-and-blue look, no "
            "matter which Rider is picked underneath. It also switches "
            "Wording to plain Professional while it's on, even if you'd "
            "set Wording to Tokusatsu. Flip Standard Mode back off "
            "and your Rider — and your Wording setting — come right back, exactly as they were."
        )

        # --- Special Rider powers ---------------------------------------- #
        heading("3. Some heroes have a secret extra power", COLOR_CLAUDE_ACCENT)
        body(
            "14 of the 38 heroes do something extra during a focus block. "
            "To turn one on, just pick that hero's name from the theme "
            "dropdown in Settings — there's nothing else to click or "
            "flip on. As soon as you start your next focus block, its "
            "power shows up by itself."
        )

        heading("Heroes with a fancy progress bar", COLOR_TIMER_ACCENT)
        for name, what in [
            ("Kamen Rider (1971)", "the progress bar becomes a spinning windmill."),
            ("Skyrider", "the progress bar climbs upward instead of filling sideways."),
            ("Fourze", "the progress bar becomes tiny stars that light up one by one."),
            ("Build", "the progress bar becomes two bottles that fill up together."),
            ("Stronger", "a soft red glow slowly grows around the edge of the window."),
            ("Kiva", "the whole app gets a warm amber glow, like nighttime."),
            ("Agito", "the progress bar's color starts dim and slowly wakes up brighter."),
            ("Black", "dark mode text gets extra bold and easy to read."),
            ("Drive", "the progress bar starts slow, then speeds up and catches up near the end."),
            ("Saber", "the progress bar becomes a bookmark ribbon that fills in as you go."),
        ]:
            bullet(f"{name} — {what}")

        heading("Heroes with quick-click buttons", COLOR_TIMER_ACCENT)
        body(
            "Pick one of these in Settings, and a row of buttons appears "
            "right above \"Timer lengths\". Click a button and it fills "
            "in your focus/break minutes for you — no typing needed."
        )
        for name, what in [
            ("Kuuga", "4 buttons that set a quick, medium, long, or extra-long focus block in one click."),
            ("Super-1", "5 buttons, one for each kind of task (coding, hardware, admin, thinking, research)."),
            ("Gavv", "one switch that turns on lots of short, repeated 10-minute sprints instead of one long block. Flip it off to go back to your own numbers, which are never erased."),
        ]:
            bullet(f"{name} — {what}")

        heading("Heroes that change what happens", COLOR_TIMER_ACCENT)
        for name, what in [
            ("Kamen Rider X", "before a focus block starts, it asks you to type what you're working on. No rush — it waits until you type something."),
            ("Amazon", "during a focus block, the screen turns into a plain, draining green field, with zero warning time before a blocked app counts against you."),
            ("ZX", "the whole app turns black-and-white, and it hides itself the moment a focus block starts — no sounds or pop-ups either."),
            ("Gaim", "a padlock appears and the window always stays on top of everything else while you focus."),
            ("555", "if you get the full-screen lockdown screen, you can type 555 on your keyboard to leave it early instead of waiting it out."),
        ]:
            bullet(f"{name} — {what}")

        body(
            "Everything else — the timer, the blocking rules, and the "
            "learning — works exactly the same no matter which hero you "
            "pick. The hero is just for fun."
        )

        # --- Tier 4 ------------------------------------------------------ #
        heading("4. Eight more heroes have their own display trick", COLOR_ENFORCE_ACCENT)
        body(
            "A separate batch, nothing to do with the progress-bar heroes "
            "above: turn one of these Riders on and something about how "
            "the app looks, sounds, or behaves changes, on top of its "
            "own colors."
        )
        for name, what in [
            ("Black RX", "a switch that makes breaks always wait for you to press Start, instead of starting on their own."),
            ("Ryuki", "the whole window flips left-to-right during a break, then flips right back the moment focus starts again."),
            ("Kabuto", "the timer digits are hidden while you focus -- hover over where they'd be to peek at the real time."),
            ("Ex-Aid", "the timer switches to a pixel font, and its alert sound becomes an 8-bit jingle."),
            ("Hibiki", "a soft ambient sound plays in the background for as long as a focus block runs."),
            ("Zero-One", "the timer restyles itself as a row of dashboard cards instead of the usual centered digits."),
            ("Ghost", "the main window hides itself and a small floating clock stays on top of everything else -- click it to bring the full window back."),
            ("Zeztz", "keyboard shortcuts take over: Space starts or pauses, S skips, R resets, as long as this window has focus."),
        ]:
            bullet(f"{name} — {what}")
        body(
            "One more hero, Saber, actually lives in the progress-bar "
            "list above instead -- its bookmark-ribbon shape uses the "
            "exact same picture-drawing code Fourze and Build already do."
        )

        # --- Tier 5 -------------------------------------------------------- #
        heading("5. Some heroes read your own history", COLOR_ENFORCE_ACCENT)
        body(
            "Something new, separate from the display tricks above: pick "
            "one of these heroes and an extra tab appears next to Help, "
            "built from your own past focus blocks instead of just "
            "changing colors or sounds."
        )
        bullet(
            "V3 — an \"Hours\" tab appears, showing how long you've "
            "focused today plus a bar chart of the last 14 days. Every "
            "block counts toward it, finished or not."
        )
        bullet(
            "Den-O — a \"Timeline\" tab appears, listing one day's focus "
            "blocks at a time (earliest first), with buttons to flip a "
            "day forward or back. Each one shows its time, how long it "
            "ran, and which task it was for."
        )
        bullet(
            "Decade — an \"Analytics\" tab appears: a 30-day version of "
            "V3's bar chart, plus your top 10 tasks by total time spent."
        )
        body(
            "More heroes will get a tab like this over time -- these "
            "three are just the first."
        )

        # --- Strict Camera Monitoring ------------------------------------ #
        heading("6. Strict Camera Monitoring (optional)", COLOR_ENFORCE_ACCENT)
        body(
            "A separate extra, nothing to do with heroes: turn it on in "
            "the Blocking tab, and Lock In peeks at your webcam every "
            "few seconds during a focus block to check for a phone. If "
            "it sees one, you get warned the same way you would for a "
            "blocked app. It's off unless you turn it on. It only "
            "watches during an actual focus block -- the second a "
            "break starts, or you flip the switch back off, the camera "
            "turns off too. Watch for the little \"Camera monitoring "
            "active\" words under the timer: the camera is only ever "
            "on when those words are showing."
        )

    # ------------------------------------------------------------------ #
    def _build_settings_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._mpack(frame, fill="both", expand=True)

        self.spinners: dict[str, ctk.CTkEntry] = {}

        def add_number(key: str, label: str, value: int) -> None:
            """Makes one number field with a label next to it. We check the value when it's saved."""
            row = ctk.CTkFrame(frame, fg_color="transparent")
            self._mpack(row, fill="x", pady=4)
            self._mpack(ctk.CTkLabel(row, text=label, width=260, anchor="w"), side="left")
            entry = ctk.CTkEntry(row, width=70)
            entry.insert(0, str(value))
            self._mpack(entry, side="left")
            self.spinners[key] = entry

        self._mpack(ctk.CTkLabel(frame, text="Timer lengths", text_color=COLOR_TIMER_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")), anchor="w", pady=(0, 4))
        add_number("focus_minutes", "Focus length (min)", self.config_obj.focus_minutes)
        add_number("short_break_minutes", "Short break (min)", self.config_obj.short_break_minutes)
        add_number("long_break_minutes", "Long break (min)", self.config_obj.long_break_minutes)
        add_number("blocks_until_long_break", "Blocks before long break",
                   self.config_obj.blocks_until_long_break)

        self._mpack(ctk.CTkLabel(frame, text="Enforcement", text_color=COLOR_ENFORCE_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")), anchor="w", pady=(14, 4))
        add_number("grace_seconds", "Grace period on a blocked app (s)",
                   self.config_obj.grace_seconds)
        add_number("strike_interval_seconds", "Seconds between escalations",
                   self.config_obj.strike_interval_seconds)
        add_number("lockdown_seconds", "Lockdown length (s)", self.config_obj.lockdown_seconds)

        self._mpack(ctk.CTkLabel(frame, text="Behavior & notifications", text_color=COLOR_LOOK_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")), anchor="w", pady=(14, 4))

        self.autobreak_var = ctk.BooleanVar(value=self.config_obj.auto_start_breaks)
        self._mpack(ctk.CTkSwitch(frame, text="Auto-start breaks", variable=self.autobreak_var,
                      progress_color=COLOR_LOOK_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=4)

        self.autofocus_var = ctk.BooleanVar(value=self.config_obj.auto_start_focus)
        self._mpack(ctk.CTkSwitch(frame, text="Auto-start next focus block", variable=self.autofocus_var,
                      progress_color=COLOR_LOOK_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=4)

        self.sound_var = ctk.BooleanVar(value=self.config_obj.sound_enabled)
        self._mpack(ctk.CTkSwitch(frame, text="Sounds", variable=self.sound_var,
                      progress_color=COLOR_LOOK_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=4)

        self.toast_var = ctk.BooleanVar(value=self.config_obj.toast_enabled)
        self._mpack(ctk.CTkSwitch(frame, text="Desktop notifications", variable=self.toast_var,
                      progress_color=COLOR_LOOK_ACCENT,
                      command=self._save_from_widgets), anchor="w", pady=4)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        self._mpack(row, fill="x", pady=(10, 4))
        self._mpack(ctk.CTkLabel(row, text="Appearance", width=260, anchor="w"), side="left")
        self.appearance_menu = ctk.CTkOptionMenu(
            row, values=["dark", "light", "system"], width=110,
            fg_color=COLOR_LOOK_ACCENT, button_color=COLOR_LOOK_ACCENT,
            command=self._on_appearance_change,
        )
        self.appearance_menu.set(self.config_obj.appearance)
        self._mpack(self.appearance_menu, side="left")

        self._mpack(ctk.CTkLabel(frame, text="Standard Mode", text_color=COLOR_LOOK_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")), anchor="w", pady=(14, 4))
        self._mpack(ctk.CTkLabel(
            frame,
            text=("Strips every Rider's color, art, and gimmick for a plain, "
                  "fast, distraction-free look, and switches Wording to "
                  "plain Professional while it's on. Your Rider pick and "
                  "Wording setting below are remembered and come right "
                  "back the moment you turn this back off."),
            text_color=COLOR_IDLE, justify="left", wraplength=440,
        ), anchor="w", pady=(0, 6))
        self.standard_mode_switch = ctk.CTkSwitch(
            frame, text="Standard Mode (plain, no Rider flavor)",
            progress_color=COLOR_LOOK_ACCENT,
            command=self._on_standard_mode_toggled,
        )
        if self.config_obj.standard_mode:
            self.standard_mode_switch.select()
        else:
            self.standard_mode_switch.deselect()
        self._mpack(self.standard_mode_switch, anchor="w", pady=(0, 10))

        rider_row = ctk.CTkFrame(frame, fg_color="transparent")
        self._mpack(rider_row, fill="x", pady=(10, 4))
        self.rider_row_label = ctk.CTkLabel(
            rider_row, text=self._rider_row_label_text(), width=260, anchor="w",
        )
        self._mpack(self.rider_row_label, side="left")
        self.rider_menu = ctk.CTkOptionMenu(
            rider_row, values=list(RIDER_THEMES.keys()), width=220,
            command=self._on_rider_theme_change,
        )
        self.rider_menu.set(self.config_obj.rider_theme)
        self._mpack(self.rider_menu, side="left")

        # Kuuga/Super-1's preset buttons and Gavv's toggle only show up
        # for their own Rider -- this whole tab already gets rebuilt
        # from scratch every time you pick a different Rider (see
        # _rebuild_tabs), so there's nothing to hide/show here, we just
        # build whichever ONE row (if any) actually matches right now.
        if not self.config_obj.standard_mode:
            if self.config_obj.rider_theme == "Kamen Rider Kuuga (2000)":
                self._build_timer_preset_row(
                    frame, KUUGA_PRESETS,
                    "Kuuga presets" if self._is_tokusatsu() else "Interval presets",
                )
            elif self.config_obj.rider_theme == "Kamen Rider Super-1 (1980)":
                self._build_timer_preset_row(
                    frame, SUPER1_PRESETS,
                    "Super-1's Five Hands" if self._is_tokusatsu() else "Task-type presets",
                )
            elif self.config_obj.rider_theme == "Kamen Rider Gavv (2024)":
                self._build_gavv_toggle_row(frame)
            elif self.config_obj.rider_theme == "Kamen Rider Black RX (1988)":
                self._build_blackrx_toggle_row(frame)

        terminology_row = ctk.CTkFrame(frame, fg_color="transparent")
        self._mpack(terminology_row, fill="x", pady=(10, 4))
        self._mpack(ctk.CTkLabel(terminology_row, text="Wording", width=140, anchor="w"), side="left")

        # A switch you can see the state of at a glance: "Professional"
        # printed in the same color the switch turns when it's off,
        # "Tokusatsu" printed in the color it turns when it's on.
        self._mpack(ctk.CTkLabel(terminology_row, text="Professional", font=ctk.CTkFont(size=12),
                     text_color=COLOR_LOOK_ACCENT), side="left", padx=(0, 8))
        self.terminology_switch = ctk.CTkSwitch(
            terminology_row, text="",
            fg_color=COLOR_LOOK_ACCENT,          # the switch's color when it's OFF (Professional)
            progress_color=COLOR_ENFORCE_ACCENT,  # the switch's color when it's ON (Tokusatsu)
            command=self._on_terminology_switch_toggled,
        )
        # Deliberately reads the SAVED value, not _is_tokusatsu(): this
        # switch needs to show its own real position, not what's currently
        # displayed -- while Standard Mode is on, _is_tokusatsu() always
        # says "professional" here, which would show the switch as off
        # even when Tokusatsu is what's actually saved.
        if self.config_obj.terminology == "tokusatsu":
            self.terminology_switch.select()
        else:
            self.terminology_switch.deselect()
        self._mpack(self.terminology_switch, side="left", padx=8)
        self._mpack(ctk.CTkLabel(terminology_row, text="Tokusatsu", font=ctk.CTkFont(size=12),
                     text_color=COLOR_ENFORCE_ACCENT), side="left")

        self._mpack(ctk.CTkButton(frame, text="Save settings",
                      command=self._save_settings), anchor="w", pady=14)

        self._mpack(ctk.CTkButton(frame, text="Rebuild model from labels", fg_color="transparent",
                      border_width=1, text_color=COLOR_DANGER,
                      command=self._reset_model), anchor="w")

    # ================================================================== #
    # The heartbeat — keeps everything moving
    # ================================================================== #
    def _pump(self) -> None:
        """
        The one loop that runs the whole app: move the timer forward, check
        the waiting lines for new info, then redraw the screen.

        This schedules itself again each time using `after`, so it never
        gets stuck waiting on anything.
        """
        try:
            for event in self.session.tick():
                if event is Event.PHASE_ENDED:
                    self._on_phase_ended()
                elif event is Event.PHASE_STARTED:
                    self._on_phase_started()

            self._drain_window_queue()
            self._drain_camera_queue()
            self._drain_claude_queue()
            self._drain_banner_queue()
            self._refresh_timer_widgets()
        finally:
            # This "finally" makes sure we always schedule the next loop,
            # even if something above broke — otherwise one bad moment
            # would freeze the whole app forever.
            self.after(self.UI_TICK_MS, self._pump)

    def _drain_window_queue(self) -> None:
        """Look at every window the background checker noticed, and judge each one."""
        latest: Optional[WindowInfo] = None
        while True:
            try:
                latest = self._window_queue.get_nowait()
            except queue.Empty:
                break

            if self.session.phase is not Phase.FOCUS or not self.session.is_running:
                continue
            if not self.config_obj.enforcement_enabled:
                continue

            # Never block someone just for looking at Lock In itself.
            if "lock in" in (latest.title or "").lower():
                continue

            verdict = judge(latest, self.config_obj, self.model, self.claude)
            action = self.enforcer.update(verdict, latest)

            # If our own model isn't sure, and we don't already have a
            # remembered Claude answer, quietly ask Claude in the background.
            # For right now, we just use the local model's "not sure" answer;
            # the real answer will be ready in time for the next check —
            # usually just a second later, since you're probably still on
            # the same window.
            if (self.config_obj.claude_fallback_enabled
                    and verdict.reason is Reason.CLASSIFIER
                    and verdict.confidence < self.config_obj.classifier_threshold):
                self.claude.judge_async(latest.text, self._claude_queue.put)

            # Write down EVERY window, not just the ones we blocked. The
            # Activity tab can only ever show you the times we wrongly
            # flagged something — this is what lets train.py also show you
            # the distracting apps that slipped past unnoticed.
            if self.config_obj.record_observations:
                predicted, confidence = self.model.predict(latest.text)
                self.observations.record(
                    text=latest.text,
                    process=latest.process_name,
                    title=latest.title,
                    predicted=predicted,
                    confidence=confidence,
                    blocked=verdict.blocked,
                )

            # Log every window here, not just blocked ones — otherwise the
            # Activity tab only ever shows the rare flagged window, which
            # looks like it's "missing" most of what you actually did.
            self._log_activity(latest, verdict)
            if action is not Action.NONE:
                self._perform(action, latest)

        if latest is not None:
            self._update_watch_label(latest)

    def _drain_camera_queue(self) -> None:
        """Look at every phone-sighting sample PhoneWatcher noticed, and act on it."""
        while True:
            try:
                phone_seen = self._camera_queue.get_nowait()
            except queue.Empty:
                return

            # PhoneWatcher only ever samples while resumed, but a sample
            # can still be sitting in the queue from the instant before
            # a pause/toggle-off took effect -- skip it rather than act
            # on a stale reading, same guard _drain_window_queue already
            # applies to window samples.
            if self.session.phase is not Phase.FOCUS or not self.session.is_running:
                continue
            if not self.config_obj.camera_monitoring_enabled:
                continue
            if not self.config_obj.enforcement_enabled:
                continue

            verdict = Verdict(phone_seen, Reason.CAMERA, 1.0)
            action = self.camera_enforcer.update(phone_seen)
            if phone_seen:
                self._log_activity(CameraEnforcer.PHONE_WINDOW, verdict)
            if action is not Action.NONE:
                self._perform(action, CameraEnforcer.PHONE_WINDOW, seconds=self.camera_enforcer.seconds_on_phone)

    def _drain_claude_queue(self) -> None:
        """
        Claude's answers show up here, sent over from a background thread.

        Every real, fresh answer (not a repeated one, and not an error) also
        gets added to the training data — that's the whole point of asking
        Claude: over time, the local model learns what Claude knows and
        needs to ask less and less.
        """
        while True:
            try:
                text, verdict = self._claude_queue.get_nowait()
            except queue.Empty:
                return
            if verdict.source != "claude":
                continue        # errors and "couldn't ask" results teach us nothing
            self.observations.record(text=text, predicted=verdict.label,
                                     confidence=verdict.confidence)
            self.observations.label_by_text(text, verdict.label)
            self.observations.save()

    def _drain_banner_queue(self) -> None:
        """Notifier can be called from any thread; its banner messages land here."""
        while True:
            try:
                title, body, urgency = self._banner_queue.get_nowait()
            except queue.Empty:
                return
            self._show_banner(f"{title} — {body}", urgency)

    # ================================================================== #
    # Actually doing something about a blocked window
    # ================================================================== #
    def _perform(self, action: Action, window: WindowInfo, seconds: Optional[float] = None) -> None:
        """Turn a step on the ladder into something you actually see or hear."""
        if seconds is None:
            seconds = self.enforcer.seconds_on_blocked_app
        title, body = message_for(
            action,
            era=self.current_era,
            terminology=self._effective_terminology(),
            app=window.display,
            remaining=self.session.format_remaining(),
            seconds=seconds,
            lockdown=self.config_obj.lockdown_seconds,
        )

        if action is Action.WARN:
            self.notifier.notify(title, body, urgency="normal")

        elif action is Action.NAG:
            self.notifier.notify(title, body, urgency="high")

        elif action is Action.MINIMIZE:
            self.notifier.notify(title, body, urgency="high")
            if window.handle is not None:
                minimize_window(window.handle)
            # Bring our own window forward, so the timer is what you see now.
            self.after(120, self._raise_self)

        elif action is Action.LOCKDOWN:
            self.notifier.notify(title, body, urgency="high")
            if window.handle is not None:
                minimize_window(window.handle)
            self._show_lockdown()

    def _raise_self(self) -> None:
        """
        Bring the timer window to the front, without keeping it pinned there
        forever.

        Quickly turning "always on top" on and then back off is the reliable
        trick to actually raise a window — just asking nicely often doesn't
        work, because Windows has its own rules about that.
        """
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(400, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def _show_lockdown(self) -> None:
        """
        Covers the whole screen for `lockdown_seconds`.

        There's always a visible way out ("End session"), on purpose. An app
        that can trap you is an app you'd delete the first time it messes up
        at a moment that actually mattered.
        """
        if self._lockdown_window is not None:
            return

        overlay = ctk.CTkToplevel(self)
        overlay.attributes("-topmost", True)
        try:
            overlay.attributes("-fullscreen", True)
        except Exception:
            overlay.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        overlay.configure(fg_color="#121417")
        overlay.protocol("WM_DELETE_WINDOW", lambda: None)   # the X button on this window does nothing
        self._lockdown_window = overlay

        self._mpack(
            ctk.CTkLabel(overlay, text=lockdown_label_for(self.current_era, self._effective_terminology()),
                         font=ctk.CTkFont(size=54, weight="bold"),
                         text_color=self.color_lockdown_text),
            pady=(220, 10),
        )

        remaining_word = "mission" if self._is_tokusatsu() else "session"
        self._mpack(
            ctk.CTkLabel(overlay, text=f"{self.session.format_remaining()} left in this {remaining_word}",
                         font=ctk.CTkFont(size=20), text_color="#9aa4b2")
        )

        countdown = ctk.CTkLabel(overlay, text="", font=ctk.CTkFont(size=16),
                                 text_color="#6b7480")
        self._mpack(countdown, pady=26)

        if self.current_tier3_effect == "code_unlock":
            code_entry = ctk.CTkEntry(overlay, width=140, justify="center",
                                       font=ctk.CTkFont(size=16))
            self._mpack(code_entry, pady=(4, 4))
            code_hint = ctk.CTkLabel(overlay, text="Enter code to unlock early",
                                      font=ctk.CTkFont(size=11), text_color="#6b7480")
            self._mpack(code_hint, pady=(0, 12))

            def check_code(event=None) -> None:
                if code_entry.get().strip() == "555":
                    self._close_lockdown()
                else:
                    code_entry.delete(0, "end")
                    code_hint.configure(text="Incorrect code", text_color=COLOR_DANGER)

            code_entry.bind("<Return>", check_code)

        end_button_text = "Abort Mission" if self._is_tokusatsu() else "End Session"
        self._mpack(
            ctk.CTkButton(overlay, text=end_button_text, width=200,
                          fg_color="transparent", border_width=1,
                          text_color="#6b7480", hover_color="#1d2026",
                          command=self._end_session_from_lockdown)
        )

        remaining = {"value": self.config_obj.lockdown_seconds}

        def step() -> None:
            """Count down the lockdown screen's own timer, then close itself."""
            if self._lockdown_window is None:
                return
            if remaining["value"] <= 0:
                self._close_lockdown()
                return
            countdown.configure(text=f"unlocks in {remaining['value']}s")
            remaining["value"] -= 1
            overlay.after(1000, step)

        step()
        try:
            overlay.focus_force()
        except Exception:
            pass

    def _close_lockdown(self) -> None:
        if self._lockdown_window is not None:
            try:
                self._lockdown_window.destroy()
            except Exception:
                pass
            self._lockdown_window = None

    def _end_session_from_lockdown(self) -> None:
        """The way out: stops the whole session, not just closes the lockdown screen."""
        self._close_lockdown()
        self._on_reset()

    def _show_ghost_widget(self) -> None:
        if self._ghost_widget is not None:
            return
        widget = ctk.CTkToplevel(self)
        widget.overrideredirect(True)
        widget.attributes("-topmost", True)
        widget.configure(fg_color="#121417")
        widget.geometry("140x50+80+80")

        self._ghost_time_label = ctk.CTkLabel(
            widget, text=self.session.format_remaining(),
            font=ctk.CTkFont(family=DISPLAY_FONT, size=22, weight="bold"),
            text_color=self.color_focus_text,
        )
        self._ghost_time_label.pack(pady=(6, 2))

        self._ghost_progress = ctk.CTkProgressBar(widget, height=4, corner_radius=2)
        self._ghost_progress.set(self.session.progress)
        self._ghost_progress.pack(fill="x", padx=8, pady=(0, 6))

        def restore(event=None) -> None:
            self._hide_ghost_widget()

        def start_drag(event) -> None:
            widget._drag_start = (event.x, event.y)
            widget._dragged = False

        def do_drag(event) -> None:
            dx = event.x - widget._drag_start[0]
            dy = event.y - widget._drag_start[1]
            if abs(dx) > 3 or abs(dy) > 3:
                widget._dragged = True
            x = widget.winfo_x() + dx
            y = widget.winfo_y() + dy
            widget.geometry(f"+{x}+{y}")

        def end_click_or_drag(event) -> None:
            if not getattr(widget, "_dragged", False):
                restore()

        widget.bind("<ButtonPress-1>", start_drag)
        widget.bind("<B1-Motion>", do_drag)
        widget.bind("<ButtonRelease-1>", end_click_or_drag)
        self._ghost_time_label.bind("<ButtonPress-1>", start_drag)
        self._ghost_time_label.bind("<B1-Motion>", do_drag)
        self._ghost_time_label.bind("<ButtonRelease-1>", end_click_or_drag)

        self._ghost_widget = widget
        self.iconify()

    def _hide_ghost_widget(self) -> None:
        # This is called unconditionally on every phase transition, for
        # every Rider -- not just Ghost. Only deiconify when this call is
        # actually undoing a ghost-widget hide; otherwise it would force
        # open a window YOU minimized by hand, for any non-Ghost Rider.
        had_widget = self._ghost_widget is not None
        if self._ghost_widget is not None:
            try:
                self._ghost_widget.destroy()
            except Exception:
                pass
            self._ghost_widget = None
        if had_widget:
            self.deiconify()

    def _refresh_ghost_widget(self) -> None:
        if self._ghost_widget is None:
            return
        self._ghost_time_label.configure(text=self.session.format_remaining())
        self._ghost_progress.set(self.session.progress)

    # ================================================================== #
    # Reacting to the timer changing phases
    # ================================================================== #
    def _on_phase_started(self) -> None:
        """Turn on watching for FOCUS, turn it off for everything else."""
        self.enforcer.reset()
        self.camera_enforcer.reset()
        phase = self.session.phase

        if phase is Phase.FOCUS:
            self._focus_block_start = datetime.now()
            self._focus_block_planned_seconds = self.session.total_seconds

        if phase is Phase.FOCUS and self.current_tier3_effect == "stealth_mute":
            # Ninja Stealth: get out of the way the moment focus starts.
            # iconify() is Tkinter's own cross-platform minimize -- no
            # need for the OS-specific minimize_window() helper, since
            # that one is built for minimizing OTHER apps' windows, not
            # this app's own.
            self.iconify()

        if self.current_tier3_effect == "lock_overlay":
            # Locks the window in front of everything else for the
            # whole block, then lets go the moment it's not FOCUS
            # anymore -- never a permanent always-on-top, just for the
            # duration of the lock.
            self.attributes("-topmost", phase is Phase.FOCUS)

        if self.current_tier3_effect == "zero_ui":
            self._sync_zero_ui_visibility()
            self.config_obj.zero_grace_mode = phase is Phase.FOCUS

        if phase is Phase.FOCUS and self.session.is_running:
            self.monitor.resume()
            self.ambient.start_if_applicable()
            if self.config_obj.camera_monitoring_enabled:
                self.camera_watcher.resume()
            if self.current_tier4_effect == "ghost_widget":
                self._show_ghost_widget()
        else:
            self.monitor.pause()
            self.camera_watcher.pause()
            self._close_lockdown()
            self._hide_ghost_widget()
            # _on_skip() only ever dispatches PHASE_STARTED (it never
            # calls _on_phase_ended(), which is where ambient.stop()
            # normally lives) -- this branch is what's supposed to
            # compensate for that, same as the two lines above it.
            self.ambient.stop()

        if phase is not Phase.IDLE:
            label = label_for(phase, self._effective_terminology())
            self.notifier.phase_chime(label)
            if phase.is_break:
                self._show_banner(
                    f"{label} — {self.session.format_remaining()} remaining.",
                    "low",
                )
            elif self._is_tokusatsu():
                self._show_banner("Henshin initiated. Blocking is active.", "low")
            else:
                self._show_banner("Focus session started. Blocking is active.", "low")

        self._sync_mirror_layout()
        self._sync_mirror_divider()

    def _log_focus_block_if_any(self, completed: bool) -> None:
        """Writes one history entry for the focus block currently being
        timed, if there is one -- called from _on_phase_ended (natural
        completion), _on_skip, and _on_reset (both cut it short).
        A no-op when no focus block is in progress (e.g. a break just
        ended, or Reset was pressed while idle)."""
        if self._focus_block_start is None:
            return
        now = datetime.now()
        if completed:
            duration = self._focus_block_planned_seconds
        else:
            elapsed = self._focus_block_planned_seconds - self.session.remaining_seconds
            duration = max(0, elapsed)
            if duration == 0:
                # Entering FOCUS and then immediately skipping/resetting
                # it without ever pressing Start isn't a session you
                # worked -- nothing counted down. Logging it would put a
                # junk zero-second row into the aggregates every
                # history-reading feature downstream starts from. Still
                # clear the snapshot so the next FOCUS entry starts clean.
                self._focus_block_start = None
                return
        try:
            self.history.record(SessionRecord(
                start=self._focus_block_start.isoformat(timespec="seconds"),
                end=now.isoformat(timespec="seconds"),
                duration_seconds=duration,
                task_id=self.current_task_id,
                completed=completed,
            ))
        except OSError:
            # A disk failure (full disk, permissions, AV lock, cloud-sync
            # conflict) must never propagate out of here: callers run
            # this immediately before critical cleanup (monitor/ambient/
            # camera teardown, session.reset()/skip()), and a raise would
            # leave the app stranded mid-transition. Only OSError is
            # swallowed -- a genuine bug still surfaces normally.
            pass
        self._focus_block_start = None

    def _on_phase_ended(self) -> None:
        self.monitor.pause()
        self.ambient.stop()
        self.camera_watcher.pause()
        self._close_lockdown()
        self._hide_ghost_widget()
        if self.current_tier3_effect == "lock_overlay":
            self.attributes("-topmost", False)
        if self.current_tier3_effect == "zero_ui":
            self._sync_zero_ui_visibility()
            self.config_obj.zero_grace_mode = False
        # Saving right when a phase ends is a natural, safe checkpoint — if
        # the app were to crash, you'd only lose at most one block's worth
        # of training data, never more. Writing history here too (rather
        # than as the first line of this method) keeps every disk write in
        # this method at the END, after the monitor/ambient/camera/lockdown
        # teardown above has already run -- so a failing write can never
        # strand the app mid-transition. Nothing above touches the two
        # values this log reads (_focus_block_start / _planned_seconds).
        self.observations.save()
        self._log_focus_block_if_any(completed=True)

        # V3's Hours tab (and any later Tier 5 Rider reading history)
        # should show this block the moment it's over, not wait for the
        # next Rider change. A no-op for every Rider without a Tier 5 tab.
        if self.current_tier5_effect != "none":
            self._build_tier5_tab()

        self._sync_mirror_layout()
        self._sync_mirror_divider()

    # ================================================================== #
    # What happens when you click a button
    # ================================================================== #
    def _on_toggle(self) -> None:
        # X's gimmick: starting fresh (not resuming from pause) needs a
        # goal typed in first. Resuming never shows the gate again --
        # only self.session.phase is Phase.IDLE catches "about to
        # start a brand new block."
        if self.current_tier3_effect == "goal_gate" and self.session.phase is Phase.IDLE:
            self._show_goal_gate()
            return
        self._do_toggle()

    def _do_toggle(self) -> None:
        was_running = self.session.is_running
        for event in self.session.toggle():
            if event is Event.PHASE_STARTED:
                self._on_phase_started()

        # Resuming a phase that was already started doesn't send an event,
        # so we check and update things ourselves here.
        if not was_running and self.session.is_running:
            if self.session.phase is Phase.FOCUS:
                # `Config.auto_start_focus` defaults to False, so a FOCUS
                # phase is normally ENTERED (which is when
                # _on_phase_started() takes its snapshot) and then just
                # sits paused until you actually press Start -- possibly
                # minutes later. History buckets by `start`, so re-snapshot
                # it here, at the real "began working" moment.
                # Only when nothing has counted down yet: remaining ==
                # planned means this block has never actually run, so this
                # is the first Start, not a resume from a mid-block pause
                # (whose original start time must be preserved).
                if self.session.remaining_seconds >= self._focus_block_planned_seconds:
                    self._focus_block_start = datetime.now()
                if self.current_task_id is not None:
                    try:
                        self.tasks.set_status(self.current_task_id, TaskStatus.IN_PROGRESS)
                    except OSError:
                        # set_status() writes tasks.json immediately. A disk
                        # failure there must not stop the monitor/camera
                        # from being resumed below, which would leave the
                        # app running a focus block with nothing watching.
                        pass
                    self._render_tasks()
                self.monitor.resume()
                if self.config_obj.camera_monitoring_enabled:
                    self.camera_watcher.resume()
        else:
            self.monitor.pause()
            self.camera_watcher.pause()
            self.ambient.stop()

        self._refresh_timer_widgets()

    def _show_goal_gate(self) -> None:
        """
        X's gimmick: before you can even start, you have to say what
        you're working on. Mirrors _show_lockdown()'s full-screen
        overlay trick, but this one asks a question instead of
        enforcing a wait -- no countdown, no timeout, just a text box.
        """
        overlay = ctk.CTkToplevel(self)
        overlay.attributes("-topmost", True)
        try:
            overlay.attributes("-fullscreen", True)
        except Exception:
            overlay.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        overlay.configure(fg_color="#121417")
        overlay.protocol("WM_DELETE_WINDOW", lambda: None)

        title = "DEEP SETUP" if self._is_tokusatsu() else "Set your goal"
        self._mpack(
            ctk.CTkLabel(overlay, text=title, font=ctk.CTkFont(size=40, weight="bold"),
                         text_color=self.color_lockdown_text),
            pady=(220, 20),
        )
        self._mpack(
            ctk.CTkLabel(overlay, text="What are you working on this block?",
                         font=ctk.CTkFont(size=16), text_color="#9aa4b2"),
            pady=(0, 16),
        )

        entry = ctk.CTkEntry(overlay, width=420, height=44, font=ctk.CTkFont(size=15))
        self._mpack(entry, pady=(0, 8))
        entry.focus_set()

        hint = ctk.CTkLabel(overlay, text="", font=ctk.CTkFont(size=12), text_color=COLOR_DANGER)
        self._mpack(hint)

        def submit(event=None) -> None:
            text = entry.get().strip()
            if not text:
                hint.configure(text="Type something before you begin.")
                return
            self.current_goal_text = text
            overlay.destroy()
            self._do_toggle()

        entry.bind("<Return>", submit)
        begin_word = "Begin" if self._is_tokusatsu() else "Start"
        self._mpack(ctk.CTkButton(overlay, text=begin_word, width=200, command=submit), pady=20)

    def _on_skip(self) -> None:
        was_focus = self.session.phase is Phase.FOCUS
        if was_focus:
            self._log_focus_block_if_any(completed=False)
        for event in self.session.skip():
            if event is Event.PHASE_STARTED:
                self._on_phase_started()
        self._refresh_timer_widgets()

    def _on_reset(self) -> None:
        self._log_focus_block_if_any(completed=False)
        self.session.reset()
        self.enforcer.reset()
        self.camera_enforcer.reset()
        self.monitor.pause()
        self.ambient.stop()
        self.camera_watcher.pause()
        self._close_lockdown()
        self._hide_ghost_widget()
        self._refresh_timer_widgets()

    def _zeztz_hotkeys_active(self) -> bool:
        """False while hotkeys aren't Zeztz's current gimmick, OR while you're
        typing into any text field -- otherwise 's' or 'r' would both type the
        letter AND trigger Skip/Reset at the same time."""
        if self.current_tier4_effect != "hotkeys":
            return False
        focused = self.focus_get()
        if focused is not None and focused.winfo_class() in ("Entry", "Text"):
            return False
        return True

    def _on_zeztz_space(self, event=None) -> None:
        if self._zeztz_hotkeys_active():
            self._on_toggle()

    def _on_zeztz_skip(self, event=None) -> None:
        if self._zeztz_hotkeys_active():
            self._on_skip()

    def _on_zeztz_reset(self, event=None) -> None:
        if self._zeztz_hotkeys_active():
            self._on_reset()

    def _on_appearance_change(self, value: str) -> None:
        ctk.set_appearance_mode(value)
        self.config_obj.appearance = value
        self.config_obj.save()
        # Some widgets (the scrolling tab areas and text boxes) don't repaint
        # themselves right away when you switch between dark and light — they
        # can be left showing old, wrong-colored backgrounds with new text
        # colors on top, which is very hard to read. Rebuilding the tabs from
        # scratch forces everything to redraw with the right colors.
        self._rebuild_tabs()

    def _on_rider_theme_change(self, value: str) -> None:
        """Called when you pick a new Kamen Rider in Settings."""
        self.config_obj.rider_theme = value
        self.config_obj.save()
        self._apply_rider_theme()
        self.driver_label.configure(text=self._driver_label_text(), text_color=self.color_driver_text)
        self.start_button.configure(fg_color=self.color_rider_accent, text_color=self.color_button_text)
        self.header_frame.configure(fg_color=self.color_surface)
        self._sync_progress_widget_visibility()
        self._refresh_timer_widgets()
        # Rebuilding the tabs is how the tab panels themselves (and the
        # selected-tab highlight) pick up the new surface color and
        # accent — same trick already used when you switch appearance
        # mode, just triggered by a Rider change instead.
        self._rebuild_tabs()
        # Switching AWAY from Amazon mid-focus-block would otherwise
        # leave the header stuck hidden under the new Rider (nothing
        # else re-shows it); switching TO Amazon mid-focus-block should
        # hide it right away instead of waiting for the next tick. Safe
        # to call for every other Rider too -- it's a no-op unless
        # current_tier3_effect is "zero_ui".
        self._sync_zero_ui_visibility()
        # Same reconciliation, for the two pieces of Tier 4 state that
        # live outside _apply_rider_theme()'s reach: switching away from
        # Hibiki mid-focus would otherwise leave its ambient loop playing
        # under the new Rider, and switching to/from Ryuki mid-break (or
        # while mirrored) would leave the header half-mirrored -- tabs
        # rebuilt against the new state, but the background/divider
        # still in the old orientation until the next phase transition.
        self.ambient.stop()
        if self.session.phase is Phase.FOCUS and self.session.is_running:
            self.ambient.start_if_applicable()
        self._sync_mirror_layout()
        self._sync_mirror_divider()

    def _on_standard_mode_toggled(self) -> None:
        """Called when you flip the Standard Mode switch in Settings."""
        self.config_obj.standard_mode = self.standard_mode_switch.get()
        self.config_obj.save()
        self._apply_rider_theme()
        self.driver_label.configure(text=self._driver_label_text(), text_color=self.color_driver_text)
        self.start_button.configure(
            text=self._henshin_word(), fg_color=self.color_rider_accent,
            text_color=self.color_button_text,
        )
        self.header_frame.configure(fg_color=self.color_surface)
        self._sync_progress_widget_visibility()
        self._refresh_timer_widgets()
        # Same reason _on_rider_theme_change() rebuilds the tabs: the tab
        # panel colors, and here also the Tier 2 preset row, need to pick
        # up the change, and the whole Settings tab already gets rebuilt
        # from scratch on every relevant change.
        self._rebuild_tabs()
        # Toggling Standard Mode flips current_tier3_effect too (see
        # _apply_rider_theme): turning it ON masks Amazon's zero-UI effect,
        # turning it OFF restores it. Same as _on_rider_theme_change(),
        # this needs to take effect immediately mid-focus-block instead of
        # waiting for the next tick. Safe to call for every Rider -- it's
        # a no-op unless current_tier3_effect is "zero_ui".
        self._sync_zero_ui_visibility()
        # Two more pieces of Tier 3 state live outside _apply_rider_theme()'s
        # reach and normally only get set/cleared at a phase transition
        # (_on_phase_started()/_on_phase_ended()): Gaim's always-on-top lock
        # and Amazon's zero-grace enforcement. If Standard Mode gets flipped
        # mid-focus-block, current_tier3_effect just changed out from under
        # both of them, so re-derive each from the current effect and phase
        # right now instead of leaving them stuck until the next transition.
        self.attributes("-topmost", self.current_tier3_effect == "lock_overlay" and self.session.phase is Phase.FOCUS)
        self.config_obj.zero_grace_mode = (
            self.current_tier3_effect == "zero_ui" and self.session.phase is Phase.FOCUS
        )
        self.config_obj.save()
        # Same reconciliation as _on_rider_theme_change(): Standard Mode
        # silences Hibiki's ambient loop and Ryuki's mirror alike (via the
        # theme-substitution intercept inside _apply_rider_theme()), but
        # neither the ambient loop already playing nor the header/divider's
        # current orientation update on their own when that intercept
        # flips mid-block -- re-derive both right now instead of leaving
        # them stuck until the next phase transition.
        self.ambient.stop()
        if self.session.phase is Phase.FOCUS and self.session.is_running:
            self.ambient.start_if_applicable()
        self._sync_mirror_layout()
        self._sync_mirror_divider()

    def _on_terminology_switch_toggled(self) -> None:
        """Called when you click the Wording switch itself."""
        value = "Tokusatsu" if self.terminology_switch.get() else "Professional"
        self._on_terminology_change(value)

    def _on_terminology_change(self, value: str) -> None:
        """
        Called when you flip the Wording switch between Professional and
        Tokusatsu in Settings.

        This changes words, not colors — but the words show up in a lot
        of places at once (the button, the settings labels, the timer's
        own phase name), so the easiest way to make sure every single
        one updates together is the same trick used for a Rider change:
        rebuild everything from scratch. The Rider name label itself
        doesn't have any wording-dependent text anymore, so it's not
        touched here.
        """
        self.config_obj.terminology = value.lower()
        self.config_obj.save()
        self.start_button.configure(text=self._henshin_word())
        self._refresh_timer_widgets()
        self._rebuild_tabs()

    def _rebuild_tabs(self) -> None:
        """Throws away and redraws the tabs, keeping whichever one was open."""
        # Zero-One's dashboard cards read colors (like the Rider accent)
        # that a theme/appearance change may have just altered, but
        # their frame is never destroyed and rebuilt on its own --
        # clearing this flag forces _refresh_timer_widgets() to rebuild
        # their contents fresh instead of leaving them stale.
        self._dashboard_built = False
        try:
            current = self.tabs.get()
        except Exception:
            current = "Blocking"
        self.tabs.destroy()
        self._build_tabs()
        self._render_activity()
        try:
            self.tabs.set(current)
        except Exception:
            pass
        # Force every freshly-built widget to actually paint right now,
        # instead of waiting for its own natural turn. Skipping this can
        # leave brand-new widgets showing a stale or blank background for
        # a moment — especially when this whole rebuild was triggered
        # from inside another widget's own click, like the theme dropdown.
        self.update_idletasks()

    # ================================================================== #
    # Saving your settings
    # ================================================================== #
    def _on_claude_toggle(self) -> None:
        """
        Turning this switch on is a real decision — confusing window titles
        will start being sent to Claude — so it gets its own special handler
        instead of quietly sharing one with all the other switches.
        """
        self.config_obj.claude_fallback_enabled = self.claude_var.get()
        self.config_obj.save()
        self.claude.clear_cache()          # an old "unavailable" answer shouldn't stick around
        self._refresh_claude_status()

    def _on_camera_switch_toggled(self) -> None:
        """
        Applies right away, even in the middle of a focus block -- same
        reasoning that already applies to every other enforcement switch
        in this app: turning Strict Camera Monitoring off should stop
        the camera immediately, not wait for the next focus block to
        start. Turning it ON mid-block starts it immediately too.
        """
        self.config_obj.camera_monitoring_enabled = self.camera_var.get()
        self.config_obj.save()
        if self.config_obj.camera_monitoring_enabled:
            if self.session.phase is Phase.FOCUS and self.session.is_running:
                self.camera_watcher.resume()
        else:
            self.camera_watcher.pause()
        self._sync_camera_indicator()

    def _refresh_claude_status(self) -> None:
        status = self.claude.status
        colour = COLOR_BREAK if status.startswith("ready") else COLOR_IDLE
        self.claude_status.configure(text=f"status: {status}", text_color=colour)

    def _build_timer_preset_row(
        self, parent, presets: list[TimerPreset], heading: str,
    ) -> None:
        """
        One row of small buttons, one per preset. Clicking a button
        calls _apply_timer_preset with THAT preset -- the button itself
        doesn't know or care what the numbers mean, it just hands over
        the whole bundle.
        """
        self._mpack(ctk.CTkLabel(parent, text=heading, text_color=COLOR_TIMER_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")), anchor="w", pady=(14, 4))

        row = ctk.CTkFrame(parent, fg_color="transparent")
        self._mpack(row, fill="x", pady=(0, 4))

        for preset in presets:
            button_name = preset.name_tokusatsu if self._is_tokusatsu() else preset.name_professional
            column = ctk.CTkFrame(row, fg_color="transparent")
            self._mpack(column, side="left", padx=(0, 8))
            self._mpack(ctk.CTkButton(
                column, text=button_name, width=90,
                fg_color=COLOR_TIMER_ACCENT,
                command=lambda p=preset: self._apply_timer_preset(p),
            ))
            if preset.description:
                self._mpack(ctk.CTkLabel(
                    column, text=preset.description, font=ctk.CTkFont(size=9),
                    text_color=COLOR_IDLE, wraplength=90,
                ), pady=(2, 0))

    def _apply_timer_preset(self, preset: TimerPreset) -> None:
        """
        Copies one preset's 4 numbers into Config, updates the number
        boxes on screen so they show what just happened, and saves --
        same save path _save_settings() already uses, so this behaves
        exactly like typing the numbers in yourself.
        """
        self.config_obj.focus_minutes = preset.focus_minutes
        self.config_obj.short_break_minutes = preset.short_break_minutes
        self.config_obj.long_break_minutes = preset.long_break_minutes
        self.config_obj.blocks_until_long_break = preset.blocks_until_long_break
        self.config_obj.save()

        for key, value in (
            ("focus_minutes", preset.focus_minutes),
            ("short_break_minutes", preset.short_break_minutes),
            ("long_break_minutes", preset.long_break_minutes),
            ("blocks_until_long_break", preset.blocks_until_long_break),
        ):
            if key in self.spinners:
                self.spinners[key].delete(0, "end")
                self.spinners[key].insert(0, str(value))

        name = preset.name_tokusatsu if self._is_tokusatsu() else preset.name_professional
        self._show_banner(
            f"Applied: {name} — {preset.focus_minutes}m focus. Applies from the next phase.",
            "low",
        )

    def _build_gavv_toggle_row(self, parent) -> None:
        """
        A single switch, not a row of buttons -- Gavv's gimmick stays on
        until you turn it off, it isn't a one-click-and-done preset.
        """
        heading = "Bite-Sized Mode" if self._is_tokusatsu() else "Micro-Sprint Mode"
        self._mpack(ctk.CTkLabel(parent, text=heading, text_color=COLOR_TIMER_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")), anchor="w", pady=(14, 4))

        self.micro_sprint_switch = ctk.CTkSwitch(
            parent, text=f"{GAVV_MICRO_SPRINT.focus_minutes}m focus / "
                         f"{GAVV_MICRO_SPRINT.short_break_minutes}m break, repeating",
            progress_color=COLOR_TIMER_ACCENT,
            command=self._on_micro_sprint_toggled,
        )
        if self.config_obj.micro_sprint_mode:
            self.micro_sprint_switch.select()
        else:
            self.micro_sprint_switch.deselect()
        self._mpack(self.micro_sprint_switch, anchor="w", pady=4)

        self._mpack(ctk.CTkLabel(
            parent,
            text="Overrides your timer lengths above until you turn this back off.",
            font=ctk.CTkFont(size=10), text_color=COLOR_IDLE,
        ), anchor="w")

    def _build_blackrx_toggle_row(self, parent) -> None:
        """A single switch, same shape as Gavv's -- Black RX's manual-break
        mode stays on until you turn it off, not a one-click preset."""
        heading = "Manual Recovery" if self._is_tokusatsu() else "Manual Break Mode"
        self._mpack(ctk.CTkLabel(parent, text=heading, text_color=COLOR_TIMER_ACCENT,
                     font=ctk.CTkFont(size=13, weight="bold")), anchor="w", pady=(14, 4))

        self.blackrx_switch = ctk.CTkSwitch(
            parent, text="Never auto-start breaks -- always wait for you to press Start",
            progress_color=COLOR_TIMER_ACCENT,
            command=self._on_blackrx_toggled,
        )
        if self.config_obj.blackrx_manual_breaks:
            self.blackrx_switch.select()
        else:
            self.blackrx_switch.deselect()
        self._mpack(self.blackrx_switch, anchor="w", pady=4)

        self._mpack(ctk.CTkLabel(
            parent,
            text="Overrides Auto-start breaks above until you turn this back off.",
            font=ctk.CTkFont(size=10), text_color=COLOR_IDLE,
        ), anchor="w")

    def _on_blackrx_toggled(self) -> None:
        """Called when you click the Manual Break Mode switch itself."""
        self.config_obj.blackrx_manual_breaks = self.blackrx_switch.get() == 1
        self.config_obj.save()

    def _on_micro_sprint_toggled(self) -> None:
        """Called when you click the Micro-Sprint switch itself."""
        self.config_obj.micro_sprint_mode = self.micro_sprint_switch.get() == 1
        self.config_obj.save()
        name = GAVV_MICRO_SPRINT.name_tokusatsu if self._is_tokusatsu() else GAVV_MICRO_SPRINT.name_professional
        state = "on" if self.config_obj.micro_sprint_mode else "off"
        self._show_banner(f"{name}: {state}. Applies from the next phase.", "low")

    def _save_from_widgets(self) -> None:
        """These switches save themselves right away — no separate save step needed."""
        c = self.config_obj
        c.enforcement_enabled = self.enforce_var.get()
        c.hard_mode = self.hard_var.get()
        c.use_classifier = self.classifier_var.get()
        c.record_observations = self.record_var.get()
        if hasattr(self, "autobreak_var"):
            c.auto_start_breaks = self.autobreak_var.get()
            c.auto_start_focus = self.autofocus_var.get()
            c.sound_enabled = self.sound_var.get()
            c.toast_enabled = self.toast_var.get()
        c.save()

    def _save_lists(self) -> None:
        """Reads the two text boxes into clean lists, and saves them."""
        def parse(box: ctk.CTkTextbox) -> list:
            raw = box.get("1.0", "end").splitlines()
            # This trick removes duplicate lines while keeping your original order.
            return list(dict.fromkeys(line.strip().lower() for line in raw if line.strip()))

        self.config_obj.blocklist = parse(self.blocklist_box)
        self.config_obj.allowlist = parse(self.allowlist_box)
        self.config_obj.save()
        self._show_banner("Lists saved.", "low")

    def _save_settings(self) -> None:
        """Checks and saves the number fields; tells you clearly if something's wrong."""
        problems = []
        for key, entry in self.spinners.items():
            try:
                value = int(entry.get())
                if value < 1:
                    raise ValueError
                setattr(self.config_obj, key, value)
            except ValueError:
                problems.append(key.replace("_", " "))

        self._save_from_widgets()

        if problems:
            self._show_banner(f"Ignored invalid values: {', '.join(problems)}", "high")
        else:
            self._show_banner("Settings saved. Applies from the next phase.", "low")

    def _reset_model(self) -> None:
        """
        Rebuilds the model from the starter examples plus everything you've
        labelled.

        This RE-builds it, it doesn't wipe it clean. Since every correction
        you've made is also saved to observations.jsonl, nothing you taught
        it is actually lost — what gets cleaned up is just extra double
        counting from clicking the same correction more than once. This does
        the exact same thing as `train.py rebuild`.
        """
        pairs = self.observations.training_pairs()
        self.model = NaiveBayesClassifier.load_seed()
        for text, label in pairs:
            self.model.learn(text, label)
        self.model.save(MODEL_PATH)
        self._update_model_stats()
        self._show_banner(f"Rebuilt from seed + {len(pairs)} of your labels.", "low")

    # ================================================================== #
    # The activity list, and teaching the model as you go
    # ================================================================== #
    def _log_activity(self, window: WindowInfo, verdict) -> None:
        """
        Adds a window to the list — every window, not just blocked ones —
        combining it with the row above if it's the very same app repeated.

        Without combining them, you'd get a brand-new row every single
        second, which would make the list far too messy to actually use for
        correcting the model.
        """
        key = window.display
        if self.activity and self.activity[-1]["key"] == key:
            self.activity[-1]["count"] += 1
            self.activity[-1]["blocked"] = verdict.blocked
            self.activity[-1]["reason"] = verdict.reason
            self.activity[-1]["confidence"] = verdict.confidence
            return

        entry = {
            "key": key,
            "text": window.text,
            "time": datetime.now().strftime("%H:%M"),
            "reason": verdict.reason,
            "confidence": verdict.confidence,
            "blocked": verdict.blocked,
            "count": 1,
            "corrected": None,
        }
        self.activity.append(entry)
        self.activity = self.activity[-40:]     # only keep the most recent entries
        self._render_activity()

    def _render_activity(self) -> None:
        """Redraws the whole activity list from scratch. There aren't many entries, so this is fine."""
        for child in self.activity_frame.winfo_children():
            child.destroy()

        if not self.activity:
            self._mpack(ctk.CTkLabel(self.activity_frame, text="Nothing logged yet.",
                         text_color=COLOR_IDLE), anchor="w", pady=20)
            return

        for entry in reversed(self.activity):
            # Red means we blocked it, green means we let it through. This
            # is what makes it easy to see, at a glance, why something
            # wasn't stopped (like Steam not getting blocked because it was
            # judged "allowed").
            dot_color = COLOR_DANGER if entry.get("blocked") else COLOR_BREAK

            row = ctk.CTkFrame(self.activity_frame, border_width=1, border_color=dot_color)
            self._mpack(row, fill="x", pady=3)

            self._mpack(ctk.CTkLabel(row, text="●", text_color=dot_color, width=20,
                         font=ctk.CTkFont(size=14)), side="left", padx=(10, 0))

            left = ctk.CTkFrame(row, fg_color="transparent")
            self._mpack(left, side="left", fill="x", expand=True, padx=10, pady=8)

            self._mpack(ctk.CTkLabel(left, text=entry["key"], anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         wraplength=280, justify="left"), anchor="w")

            status = "blocked" if entry.get("blocked") else "allowed"
            detail = f"{entry['time']} · {status} · {entry['reason'].value}"
            if entry["reason"] in (Reason.CLASSIFIER, Reason.CLAUDE):
                detail += f" {entry['confidence']:.0%}"
            if entry["count"] > 1:
                detail += f" · seen {entry['count']}×"
            if entry["corrected"]:
                detail += f" · you said: {entry['corrected']}"

            self._mpack(ctk.CTkLabel(left, text=detail, anchor="w",
                         font=ctk.CTkFont(size=10),
                         text_color=COLOR_IDLE), anchor="w")

            # These two buttons are how you actually correct and teach the
            # model -- they don't make sense for a camera-sourced row (there's
            # no text to learn from, and clicking "was studying" would
            # allowlist "your phone"), so camera rows don't get them.
            if entry["reason"] is not Reason.CAMERA:
                self._mpack(ctk.CTkButton(row, text="was studying", width=90, height=26,
                              font=ctk.CTkFont(size=10), fg_color="transparent",
                              border_width=1,
                              command=lambda e=entry: self._correct(e, STUDY)
                              ), side="right", padx=(0, 10))

                self._mpack(ctk.CTkButton(row, text="distraction", width=80, height=26,
                              font=ctk.CTkFont(size=10), fg_color=COLOR_DANGER,
                              hover_color="#96281b",
                              command=lambda e=entry: self._correct(e, DISTRACTION)
                              ), side="right", padx=6)

    def _correct(self, entry: dict, label: str) -> None:
        """
        Teaches the model from one click, and saves it right away.

        The model only needs to update a few simple counts, so this happens
        instantly — the very next check already uses what it just learned.
        """
        self.model.learn(entry["text"], label)
        self.model.save(MODEL_PATH)
        entry["corrected"] = label

        # Also save this decision into the training data, so `train.py`
        # doesn't ask you about a window you already corrected here.
        self.observations.label_by_text(entry["text"], label)
        self.observations.save()

        # Saying "this was studying" is also a strong hint that this app
        # should just always be allowed — so we offer to do that for you
        # right away, instead of making you go find it in the Blocking tab.
        process = entry["key"].split(" — ")[0].strip().lower()
        if label == STUDY and process and process not in self.config_obj.normalised_allowlist():
            self.config_obj.allowlist.append(process)
            self.config_obj.save()
            self._sync_list_boxes()
            self._show_banner(f"Learned. Also allow-listed {process}.", "low")
        else:
            self._show_banner("Learned.", "low")

        self._update_model_stats()
        self._render_activity()

    def _sync_list_boxes(self) -> None:
        """Puts the saved lists back into the text boxes after we've changed them in code."""
        self.blocklist_box.delete("1.0", "end")
        self.blocklist_box.insert("1.0", "\n".join(self.config_obj.blocklist))
        self.allowlist_box.delete("1.0", "end")
        self.allowlist_box.insert("1.0", "\n".join(self.config_obj.allowlist))

    def _update_model_stats(self) -> None:
        """Shows how big the model is, and nudges you toward `train.py label` if there's a backlog."""
        total = sum(self.model.label_counts.values())
        text = f"{total} examples · {len(self.model.vocabulary)} tokens"

        pending = len(self.observations.pending())
        if pending:
            text += f" · {pending} to label"

        self.model_stats.configure(text=text)

    # ================================================================== #
    # Helpers that redraw parts of the screen
    # ================================================================== #
    def _sync_camera_indicator(self) -> None:
        active = (
            self.config_obj.camera_monitoring_enabled
            and self.session.phase is Phase.FOCUS
            and self.session.is_running
            and self.camera_watcher.is_capturing
        )
        self.camera_indicator_label.configure(
            text="\U0001F4F7 Camera monitoring active" if active else ""
        )

    def _set_kabuto_revealed(self, revealed: bool) -> None:
        """Called on hover enter/leave over the timer digits."""
        self._kabuto_revealed = revealed
        self._refresh_timer_widgets()

    def _refresh_timer_widgets(self) -> None:
        phase = self.session.phase
        label = label_for(phase, self._effective_terminology())
        progress_fraction = self.session.progress

        driver_text = self._driver_label_text()
        if phase is Phase.FOCUS and self.current_tier3_effect == "goal_gate" and self.current_goal_text:
            driver_text = self.current_goal_text.upper()
        self.driver_label.configure(text=driver_text)

        hide_kabuto_digits = (
            self.current_tier4_effect == "hidden_timer"
            and phase is Phase.FOCUS
            and not self._kabuto_revealed
        )
        self.time_label.configure(text="--:--" if hide_kabuto_digits else self.session.format_remaining())

        # The progress bar's fill uses the plain, vivid Rider color — but
        # the WORDS use the separate, always-readable version instead,
        # since a word-colored-exactly-like-its-own-background is a word
        # nobody can read (this is exactly the bug some Riders, like
        # Fourze's pure white, used to have).
        fill_color = {
            Phase.FOCUS: self.color_focus,
            Phase.SHORT_BREAK: COLOR_BREAK,
            Phase.LONG_BREAK: COLOR_BREAK,
            Phase.IDLE: COLOR_IDLE,
        }[phase]
        text_color = {
            Phase.FOCUS: self.color_focus_text,
            Phase.SHORT_BREAK: COLOR_BREAK,
            Phase.LONG_BREAK: COLOR_BREAK,
            Phase.IDLE: COLOR_IDLE,
        }[phase]

        if phase is Phase.FOCUS:
            # Agito's whole gimmick is that its color wakes up over the
            # block instead of staying still -- swap in that shifting
            # color ONLY during a focus block, so break/idle still look normal.
            if self.current_tier1_effect == "color_interpolation":
                primary_light, primary_dark = self.rider_primary_pair
                fill_color = (
                    interpolate_agito_color(progress_fraction, primary_light),
                    interpolate_agito_color(progress_fraction, primary_dark),
                )
            # Drive's gimmick lives in how fast the bar itself appears
            # to move, not its color or shape -- so we bend the NUMBER
            # fed to the bar, not what draws it.
            if self.current_tier1_effect == "accelerating_fill":
                progress_fraction = ease_drive_progress(progress_fraction)

        suffix = " (paused)" if self.session.is_paused and phase is not Phase.IDLE else ""
        self.phase_label.configure(text=label + suffix, text_color=text_color)
        self.time_label.configure(text_color=text_color)

        if self.current_tier1_effect in SHAPE_EFFECTS:
            self._refresh_progress_shape(progress_fraction)
        else:
            self.progress.set(progress_fraction)
            self.progress.configure(progress_color=fill_color)

        if (self.current_tier1_effect in ("border_glow", "night_overlay")
                or self.current_tier3_effect == "lock_overlay"
                or self.current_tier4_effect == "mirror_flip"):
            self._refresh_background_effect(progress_fraction)

        if self.current_tier3_effect == "zero_ui" and phase is Phase.FOCUS:
            self._refresh_zero_ui_drain(progress_fraction)
            # Icon-only text still needs to track paused/running, just
            # like the normal button text below does -- it's just a
            # different label for the same two states.
            self.start_button.configure(text="⏸" if self.session.is_running else "▶")
        else:
            self.start_button.configure(text="Pause" if self.session.is_running else self._henshin_word())

        done = self.session.completed_focus_blocks
        until_long = self.session.blocks_until_long_break
        if self._is_tokusatsu():
            streak_text = f"{done} mission{'s' if done != 1 else ''} complete · Full Recovery in {until_long}"
        else:
            streak_text = f"{done} session{'s' if done != 1 else ''} complete · Long break in {until_long}"
        self.streak_label.configure(text=streak_text, text_color=COLOR_LOOK_ACCENT)

        if self.current_tier4_effect == "dashboard_cards":
            # Cards render INSTEAD OF the centered timer stack, not
            # alongside it -- same whole-header swap Amazon's zero-UI
            # reskin already does.
            if self.normal_header_content.winfo_manager():
                self.normal_header_content.pack_forget()
            if not self._dashboard_built:
                for child in self._dashboard_cards_frame.winfo_children():
                    child.destroy()
                self._build_dashboard_cards(self._dashboard_cards_frame)
                self._mpack(self._dashboard_cards_frame, fill="x")
                self._dashboard_built = True
            self._dashboard_status_value.configure(
                text=label_for(phase, self._effective_terminology()))
            self._dashboard_time_value.configure(text=self.session.format_remaining())
            self._dashboard_streak_value.configure(text=str(self.session.completed_focus_blocks))
            self._dashboard_profile_value.configure(text=self._driver_label_text())
        elif self._dashboard_built:
            # winfo_ismapped() would also read False -- and thrash this
            # branch every tick -- while the window is simply minimized,
            # not just when the cards are actually pack_forget()-ten. A
            # plain flag isn't fooled by that.
            self._dashboard_cards_frame.pack_forget()
            self._dashboard_built = False
            if not self.normal_header_content.winfo_manager():
                # Anchor on task_row (which stays packed right through the
                # card swap) so the timer stack lands back ABOVE the
                # picker and progress bar rather than between them.
                # task_row is only ever unpacked by Amazon's zero-UI, and
                # pack(before=) needs a currently-managed sibling, so fall
                # back to controls in that case -- _sync_zero_ui_visibility
                # re-stacks everything itself on the way out anyway.
                self._mpack(self.normal_header_content, before=self._header_stack_anchor())

        # The title bar also shows a tiny timer, so it's visible even when
        # this window is hidden behind others.
        title_time = "--:--" if hide_kabuto_digits else self.session.format_remaining()
        self.title(f"{title_time} · {label} — Lock In")
        self._sync_camera_indicator()
        self._refresh_ghost_widget()

    def _refresh_progress_shape(self, progress_fraction: float) -> None:
        """
        Redraw the picture for one of the 4 Riders with their own
        custom progress shape, and push it onto the picture widget
        already on screen. Renders BOTH a light-mode and a dark-mode
        version, same trick already used for the background wallpaper.
        """
        primary_light, primary_dark = self.rider_primary_pair
        secondary_light, secondary_dark = self.rider_secondary_pair
        light_image = render_progress(
            self.current_tier1_effect, PROGRESS_SHAPE_WIDTH, PROGRESS_SHAPE_HEIGHT,
            progress_fraction, primary_light, secondary_light, False,
        )
        dark_image = render_progress(
            self.current_tier1_effect, PROGRESS_SHAPE_WIDTH, PROGRESS_SHAPE_HEIGHT,
            progress_fraction, primary_dark, secondary_dark, True,
        )
        if hasattr(self, "_progress_shape_image"):
            self._progress_shape_image.configure(light_image=light_image, dark_image=dark_image)
        else:
            self._progress_shape_image = ctk.CTkImage(
                light_image=light_image, dark_image=dark_image,
                size=(PROGRESS_SHAPE_WIDTH, PROGRESS_SHAPE_HEIGHT),
            )
            self.progress_shape.configure(image=self._progress_shape_image)

    def _header_stack_anchor(self):
        """Whichever widget normal_header_content should be packed
        immediately before. Normally that's the current-task picker row;
        while Amazon's zero-UI has the picker hidden, the button row --
        which is never unpacked -- is the only safe target."""
        return self.task_row if self.task_row.winfo_manager() else self.controls

    def _sync_progress_widget_visibility(self) -> None:
        """
        Show whichever ONE of the two progress widgets this Rider
        actually needs, and hide the other. Always re-inserts the
        visible one right before the button row (`before=self.controls`)
        instead of just calling plain `.pack()` again -- packing a
        forgotten widget with no `before=` appends it at the END of the
        layout order instead of putting it back where it was, which
        would silently push it below the button row.
        """
        if self.current_tier1_effect in SHAPE_EFFECTS:
            self.progress.pack_forget()
            self._mpack(self.progress_shape, fill="x", pady=(12, 14), before=self.controls)
        else:
            self.progress_shape.pack_forget()
            self._mpack(self.progress, fill="x", pady=(12, 14), before=self.controls)

    def _sync_zero_ui_visibility(self) -> None:
        """
        Amazon's "zero UI" look replaces the normal timer words and
        progress bar with just a draining color field, and shrinks the
        buttons to icons -- but ONLY during an actual focus block. Any
        other time (break, idle, or before you've even started) you
        see the normal UI, same as every other Rider.
        """
        active = (
            self.current_tier3_effect == "zero_ui"
            and self.session.phase is Phase.FOCUS
        )

        if active:
            self.normal_header_content.pack_forget()
            # The current-task picker is a sibling of normal_header_content
            # now (so Zero-One's card swap can't take it away), so hiding
            # the normal header means hiding it explicitly too -- Amazon's
            # gimmick is showing nothing but the draining field.
            self.task_row.pack_forget()
            self.progress.pack_forget()
            self.progress_shape.pack_forget()
            self._timer_glow_label.place_forget()
            self.tabs.pack_forget()
            self._mpack(self.zero_ui_label, pady=(20, 20), before=self.controls)
            self.start_button.configure(text="⏸" if self.session.is_running else "▶", width=44)
            self.skip_button.configure(text="⏭", width=44)
            self.reset_button.configure(text="⟲", width=44)
        else:
            self.zero_ui_label.pack_forget()
            if not self.normal_header_content.winfo_ismapped():
                # self.progress may currently be unpacked too (zero-UI
                # hides it along with everything else), so anchoring on
                # self.controls -- which is never toggled, always
                # packed -- is the only always-safe target here. Packing
                # normal_header_content before controls FIRST, then
                # letting _sync_progress_widget_visibility() pack the
                # progress widget before controls too, naturally stacks
                # them in the right order: content, then progress, then
                # controls.
                self._mpack(self.normal_header_content, before=self.controls)
                # Packed after normal_header_content and before the
                # progress widget below, which rebuilds the usual stack:
                # content, picker, progress, controls.
                self._mpack(self.task_row, pady=(6, 0), before=self.controls)
                self._mplace(self._timer_glow_label, relx=0.5, rely=0.33, anchor="center")
                self._mpack(self.tabs, fill="both", expand=True, padx=20, pady=(0, 16), after=self._divider_label)
                self._sync_progress_widget_visibility()
                self.start_button.configure(
                    text="Pause" if self.session.is_running else self._henshin_word(), width=140,
                )
                self.skip_button.configure(text="Skip", width=80)
                self.reset_button.configure(text="Reset", width=80)

    def _refresh_zero_ui_drain(self, progress_fraction: float) -> None:
        """Redraw Amazon's draining field and push it onto the label already
        on screen -- same light/dark-both-the-same trick as the button glow,
        since this picture's color never depends on appearance mode."""
        drain = render_amazon_drain(ZERO_UI_WIDTH, ZERO_UI_HEIGHT, progress_fraction)
        if hasattr(self, "_zero_ui_image"):
            self._zero_ui_image.configure(light_image=drain, dark_image=drain)
        else:
            self._zero_ui_image = ctk.CTkImage(
                light_image=drain, dark_image=drain, size=(ZERO_UI_WIDTH, ZERO_UI_HEIGHT),
            )
            self.zero_ui_label.configure(image=self._zero_ui_image)

    def _update_watch_label(self, window: WindowInfo) -> None:
        if self.session.phase is Phase.FOCUS and self.monitor.is_active:
            self.watch_label.configure(text=f"watching: {window.display}")
        else:
            self.watch_label.configure(text="")

    def _queue_banner(self, title: str, body: str, urgency: str) -> None:
        """Notifier calls this from any thread — it's safe to use that way."""
        self._banner_queue.put((title, body, urgency))

    def _show_banner(self, text: str, urgency: str = "low", duration_ms: Optional[int] = None) -> None:
        """Shows a short message banner above the timer for a little while."""
        colors = {
            "low": ("#1f6aa5", "#dbe9f4"),
            "normal": (COLOR_WARN, "#241d00"),
            "high": (COLOR_DANGER, "#ffe8e5"),
        }
        bg, fg = colors.get(urgency, colors["low"])

        self.banner.configure(text=text, fg_color=bg, text_color=fg)
        self._mpack(self.banner, fill="x", pady=(0, 10), before=self.phase_label)

        # Cancel any earlier "hide the banner" timer, so a new banner always
        # gets its own full amount of time on screen.
        if self._banner_after_id is not None:
            try:
                self.after_cancel(self._banner_after_id)
            except Exception:
                pass
        self._banner_after_id = self.after(duration_ms or self.BANNER_MS, self.banner.pack_forget)

    # ================================================================== #
    def _on_close(self) -> None:
        """Saves everything and shuts down the background checker cleanly."""
        try:
            self.config_obj.save()
            self.model.save(MODEL_PATH)
            self.observations.save()
        finally:
            self.monitor.stop()
            self.ambient.stop()
            self.camera_watcher.stop()
            self.destroy()


def run() -> None:
    """This is what main.py calls to actually open the app."""
    LockInApp().mainloop()