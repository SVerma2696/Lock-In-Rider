"""
ui/updates.py
=============
Checking for a newer Lock In, and the "Update ready" strip at the top of
the window. Same steps as before, just in their own file:

1. A background helper asks GitHub about the newest release (never on
   the screen's own thread, so the window can't freeze).
2. It posts the answer to the app's mailbox (an `UpdateChecked` note).
3. The app's heartbeat hands the note to `_on_update_checked`, on the
   screen's own thread, which shows it.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

from .. import __version__, updater
from ..application.events import UpdateChecked
from ..application.update_service import prepare_update

# update_fetch (web requests) and update_apply (unpacking) are loaded only
# when they're actually used -- a moment after launch, on the background
# helper -- so opening the app doesn't wait for them.
from ..session import Phase
from ..updater import UpdateInfo
from .host import AppHost


class UpdatesMixin(AppHost):
    def _start_update_check(self, manual: bool = False) -> None:
        """Kicks off a background check for a newer release: once at
        launch (quiet, and only if the Settings switch is on), and again
        whenever "Check for updates now" is clicked (always allowed, and
        it always answers out loud). Runs entirely off the main thread --
        fetching from GitHub, and (only for the packaged app) downloading
        and unpacking the update -- so it can never freeze the window."""
        if manual:
            # Even if the launch check is still running, the person
            # asked -- so whichever check finishes next answers them.
            self._update_message_wanted = True
            self._set_update_check_busy(True)
        elif not self.config_obj.check_for_updates:
            return
        if self._update_check_running:
            return
        self._update_check_running = True

        def run() -> None:
            # Every step (fetch, fingerprint check, download, unpack) lives
            # in prepare_update(), which never raises -- so this always
            # reports back exactly once, and the button can never get
            # stuck on "Checking...". Only the packaged app installs.
            result, extracted_path = prepare_update(
                __version__, sys.platform, can_install=getattr(sys, "frozen", False)
            )
            self.controller.events.post(UpdateChecked(result, extracted_path))

        threading.Thread(target=run, daemon=True, name="update-check").start()

    def _on_update_checked(self, event: UpdateChecked) -> None:
        """The background check reports back here, on the main thread. A
        found update always shows the strip at the top; the words next to
        the button only appear if somebody asked for them."""
        result, extracted_path = event.result, event.extracted_path
        self._update_check_running = False
        if result.status == updater.CHECK_AVAILABLE and result.info is not None:
            self._show_update_ready_frame(result.info, extracted_path)
        if self._update_message_wanted:
            self._update_message_wanted = False
            self._set_update_check_busy(False)
            self._set_update_status_text(
                updater.check_message(result, __version__, can_restart=extracted_path is not None)
            )

    def _on_check_updates_clicked(self) -> None:
        """The "Check for updates now" button."""
        if self._pending_update is not None:
            # Already found one earlier this run -- no need to ask again.
            info, extracted_path = self._pending_update
            self._set_update_status_text(
                updater.check_message(
                    updater.CheckResult(updater.CHECK_AVAILABLE, info=info, latest=info.version),
                    __version__,
                    can_restart=extracted_path is not None,
                )
            )
            return
        self._start_update_check(manual=True)

    # ------------------------------------------------------------------ #
    # The button and its sentence live on the Settings page, which gets
    # rebuilt now and then -- so the app remembers them and puts them back.
    # ------------------------------------------------------------------ #
    def _settings_update_widgets(self):
        page = self.pages.get("settings")
        if page is None:
            return None, None
        return getattr(page, "update_check_button", None), getattr(
            page, "update_check_status", None
        )

    def _set_update_check_busy(self, busy: bool) -> None:
        """Greys the button out and says "Checking..." while a check runs."""
        self._update_check_busy = busy
        if busy:
            self._update_status_text = ""
        self._restore_update_check_state()

    def _set_update_status_text(self, text: str) -> None:
        self._update_status_text = text
        self._restore_update_check_state()

    def _restore_update_check_state(self) -> None:
        button, status = self._settings_update_widgets()
        try:
            if button is not None:
                if self._update_check_busy:
                    button.configure(state="disabled", text="Checking…")
                else:
                    button.configure(state="normal", text="Check for updates now")
            if status is not None:
                status.configure(text=self._update_status_text)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    def _show_update_ready_frame(self, info: UpdateInfo, extracted_path: Path | None) -> None:
        """Shows the "update ready" strip at the top of the window. It
        stays until you act on it. extracted_path is None when running
        from source -- there's no file to swap then, so the restart
        button hides and the words point at the Releases page instead."""
        self._pending_update = (info, extracted_path)
        if extracted_path is None:
            self.update_label.configure(
                text=f"Lock In v{info.version} is available — see the Releases page."
            )
            self.update_restart_button.pack_forget()
        else:
            self.update_label.configure(text=f"Update ready — v{info.version}")
            self.layout.pack(self.update_restart_button, side="right", padx=(0, 10), pady=8)
        self.layout.pack(self.update_frame, fill="x", padx=12, pady=(12, 0), before=self.page_host)

    def _on_restart_update_clicked(self) -> None:
        """Swaps in the new version and reopens the app -- but never in
        the middle of a focus block or the lockdown screen. Checked at
        click time, since a block could have started since."""
        if self._pending_update is None:
            return
        info, extracted_path = self._pending_update
        if extracted_path is None:
            return  # no button should be visible in this case; guard anyway

        if self.session.phase is Phase.FOCUS or self._lockdown_window is not None:
            self._show_banner("Finish your focus block first.", "normal")
            return

        # The unpacked update waits in the OS temp folder, maybe for
        # hours -- a cleaner could have swept it away. exists() never
        # raises, even if the whole temp folder is gone.
        if not extracted_path.exists():
            self._show_banner(
                "That update is no longer available — it'll be checked "
                "again next time you open the app.",
                "normal",
            )
            self._pending_update = None
            self.update_frame.pack_forget()
            return

        from .. import update_apply

        current_path = update_apply.current_app_path(sys.platform)
        script_path = update_apply.write_relauncher_script(
            extracted_path.parent,
            current_path,
            extracted_path,
            pid=update_apply.app_process_id(),
            platform=sys.platform,
        )
        update_apply.launch_relauncher_and_quit(script_path, sys.platform)
        self._on_close()
