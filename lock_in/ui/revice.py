"""
ui/revice.py
============
Kamen Rider Revice's buddy link, from the app's side: what the Buddy
page's buttons do, and the check that runs on every timer tick.

The network part is still lock_in/revice_link.py and the rules are still
lock_in/revice_sync.py -- neither changed. This is the same code the app
always had, moved into its own file. The only new thing: it finds the
Buddy page through the page list instead of a tab.
"""

from __future__ import annotations

import time

from .. import revice_sync


class ReviceMixin:
    def _on_buddy_share(self) -> None:
        try:
            self._buddy_message = ""
            self._buddy_status = None
            self.buddy_link.share()
        except Exception:
            pass

    def _on_buddy_receive(self, code: str) -> None:
        try:
            if not revice_sync.is_valid_code(code):
                self._buddy_message = revice_sync.MSG_TYPE_FOUR
                return
            self._buddy_message = ""
            self._buddy_status = None
            self.buddy_link.receive(code)
        except Exception:
            pass

    def _on_buddy_cancel(self) -> None:
        try:
            self._buddy_message = ""
            self._buddy_status = None
            self.buddy_link.close()
        except Exception:
            pass

    def _on_buddy_pull(self) -> None:
        try:
            if self.buddy_link.request_pull():
                self._buddy_message = ""
        except Exception:
            pass

    @property
    def _buddy_tab(self):
        """The Buddy page's screens, if that page has been drawn."""
        page = self.pages.get("buddy") if hasattr(self, "pages") else None
        return getattr(page, "tab", None)

    def _drain_buddy_link(self) -> None:
        """Called every tick from _pump(). Reads what the link heard,
        sends our timer about once a second, and redraws the Buddy page.
        Closes the link as soon as Revice isn't the Rider any more
        (another Rider, or Standard Mode). Never lets an error reach the
        timer."""
        try:
            link = self.buddy_link
            if self.current_tier6_effect != "buddy_link":
                if link.state != "idle":
                    link.close()
                link.poll()
                self._buddy_status = None
                self._buddy_message = ""
                return
            for event in link.poll():
                kind = event[0]
                if kind == "paired":
                    self._buddy_message = ""
                    self._buddy_status = None
                elif kind == "status":
                    self._buddy_status = revice_sync.clean_status(event[1])
                elif kind == "pull_request":
                    sessions, task_list = revice_sync.pull_reply_payload(self.history, self.tasks)
                    link.send_pull_reply(sessions, task_list)
                elif kind == "pull_reply":
                    # The merge alone is wrapped here (not the whole
                    # handler) so a mid-merge failure -- e.g.
                    # sessions.jsonl locked by OneDrive -- still shows a
                    # message instead of leaving the page looking frozen.
                    before = len(self.tasks.all())
                    try:
                        added = revice_sync.merge_pull(self.history, self.tasks, event[1], event[2])
                        self._buddy_message = revice_sync.pull_result_text(*added)
                    except Exception:
                        self._buddy_message = revice_sync.MSG_PULL_FAILED
                    finally:
                        # Redraw whenever a task actually got added, even
                        # if something above failed partway through.
                        if len(self.tasks.all()) != before:
                            self._render_tasks()
                            self._refresh_current_task_picker()
                elif kind == "pull_failed":
                    self._buddy_message = revice_sync.MSG_PULL_FAILED
                elif kind == "left":
                    self._buddy_message = revice_sync.MSG_BUDDY_LEFT
                    self._buddy_status = None
                elif kind == "error":
                    self._buddy_message = event[1]
            now = time.monotonic()
            if link.state == "paired" and now - self._buddy_last_sent >= revice_sync.STATUS_EVERY_SECONDS:
                self._buddy_last_sent = now
                task = self.tasks.get(self.current_task_id) if self.current_task_id else None
                link.send_status(revice_sync.status_from_session(
                    self.session, task.name if task else None, link.name))
            tab = self._buddy_tab
            if tab is not None:
                tab.show(link, self._buddy_status, self._buddy_message, now)
        except Exception:
            pass
