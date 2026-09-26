"""
ui/app.py
=========
The main Lock In window, and the brain behind it.

What the window looks like
--------------------------
    ┌──────────────────────────────────────────────────────┐
    │  LOCK IN                                ● Focus active│   top bar
    ├────────────┬─────────────────────────────────────────┤
    │  Focus     │                                         │
    │  Tasks     │          the page you picked            │
    │  Blocking  │     (Focus, Tasks, Blocking, ...)       │
    │  Activity  │                                         │
    │  Insights  │                                         │
    │  RIDER     │                                         │
    │  (extra)   │                                         │
    │            │                                         │
    │  Help      │                                         │
    │  Settings  │                                         │
    └────────────┴─────────────────────────────────────────┘

How the background helpers and the screen work together (important!)
--------------------------------------------------------------------
Some jobs run on their own background helper (watching which window
you're in, the camera, Claude, the update check, Revice's network
link). The screen toolkit isn't safe to touch from those helpers, so
each one only drops a note in a safe waiting line (a "queue"). The
app's heartbeat (`_pump`, five times a second) reads those notes on the
screen's own thread. It is the only place that changes what you see.

Where things live
-----------------
    app.py          this file: the window, the timer, blocking, pages
    overlays.py     the lockdown screen, X's goal screen, Ghost's clock
    updates.py      checking for a newer Lock In
    gestures.py     Wizard's mouse gestures
    revice.py       Revice's buddy link
    preferences.py  what happens when you change a setting
    pages/          one file per page
    components/     cards, buttons, badges, the side bar, the timer
    theme.py        every color and size
"""

from __future__ import annotations

import dataclasses
import queue
import socket
import sys
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

from ..classifier import STUDY, NaiveBayesClassifier
from ..claude_fallback import ClaudeFallback
from ..config import Config, LOG_PATH, MODEL_PATH, OBSERVATIONS_PATH, TASKS_PATH, app_data_dir
from ..observations import ObservationStore
from ..tasks import TaskStatus, TaskStore
from ..history import HistoryStore, SessionRecord
from ..tier5 import TIER5_BUILDERS
from ..revice_link import BuddyLink
from ..camera_enforcer import CAMERA_BACKEND_AVAILABLE, CameraEnforcer, PhoneWatcher
from ..enforcer import Action, Enforcer, Reason, Verdict, WindowInfo, judge, message_for
from ..ambient import AmbientPlayer
from ..monitor import BACKEND_AVAILABLE, ActiveWindowMonitor, minimize_window
from ..notifier import Notifier
from ..session import Event, Phase, PomodoroSession, label_for
from ..rider_themes import DEFAULT_RIDER_THEME, RIDER_THEMES, STANDARD_THEME, desaturate
from ..visuals import (
    SHAPE_EFFECTS,
    apply_gaim_lock_overlay,
    apply_tier1_background_effect,
    display_font_family,
    ease_drive_progress,
    interpolate_agito_color,
    load_app_icon,
    load_pixel_font,
    make_flat_fill,
    make_panel_divider,
    render_amazon_drain,
    render_progress,
)
from . import theme as t
from .components.box import Box
from .components import Sidebar, StatusBadge
from .components.timer_display import (
    PROGRESS_SHAPE_HEIGHT, PROGRESS_SHAPE_WIDTH, ZERO_UI_HEIGHT, ZERO_UI_WIDTH,
)
from .gestures import WizardGesturesMixin
from .mirror import MirrorLayout, mirrored_column
from .overlays import OverlaysMixin
from .pages import PAGE_CLASSES
from .pages.base import tasks_signature
from .preferences import PreferencesMixin
from .revice import ReviceMixin
from .router import FIRST_ROUTE_ID, Router, build_routes
from .task_picker import build_task_picker_entries
from .updates import UpdatesMixin

# The nicer-looking font for the timer digits and headings. Picked once
# per computer in visuals.py -- see that file for why.
DISPLAY_FONT = display_font_family()

# The picture behind the page area. Stronger's glow, Kiva's night tint,
# and Gaim's dimming are painted onto it; for everyone else it's just the
# plain background color. It only shows in the thin gap around the page
# and gets stretched to fit, so a small picture is plenty -- and a small
# picture is much quicker to redraw and uses much less memory.
BG_TEXTURE_WIDTH = 480
BG_TEXTURE_HEIGHT = 640
# Stronger's glow grows in this many steps (see visuals.render_border_glow_overlay).
GLOW_STEPS = 14

# The thin era strip under the top bar (Riders only, never Standard Mode).
DIVIDER_WIDTH = 1400
DIVIDER_HEIGHT = 4

# The gap around the page area, where the background picture shows.
CONTENT_MARGIN = t.SPACE_3


