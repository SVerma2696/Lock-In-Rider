"""
ui/pages/
=========
One file per page in the side bar. `PAGE_CLASSES` says which class
draws which page, by the page's fixed name (see ui/router.py).
"""

from .activity import ActivityPage
from .blocking import BlockingPage
from .buddy import BuddyPage
from .focus import FocusPage
from .help import HelpPage
from .insights import InsightsPage
from .rider import RiderPage
from .settings import SettingsPage
from .tasks import TasksPage

PAGE_CLASSES = {
    "focus": FocusPage,
    "tasks": TasksPage,
    "blocking": BlockingPage,
    "activity": ActivityPage,
    "insights": InsightsPage,
    "rider": RiderPage,
    "buddy": BuddyPage,
    "help": HelpPage,
    "settings": SettingsPage,
}

__all__ = ["PAGE_CLASSES"] + [cls.__name__ for cls in PAGE_CLASSES.values()]
