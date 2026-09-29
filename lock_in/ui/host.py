"""
ui/host.py
==========
What the window's add-on parts (preferences.py, overlays.py, updates.py,
gestures.py, revice.py) can use from the main window.

Those parts are "mixins": pieces of LockInApp kept in their own files.
When the app runs they're always part of the main window, but a type
checker reading one file on its own can't know that. `AppHost` tells it.

Only the type checker ever sees this class. When the app runs, AppHost
is plain `object`, so nothing about how the app works changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import customtkinter as ctk

    from ..ambient import AmbientPlayer
    from ..application import AppController
    from ..camera_enforcer import PhoneWatcher
    from ..classifier import NaiveBayesClassifier
    from ..claude_fallback import ClaudeFallback
    from ..config import Config
    from ..observations import ObservationStore
    from ..rider_effects import Era
    from ..rider_themes import RiderAbilities
    from ..session import PomodoroSession
    from ..updater import UpdateInfo
    from .mirror import MirrorLayout
    from .router import Router
    from .theme import Palette

    class AppHost(ctk.CTk):
        # ---- Owned by the controller (read through the window) ---------- #
        controller: AppController

        @property
        def config_obj(self) -> Config: ...
        @property
        def session(self) -> PomodoroSession: ...
        @property
        def model(self) -> NaiveBayesClassifier: ...
        @model.setter
        def model(self, value: NaiveBayesClassifier) -> None: ...
        @property
        def observations(self) -> ObservationStore: ...
        @property
        def claude(self) -> ClaudeFallback: ...
        @property
        def ambient(self) -> AmbientPlayer: ...
        @property
        def camera_watcher(self) -> PhoneWatcher: ...

        # ---- The window's own state -------------------------------------- #
        abilities: RiderAbilities
        palette: Palette
        layout: MirrorLayout
        router: Router
        pages: dict[str, Any]
        display_font: str
        current_era: Era
        color_focus: tuple[str, str]
        color_focus_text: tuple[str, str]
        color_lockdown_text: str
        page_host: ctk.CTkFrame
        update_frame: ctk.CTkFrame
        update_label: ctk.CTkLabel
        update_restart_button: ctk.CTkButton
        _lockdown_window: ctk.CTkToplevel | None
        _claude_status_labels: list[Any]
        _pending_update: tuple[UpdateInfo, Path | None] | None
        _update_check_running: bool
        _update_message_wanted: bool
        _update_check_busy: bool
        _update_status_text: str
        _ghost_widget: ctk.CTkToplevel | None

        # ---- The window's own methods ------------------------------------ #
        def _show_banner(
            self, text: str, urgency: str = "low", duration_ms: int | None = None
        ) -> None: ...
        def _is_tokusatsu(self) -> bool:
            raise NotImplementedError

        def _effective_terminology(self) -> str:
            raise NotImplementedError

        def navigate(self, route_id: str) -> bool:
            raise NotImplementedError

        def _page(self, route_id: str) -> Any: ...
        def _do_toggle(self) -> None: ...
        def _on_reset(self) -> None: ...
        def _on_close(self) -> None: ...
        def _apply_rider_theme(self) -> None: ...
        def _rebuild_pages(self, initial: bool = False) -> None: ...
        def _sync_zero_ui_visibility(self) -> None: ...
        def _sync_mirror_layout(self) -> None: ...
        def _sync_mirror_divider(self) -> None: ...
        def _sync_camera_indicator(self) -> None: ...
        def _update_model_stats(self) -> None: ...
        def _render_tasks(self) -> None: ...
        def _refresh_current_task_picker(self) -> None: ...
        def _after(self, name: str, delay_ms: int, callback: Callable[[], object]) -> None: ...

else:
    AppHost = object

__all__ = ["AppHost"]
