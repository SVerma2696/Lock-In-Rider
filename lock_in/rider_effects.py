"""
rider_effects.py
================
The names of every Rider power ("effect"), as fixed lists instead of
loose words.

Before, the code asked things like `if effect == "mirror_flip":`. One
typo ("mirorr_flip") and that power silently never turned on. Now each
power is a named value, like `DisplayEffect.MIRROR_FLIP`: a typo is an
error straight away, your editor can suggest the names, and a search
finds every place a power is used.

Each value is still its old word underneath (a `StrEnum`), so
`DisplayEffect.MIRROR_FLIP == "mirror_flip"` is True. Nothing saved on
disk changes.

The six kinds of power, one per Tier:

    Tier 1  ProgressEffect      how the progress bar or background looks
    Tier 2  PresetEffect        quick-pick buttons in Settings
    Tier 3  EnforcementEffect   how blocking and the window behave
    Tier 4  DisplayEffect       other display, sound, and keyboard tricks
    Tier 5  ProductivityEffect  a Rider page built from your history
    Tier 6  InteractionEffect   something brand new (gestures, buddy link)
"""

from __future__ import annotations

from enum import StrEnum


class Era(StrEnum):
    SHOWA = "Showa"
    HEISEI = "Heisei"
    REIWA = "Reiwa"
    # Standard Mode's plain look. Not a Kamen Rider era.
    STANDARD = "Standard"


class ProgressEffect(StrEnum):
    """Tier 1."""

    NONE = "none"
    WINDMILL = "windmill"  # Kamen Rider (1971)
    BORDER_GLOW = "border_glow"  # Stronger
    RISING_BAR = "rising_bar"  # Skyrider
    HIGH_CONTRAST_DARK = "high_contrast_dark"  # Black
    COLOR_INTERPOLATION = "color_interpolation"  # Agito
    NIGHT_OVERLAY = "night_overlay"  # Kiva
    CONSTELLATION = "constellation"  # Fourze
    ACCELERATING_FILL = "accelerating_fill"  # Drive
    VIALS = "vials"  # Build
    BOOKMARK = "bookmark"  # Saber


class PresetEffect(StrEnum):
    """Tier 2."""

    NONE = "none"
    INTERVAL_PRESETS = "interval_presets"  # Kuuga
    TASK_PRESETS = "task_presets"  # Super-1
    MICRO_SPRINT = "micro_sprint"  # Gavv


class EnforcementEffect(StrEnum):
    """Tier 3."""

    NONE = "none"
    GOAL_GATE = "goal_gate"  # X
    ZERO_UI = "zero_ui"  # Amazon
    STEALTH_MUTE = "stealth_mute"  # ZX
    CODE_UNLOCK = "code_unlock"  # 555
    LOCK_OVERLAY = "lock_overlay"  # Gaim


class DisplayEffect(StrEnum):
    """Tier 4."""

    NONE = "none"
    MANUAL_BREAK_TOGGLE = "manual_break_toggle"  # Black RX
    MIRROR_FLIP = "mirror_flip"  # Ryuki
    AMBIENT_LOOP = "ambient_loop"  # Hibiki
    HIDDEN_TIMER = "hidden_timer"  # Kabuto
    GHOST_WIDGET = "ghost_widget"  # Ghost
    CHIPTUNE_ALERT = "chiptune_alert"  # Ex-Aid
    DASHBOARD_CARDS = "dashboard_cards"  # Zero-One
    HOTKEYS = "hotkeys"  # Zeztz


class ProductivityEffect(StrEnum):
    """Tier 5."""

    NONE = "none"
    HOURS_TAB = "hours_tab"  # V3
    KANBAN_BOARD = "kanban_board"  # Blade
    TIMELINE_VIEW = "timeline_view"  # Den-O
    ANALYTICS_DASHBOARD = "analytics_dashboard"  # Decade
    WEEK_COMPARE = "week_compare"  # W
    PHASE_COMBO = "phase_combo"  # OOO
    HISTORY_EDITOR = "history_editor"  # Zi-O
    GOAL_STREAK = "goal_streak"  # Geats
    BADGE_CARDS = "badge_cards"  # Gotchard
    PRIORITY_ORDER = "priority_order"  # MY-TH


class InteractionEffect(StrEnum):
    """Tier 6."""

    NONE = "none"
    MOUSE_GESTURES = "mouse_gestures"  # Wizard
    BUDDY_LINK = "buddy_link"  # Revice


# The same six, under the Tier numbers the rest of the code and the
# design notes use. `Tier1Effect` and `ProgressEffect` are the same thing.
Tier1Effect = ProgressEffect
Tier2Effect = PresetEffect
Tier3Effect = EnforcementEffect
Tier4Effect = DisplayEffect
Tier5Effect = ProductivityEffect
Tier6Effect = InteractionEffect

EFFECT_TYPES: tuple[type[StrEnum], ...] = (
    ProgressEffect,
    PresetEffect,
    EnforcementEffect,
    DisplayEffect,
    ProductivityEffect,
    InteractionEffect,
)
