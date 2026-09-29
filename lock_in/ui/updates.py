"""
ui/updates.py
=============
Checking for a newer Lock In, and the "Update ready" strip at the top of
the window. Same steps as before, just in their own file:

1. A background helper asks GitHub about the newest release (never on
   the screen's own thread, so the window can't freeze).
2. It drops the answer in a waiting line (`_update_queue`).
3. The app's heartbeat picks the answer up and shows it.
"""

from __future__ import annotations

import queue
import shutil
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

from .. import __version__, updater
# update_fetch (web requests) and update_apply (unpacking) are loaded only
# when they're actually used -- a moment after launch, on the background
# helper -- so opening the app doesn't wait for them.
from ..session import Phase
from ..updater import UpdateInfo


class UpdatesMixin:
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
            # One catch-all around the whole thread body, on purpose:
            # an error here would be invisible in the packaged app (no
            # console). It always reports back exactly once, so the
            # button can never get stuck on "Checking...".
            result = updater.CheckResult(updater.CHECK_FAILED)
            extracted_path: Optional[Path] = None
            try:
                from .. import update_apply, update_fetch
                release_data = update_fetch.fetch_latest_release()
                result = updater.classify_check(__version__, release_data, sys.platform)
                info = result.info
                if info is not None and getattr(sys, "frozen", False):
                    temp_dir = Path(tempfile.mkdtemp(prefix="lockin_update_"))
                    archive_path = temp_dir / info.asset_name
                    if not update_fetch.download_file(info.download_url, archive_path):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        result = updater.CheckResult(
                            updater.CHECK_DOWNLOAD_FAILED, latest=result.latest)
                    else:
                        extracted_path = update_apply.extract_archive(
                            archive_path, temp_dir, sys.platform)
                        if extracted_path is None:
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            result = updater.CheckResult(
                                updater.CHECK_DOWNLOAD_FAILED, latest=result.latest)
                        else:
                            # Only the unpacked app is needed from here on.
                            # Keep temp_dir itself -- extracted_path lives in it.
                            archive_path.unlink(missing_ok=True)
            except Exception:
                result = updater.CheckResult(updater.CHECK_FAILED)
                extracted_path = None
            self._update_queue.put((result, extracted_path))

        threading.Thread(target=run, daemon=True, name="update-check").start()

    def _drain_update_queue(self) -> None:
        """The background check reports back here, on the main thread. A
        found update always shows the strip at the top; the words next to
        the button only appear if somebody asked for them."""
        try:
            result, extracted_path = self._update_queue.get_nowait()
        except queue.Empty:
            return
        self._update_check_running = False
        if result.status == updater.CHECK_AVAILABLE and result.info is not None:
            self._show_update_ready_frame(result.info, extracted_path)
        if self._update_message_wanted:
            self._update_message_wanted = False
            self._set_update_check_busy(False)
            self._set_update_status_text(updater.check_message(
                result, __version__, can_restart=extracted_path is not None))

    def _on_check_updates_clicked(self) -> None:
        """The "Check for updates now" button."""
        if self._pending_update is not None:
            # Already found one earlier this run -- no need to ask again.
            info, extracted_path = self._pending_update
            self._set_update_status_text(updater.check_message(
                updater.CheckResult(updater.CHECK_AVAILABLE, info=info, latest=info.version),
                __version__, can_restart=extracted_path is not None))
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
        return getattr(page, "update_check_button", None), getattr(page, "update_check_status", None)

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
    def _show_update_ready_frame(self, info: UpdateInfo, extracted_path: Optional[Path]) -> None:
        """Shows the "update ready" strip at the top of the window. It
        stays until you act on it. extracted_path is None when running
        from source -- there's no file to swap then, so the restart
        button hides and the words point at the Releases page instead."""
        self._pending_update = (info, extracted_path)
        if extracted_path is None:
            self.update_label.configure(
                text=f"Lock In v{info.version} is available — see the Releases page.")
            self.update_restart_button.pack_forget()
        else:
            self.update_label.configure(text=f"Update ready — v{info.version}")
            self.layout.pack(self.update_restart_button, side="right", padx=(0, 10), pady=8)
        self.layout.pack(self.update_frame, fill="x", padx=12, pady=(12, 0),
                         before=self.page_host)

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
                "again next time you open the app.", "normal")
            self._pending_update = None
            self.update_frame.pack_forget()
            return

        from .. import update_apply
        current_path = update_apply.current_app_path(sys.platform)
        script_path = update_apply.write_relauncher_script(
            extracted_path.parent, current_path, extracted_path,
            pid=update_apply.app_process_id(), platform=sys.platform,
        )
        update_apply.launch_relauncher_and_quit(script_path, sys.platform)
        self._on_close()
