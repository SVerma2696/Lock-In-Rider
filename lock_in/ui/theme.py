"""
ui/theme.py
===========
Every base color, size, and space the screen uses, kept in ONE place.

Think of it like a box of crayons. The pages never pick their own
crayon. They ask this file: "what color is a card?", "what color is
small grey text?" That way the whole app matches, and changing a color
means changing one line here.

Colors come as a PAIR: (light mode, dark mode). CustomTkinter picks the
right half by itself when you switch modes.

There are three kinds of color here:

1. Base colors (grey-ish): the window, the side bar, cards, and text.
   These are the same for every Rider. They are the calm part.
2. The Rider color (the "accent"): ONE color from the picked Rider. It
   marks the main button, the progress bar, and the page you are on.
3. Status colors: green, amber, and red. These only ever mean
   something ("good", "careful", "blocked") -- never decoration.

Nothing in this file touches the screen, so it can be tested without
opening a window.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..rider_effects import ProgressEffect
from ..rider_themes import RiderTheme, darken, lighten, readable_text_color

Pair = tuple  # (light mode color, dark mode color)

# ---------------------------------------------------------------------- #
# Base colors
# ---------------------------------------------------------------------- #
APP_BG = ("#F4F6F8", "#0D1117")
SIDEBAR_BG = ("#FFFFFF", "#11161D")
CARD_BG = ("#FFFFFF", "#18181B")
CARD_BG_ELEVATED = ("#F8FAFC", "#202024")
CARD_BORDER = ("#D8DEE6", "#2A2F36")
TEXT_PRIMARY = ("#111827", "#F5F7FA")
TEXT_SECONDARY = ("#4B5563", "#A7AFB8")
TEXT_MUTED = ("#6B7280", "#737B85")
CONTROL_BG = ("#EEF1F4", "#22262D")
CONTROL_HOVER = ("#E3E7EC", "#2B3038")
# A switch's track when it's OFF -- dark enough to see on a white card.
SWITCH_OFF = ("#D5DBE3", "#3A414B")
# A switch's round knob. In light mode a white knob vanished into the
# white card around it, so it's a mid grey there: easy to see on both the
# grey OFF track and a colored ON track.
SWITCH_KNOB = ("#5B6573", "#E8EBEF")
SWITCH_KNOB_HOVER = ("#434C58", "#FFFFFF")
# The picked part of a segmented chooser (like Light | Dark | System).
SEGMENT_SELECTED = ("#FFFFFF", "#3A414B")

# ---------------------------------------------------------------------- #
# Status colors -- only for things that MEAN something
# ---------------------------------------------------------------------- #
SUCCESS = ("#1F8A4C", "#3FB96F")
WARNING = ("#A86A00", "#E0A800")
DANGER = ("#C0392B", "#F0605A")
INFO = ("#1C6FC4", "#4DABF7")
NEUTRAL = TEXT_SECONDARY

# The soft pill behind a status badge's words.
SUCCESS_SOFT = ("#E3F4EA", "#13261B")
WARNING_SOFT = ("#FBF0D9", "#2A2310")
DANGER_SOFT = ("#FBE4E1", "#2C1616")
INFO_SOFT = ("#E1EEFB", "#132131")
NEUTRAL_SOFT = CONTROL_BG

STATUS_COLORS = {
    "success": (SUCCESS, SUCCESS_SOFT),
    "warning": (WARNING, WARNING_SOFT),
    "danger": (DANGER, DANGER_SOFT),
    "info": (INFO, INFO_SOFT),
    "neutral": (NEUTRAL, NEUTRAL_SOFT),
}

# The pop-up message strip: (background, words) for each kind.
BANNER_COLORS = {
    "low": (INFO_SOFT, INFO),
    "normal": (WARNING_SOFT, WARNING),
    "high": (DANGER_SOFT, DANGER),
}

# The lockdown and goal screens are always dark, whatever the mode.
OVERLAY_BG = "#121417"
OVERLAY_TEXT = "#9AA4B2"
OVERLAY_MUTED = "#6B7480"
OVERLAY_HOVER = "#1D2026"

# ---------------------------------------------------------------------- #
# Spacing -- only these steps, so gaps always line up
# ---------------------------------------------------------------------- #
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_7 = 32
SPACING_SCALE = (SPACE_1, SPACE_2, SPACE_3, SPACE_4, SPACE_5, SPACE_6, SPACE_7)

# ---------------------------------------------------------------------- #
# Sizes
# ---------------------------------------------------------------------- #
WINDOW_SIZE = (960, 680)
WINDOW_MIN_SIZE = (820, 600)
SIDEBAR_WIDTH = 184
CARD_RADIUS = 12
CONTROL_RADIUS = 8
BUTTON_HEIGHT = 42
ICON_SIZE = 18

# Words: body, small, section, page title, big timer, timer phase.
FONT_BODY = 13
FONT_SMALL = 11
FONT_SECTION = 15
FONT_PAGE_TITLE = 23
FONT_TIMER = 72
FONT_PHASE = 15


_FONTS: dict = {}


def font(family=None, size: int = FONT_BODY, weight: str = "normal"):
    """One shared font per (family, size, weight).

    Every label used to make its own font, and Tk has to load and measure
    each new font separately -- that made drawing a page about three times
    slower than it needed to be. Sharing them is quicker and uses less
    memory. (Needs the app window to exist, so it's only called while
    building the screen.)"""
    key = (family, size, weight)
    shared = _FONTS.get(key)
    if shared is None:
        import customtkinter as ctk

        shared = ctk.CTkFont(family=family, size=size, weight=weight)
        _FONTS[key] = shared
    return shared


# ---------------------------------------------------------------------- #
# The palette for one Rider
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class Palette:
    """Every color one screen needs, for the Rider that's picked right
    now. The base colors are usually the plain ones above; only the
    accent pairs come from the Rider."""

    app_bg: Pair
    sidebar_bg: Pair
    card_bg: Pair
    card_bg_elevated: Pair
    card_border: Pair
    text_primary: Pair
    text_secondary: Pair
    text_muted: Pair
    control_bg: Pair
    control_hover: Pair
    # The Rider's main color, as a fill (buttons, bars, the marker).
    accent: Pair
    # A darker/lighter version used when you hover the main button.
    accent_hover: Pair
    # Words sitting ON TOP of the accent fill -- plain black or white.
    accent_on: Pair
    # The accent, safe to use as WORDS on a card.
    accent_text: Pair
    # The accent, pushed darker when it's very pale -- for fills that sit
    # under a white knob or white words (switches, the side bar stripe).
    accent_strong: Pair
    # The Rider's second color, used sparingly.
    secondary: Pair
    secondary_text: Pair


def _hover_shade(color: str, dark_mode: bool) -> str:
    """A slightly different shade for hovering. Very dark colors get
    lighter; everything else gets a little darker."""
    if readable_text_color(color) == "#ffffff" and dark_mode:
        return lighten(color, 0.15)
    return darken(color, 0.15)


def _strong(color: str) -> str:
    """The same color, darkened only if it's too pale for white on top."""
    return color if readable_text_color(color) == "#ffffff" else darken(color, 0.32)


