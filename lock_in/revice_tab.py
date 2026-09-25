"""
revice_tab.py
=============
The "Buddy" tab Kamen Rider Revice adds. Draws one of five screens:

- start:    Share and Receive buttons
- typing:   a box for the 4-digit code, Connect, Back
- sharing:  the big code, a countdown, Cancel
- finding:  "Looking for your buddy...", Cancel
- paired:   their name, timer, what they're doing, task,
            Pull History, Unpair

All the widgets are made once; show() only switches which screen is
visible and changes text, so calling it on every timer tick is cheap.
The buttons just call the functions ui.py hands in -- this file never
touches the network itself. Checked by hand in the running app, like
every other tab.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from . import revice_sync as rs


class BuddyTab:
    def __init__(self, parent, *, accent: str, text_color: str,
                 on_share: Callable[[], None], on_receive: Callable[[str], None],
                 on_cancel: Callable[[], None], on_pull: Callable[[], None],
                 on_unpair: Callable[[], None]) -> None:
        self._on_receive = on_receive
        self._typing = False
        self._screen: Optional[str] = None

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.message_label = ctk.CTkLabel(self.frame, text="", wraplength=420)
        self.message_label.pack(anchor="w", pady=(0, 8))

        def button(master, text, command):
            return ctk.CTkButton(master, text=text, command=command,
                                 fg_color=accent, text_color=text_color)

        # start
        self.start_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctk.CTkLabel(self.start_frame, justify="left", wraplength=420, text=(
            "Pair with a friend's computer on the same Wi-Fi. They need "
            "Revice picked too. One of you presses Share, the other "
            "presses Receive and types the code.")).pack(anchor="w", pady=(0, 10))
        button(self.start_frame, "Share", on_share).pack(anchor="w", pady=4)
        button(self.start_frame, "Receive", self._start_typing).pack(anchor="w", pady=4)

        # typing
        self.typing_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctk.CTkLabel(self.typing_frame, text="Type the 4 numbers from the other computer:"
                     ).pack(anchor="w", pady=(0, 6))
        self.code_entry = ctk.CTkEntry(self.typing_frame, width=120,
                                       font=ctk.CTkFont(size=24, weight="bold"))
        self.code_entry.pack(anchor="w", pady=4)
        self.code_entry.bind("<Return>", lambda _e: self._connect())
        button(self.typing_frame, "Connect", self._connect).pack(anchor="w", pady=4)
        ctk.CTkButton(self.typing_frame, text="Back", fg_color="transparent", border_width=1,
                      command=self._stop_typing).pack(anchor="w", pady=4)

        # sharing
        self.sharing_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctk.CTkLabel(self.sharing_frame, text="Type this code on the other computer:"
                     ).pack(anchor="w")
        self.code_label = ctk.CTkLabel(self.sharing_frame, text="",
                                       font=ctk.CTkFont(size=48, weight="bold"))
        self.code_label.pack(anchor="w", pady=6)
        self.countdown_label = ctk.CTkLabel(self.sharing_frame, text="")
        self.countdown_label.pack(anchor="w", pady=(0, 8))
        button(self.sharing_frame, "Cancel", on_cancel).pack(anchor="w")

        # finding
        self.finding_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctk.CTkLabel(self.finding_frame, text="Looking for your buddy…").pack(anchor="w", pady=(0, 8))
        button(self.finding_frame, "Cancel", on_cancel).pack(anchor="w")

        # paired
        self.paired_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.paired_label = ctk.CTkLabel(self.paired_frame, text="",
                                         font=ctk.CTkFont(size=16, weight="bold"))
        self.paired_label.pack(anchor="w")
        self.time_label = ctk.CTkLabel(self.paired_frame, text="--:--",
                                       font=ctk.CTkFont(size=40, weight="bold"))
        self.time_label.pack(anchor="w", pady=(6, 0))
        self.doing_label = ctk.CTkLabel(self.paired_frame, text="")
        self.doing_label.pack(anchor="w")
        self.task_label = ctk.CTkLabel(self.paired_frame, text="", wraplength=420)
        self.task_label.pack(anchor="w", pady=(0, 10))
        self.pull_button = button(self.paired_frame, "Pull History", on_pull)
        self.pull_button.pack(anchor="w", pady=4)
        button(self.paired_frame, "Unpair", on_unpair).pack(anchor="w", pady=4)

        self._frames = {"start": self.start_frame, "typing": self.typing_frame,
                        "sharing": self.sharing_frame, "finding": self.finding_frame,
                        "paired": self.paired_frame}

    # ------------------------------------------------------------------ #
    def _start_typing(self) -> None:
        self._typing = True
        self.code_entry.delete(0, "end")

    def _stop_typing(self) -> None:
        self._typing = False

    def _connect(self) -> None:
        code = self.code_entry.get()
        self._on_receive(code)
        if rs.is_valid_code(code):
            self._typing = False

    def _switch(self, screen: str) -> None:
        if screen == self._screen:
            return
        for frame in self._frames.values():
            frame.pack_forget()
        self._frames[screen].pack(fill="both", expand=True)
        self._screen = screen
        if screen == "typing":
            self.code_entry.focus_set()

    def _set(self, label, text: str) -> None:
        if label.cget("text") != text:
            label.configure(text=text)

    # ------------------------------------------------------------------ #
    def show(self, link, status: Optional[dict], message: str, now: float) -> None:
        """Bring the tab up to date with the link. `now` is in the same
        clock as link.code_deadline."""
        if link.state == "paired":
            self._typing = False
            screen = "paired"
        elif link.state == "sharing":
            screen = "sharing"
        elif link.state == "finding":
            screen = "finding"
        else:
            screen = "typing" if self._typing else "start"
        self._switch(screen)
        self._set(self.message_label, message)

        if screen == "sharing":
            self._set(self.code_label, link.code or "")
            left = max(0, int(link.code_deadline - now))
            self._set(self.countdown_label,
                      f"Waiting for your buddy… {left // 60}:{left % 60:02d} left")
        elif screen == "paired":
            self._set(self.paired_label, f"Paired with {link.buddy_name or 'Buddy'}")
            if status is None:
                time_text, doing, task = "--:--", "Waiting for their timer…", ""
            else:
                time_text, doing, task = rs.describe_status(status)
                task = f"Task: {task}"
            self._set(self.time_label, time_text)
            self._set(self.doing_label, doing)
            self._set(self.task_label, task)
            pull_text = "Pulling…" if link.pull_pending else "Pull History"
            if self.pull_button.cget("text") != pull_text:
                self.pull_button.configure(
                    text=pull_text, state="disabled" if link.pull_pending else "normal")
