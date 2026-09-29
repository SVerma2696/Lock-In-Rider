"""
application/
============
The part of Lock In that decides things, kept apart from the part that
draws them. Nothing in this folder imports the screen toolkit, so every
piece here can be tested without opening a window.

    controller.py             AppController: builds and owns everything below
    events.py                 the one mailbox background helpers post notes to
    lifecycle.py              starting and stopping helpers cleanly
    task_controller.py        which task the next focus block is for
    focus_controller.py       writing each focus block into history
    enforcement_controller.py judging windows and phones, the Activity list
    buddy_controller.py       Revice's buddy link

The window (lock_in/ui/app.py) makes one AppController, shows what it
says, and passes your clicks to it.
"""

from .controller import AppController, AppPaths
from .events import (
    AppEvent,
    BannerRequested,
    ClaudeAnswered,
    EventBus,
    PhoneSample,
    UpdateChecked,
    WindowSeen,
)

__all__ = [
    "AppController",
    "AppEvent",
    "AppPaths",
    "BannerRequested",
    "ClaudeAnswered",
    "EventBus",
    "PhoneSample",
    "UpdateChecked",
    "WindowSeen",
]
