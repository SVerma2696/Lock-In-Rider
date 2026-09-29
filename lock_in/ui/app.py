"""
ui/app.py
=========
The main Lock In window. It shows things and passes your clicks on;
the deciding happens in lock_in/application/ (the AppController).

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
each one only posts a small note to one mailbox (the controller's
`events`, see application/events.py). The app's heartbeat (`_pump`,
five times a second) hands those notes out on the screen's own thread.
It is the only place that changes what you see.

Where things live
-----------------
    app.py          this file: the window, its heartbeat, the pages
    effects.py      the Rider pictures (glow, era strip, progress shapes)
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
import logging
import sys

import customtkinter as ctk
from PIL import ImageTk

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

from ..application import (
    AppController,
    BannerRequested,
    ClaudeAnswered,
    PhoneSample,
    UpdateChecked,
    WindowSeen,
)
from ..application.enforcement_controller import Decision
from ..camera_enforcer import CAMERA_BACKEND_AVAILABLE
from ..config import app_data_dir
from ..diagnostics import setup_logging
from ..enforcer import Action, WindowInfo, message_for
from ..monitor import BACKEND_AVAILABLE, minimize_window
from ..rider_effects import DisplayEffect, EnforcementEffect, ProgressEffect
from ..rider_themes import (
    DEFAULT_RIDER_THEME,
    RIDER_THEMES,
    STANDARD_THEME,
    RiderAbilities,
    desaturate,
)
from ..session import Event, Phase, label_for
from ..tier5 import TIER5_BUILDERS
from ..visuals import (
    SHAPE_EFFECTS,
    display_font_family,
    ease_drive_progress,
    interpolate_agito_color,
    load_app_icon,
    load_pixel_font,
)
from . import theme as t
from .components import Sidebar, StatusBadge
from .components.box import Box
from .effects import DIVIDER_HEIGHT, BackgroundState, RiderVisuals
from .gestures import WizardGesturesMixin
from .mirror import MirrorLayout, mirrored_column
from .overlays import OverlaysMixin
from .pages import PAGE_CLASSES
from .pages.base import tasks_signature
from .preferences import PreferencesMixin
from .revice import ReviceMixin
from .router import FIRST_ROUTE_ID, Router, build_routes
from .updates import UpdatesMixin

logger = logging.getLogger(__name__)

# The nicer-looking font for the timer digits and headings. Picked once
# per computer in visuals.py -- see that file for why.
DISPLAY_FONT = display_font_family()

# The gap around the page area, where the background picture shows.
CONTENT_MARGIN = t.SPACE_3


class LockInApp(
    OverlaysMixin, UpdatesMixin, WizardGesturesMixin, ReviceMixin, PreferencesMixin, ctk.CTk
):
    """The main app window -- everything you see lives inside this."""

    UI_TICK_MS = 200  # how often we redraw the countdown, in milliseconds
    BANNER_MS = 6000  # how long a pop-up banner stays on screen, in milliseconds

    def __init__(self, controller: AppController | None = None) -> None:
        super().__init__()

        # ---------------- Everything that isn't drawing ----------------- #
        # The timer, tasks, history, blocking, camera, Claude helper,
        # notifications, and Revice's link all live in the controller
        # (lock_in/application/). This window shows what it says.
        self.controller = controller or AppController()
        self.display_font = DISPLAY_FONT
        self.layout = MirrorLayout(lambda: self._is_mirrored)
        # Which way the widgets are flipped right now (Ryuki's mirror).
        self._layout_mirrored = False
        self.visuals = RiderVisuals()
        self._apply_rider_theme()
        # X's goal-entry gate stores what you typed here -- in memory
        # only, reset every time the app restarts.
        self.current_goal_text = ""
        # Kabuto's hidden timer: True only while you hover the digits.
        self._kabuto_revealed = False

        self._lockdown_window: ctk.CTkToplevel | None = None
        self._ghost_widget: ctk.CTkToplevel | None = None
        self._banner_after_id: str | None = None
        # Timers the window set with after(), by name, so closing the
        # window can cancel every one of them.
        self._after_ids: dict[str, str] = {}
        self._closing = False
        # (UpdateInfo, Optional[Path]) once the background check finds one.
        self._pending_update: tuple | None = None
        self._update_check_running = False
        self._update_message_wanted = False
        self._update_check_busy = False
        self._update_status_text = ""

        # Things the pages remember while they're redrawn.
        self.pages: dict = {}
        self.sidebar: Sidebar | None = None
        self._retired: list = []
        self._page_order: list = []
        self._retire_after: str | None = None
        self._claude_status_labels: list = []
        self._task_filter = "All"
        self._expanded_tasks: dict = {}
        self._watching_text = ""
        self._zero_ui_on = False
        self._zero_ui_saved_route: str | None = None

        # Which function handles which note from the background helpers.
        events = self.controller.events
        events.subscribe(WindowSeen, self._on_window_seen)
        events.subscribe(PhoneSample, self._on_phone_sample)
        events.subscribe(ClaudeAnswered, self._on_claude_answered)
        events.subscribe(BannerRequested, self._on_banner_requested)
        events.subscribe(UpdateChecked, self._on_update_checked)

        # ---------------- The window frame ------------------------------ #
        ctk.set_appearance_mode(self.config_obj.appearance)
        ctk.set_default_color_theme(self.config_obj.accent)

        self.title("Lock In")
        self.geometry(f"{t.WINDOW_SIZE[0]}x{t.WINDOW_SIZE[1]}")
        self.minsize(*t.WINDOW_MIN_SIZE)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_app_icon()

        self._make_setting_vars()
        self.router = Router(
            show=self._show_page, hide=self._hide_page, on_change=self._on_route_changed
        )
        self._build_shell()
        self._rebuild_pages(initial=True)

        # Zeztz's keyboard shortcuts. Each one checks for itself whether
        # Zeztz is picked, so a Rider change needs no re-binding.
        self.bind_all("<space>", self._on_zeztz_space)
        self.bind_all("s", self._on_zeztz_skip)
        self.bind_all("r", self._on_zeztz_reset)
        self._bind_wizard_gestures()

        self.controller.start()
        self._pump()  # start the heartbeat
        self._refresh_timer_widgets()
        # Wait a moment, so the window is fully drawn before a banner shows.
        self._after("detection_warning", 400, self._warn_if_app_detection_unavailable)
        self._after("update_check", 2000, self._start_update_check)

    # ================================================================== #
    # The parts the controller owns, under the names the pages use
    # ================================================================== #
    @property
    def config_obj(self):
        return self.controller.config

    @property
    def session(self):
        return self.controller.session

    @property
    def model(self):
        return self.controller.model

    @model.setter
    def model(self, value) -> None:
        # "Rebuild model" swaps in a fresh model; blocking must use it too.
        self.controller.model = value
        self.controller.enforcement.model = value

    @property
    def observations(self):
        return self.controller.observations

    @property
    def tasks(self):
        return self.controller.tasks

    @property
    def history(self):
        return self.controller.history

    @property
    def claude(self):
        return self.controller.claude

    @property
    def enforcer(self):
        return self.controller.enforcement.enforcer

    @property
    def camera_enforcer(self):
        return self.controller.enforcement.camera_enforcer

    @property
    def notifier(self):
        return self.controller.notifier

    @property
    def ambient(self):
        return self.controller.ambient

    @property
    def monitor(self):
        return self.controller.monitor

    @property
    def camera_watcher(self):
        return self.controller.camera_watcher

    @property
    def buddy_link(self):
        return self.controller.buddy.link

    @property
    def activity(self) -> list[dict]:
        """The Activity page's rows (see ActivityLog)."""
        return self.controller.enforcement.activity.entries

    @property
    def current_task_id(self) -> str | None:
        return self.controller.tasks_ctl.current_task_id

    @current_task_id.setter
    def current_task_id(self, value: str | None) -> None:
        self.controller.tasks_ctl.current_task_id = value

    # The picked Rider's powers, under their older Tier names.
    @property
    def current_tier1_effect(self) -> ProgressEffect:
        return self.abilities.progress

    @property
    def current_tier2_effect(self):
        return self.abilities.preset

    @property
    def current_tier3_effect(self) -> EnforcementEffect:
        return self.abilities.enforcement

    @property
    def current_tier4_effect(self) -> DisplayEffect:
        return self.abilities.display

    @property
    def current_tier5_effect(self):
        return self.abilities.productivity

    @property
    def current_tier6_effect(self):
        return self.abilities.interaction

    def _after(self, name: str, delay_ms: int, callback) -> None:
        """after(), remembered by name so _on_close() can cancel it. A
        timer set again under the same name replaces the old one."""
        if self._closing:
            return
        old = self._after_ids.pop(name, None)
        if old is not None:
            try:
                self.after_cancel(old)
            except Exception:
                pass

        def run() -> None:
            self._after_ids.pop(name, None)
            callback()

        self._after_ids[name] = self.after(delay_ms, run)

    def report_callback_exception(self, kind, error, trace) -> None:
        """An error inside a button click or timer. The screen toolkit
        normally prints it to a console, which the packaged app doesn't
        have -- so it goes to the log instead. The app keeps running."""
        logger.error("Error in a window callback", exc_info=(kind, error, trace))

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
                        ico_path,
                        format="ICO",
                        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
                    )
                self.iconbitmap(default=str(ico_path))
            except Exception:
                logger.warning("Couldn't set the Windows title-bar icon", exc_info=True)

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
        theme = (
            STANDARD_THEME
            if self.config_obj.standard_mode
            else RIDER_THEMES.get(self.config_obj.rider_theme, RIDER_THEMES[DEFAULT_RIDER_THEME])
        )
        # ZX's whole gimmick is going monochrome. Swapping in a grey copy
        # of the theme HERE means every color made from it below comes out
        # grey automatically -- widgets and drawn pictures alike.
        if theme.tier3_effect == EnforcementEffect.STEALTH_MUTE:
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

        # The picked Rider's powers, one per Tier, as typed values.
        # Standard Mode swaps in STANDARD_THEME above, so every one of them
        # is NONE there automatically -- no Wizard gestures, no buddy link.
        self.abilities: RiderAbilities = theme.abilities

        if self.abilities.display is DisplayEffect.CHIPTUNE_ALERT:
            self._active_display_font = load_pixel_font()
        else:
            self._active_display_font = DISPLAY_FONT
        self.rider_primary_pair = theme.primary
        self.rider_secondary_pair = theme.secondary

        self.visuals.apply_theme(theme, self.palette, self.config_obj.standard_mode)
        self._refresh_background_effect(self.session.progress)

    def _refresh_background_effect(self, progress_fraction: float) -> None:
        """Stronger's glow, Kiva's night tint, or Gaim's dimming on the
        background, during a focus block (see ui/effects.py)."""
        self.visuals.refresh_background(
            BackgroundState(
                progress_effect=self.abilities.progress,
                enforcement_effect=self.abilities.enforcement,
                in_focus=self.session.phase is Phase.FOCUS,
                mirrored=self._is_mirrored,
                progress=progress_fraction,
            )
        )

    def _sync_mirror_divider(self) -> None:
        """Ryuki's flip for the era strip under the top bar."""
        self.visuals.sync_divider(self._is_mirrored)

    # ================================================================== #
    # Ryuki's mirror (see ui/mirror.py)
    # ================================================================== #
    @property
    def _is_mirrored(self) -> bool:
        return self.abilities.display is DisplayEffect.MIRROR_FLIP and self.session.phase.is_break

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
            self.layout.pack(
                ctk.CTkLabel(brand, text="", image=self._brand_image, width=24, font=t.font()),
                side="left",
                padx=(0, t.SPACE_2),
            )
        self.brand_label = ctk.CTkLabel(
            brand,
            text="LOCK IN",
            text_color=p.text_primary,
            font=t.font(family=DISPLAY_FONT, size=15, weight="bold"),
        )
        self.layout.pack(self.brand_label, side="left")

        badges = Box(self.topbar)
        self.layout.pack(badges, side="right", padx=(0, t.SPACE_5))
        self.phase_badge = StatusBadge(badges, p, text="Ready", kind="neutral")
        self.layout.pack(self.phase_badge, side="right")
        # Gaim's padlock: shown only while Gaim locks the window on top.
        self.lock_badge = StatusBadge(badges, p, text="Locked on top", kind="warning", dot=False)
        self._badges_frame = badges

        # ---- the era strip ------------------------------------------------ #
        self._divider_label = ctk.CTkLabel(
            self, text="", image=self.visuals.divider_image, height=DIVIDER_HEIGHT, font=t.font()
        )
        self.layout.grid(
            self._divider_label, total_columns=2, row=1, column=0, columnspan=2, sticky="ew"
        )

        # ---- the page area ------------------------------------------------ #
        self.content = ctk.CTkFrame(self, fg_color=p.app_bg, corner_radius=0)
        self.layout.grid(self.content, total_columns=2, row=2, column=1, sticky="nsew")
        # Made FIRST so it sits behind everything else in the page area.
        self._bg_label = ctk.CTkLabel(
            self.content, text="", image=self.visuals.bg_image, font=t.font()
        )
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.content.bind("<Configure>", self._on_content_resized, add="+")

        # A short pop-up message. Starts hidden; _show_banner reveals it.
        self.banner = ctk.CTkLabel(
            self.content,
            text="",
            corner_radius=t.CONTROL_RADIUS,
            height=40,
            font=t.font(size=13),
            wraplength=640,
            justify="left",
            anchor="w",
        )
        # The "a new version is ready" strip. Unlike the banner, it stays
        # until you act on it. Starts hidden.
        self.update_frame = ctk.CTkFrame(
            self.content,
            fg_color=t.INFO_SOFT,
            corner_radius=t.CONTROL_RADIUS,
            border_width=1,
            border_color=t.INFO,
        )
        self.update_label = ctk.CTkLabel(
            self.update_frame,
            text="",
            text_color=t.INFO,
            font=t.font(size=12, weight="bold"),
            anchor="w",
        )
        self.layout.pack(
            self.update_label, side="left", padx=(12, 6), pady=8, fill="x", expand=True
        )
        self.update_restart_button = ctk.CTkButton(
            self.update_frame,
            text="Restart now",
            width=110,
            height=30,
            fg_color=t.INFO,
            text_color="#FFFFFF",
            command=self._on_restart_update_clicked,
            font=t.font(),
        )
        self.layout.pack(self.update_restart_button, side="right", padx=(0, 10), pady=8)

        self.page_host = ctk.CTkFrame(self.content, fg_color=p.app_bg, corner_radius=t.CARD_RADIUS)
        self.layout.pack(
            self.page_host, fill="both", expand=True, padx=CONTENT_MARGIN, pady=CONTENT_MARGIN
        )
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
        """Stretch the background picture to match the page area.
        CustomTkinter reports this from the frame's inner drawing area, so
        the size is read from the frame itself."""
        self.visuals.resize(
            (max(self.content.winfo_width(), 1), max(self.content.winfo_height(), 1)),
            max(self.winfo_width(), 1),
        )

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
        self.visuals.forget_page_images()
        if self.sidebar is not None:
            self._retire(self.sidebar)
        self._apply_shell_palette()

        self.sidebar = Sidebar(
            self,
            self.palette,
            layout=self.layout,
            on_select=self.navigate,
            rider_heading="Rider Gear" if self._is_tokusatsu() else "Rider",
        )
        self.layout.grid(self.sidebar, total_columns=2, row=2, column=0, sticky="nsw")
        routes = build_routes(
            self.abilities.productivity,
            self.abilities.interaction,
            known_tier5_effects=TIER5_BUILDERS,
        )
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
            self.layout.place(page.frame, relx=0.5, rely=0, anchor="n", relwidth=1, relheight=1)
        page.frame.lift()
        try:
            page.on_show()
        except Exception:
            logger.exception("Showing the %s page failed", route_id)

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
        """Rebuild the menu's choices from the open tasks (see TaskController)."""
        if not self._focus_ready:
            return
        values, showing = self.controller.tasks_ctl.menu()
        menu = self.current_task_menu
        menu.configure(values=values)
        menu.set(showing)

    def _on_current_task_selected(self, name: str) -> None:
        self.controller.tasks_ctl.select(name)

    def _render_tasks(self) -> None:
        page = self.pages.get("tasks")
        if page is not None:
            page.render()

    # ================================================================== #
    # The heartbeat -- keeps everything moving
    # ================================================================== #
    def _pump(self) -> None:
        """
        The one loop that runs the whole app: move the timer forward, hand
        out the notes the background helpers left, then redraw the screen.
        It schedules itself again every time, so it never gets stuck.
        """
        if self._closing:
            return
        try:
            for event in self.session.tick():
                if event is Event.PHASE_ENDED:
                    self._on_phase_ended()
                elif event is Event.PHASE_STARTED:
                    self._on_phase_started()

            self._dispatch_events()
            self._drain_buddy_link()
            self._refresh_timer_widgets()
        except Exception:
            logger.exception("A heartbeat step failed")
        finally:
            # Always schedule the next beat, even if something above broke
            # -- otherwise one bad moment would freeze the app forever.
            self._after("pump", self.UI_TICK_MS, self._pump)

    def _dispatch_events(self) -> int:
        """Hand every waiting note to its handler, on this (the screen's)
        thread. Returns how many there were."""
        return self.controller.events.dispatch_pending()

    def _on_window_seen(self, event: WindowSeen) -> None:
        """The window watcher saw you on a window: judge it, and act."""
        decision = self.controller.enforcement.judge_window(
            event.window, self.controller.focus_running
        )
        if decision is not None:
            self._apply_decision(decision)
        self._update_watch_label(event.window)

    def _on_phone_sample(self, event: PhoneSample) -> None:
        """The camera took one look: act on what it saw."""
        decision = self.controller.enforcement.judge_phone(
            event.seen, self.controller.focus_running
        )
        if decision is not None:
            self._apply_decision(decision)

    def _apply_decision(self, decision: Decision) -> None:
        if decision.new_activity_row:
            self._render_activity()
        if decision.action is not Action.NONE:
            self._perform(decision.action, decision.window, seconds=decision.seconds)

    def _on_claude_answered(self, event: ClaudeAnswered) -> None:
        """Claude's answer arrived: it also goes into the training data,
        so over time the local model needs to ask less and less."""
        self.controller.enforcement.learn_from_claude(event.text, event.verdict)

    def _on_banner_requested(self, event: BannerRequested) -> None:
        """The notifier can be called from any thread; its banners land here."""
        self._show_banner(f"{event.title} — {event.body}", event.urgency)

    # ================================================================== #
    # Doing something about a blocked window
    # ================================================================== #
    def _perform(self, action: Action, window: WindowInfo, seconds: float | None = None) -> None:
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
            self._after("raise_self", 120, self._raise_self)

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
        self.controller.enforcement.reset()
        self.controller.focus.phase_started()
        phase = self.session.phase

        if phase is Phase.FOCUS and self.abilities.enforcement is EnforcementEffect.STEALTH_MUTE:
            # ZX's Ninja Stealth: get out of the way the moment focus starts.
            self.iconify()

        if self.abilities.enforcement is EnforcementEffect.LOCK_OVERLAY:
            # Gaim locks the window in front of everything for the block,
            # and lets go the moment it's not FOCUS any more.
            self.attributes("-topmost", phase is Phase.FOCUS)

        if self.abilities.enforcement is EnforcementEffect.ZERO_UI:
            self._sync_zero_ui_visibility()
            self.config_obj.zero_grace_mode = phase is Phase.FOCUS

        if phase is Phase.FOCUS and self.session.is_running:
            self.controller.resume_watching()
            self.ambient.start_if_applicable()
            if self.abilities.display is DisplayEffect.GHOST_WIDGET:
                self._show_ghost_widget()
        else:
            # _on_skip() never calls _on_phase_ended() (where the sound is
            # normally stopped), so this branch stops it too.
            self.controller.pause_watching()
            self._close_lockdown()
            self._hide_ghost_widget()

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
        """Write the focus block being timed into history, if there is one
        (see FocusController.log_block)."""
        self.controller.focus.log_block(completed)

    def _on_phase_ended(self) -> None:
        self.controller.pause_watching()
        self._close_lockdown()
        self._hide_ghost_widget()
        if self.abilities.enforcement is EnforcementEffect.LOCK_OVERLAY:
            self.attributes("-topmost", False)
        if self.abilities.enforcement is EnforcementEffect.ZERO_UI:
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
                    logger.exception("Refreshing the %s page failed", route_id)

        self._sync_mirror_layout()
        self._sync_mirror_divider()

    # ================================================================== #
    # The Start / Skip / Reset buttons
    # ================================================================== #
    def _on_toggle(self) -> None:
        # X's gimmick: starting fresh (not resuming) needs a goal first.
        if (
            self.abilities.enforcement is EnforcementEffect.GOAL_GATE
            and self.session.phase is Phase.IDLE
        ):
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
                if self.controller.focus.work_resumed():
                    self._render_tasks()
                self.controller.resume_watching()
        else:
            self.controller.pause_watching()

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
        self.controller.enforcement.reset()
        self.controller.pause_watching()
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
        if self.abilities.display is not DisplayEffect.HOTKEYS:
            return False
        focused = self.focus_get()
        return focused is None or focused.winfo_class() not in ("Entry", "Text")

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
    def _render_activity(self) -> None:
        page = self.pages.get("activity")
        if page is not None:
            page.render()

    def _correct(self, entry: dict, label: str) -> None:
        """Teaches the model from one click, and saves it right away. The
        very next check already uses what it just learned."""
        allowed = self.controller.enforcement.correct(entry, label)
        if allowed:
            self._sync_list_boxes()
            self._show_banner(f"Learned. Also allow-listed {allowed}.", "low")
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
        if self.abilities.display is DisplayEffect.DASHBOARD_CARDS:
            return "dashboard"
        return "normal"

    def _sync_focus_layout(self) -> None:
        """Tell the Focus page which look to show right now (it does
        nothing if that's already showing)."""
        if not self._focus_ready:
            return
        mode = "shape" if self.abilities.progress in SHAPE_EFFECTS else "bar"
        self.focus_page.restack(self._focus_look(), mode)

    # Old name, kept: shows the plain bar or the Tier 1 shape.
    _sync_progress_widget_visibility = _sync_focus_layout

    def _sync_zero_ui_visibility(self) -> None:
        """
        Amazon's "zero UI": during a focus block, the Focus page shows only
        a draining green field and three tiny buttons, and the side bar
        hides. Any other time (break, idle) everything looks normal.
        """
        active = (
            self.abilities.enforcement is EnforcementEffect.ZERO_UI
            and self.session.phase is Phase.FOCUS
        )
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
                    text="Pause" if self.session.is_running else self._henshin_word()
                )
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
        watching = (
            self._watching_text
            if (self.session.phase is Phase.FOCUS and self.monitor.is_active)
            else ""
        )
        page.watch_card.set(
            watching or "Nothing yet",
            "The window you're on" if watching else "Only during a focus block",
        )

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
        if (
            phase is Phase.FOCUS
            and self.abilities.enforcement is EnforcementEffect.GOAL_GATE
            and self.current_goal_text
        ):
            driver_text = self.current_goal_text.upper()
        page.timer.driver_label.configure(text=driver_text)

        hide_kabuto_digits = (
            self.abilities.display is DisplayEffect.HIDDEN_TIMER
            and phase is Phase.FOCUS
            and not self._kabuto_revealed
        )
        page.timer.time_label.configure(
            text="--:--" if hide_kabuto_digits else self.session.format_remaining()
        )

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
            if self.abilities.progress is ProgressEffect.COLOR_INTERPOLATION:
                primary_light, primary_dark = self.rider_primary_pair
                fill_color = (
                    interpolate_agito_color(progress_fraction, primary_light),
                    interpolate_agito_color(progress_fraction, primary_dark),
                )
            # Drive: bend the NUMBER fed to the bar, so it starts slow and
            # speeds up near the end.
            if self.abilities.progress is ProgressEffect.ACCELERATING_FILL:
                progress_fraction = ease_drive_progress(progress_fraction)

        suffix = " (paused)" if self.session.is_paused and phase is not Phase.IDLE else ""
        page.timer.phase_label.configure(text=label + suffix, text_color=text_color)

        self._sync_focus_layout()
        if self.abilities.progress in SHAPE_EFFECTS:
            self._refresh_progress_shape(progress_fraction)
        else:
            self.progress.set(progress_fraction)
            self.progress.configure(progress_color=fill_color)

        if (
            self.abilities.progress in (ProgressEffect.BORDER_GLOW, ProgressEffect.NIGHT_OVERLAY)
            or self.abilities.enforcement is EnforcementEffect.LOCK_OVERLAY
            or self.abilities.display is DisplayEffect.MIRROR_FLIP
        ):
            self._refresh_background_effect(progress_fraction)

        if self.abilities.enforcement is EnforcementEffect.ZERO_UI and phase is Phase.FOCUS:
            self._refresh_zero_ui_drain(progress_fraction)
            self.start_button.configure(text="⏸" if self.session.is_running else "▶")
        else:
            self.start_button.configure(
                text="Pause" if self.session.is_running else self._henshin_word()
            )

        done = self.session.completed_focus_blocks
        until_long = self.session.blocks_until_long_break
        if self._is_tokusatsu():
            streak_text = (
                f"{done} mission{'s' if done != 1 else ''} complete · Full Recovery in {until_long}"
            )
        else:
            streak_text = (
                f"{done} session{'s' if done != 1 else ''} complete · Long break in {until_long}"
            )
        page.timer.streak_label.configure(text=streak_text)

        if self.abilities.display is DisplayEffect.DASHBOARD_CARDS:
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
        if phase is Phase.FOCUS and self.abilities.progress is ProgressEffect.ACCELERATING_FILL:
            progress_fraction = ease_drive_progress(progress_fraction)
        if (
            self.abilities.progress in (ProgressEffect.BORDER_GLOW, ProgressEffect.NIGHT_OVERLAY)
            or self.abilities.enforcement is EnforcementEffect.LOCK_OVERLAY
            or self.abilities.display is DisplayEffect.MIRROR_FLIP
        ):
            self._refresh_background_effect(progress_fraction)
        self._refresh_top_badges(phase, label)
        hidden = (
            self.abilities.display is DisplayEffect.HIDDEN_TIMER
            and phase is Phase.FOCUS
            and not self._kabuto_revealed
        )
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
        locked = (
            self.abilities.enforcement is EnforcementEffect.LOCK_OVERLAY and phase is Phase.FOCUS
        )
        if locked and not self.lock_badge.winfo_manager():
            self.layout.pack(self.lock_badge, side="right", padx=(0, t.SPACE_2))
        elif not locked and self.lock_badge.winfo_manager():
            self.lock_badge.pack_forget()

    def _refresh_progress_shape(self, progress_fraction: float) -> None:
        """A Tier 1 Rider's progress shape (drawn in ui/effects.py)."""
        image = self.visuals.progress_shape(
            self.abilities.progress,
            progress_fraction,
            self.rider_primary_pair,
            self.rider_secondary_pair,
        )
        if self.progress_shape.cget("image") is not image:
            self.progress_shape.configure(image=image)

    def _refresh_zero_ui_drain(self, progress_fraction: float) -> None:
        """Amazon's draining field (drawn in ui/effects.py)."""
        image = self.visuals.zero_ui_drain(progress_fraction)
        if self.zero_ui_label.cget("image") is not image:
            self.zero_ui_label.configure(image=image)

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
                "high",
                duration_ms=20000,
            )

    def _show_banner(self, text: str, urgency: str = "low", duration_ms: int | None = None) -> None:
        """Shows a short message at the top of the page area for a little while."""
        bg, fg = t.BANNER_COLORS.get(urgency, t.BANNER_COLORS["low"])
        self.banner.configure(text=f"   {text}", fg_color=bg, text_color=fg)
        anchor = self.update_frame if self.update_frame.winfo_manager() else self.page_host
        self.layout.pack(
            self.banner, fill="x", padx=CONTENT_MARGIN, pady=(CONTENT_MARGIN, 0), before=anchor
        )

        # Cancel any earlier "hide the banner" timer, so a new banner always
        # gets its own full time on screen.
        if self._banner_after_id is not None:
            try:
                self.after_cancel(self._banner_after_id)
            except Exception:
                pass
        self._banner_after_id = self.after(duration_ms or self.BANNER_MS, self._hide_banner)

    def _hide_banner(self) -> None:
        self._banner_after_id = None
        try:
            self.banner.pack_forget()
        except Exception:
            pass

    # ================================================================== #
    def _on_close(self) -> None:
        """Saves everything, stops every background helper, cancels every
        timer, and closes the window. Safe to call twice: the second call
        does nothing. One step failing never stops the steps after it."""
        if self._closing:
            return
        self._closing = True
        failed = self.controller.shutdown()
        if failed:
            logger.warning("Some clean-up steps failed while closing: %s", ", ".join(failed))
        for after_id in [*self._after_ids.values(), self._banner_after_id, self._retire_after]:
            if after_id is not None:
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
        self._after_ids.clear()
        for close in (self._close_lockdown, self._hide_ghost_widget):
            try:
                close()
            except Exception:
                logger.exception("Closing an extra window failed")
        try:
            self.destroy()
        except Exception:
            logger.exception("Destroying the window failed")


def run() -> None:
    """This is what main.py calls to actually open the app."""
    setup_logging()
    LockInApp().mainloop()
