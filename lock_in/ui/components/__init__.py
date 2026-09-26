"""
ui/components/
==============
The small building blocks every page is made from: cards, buttons,
badges, setting rows, the side bar, and the timer. Each page uses these
instead of styling its own widgets, so the whole app looks the same.
"""

from .buttons import DangerButton, PrimaryButton, SecondaryButton
from .card import ModernCard, StatCard
from .menu_button import MenuButton
from .setting_row import SettingRow
from .sidebar import Sidebar, SidebarButton
from .status_badge import StatusBadge
from .timer_display import ProgressArea, TimerDisplay

__all__ = [
    "DangerButton", "PrimaryButton", "SecondaryButton", "ModernCard", "StatCard", "MenuButton",
    "SettingRow", "Sidebar", "SidebarButton", "StatusBadge", "ProgressArea", "TimerDisplay",
]
