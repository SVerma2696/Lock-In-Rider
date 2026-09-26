"""Tests for ui/theme.py: the base colors and each Rider's palette.
No window is opened anywhere in this file."""

import re

import pytest

from lock_in.rider_themes import RIDER_THEMES, STANDARD_THEME, readable_text_color
from lock_in.ui import theme as t

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

MYTH = "Kamen Rider MY-TH (2026)"


def _pairs(palette):
    return [getattr(palette, name) for name in palette.__dataclass_fields__]


def test_base_tokens_match_the_design():
    assert t.APP_BG == ("#F4F6F8", "#0D1117")
    assert t.SIDEBAR_BG == ("#FFFFFF", "#11161D")
    assert t.CARD_BG == ("#FFFFFF", "#18181B")
    assert t.CARD_BG_ELEVATED == ("#F8FAFC", "#202024")
    assert t.CARD_BORDER == ("#D8DEE6", "#2A2F36")
    assert t.TEXT_PRIMARY == ("#111827", "#F5F7FA")
    assert t.TEXT_SECONDARY == ("#4B5563", "#A7AFB8")
    assert t.TEXT_MUTED == ("#6B7280", "#737B85")
    assert t.CONTROL_BG == ("#EEF1F4", "#22262D")
    assert t.CONTROL_HOVER == ("#E3E7EC", "#2B3038")


def test_window_size_and_minimum():
    assert t.WINDOW_SIZE == (960, 680)
    assert t.WINDOW_MIN_SIZE == (820, 600)
    assert 170 <= t.SIDEBAR_WIDTH <= 190


def test_spacing_scale_is_the_agreed_steps():
    assert t.SPACING_SCALE == (4, 8, 12, 16, 20, 24, 32)


def test_status_colors_are_not_any_riders_accent_by_accident():
    # Status colors mean something; they're fixed, never taken from a Rider.
    for kind in ("success", "warning", "danger", "info", "neutral"):
        fg, bg = t.STATUS_COLORS[kind]
        assert len(fg) == 2 and len(bg) == 2


@pytest.mark.parametrize("name", list(RIDER_THEMES))
def test_every_rider_palette_is_all_valid_light_dark_hex_pairs(name):
    palette = t.resolve_palette(RIDER_THEMES[name])
    for pair in _pairs(palette):
        assert isinstance(pair, tuple) and len(pair) == 2
        assert all(HEX.match(c) for c in pair)


@pytest.mark.parametrize("name", list(RIDER_THEMES))
def test_accent_is_the_riders_own_primary_color(name):
    theme = RIDER_THEMES[name]
    assert t.resolve_palette(theme).accent == theme.primary


@pytest.mark.parametrize("name", list(RIDER_THEMES))
def test_words_on_the_main_button_are_readable(name):
    palette = t.resolve_palette(RIDER_THEMES[name])
    for fill, words in zip(palette.accent, palette.accent_on):
        assert words == readable_text_color(fill)


@pytest.mark.parametrize("name", list(RIDER_THEMES))
def test_switch_fill_is_never_too_pale_for_a_white_knob(name):
    palette = t.resolve_palette(RIDER_THEMES[name])
    for original, strong in zip(palette.accent, palette.accent_strong):
        if readable_text_color(original) == "#ffffff":
            assert strong == original          # already dark enough
        else:
            assert strong != original          # pushed darker


def test_only_one_rider_accent_the_base_colors_stay_neutral():
    # Two very different Riders share every base color: only accents differ.
    a = t.resolve_palette(RIDER_THEMES["Kamen Rider Kuuga (2000)"])
    b = t.resolve_palette(RIDER_THEMES["Kamen Rider Gotchard (2023)"])
    for field in ("app_bg", "sidebar_bg", "card_bg", "card_border",
                  "text_primary", "text_secondary", "text_muted", "control_bg"):
        assert getattr(a, field) == getattr(b, field)
    assert a.accent != b.accent


def test_myth_is_one_pick_not_two():
    assert sum(1 for name in RIDER_THEMES if "MY-TH" in name) == 1


def test_myth_light_mode_is_normal_myth_blue_and_silver():
    theme = RIDER_THEMES[MYTH]
    assert theme.primary[0] == "#0f4a8f"      # blue
    assert theme.secondary[0] == "#78909c"    # silver
    assert t.resolve_palette(theme).accent[0] == "#0f4a8f"


def test_myth_dark_mode_is_myth_origin_red_and_gunmetal():
    theme = RIDER_THEMES[MYTH]
    assert theme.primary[1] == "#ef5350"      # crimson
    assert theme.secondary[1] == "#616161"    # gunmetal
    assert t.resolve_palette(theme).accent[1] == "#ef5350"


def test_myth_keeps_its_priority_page():
    assert RIDER_THEMES[MYTH].tier5_effect == "priority_order"


def test_black_gets_a_stricter_dark_mode_and_nobody_else_does():
    black = t.resolve_palette(RIDER_THEMES["Kamen Rider Black (1987)"])
    normal = t.resolve_palette(RIDER_THEMES["Kamen Rider Kuuga (2000)"])
    assert black.app_bg[1] == "#000000"
    assert black.text_secondary[1] != normal.text_secondary[1]
    # Light mode is the same for everyone.
    assert black.app_bg[0] == normal.app_bg[0]
    assert black.text_secondary[0] == normal.text_secondary[0]


def test_standard_mode_palette_is_plain_slate_and_blue():
    palette = t.resolve_palette(STANDARD_THEME)
    assert palette.accent == ("#475569", "#94a3b8")
    assert palette.secondary == ("#1c7ed6", "#4dabf7")
    assert palette.app_bg == t.APP_BG


def test_pick_chooses_the_right_half():
    assert t.pick(("#111111", "#eeeeee"), "light") == "#111111"
    assert t.pick(("#111111", "#eeeeee"), "Dark") == "#eeeeee"