class LockInApp(OverlaysMixin, UpdatesMixin, WizardGesturesMixin, ReviceMixin,
                PreferencesMixin, ctk.CTk):
    """The main app window -- everything you see lives inside this."""

    UI_TICK_MS = 200      # how often we redraw the countdown, in milliseconds
    BANNER_MS = 6000      # how long a pop-up banner stays on screen, in milliseconds

    def __init__(self) -> None:
        super().__init__()

        # ---------------- The main pieces of the app -------------------- #
        self.config_obj = Config.load()
        # The session has to exist BEFORE _apply_rider_theme(), which
        # checks what phase we're in (for Stronger/Kiva's effect).
        self.session = PomodoroSession(self.config_obj)
        self.display_font = DISPLAY_FONT
        self.layout = MirrorLayout(lambda: self._is_mirrored)
        # Which way the widgets are flipped right now (Ryuki's mirror).
        self._layout_mirrored = False
        self._apply_rider_theme()
        # X's goal-entry gate stores what you typed here -- in memory
        # only, reset every time the app restarts.
        self.current_goal_text = ""
        # Kabuto's hidden timer: True only while you hover the digits.
        self._kabuto_revealed = False
        self.model = NaiveBayesClassifier.load(MODEL_PATH)
        self.observations = ObservationStore(OBSERVATIONS_PATH)
        self.tasks = TaskStore(TASKS_PATH)
        self.history = HistoryStore(LOG_PATH)
        # The task picked on the Focus page. None means an untagged block.
        # Never saved -- it's meant to change often.
        self.current_task_id: Optional[str] = None
        # Set the instant a FOCUS phase begins, cleared once it's logged to
        # history (finished, skipped, or reset). None means "no focus block
        # is being timed right now".
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
        self._update_queue: "queue.Queue[tuple]" = queue.Queue()

        self.monitor = ActiveWindowMonitor(
            callback=self._window_queue.put,   # safe to call from any thread
            interval=1.0,
        )
        self.camera_watcher = PhoneWatcher(callback=self._camera_queue.put)

        # The activity list: dicts of {time, text, blocked, reason, ...}
        self.activity: List[dict] = []
        self._lockdown_window: Optional[ctk.CTkToplevel] = None
        self._ghost_widget: Optional[ctk.CTkToplevel] = None
        self._banner_after_id: Optional[str] = None
        # (UpdateInfo, Optional[Path]) once the background check finds one.
        self._pending_update: Optional[tuple] = None
        self._update_check_running = False
        self._update_message_wanted = False
        self._update_check_busy = False
        self._update_status_text = ""

        # Things the pages remember while they're redrawn.
        self.pages: dict = {}
        self.sidebar: Optional[Sidebar] = None
        self._retired: list = []
        self._page_order: list = []
        self._retire_after: Optional[str] = None
        self._claude_status_labels: list = []
        self._task_filter = "All"
        self._expanded_tasks: dict = {}
        self._task_menu_ids: dict = {}
        self._watching_text = ""
        self._zero_ui_on = False
        self._zero_ui_saved_route: Optional[str] = None

        # Revice's buddy link. Made once for the app's whole life, so
        # redrawing the pages (dark mode, a Rider switch) never drops the
        # connection. It doesn't touch the network until Share or Receive
        # is pressed -- see lock_in/revice_link.py.
        self.buddy_link = BuddyLink(socket.gethostname() or "Buddy")
        self._buddy_status: Optional[dict] = None
        self._buddy_message = ""
        self._buddy_last_sent = 0.0

        # ---------------- The window frame ------------------------------ #
        ctk.set_appearance_mode(self.config_obj.appearance)
        ctk.set_default_color_theme(self.config_obj.accent)

        self.title("Lock In")
        self.geometry(f"{t.WINDOW_SIZE[0]}x{t.WINDOW_SIZE[1]}")
        self.minsize(*t.WINDOW_MIN_SIZE)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_app_icon()

        self._make_setting_vars()
        self.router = Router(show=self._show_page, hide=self._hide_page,
                             on_change=self._on_route_changed)
        self._build_shell()
        self._rebuild_pages(initial=True)

        # Zeztz's keyboard shortcuts. Each one checks for itself whether
        # Zeztz is picked, so a Rider change needs no re-binding.
        self.bind_all("<space>", self._on_zeztz_space)
        self.bind_all("s", self._on_zeztz_skip)
        self.bind_all("r", self._on_zeztz_reset)
        self._bind_wizard_gestures()

        self.monitor.start()
        self.camera_watcher.start()
        self._pump()          # start the heartbeat
        self._refresh_timer_widgets()
        # Wait a moment, so the window is fully drawn before a banner shows.
        self.after(400, self._warn_if_app_detection_unavailable)
        self.after(2000, self._start_update_check)

    def _set_app_icon(self) -> None:
        """
        Puts the app's own picture in the title bar and the taskbar. If
        the picture is missing, `load_app_icon()` gives back None and we
        quietly keep the toolkit's plain icon instead of crashing.
        """
        icon = load_app_icon()
        if icon is None:
            return
        # Kept on `self`, or the toolkit could throw the picture away early.
        self._icon_image = ImageTk.PhotoImage(icon)
        self.iconphoto(True, self._icon_image)

        # Windows' title bar and taskbar need a real ".ico" file. Saved
        # once in the app's own settings folder (never the install folder,
        # which might not be writable).
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
    # Picking words: "professional" or "tokusatsu"
    # ================================================================== #
    def _is_tokusatsu(self) -> bool:
        # Standard Mode always reads as Professional, whatever the Wording
        # switch says -- the switch's real value is never overwritten.
        return self.config_obj.terminology == "tokusatsu" and not self.config_obj.standard_mode

    def _effective_terminology(self) -> str:
        """The wording value for label_for()/message_for()/lockdown_label_for()."""
        return "tokusatsu" if self._is_tokusatsu() else "professional"

    def _henshin_word(self) -> str:
        """What the main Start/Henshin button says when it's not running."""
        return "Henshin" if self._is_tokusatsu() else "Start"

    def _rider_row_label_text(self) -> str:
        """What the color-theme picker's row is called in Settings."""
        return "Kamen Rider theme" if self._is_tokusatsu() else "Color theme"

    def _driver_label_text(self) -> str:
        """What the small name under the timer digits should say right now."""
        if self.config_obj.standard_mode:
            return "STANDARD MODE"
        return self.config_obj.rider_theme.upper()

    # ================================================================== #
    # The Rider's colors and gimmicks
    # ================================================================== #
    def _apply_rider_theme(self) -> None:
        """
        Look up which Kamen Rider is picked (or Standard Mode's plain
        theme) and remember everything about it the rest of the app
        needs: its palette, and which gimmick it has in each Tier.
        If the saved name isn't recognized, use the default Rider.
        """
        theme = STANDARD_THEME if self.config_obj.standard_mode else RIDER_THEMES.get(
            self.config_obj.rider_theme, RIDER_THEMES[DEFAULT_RIDER_THEME]
        )
        # ZX's whole gimmick is going monochrome. Swapping in a grey copy
        # of the theme HERE means every color made from it below comes out
        # grey automatically -- widgets and drawn pictures alike.
        if theme.tier3_effect == "stealth_mute":
            theme = dataclasses.replace(
                theme,
                primary=(desaturate(theme.primary[0]), desaturate(theme.primary[1])),
                secondary=(desaturate(theme.secondary[0]), desaturate(theme.secondary[1])),
            )
        self._current_rider_theme = theme
        self.palette = t.resolve_palette(theme)
        self.color_focus = self.palette.accent
        self.color_focus_text = self.palette.accent_text
        # The lockdown screen is always dark, so its big words use the
        # dark-mode half of the Rider's color as-is.
        self.color_lockdown_text = theme.primary[1]
        # Which era this Rider is from -- picks notification wording,
        # the lockdown words, the era strip, and the sounds.
        self.current_era = theme.era

        self.current_tier1_effect = theme.tier1_effect
        self.current_tier2_effect = theme.tier2_effect
        self.current_tier3_effect = theme.tier3_effect
        self.current_tier4_effect = theme.tier4_effect
        self.current_tier5_effect = theme.tier5_effect
        # Standard Mode swaps in STANDARD_THEME above, so this reads "none"
        # there automatically -- no Wizard gestures, no buddy link.
        self.current_tier6_effect = theme.tier6_effect

        if self.current_tier4_effect == "chiptune_alert":
            self._active_display_font = load_pixel_font()
        else:
            self._active_display_font = DISPLAY_FONT
        self.rider_primary_pair = theme.primary
        self.rider_secondary_pair = theme.secondary
        # Stronger's glow uses the Rider's own primary (a red); Kiva's
        # night wash uses the secondary (the amber gold).
        self.color_tier1_effect_pair = (
            theme.primary if theme.tier1_effect == "border_glow" else theme.secondary
        )

        bg_light_color, bg_dark_color = self.palette.app_bg
        # A flat fill is the calm, modern base for every Rider. The Tier 1
        # and Tier 3 effects are painted on top of it (see below).
        self._base_bg_light = make_flat_fill(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, bg_light_color)
        self._base_bg_dark = make_flat_fill(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT, bg_dark_color)
        if self.config_obj.standard_mode:
            border_light, border_dark = self.palette.card_border
            divider_light = make_flat_fill(DIVIDER_WIDTH, DIVIDER_HEIGHT, border_light)
            divider_dark = make_flat_fill(DIVIDER_WIDTH, DIVIDER_HEIGHT, border_dark)
        else:
            (primary_light, primary_dark), (secondary_light, secondary_dark) = (
                theme.primary, theme.secondary)
            divider_light = make_panel_divider(
                DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_light, secondary_light, era=theme.era)
            divider_dark = make_panel_divider(
                DIVIDER_WIDTH, DIVIDER_HEIGHT, primary_dark, secondary_dark, era=theme.era)
        self._base_divider_light = divider_light
        self._base_divider_dark = divider_dark

        if hasattr(self, "_bg_image"):
            self._divider_image.configure(light_image=divider_light, dark_image=divider_dark)
        else:
            self._bg_image = ctk.CTkImage(
                light_image=self._base_bg_light, dark_image=self._base_bg_dark,
                size=(BG_TEXTURE_WIDTH, BG_TEXTURE_HEIGHT),
            )
            self._divider_image = ctk.CTkImage(
                light_image=divider_light, dark_image=divider_dark,
                size=(DIVIDER_WIDTH, DIVIDER_HEIGHT),
            )
        # A new theme drops the old Tier 1 picture's size and colors.
        if hasattr(self, "_progress_shape_image"):
            del self._progress_shape_image
        self._bg_key = None      # new colors: the background must be redrawn
        self._refresh_background_effect(self.session.progress)

    def _refresh_background_effect(self, progress_fraction: float) -> None:
        """
        Redraw the background picture with Stronger's glow, Kiva's night
        tint, or Gaim's dimming, if this Rider has one. Those only show
        DURING a focus block. Everyone else just gets the plain picture.
        """
        in_focus = self.session.phase is Phase.FOCUS
        active_effect = self.current_tier1_effect if in_focus else "none"
        if active_effect not in ("border_glow", "night_overlay"):
            active_effect = "none"
        lock_on = self.current_tier3_effect == "lock_overlay" and in_focus
        # Drawing this picture is the slowest thing the timer does, so it
        # is only redrawn when what it shows really changes: Stronger's
        # glow moves in GLOW_STEPS small steps, and everything else only
        # changes when a focus block starts or stops (or Ryuki flips).
        step = (round(GLOW_STEPS * max(0.0, min(1.0, progress_fraction)))
                if active_effect == "border_glow" else 0)
        painted = active_effect != "none" or lock_on
        key = (active_effect, step, lock_on, self._is_mirrored and painted)
        if key == getattr(self, "_bg_key", None):
            return
        self._bg_key = key
        if not painted:
            self._bg_image.configure(light_image=self._base_bg_light, dark_image=self._base_bg_dark)
            return
        progress_fraction = step / GLOW_STEPS
        effect_color_light, effect_color_dark = self.color_tier1_effect_pair
        bg_light = apply_tier1_background_effect(
            self._base_bg_light, active_effect, effect_color_light, progress_fraction,
        )
        bg_dark = apply_tier1_background_effect(
            self._base_bg_dark, active_effect, effect_color_dark, progress_fraction,
        )
        if lock_on:
            bg_light = apply_gaim_lock_overlay(bg_light, True)
            bg_dark = apply_gaim_lock_overlay(bg_dark, True)
        if self._is_mirrored:
            bg_light = ImageOps.mirror(bg_light)
            bg_dark = ImageOps.mirror(bg_dark)
        self._bg_image.configure(light_image=bg_light, dark_image=bg_dark)

    def _sync_mirror_divider(self) -> None:
        """Ryuki's flip for the era strip under the top bar."""
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

    # ================================================================== #
    # Ryuki's mirror (see ui/mirror.py)
    # ================================================================== #
    @property
    def _is_mirrored(self) -> bool:
        return self.current_tier4_effect == "mirror_flip" and self.session.phase.is_break

    # Short names kept for the rest of the app: put a widget down through
    # the mirror-aware layout helper.
    def _mpack(self, widget, **kwargs) -> None:
        self.layout.pack(widget, **kwargs)

    def _mplace(self, widget, **kwargs) -> None:
        self.layout.place(widget, **kwargs)

    def _mgrid(self, widget, total_columns: int, **kwargs) -> None:
        self.layout.grid(widget, total_columns=total_columns, **kwargs)

    def _sync_mirror_layout(self) -> None:
        """Re-place every widget whenever the mirror state CHANGES -- a
        Ryuki break starting or ending, or leaving Ryuki (another Rider,
        Standard Mode, Reset) while still flipped. When nothing changed it
        does nothing, so it can never bring back something another
        feature hid on purpose."""
        mirrored = self._is_mirrored
        if mirrored != self._layout_mirrored:
            self._layout_mirrored = mirrored
            self.layout.sync()
        self._apply_shell_columns()
        if self.sidebar is not None:
            self.sidebar.set_mirrored(mirrored)

    # ================================================================== #
    # The window's frame: top bar, side bar, page area
    # ================================================================== #
    def _build_shell(self) -> None:
        p = self.palette
        self.configure(fg_color=p.app_bg)
        self.grid_rowconfigure(2, weight=1)

        # ---- top bar --------------------------------------------------- #
        self.topbar = ctk.CTkFrame(self, fg_color=p.sidebar_bg, corner_radius=0, height=52)
        self.layout.grid(self.topbar, total_columns=2, row=0, column=0, columnspan=2, sticky="ew")
        self.topbar.pack_propagate(False)
        brand = Box(self.topbar)
        self.layout.pack(brand, side="left", padx=(t.SPACE_5, 0))
        icon = load_app_icon()
        if icon is not None:
            self._brand_image = ctk.CTkImage(light_image=icon, dark_image=icon, size=(24, 24))
            self.layout.pack(ctk.CTkLabel(brand, text="", image=self._brand_image, width=24, font=t.font()),
                             side="left", padx=(0, t.SPACE_2))
        self.brand_label = ctk.CTkLabel(brand, text="LOCK IN", text_color=p.text_primary,
                                        font=t.font(family=DISPLAY_FONT, size=15, weight="bold"))
        self.layout.pack(self.brand_label, side="left")

        badges = Box(self.topbar)
        self.layout.pack(badges, side="right", padx=(0, t.SPACE_5))
        self.phase_badge = StatusBadge(badges, p, text="Ready", kind="neutral")
        self.layout.pack(self.phase_badge, side="right")
        # Gaim's padlock: shown only while Gaim locks the window on top.
        self.lock_badge = StatusBadge(badges, p, text="Locked on top", kind="warning", dot=False)
        self._badges_frame = badges

        # ---- the era strip ------------------------------------------------ #
        self._divider_label = ctk.CTkLabel(self, text="", image=self._divider_image, height=DIVIDER_HEIGHT, font=t.font())
        self.layout.grid(self._divider_label, total_columns=2, row=1, column=0, columnspan=2,
                         sticky="ew")

        # ---- the page area ------------------------------------------------ #
        self.content = ctk.CTkFrame(self, fg_color=p.app_bg, corner_radius=0)
        self.layout.grid(self.content, total_columns=2, row=2, column=1, sticky="nsew")
        # Made FIRST so it sits behind everything else in the page area.
        self._bg_label = ctk.CTkLabel(self.content, text="", image=self._bg_image, font=t.font())
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.content.bind("<Configure>", self._on_content_resized, add="+")

        # A short pop-up message. Starts hidden; _show_banner reveals it.
        self.banner = ctk.CTkLabel(self.content, text="", corner_radius=t.CONTROL_RADIUS,
                                   height=40, font=t.font(size=13), wraplength=640,
                                   justify="left", anchor="w")
        # The "a new version is ready" strip. Unlike the banner, it stays
        # until you act on it. Starts hidden.
        self.update_frame = ctk.CTkFrame(self.content, fg_color=t.INFO_SOFT,
                                         corner_radius=t.CONTROL_RADIUS,
                                         border_width=1, border_color=t.INFO)
        self.update_label = ctk.CTkLabel(self.update_frame, text="", text_color=t.INFO,
                                         font=t.font(size=12, weight="bold"), anchor="w")
        self.layout.pack(self.update_label, side="left", padx=(12, 6), pady=8, fill="x", expand=True)
        self.update_restart_button = ctk.CTkButton(
            self.update_frame, text="Restart now", width=110, height=30,
            fg_color=t.INFO, text_color="#FFFFFF", command=self._on_restart_update_clicked, font=t.font()
        )
        self.layout.pack(self.update_restart_button, side="right", padx=(0, 10), pady=8)

        self.page_host = ctk.CTkFrame(self.content, fg_color=p.app_bg, corner_radius=t.CARD_RADIUS)
        self.layout.pack(self.page_host, fill="both", expand=True,
                         padx=CONTENT_MARGIN, pady=CONTENT_MARGIN)
        self._apply_shell_columns()

    def _apply_shell_palette(self) -> None:
        """After a Rider change, repaint the few pieces of the frame that
        stay on screen (only Black changes these, for its extra-dark look)."""
        p = self.palette
        self.configure(fg_color=p.app_bg)
        self.topbar.configure(fg_color=p.sidebar_bg)
        self.brand_label.configure(text_color=p.text_primary)
        self.content.configure(fg_color=p.app_bg)
        self.page_host.configure(fg_color=p.app_bg)
        self.phase_badge.set_palette(p)
        self.lock_badge.set_palette(p)

    def _apply_shell_columns(self) -> None:
        """The page area's column stretches; the side bar's doesn't. When
        Ryuki flips the window, the stretching moves with them."""
        mirrored = self._is_mirrored
        content_column = mirrored_column(mirrored, 2, 1)
        self.grid_columnconfigure(content_column, weight=1)
        self.grid_columnconfigure(1 - content_column, weight=0)

    def _on_content_resized(self, event) -> None:
        """Stretch the background picture to match the page area. Skips
        the work unless the size really changed (dragging a window edge
        fires this a lot). CustomTkinter reports this from the frame's
        inner drawing area, so the size is read from the frame itself."""
        new_size = (max(self.content.winfo_width(), 1), max(self.content.winfo_height(), 1))
        if self._bg_image.cget("size") != new_size:
            self._bg_image.configure(size=new_size)
        width = max(self.winfo_width(), 1)
        if self._divider_image.cget("size") != (width, DIVIDER_HEIGHT):
            self._divider_image.configure(size=(width, DIVIDER_HEIGHT))

    # ================================================================== #
    # Pages and the side bar
    # ================================================================== #
    def _rebuild_pages(self, initial: bool = False) -> None:
        """Throw away every page and the side bar, and build them again
        for the current Rider, colors, and wording. Stays on the same page
        if it still exists (a Rider's own page goes away with that Rider)."""
        keep = None if initial else self.router.active
        # Old pages are hidden right away and thrown away a little later,
        # one at a time (see _retire), so the new page shows up quickly
        # instead of waiting for every old widget to be taken apart first.
        for page in list(self.pages.values()):
            self._retire(page.frame)
        self.pages = {}
        self._page_order = []
        # These pictures were tied to the old Focus page's widgets; the new
        # page makes its own on its first redraw.
        for name in ("_progress_shape_image", "_zero_ui_image"):
            if hasattr(self, name):
                delattr(self, name)
        if self.sidebar is not None:
            self._retire(self.sidebar)
        self._apply_shell_palette()

        self.sidebar = Sidebar(self, self.palette, layout=self.layout,
                               on_select=self.navigate,
                               rider_heading="Rider Gear" if self._is_tokusatsu() else "Rider")
        self.layout.grid(self.sidebar, total_columns=2, row=2, column=0, sticky="nsw")
        routes = build_routes(self.current_tier5_effect, self.current_tier6_effect,
                              known_tier5_effects=TIER5_BUILDERS)
        self.sidebar.set_routes(routes)
        if initial or not self.LAZY_FOCUS_PAGE:
            self._page(FIRST_ROUTE_ID)
        # Otherwise the Focus page is drawn the next time you open it --
        # after a Rider change from Settings you're not looking at it, so
        # there's no need to wait for it. Everything else keeps running.
        self.router.set_routes(routes, keep=keep)

        self._refresh_current_task_picker()
        self._zero_ui_on = False
        self._sync_focus_layout()
        self._sync_zero_ui_visibility()
        self._refresh_timer_widgets()
        self._sync_mirror_layout()
        # Paint every new widget now, not whenever it gets its turn --
        # otherwise a rebuild started from a click can flash stale colors.
        self.update_idletasks()

    def _retire(self, widget) -> None:
        """Hide a widget now, destroy it soon. Destroying a whole page takes
        a noticeable moment, so pages are destroyed one per short pause
        after the new screen is already showing."""
        for forget in ("place_forget", "grid_forget", "pack_forget"):
            try:
                getattr(widget, forget)()
            except Exception:
                pass
        self._retired.append(widget)
        if self._retire_after is None:
            self._retire_after = self.after(150, self._destroy_retired)

    def _destroy_retired(self) -> None:
        self._retire_after = None
        if self._retired:
            widget = self._retired.pop(0)
            try:
                widget.destroy()
            except Exception:
                pass
        if self._retired:
            self._retire_after = self.after(40, self._destroy_retired)

    def _page(self, route_id: str):
        """The page for one route, drawn the first time it's needed."""
        page = self.pages.get(route_id)
        if page is None:
            page = PAGE_CLASSES[route_id](self, self.page_host)
            self.pages[route_id] = page
        return page

    # How many pages (besides Focus and the one on screen) stay ready in
    # memory. Opening one of these again is instant; older ones are put
    # away to save memory and simply drawn again if you come back.
    KEEP_PAGES = 4
    # After a Rider change, draw the Focus page only when it's opened.
    LAZY_FOCUS_PAGE = True

    def _forget_old_pages(self, showing: str) -> None:
        self._page_order = [r for r in self._page_order if r != showing] + [showing]
        spare = [r for r in self._page_order if r not in (showing, FIRST_ROUTE_ID)]
        while len(spare) > self.KEEP_PAGES:
            oldest = spare.pop(0)
            self._page_order.remove(oldest)
            page = self.pages.pop(oldest, None)
            if page is not None:
                self._retire(page.frame)

    def _show_page(self, route_id: str) -> None:
        """Pages that were already drawn stay put, stacked on top of each
        other, and the one you pick is simply brought to the front.
        Taking a page off the screen and putting it back made every
        widget on it lay itself out and redraw again -- this doesn't."""
        page = self._page(route_id)
        self._forget_old_pages(route_id)
        if page.frame.winfo_manager() != "place":
            self.layout.place(page.frame, relx=0.5, rely=0, anchor="n",
                              relwidth=1, relheight=1)
        page.frame.lift()
        try:
            page.on_show()
        except Exception:
            pass

    def _hide_page(self, route_id: str) -> None:
        # Nothing to do: the next page is simply raised on top of this one.
        pass

    def _on_route_changed(self, route_id: str) -> None:
        if self.sidebar is not None:
            self.sidebar.set_active(route_id)

    def navigate(self, route_id: str) -> bool:
        """Open a page by its fixed name ("focus", "tasks", ...)."""
        return self.router.navigate(route_id)

    @property
    def focus_page(self):
        return self._page(FIRST_ROUTE_ID)

    @property
    def _focus_ready(self) -> bool:
        """True once the Focus page has been drawn. Until then, updates
        meant only for its widgets are skipped (it catches up on open)."""
        return FIRST_ROUTE_ID in self.pages

    def _on_focus_page_shown(self) -> None:
        """The Focus page is on screen. The first time after it's drawn,
        bring every part of it up to date; after that the heartbeat keeps
        it current, so only the task menu is checked (tasks can change on
        other pages)."""
        page = self.focus_page
        signature = tasks_signature(self.tasks.open())
        if getattr(page, "_seen", False):
            if signature != getattr(page, "_tasks_seen", None):
                page._tasks_seen = signature
                self._refresh_current_task_picker()
            return
        page._seen = True
        page._tasks_seen = signature
        self._refresh_current_task_picker()
        self._sync_focus_layout()
        if self._zero_ui_on:
            self.skip_button.configure(text="⏭")
            self.reset_button.configure(text="⟲")
        self._refresh_timer_widgets()

    # Old names for the Focus page's main widgets, so every part of the
    # app (and the smoke test) can keep using them.
    @property
    def time_label(self):
        return self.focus_page.timer.time_label

    @property
    def phase_label(self):
        return self.focus_page.timer.phase_label

    @property
    def start_button(self):
        return self.focus_page.start_button

    @property
    def skip_button(self):
        return self.focus_page.skip_button

    @property
    def reset_button(self):
        return self.focus_page.reset_button

    @property
    def progress(self):
        return self.focus_page.progress_area.progress

    @property
    def progress_shape(self):
        return self.focus_page.progress_area.progress_shape

    @property
    def zero_ui_label(self):
        return self.focus_page.progress_area.zero_ui_label

    @property
    def current_task_menu(self):
        return self.focus_page.current_task_menu

    # ================================================================== #
    # The current-task picker
    # ================================================================== #
    def _refresh_current_task_picker(self) -> None:
        """Rebuild the menu's choices from the open tasks. The label -> id
        matching (including two tasks with the same name) is done by
        build_task_picker_entries(), which is tested on its own."""
        if not self._focus_ready:
            return
        open_tasks = self.tasks.open()
        values, self._task_menu_ids = build_task_picker_entries(open_tasks)
        menu = self.current_task_menu
        menu.configure(values=values)
        if self.current_task_id not in {task.id for task in open_tasks}:
            # The picked task was finished or deleted -- fall back to
            # "No task" instead of pointing at a task that's gone.
            self.current_task_id = None
            menu.set("No task")
        else:
            label = next((k for k, v in self._task_menu_ids.items()
                          if v == self.current_task_id), "No task")
            menu.set(label)

    def _on_current_task_selected(self, name: str) -> None:
        self.current_task_id = self._task_menu_ids.get(name)  # None for "No task"

    def _render_tasks(self) -> None:
        page = self.pages.get("tasks")
        if page is not None:
            page.render()

    # ================================================================== #
    # The heartbeat -- keeps everything moving
    # ================================================================== #
    def _pump(self) -> None:
        """
        The one loop that runs the whole app: move the timer forward, read
        the waiting lines, then redraw the screen. It schedules itself
        again every time, so it never gets stuck waiting on anything.
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
            self._drain_update_queue()
            self._drain_buddy_link()
            self._refresh_timer_widgets()
        finally:
            # Always schedule the next beat, even if something above broke
            # -- otherwise one bad moment would freeze the app forever.
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

            # If our own model isn't sure, quietly ask Claude in the
            # background. The answer is ready by the next check.
            if (self.config_obj.claude_fallback_enabled
                    and verdict.reason is Reason.CLASSIFIER
                    and verdict.confidence < self.config_obj.classifier_threshold):
                self.claude.judge_async(latest.text, self._claude_queue.put)

            # Write down EVERY window, not just the blocked ones, so
            # train.py can also show the distractions that slipped past.
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

            # A sample can still be waiting from the instant before a
            # pause/switch-off -- skip it rather than act on it.
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
                self._perform(action, CameraEnforcer.PHONE_WINDOW,
                              seconds=self.camera_enforcer.seconds_on_phone)

    def _drain_claude_queue(self) -> None:
        """
        Claude's answers arrive here from a background thread. Every real,
        fresh answer also goes into the training data, so over time the
        local model needs to ask less and less.
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
    # Doing something about a blocked window
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
            # ZX's Ninja Stealth: get out of the way the moment focus starts.
            self.iconify()

        if self.current_tier3_effect == "lock_overlay":
            # Gaim locks the window in front of everything for the block,
            # and lets go the moment it's not FOCUS any more.
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
            # _on_skip() never calls _on_phase_ended() (where ambient.stop()
            # normally lives), so this branch has to stop it too.
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
        """Writes one history entry for the focus block being timed, if
        there is one -- from _on_phase_ended (finished), _on_skip, and
        _on_reset (both cut short). Does nothing when no focus block is
        in progress."""
        if self._focus_block_start is None:
            return
        now = datetime.now()
        if completed:
            duration = self._focus_block_planned_seconds
        else:
            elapsed = self._focus_block_planned_seconds - self.session.remaining_seconds
            duration = max(0, elapsed)
            if duration == 0:
                # Entering FOCUS and skipping it without ever pressing Start
                # isn't a session you worked. Don't log a zero-second row.
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
            # A disk problem (full disk, a locked file, cloud sync) must
            # never stop the cleanup that runs right after this. Only
            # OSError is swallowed -- a real bug still shows up.
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
        # Disk writes go LAST, after all the cleanup above, so a failing
        # write can never strand the app halfway through a phase change.
        self.observations.save()
        self._log_focus_block_if_any(completed=True)

        # Tier 5 pages and Insights read history, so show this block now.
        for route_id in ("rider", "insights"):
            page = self.pages.get(route_id)
            if page is not None:
                try:
                    page.refresh()
                except Exception:
                    pass

        self._sync_mirror_layout()
        self._sync_mirror_divider()

    # ================================================================== #
    # The Start / Skip / Reset buttons
    # ================================================================== #
    def _on_toggle(self) -> None:
        # X's gimmick: starting fresh (not resuming) needs a goal first.
        if self.current_tier3_effect == "goal_gate" and self.session.phase is Phase.IDLE:
            self._show_goal_gate()
            return
        self._do_toggle()

    def _do_toggle(self) -> None:
        was_running = self.session.is_running
        for event in self.session.toggle():
            if event is Event.PHASE_STARTED:
                self._on_phase_started()

        # Resuming a phase that already started sends no event, so we
        # check and update things ourselves here.
        if not was_running and self.session.is_running:
            if self.session.phase is Phase.FOCUS:
                # A FOCUS phase is often entered, then sits paused until you
                # press Start. History goes by `start`, so take the start
                # time again at the real "began working" moment -- but only
                # if nothing has counted down yet (not a resume mid-block).
                if self.session.remaining_seconds >= self._focus_block_planned_seconds:
                    self._focus_block_start = datetime.now()
                if self.current_task_id is not None:
                    try:
                        self.tasks.set_status(self.current_task_id, TaskStatus.IN_PROGRESS)
                    except OSError:
                        # A disk failure here must not stop the watching
                        # below from starting.
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
        # Reset during a Ryuki break must flip the window back, too.
        self._sync_mirror_layout()
        self._sync_mirror_divider()
        self._refresh_timer_widgets()

    # ------------------------------------------------------------------ #
    # Zeztz's keyboard shortcuts
    # ------------------------------------------------------------------ #
    def _zeztz_hotkeys_active(self) -> bool:
        """False unless Zeztz is picked, and also while you're typing in a
        text box -- otherwise 's' or 'r' would type AND skip/reset."""
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

    # ================================================================== #
    # The activity list, and teaching the model as you go
    # ================================================================== #
    def _log_activity(self, window: WindowInfo, verdict) -> None:
        """
        Adds a window to the list -- every window, not just blocked ones --
        combining it with the row above if it's the very same app again.
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
        page = self.pages.get("activity")
        if page is not None:
            page.render()

    def _correct(self, entry: dict, label: str) -> None:
        """
        Teaches the model from one click, and saves it right away. The
        very next check already uses what it just learned.
        """
        self.model.learn(entry["text"], label)
        self.model.save(MODEL_PATH)
        entry["corrected"] = label

        # Also save this into the training data, so `train.py` doesn't ask
        # about a window you already corrected here.
        self.observations.label_by_text(entry["text"], label)
        self.observations.save()

        # "This was studying" is a strong hint the app should just always
        # be allowed -- so we do that for you right away.
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
        """Puts the saved lists back into the Blocking page's boxes."""
        page = self.pages.get("blocking")
        if page is not None:
            page.sync_list_boxes()
            page.refresh_summary()

    def _update_model_stats(self) -> None:
        """Shows how big the model is, and nudges you toward `train.py label`."""
        total = sum(self.model.label_counts.values())
        detail = f"{len(self.model.vocabulary)} words known"
        pending = len(self.observations.pending())
        if pending:
            detail += f" · {pending} to label"
        self._model_stats_text = (f"{total} examples", detail)
        page = self.pages.get("activity")
        if page is not None:
            page.set_model_stats(*self._model_stats_text)

    # ================================================================== #
    # Redrawing the Focus page
    # ================================================================== #
    def _focus_look(self) -> str:
        if self._zero_ui_on:
            return "zero_ui"
        if self.current_tier4_effect == "dashboard_cards":
            return "dashboard"
        return "normal"

    def _sync_focus_layout(self) -> None:
        """Tell the Focus page which look to show right now (it does
        nothing if that's already showing)."""
        if not self._focus_ready:
            return
        mode = "shape" if self.current_tier1_effect in SHAPE_EFFECTS else "bar"
        self.focus_page.restack(self._focus_look(), mode)

    # Old name, kept: shows the plain bar or the Tier 1 shape.
    _sync_progress_widget_visibility = _sync_focus_layout

    def _sync_zero_ui_visibility(self) -> None:
        """
        Amazon's "zero UI": during a focus block, the Focus page shows only
        a draining green field and three tiny buttons, and the side bar
        hides. Any other time (break, idle) everything looks normal.
        """
        active = self.current_tier3_effect == "zero_ui" and self.session.phase is Phase.FOCUS
        if active != self._zero_ui_on:
            self._zero_ui_on = active
            if active:
                if self.router.active != FIRST_ROUTE_ID:
                    self._zero_ui_saved_route = self.router.active
                    self.navigate(FIRST_ROUTE_ID)
                if self.sidebar is not None:
                    self.sidebar.grid_remove()
            if not self._focus_ready:
                pass
            elif active:
                self.start_button.configure(text="⏸" if self.session.is_running else "▶")
                self.skip_button.configure(text="⏭")
                self.reset_button.configure(text="⟲")
            else:
                self.start_button.configure(
                    text="Pause" if self.session.is_running else self._henshin_word())
                self.skip_button.configure(text="Skip")
                self.reset_button.configure(text="Reset")
            if not active:
                if self.sidebar is not None and not self.sidebar.winfo_manager():
                    self.layout.grid(self.sidebar, total_columns=2, row=2, column=0, sticky="nsw")
                saved, self._zero_ui_saved_route = self._zero_ui_saved_route, None
                if saved and self.router.has(saved):
                    self.navigate(saved)
        self._sync_focus_layout()

    def _sync_camera_indicator(self) -> None:
        """The "Phone check" card. It says "Camera monitoring active" ONLY
        while the camera is really open -- exactly as before."""
        if not self._focus_ready:
            return
        card = self.focus_page.camera_card
        active = (
            self.config_obj.camera_monitoring_enabled
            and self.session.phase is Phase.FOCUS
            and self.session.is_running
            and self.camera_watcher.is_capturing
        )
        if not CAMERA_BACKEND_AVAILABLE:
            card.set("Unavailable", "Needs OpenCV", self.palette.text_muted)
        elif active:
            card.set("ON", "Camera monitoring active", t.SUCCESS)
        elif self.config_obj.camera_monitoring_enabled:
            card.set("ON", "Camera idle until focus runs", self.palette.text_primary)
        else:
            card.set("OFF", "Camera idle", self.palette.text_muted)

    def _refresh_status_cards(self) -> None:
        if not self._focus_ready:
            return
        page = self.focus_page
        c = self.config_obj
        if not BACKEND_AVAILABLE:
            page.blocking_card.set("Unavailable", "App detection isn't installed", t.WARNING)
        elif c.enforcement_enabled:
            detail = f"{len(c.blocklist)} apps blocked"
            if c.hard_mode:
                detail += " · Hard mode"
            page.blocking_card.set("ON", detail, t.SUCCESS)
        else:
            page.blocking_card.set("OFF", "Nothing gets blocked", t.DANGER)
        watching = self._watching_text if (self.session.phase is Phase.FOCUS
                                           and self.monitor.is_active) else ""
        page.watch_card.set(watching or "Nothing yet",
                            "The window you're on" if watching else "Only during a focus block")

    def _set_kabuto_revealed(self, revealed: bool) -> None:
        """Called on hover enter/leave over the timer digits."""
        self._kabuto_revealed = revealed
        self._refresh_timer_widgets()

    def _refresh_timer_widgets(self) -> None:
        p = self.palette
        phase = self.session.phase
        label = label_for(phase, self._effective_terminology())
        progress_fraction = self.session.progress
        if not self._focus_ready:
            # The Focus page isn't drawn yet: only keep the parts that live
            # outside it up to date (background effects, badges, title bar,
            # Ghost's floating clock).
            self._refresh_outside_focus(phase, label, progress_fraction)
            return
        page = self.focus_page

        driver_text = self._driver_label_text()
        if phase is Phase.FOCUS and self.current_tier3_effect == "goal_gate" and self.current_goal_text:
            driver_text = self.current_goal_text.upper()
        page.timer.driver_label.configure(text=driver_text)

        hide_kabuto_digits = (
            self.current_tier4_effect == "hidden_timer"
            and phase is Phase.FOCUS
            and not self._kabuto_revealed
        )
        page.timer.time_label.configure(
            text="--:--" if hide_kabuto_digits else self.session.format_remaining())

        # The bar uses the vivid Rider color; the WORDS use the
        # always-readable version, so pale Riders like Fourze stay legible.
        fill_color = {
            Phase.FOCUS: p.accent,
            Phase.SHORT_BREAK: t.SUCCESS,
            Phase.LONG_BREAK: t.SUCCESS,
            Phase.IDLE: p.text_muted,
        }[phase]
        text_color = {
            Phase.FOCUS: p.accent_text,
            Phase.SHORT_BREAK: t.SUCCESS,
            Phase.LONG_BREAK: t.SUCCESS,
            Phase.IDLE: p.text_secondary,
        }[phase]

        if phase is Phase.FOCUS:
            # Agito: the color wakes up brighter over the block.
            if self.current_tier1_effect == "color_interpolation":
                primary_light, primary_dark = self.rider_primary_pair
                fill_color = (
                    interpolate_agito_color(progress_fraction, primary_light),
                    interpolate_agito_color(progress_fraction, primary_dark),
                )
            # Drive: bend the NUMBER fed to the bar, so it starts slow and
            # speeds up near the end.
            if self.current_tier1_effect == "accelerating_fill":
                progress_fraction = ease_drive_progress(progress_fraction)

        suffix = " (paused)" if self.session.is_paused and phase is not Phase.IDLE else ""
        page.timer.phase_label.configure(text=label + suffix, text_color=text_color)

        self._sync_focus_layout()
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
            self.start_button.configure(text="⏸" if self.session.is_running else "▶")
        else:
            self.start_button.configure(
                text="Pause" if self.session.is_running else self._henshin_word())

        done = self.session.completed_focus_blocks
        until_long = self.session.blocks_until_long_break
        if self._is_tokusatsu():
            streak_text = f"{done} mission{'s' if done != 1 else ''} complete · Full Recovery in {until_long}"
        else:
            streak_text = f"{done} session{'s' if done != 1 else ''} complete · Long break in {until_long}"
        page.timer.streak_label.configure(text=streak_text)

        if self.current_tier4_effect == "dashboard_cards":
            # Zero-One: the same numbers, as four cards.
            cards = page.dashboard_cards
            cards["status"].set(label)
            cards["time"].set(self.session.format_remaining())
            cards["streak"].set(str(done))
            cards["profile"].set(self._driver_label_text())

        self._refresh_top_badges(phase, label)
        # The title bar shows a tiny timer too, visible even when this
        # window is behind others.
        title_time = "--:--" if hide_kabuto_digits else self.session.format_remaining()
        self.title(f"{title_time} · {label} — Lock In")
        self._sync_camera_indicator()
        self._refresh_status_cards()
        self._refresh_ghost_widget()

    def _refresh_outside_focus(self, phase: Phase, label: str, progress_fraction: float) -> None:
        if phase is Phase.FOCUS and self.current_tier1_effect == "accelerating_fill":
            progress_fraction = ease_drive_progress(progress_fraction)
        if (self.current_tier1_effect in ("border_glow", "night_overlay")
                or self.current_tier3_effect == "lock_overlay"
                or self.current_tier4_effect == "mirror_flip"):
            self._refresh_background_effect(progress_fraction)
        self._refresh_top_badges(phase, label)
        hidden = (self.current_tier4_effect == "hidden_timer" and phase is Phase.FOCUS
                  and not self._kabuto_revealed)
        title_time = "--:--" if hidden else self.session.format_remaining()
        self.title(f"{title_time} · {label} — Lock In")
        self._refresh_ghost_widget()

    def _refresh_top_badges(self, phase: Phase, label: str) -> None:
        if phase is Phase.IDLE:
            self.phase_badge.set(label, "neutral")
        elif self.session.is_paused:
            self.phase_badge.set(f"{label} · paused", "warning")
        elif phase.is_break:
            self.phase_badge.set(label, "success")
        else:
            words = f"{label} active" if not self._is_tokusatsu() else label
            self.phase_badge.set(words, "accent")
        locked = self.current_tier3_effect == "lock_overlay" and phase is Phase.FOCUS
        if locked and not self.lock_badge.winfo_manager():
            self.layout.pack(self.lock_badge, side="right", padx=(0, t.SPACE_2))
        elif not locked and self.lock_badge.winfo_manager():
            self.lock_badge.pack_forget()

    def _refresh_progress_shape(self, progress_fraction: float) -> None:
        """Redraw the picture for a Tier 1 Rider with its own progress
        shape -- a light-mode and a dark-mode version, as always. Skipped
        when the picture would come out the same as last time (the bar
        only moves about one pixel every few seconds)."""
        key = (self.current_tier1_effect, round(progress_fraction * PROGRESS_SHAPE_WIDTH))
        if key == getattr(self, "_shape_key", None) and hasattr(self, "_progress_shape_image"):
            return
        self._shape_key = key
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
        if self.progress_shape.cget("image") is not self._progress_shape_image:
            self.progress_shape.configure(image=self._progress_shape_image)

    def _refresh_zero_ui_drain(self, progress_fraction: float) -> None:
        """Redraw Amazon's draining field. Its green never depends on
        light/dark mode, so both halves get the same picture."""
        key = round(progress_fraction * ZERO_UI_HEIGHT)
        if key == getattr(self, "_drain_key", None) and hasattr(self, "_zero_ui_image"):
            return
        self._drain_key = key
        drain = render_amazon_drain(ZERO_UI_WIDTH, ZERO_UI_HEIGHT, progress_fraction)
        if hasattr(self, "_zero_ui_image"):
            self._zero_ui_image.configure(light_image=drain, dark_image=drain)
        else:
            self._zero_ui_image = ctk.CTkImage(
                light_image=drain, dark_image=drain, size=(ZERO_UI_WIDTH, ZERO_UI_HEIGHT),
            )
        if self.zero_ui_label.cget("image") is not self._zero_ui_image:
            self.zero_ui_label.configure(image=self._zero_ui_image)

    def _update_watch_label(self, window: WindowInfo) -> None:
        if self.session.phase is Phase.FOCUS and self.monitor.is_active:
            self._watching_text = window.display
        else:
            self._watching_text = ""

    # ================================================================== #
    # Messages
    # ================================================================== #
    def _warn_if_app_detection_unavailable(self) -> None:
        """
        A clear on-screen warning if blocking can't work at all. run.bat
        opens the app with no console window, so the warning main.py
        prints would be thrown away -- this makes sure it's seen.
        """
        if not BACKEND_AVAILABLE:
            self._show_banner(
                "Blocking isn't working: pywin32 and psutil aren't "
                "installed, so the app can't see which window you're in. "
                "Run: pip install pywin32 psutil",
                "high", duration_ms=20000,
            )

    def _queue_banner(self, title: str, body: str, urgency: str) -> None:
        """Notifier calls this from any thread -- it's safe to use that way."""
        self._banner_queue.put((title, body, urgency))

    def _show_banner(self, text: str, urgency: str = "low", duration_ms: Optional[int] = None) -> None:
        """Shows a short message at the top of the page area for a little while."""
        bg, fg = t.BANNER_COLORS.get(urgency, t.BANNER_COLORS["low"])
        self.banner.configure(text=f"   {text}", fg_color=bg, text_color=fg)
        anchor = self.update_frame if self.update_frame.winfo_manager() else self.page_host
        self.layout.pack(self.banner, fill="x", padx=CONTENT_MARGIN, pady=(CONTENT_MARGIN, 0),
                         before=anchor)

        # Cancel any earlier "hide the banner" timer, so a new banner always
        # gets its own full time on screen.
        if self._banner_after_id is not None:
            try:
                self.after_cancel(self._banner_after_id)
            except Exception:
                pass
        self._banner_after_id = self.after(duration_ms or self.BANNER_MS, self.banner.pack_forget)

    # ================================================================== #
    def _on_close(self) -> None:
        """Saves everything and shuts down the background helpers cleanly."""
        try:
            self.config_obj.save()
            self.model.save(MODEL_PATH)
            self.observations.save()
        finally:
            try:
                self.buddy_link.close()
            except Exception:
                pass
            self.monitor.stop()
            self.ambient.stop()
            self.camera_watcher.stop()
            self.destroy()


def run() -> None:
    """This is what main.py calls to actually open the app."""
    LockInApp().mainloop()