def resolve_palette(theme: RiderTheme) -> Palette:
    """Build the palette for one Rider (or Standard Mode's plain theme).

    Kamen Rider Black's gimmick is a stricter, higher-contrast dark
    mode, so Black alone gets darker cards and brighter grey words in
    dark mode. Light mode is the same for everyone."""
    primary_light, primary_dark = theme.primary
    app_bg, card_bg, card_border = APP_BG, CARD_BG, CARD_BORDER
    text_secondary, text_muted = TEXT_SECONDARY, TEXT_MUTED
    if theme.tier1_effect == ProgressEffect.HIGH_CONTRAST_DARK:
        app_bg = (APP_BG[0], "#000000")
        card_bg = (CARD_BG[0], "#0B0B0C")
        card_border = (CARD_BORDER[0], "#4A525C")
        text_secondary = (TEXT_SECONDARY[0], "#E1E6EC")
        text_muted = (TEXT_MUTED[0], "#B6BEC8")
    return Palette(
        app_bg=app_bg,
        sidebar_bg=SIDEBAR_BG if app_bg is APP_BG else (SIDEBAR_BG[0], "#050505"),
        card_bg=card_bg,
        card_bg_elevated=CARD_BG_ELEVATED,
        card_border=card_border,
        text_primary=TEXT_PRIMARY,
        text_secondary=text_secondary,
        text_muted=text_muted,
        control_bg=CONTROL_BG,
        control_hover=CONTROL_HOVER,
        accent=theme.primary_pair,
        accent_hover=(_hover_shade(primary_light, False), _hover_shade(primary_dark, True)),
        accent_on=(readable_text_color(primary_light), readable_text_color(primary_dark)),
        accent_text=theme.primary_text_pair,
        accent_strong=(_strong(primary_light), _strong(primary_dark)),
        secondary=theme.secondary_pair,
        secondary_text=theme.secondary_text_pair,
    )


def pick(pair: Pair, appearance: str) -> str:
    """The one half of a (light, dark) pair for "light" or "dark"."""
    return pair[1] if appearance.lower() == "dark" else pair[0]
