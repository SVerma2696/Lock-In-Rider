from lock_in.rider_themes import (
    DEFAULT_RIDER_THEME,
    RIDER_THEMES,
    STANDARD_THEME,
    darken,
    lighten,
    readable_text_color,
)


def _brightness(hex_color: str) -> int:
    hex_color = hex_color.lstrip("#")
    return sum(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def test_has_all_38_riders():
    assert len(RIDER_THEMES) == 38


def test_default_theme_is_the_original():
    assert DEFAULT_RIDER_THEME == "Kamen Rider (1971)"
    assert DEFAULT_RIDER_THEME in RIDER_THEMES


def test_spot_check_corrected_palette_values():
    # These pin the hand-corrected, per-mode palette so a future edit
    # can't quietly drift back toward the older, single-shade guesses.
    assert RIDER_THEMES["Kamen Rider (1971)"].primary == ("#154a2e", "#237a4b")
    assert RIDER_THEMES["Kamen Rider (1971)"].secondary == ("#a83225", "#d94436")
    assert RIDER_THEMES["Kamen Rider V3 (1973)"].primary == ("#225c25", "#4caf50")
    assert RIDER_THEMES["Kamen Rider Zero-One (2019)"].primary == ("#77a100", "#c6ff00")
    assert RIDER_THEMES["Kamen Rider Gavv (2024)"].secondary == ("#c48000", "#ffee58")
    assert RIDER_THEMES["Kamen Rider MY-TH (2026)"].primary == ("#0f4a8f", "#42a5f5")


def test_every_entry_has_valid_hex_colors():
    for name, theme in RIDER_THEMES.items():
        for pair in (theme.primary, theme.secondary):
            for value in pair:
                assert value.startswith("#") and len(value) == 7, f"{name}: {value!r}"


def test_lighten_moves_toward_white():
    assert lighten("#000000", 0.5) == "#808080"
    assert lighten("#000000", 0.0) == "#000000"
    assert lighten("#000000", 1.0) == "#ffffff"


def test_theme_color_pairs_are_light_dark_tuples():
    theme = RIDER_THEMES["Kamen Rider (1971)"]
    assert theme.primary_pair == theme.primary  # just hands back the stored pair
    light, dark = theme.primary_pair
    assert light != dark  # the light/dark shades must actually differ


def test_darken_moves_toward_black():
    assert darken("#ffffff", 0.5) == "#808080"
    assert darken("#ffffff", 0.0) == "#ffffff"
    assert darken("#ffffff", 1.0) == "#000000"


def test_surface_pair_is_pale_for_light_and_near_black_for_dark():
    theme = RIDER_THEMES["Kamen Rider (1971)"]  # primary is a green
    light_surface, dark_surface = theme.surface_pair

    def brightness(hex_color: str) -> int:
        hex_color = hex_color.lstrip("#")
        return sum(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    # Light mode surface should read as "pale" (bright), dark mode as
    # "near-black" (dim) -- same underlying hue, very different brightness.
    assert brightness(light_surface) > 600   # close to white (max 765)
    assert brightness(dark_surface) < 100    # close to black


def test_surface_pair_keeps_the_riders_hue_recognisable():
    """Two different Riders' surfaces shouldn't collapse to the same grey."""
    green_rider = RIDER_THEMES["Kamen Rider (1971)"]
    red_rider = RIDER_THEMES["Kamen Rider Kuuga (2000)"]
    assert green_rider.surface_pair != red_rider.surface_pair


def test_readable_text_color_picks_black_on_light_backgrounds():
    assert readable_text_color("#ffffff") == "#000000"
    assert readable_text_color("#ffca28") == "#000000"   # a light gold


def test_readable_text_color_picks_white_on_dark_backgrounds():
    assert readable_text_color("#000000") == "#ffffff"
    assert readable_text_color("#1a1a1a") == "#ffffff"   # a near-black


def test_primary_text_pair_is_never_the_same_as_its_own_light_mode_surface():
    """
    This is the same bug class primary_text_pair exists to prevent: a
    Rider whose light-mode primary sits very close to white (Fourze's
    is a pale grey) needs its TEXT pushed further away from its own
    pale surface, or the two become impossible to tell apart.
    """
    fourze = RIDER_THEMES["Kamen Rider Fourze (2011)"]
    light_text, _ = fourze.primary_text_pair
    light_surface, _ = fourze.surface_pair
    assert light_text != light_surface


def test_primary_text_pair_is_readable_against_its_own_surface_both_modes():
    for name, theme in RIDER_THEMES.items():
        light_text, dark_text = theme.primary_text_pair
        light_surface, dark_surface = theme.surface_pair
        # A gap of at least ~150 (out of a max possible 765) between the
        # text and the surface it sits on is enough that they can never
        # be mistaken for the same color, in either mode.
        assert abs(_brightness(light_text) - _brightness(light_surface)) > 150, name
        assert abs(_brightness(dark_text) - _brightness(dark_surface)) > 150, name


def test_secondary_text_pair_is_readable_against_its_primary_surface_both_modes():
    for name, theme in RIDER_THEMES.items():
        light_text, dark_text = theme.secondary_text_pair
        light_surface, dark_surface = theme.surface_pair
        assert abs(_brightness(light_text) - _brightness(light_surface)) > 100, name
        assert abs(_brightness(dark_text) - _brightness(dark_surface)) > 100, name


def test_tier1_effect_defaults_to_none_for_ordinary_riders():
    assert RIDER_THEMES["Kamen Rider V3 (1973)"].tier1_effect == "none"
    assert RIDER_THEMES["Kamen Rider Gavv (2024)"].tier1_effect == "none"


def test_tier1_effect_is_assigned_to_exactly_the_10_named_riders():
    expected = {
        "Kamen Rider (1971)": "windmill",
        "Kamen Rider Skyrider (1979)": "rising_bar",
        "Kamen Rider Stronger (1975)": "border_glow",
        "Kamen Rider Black (1987)": "high_contrast_dark",
        "Kamen Rider Fourze (2011)": "constellation",
        "Kamen Rider Build (2017)": "vials",
        "Kamen Rider Drive (2014)": "accelerating_fill",
        "Kamen Rider Agito (2001)": "color_interpolation",
        "Kamen Rider Kiva (2008)": "night_overlay",
        "Kamen Rider Saber (2020)": "bookmark",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier1_effect == effect, name

    # Nobody outside this list should have picked up an effect by accident.
    everyone_else = set(RIDER_THEMES) - set(expected)
    for name in everyone_else:
        assert RIDER_THEMES[name].tier1_effect == "none", name


def test_black_gets_stricter_dark_mode_text_contrast_than_normal_riders():
    """Black's Tier 1 gimmick: dark-mode text gets pushed further toward
    white than every other Rider, for stricter contrast."""
    black = RIDER_THEMES["Kamen Rider Black (1987)"]
    ordinary = RIDER_THEMES["Kamen Rider V3 (1973)"]
    assert black.primary_text_pair[1] == lighten(black.primary[1], 0.55)
    assert ordinary.primary_text_pair[1] == lighten(ordinary.primary[1], 0.35)


def test_black_light_mode_text_is_unaffected():
    """Black's gimmick is stricter DARK mode contrast only -- light mode
    should use the same amount every other Rider gets."""
    black = RIDER_THEMES["Kamen Rider Black (1987)"]
    assert black.primary_text_pair[0] == darken(black.primary[0], 0.35)
    assert black.secondary_text_pair[0] == darken(black.secondary[0], 0.35)


def test_desaturate_produces_equal_rgb_channels():
    from lock_in.rider_themes import desaturate
    gray = desaturate("#ff0000").lstrip("#")
    r, g, b = gray[0:2], gray[2:4], gray[4:6]
    assert r == g == b


def test_desaturate_preserves_relative_brightness():
    from lock_in.rider_themes import desaturate

    def brightness(hex_color):
        hex_color = hex_color.lstrip("#")
        return sum(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    bright = desaturate("#ffff00")   # yellow -- perceived as bright
    dark = desaturate("#000080")     # navy -- perceived as dark
    assert brightness(bright) > brightness(dark)


def test_desaturate_keeps_two_different_colors_visually_distinct():
    from lock_in.rider_themes import desaturate
    assert desaturate("#ff0000") != desaturate("#0000ff")


def test_tier3_effect_defaults_to_none_for_ordinary_riders():
    assert RIDER_THEMES["Kamen Rider V3 (1973)"].tier3_effect == "none"
    assert RIDER_THEMES["Kamen Rider Kuuga (2000)"].tier3_effect == "none"


def test_tier3_effect_is_assigned_to_exactly_the_5_named_riders():
    expected = {
        "Kamen Rider X (1974)": "goal_gate",
        "Kamen Rider Amazon (1974)": "zero_ui",
        "Kamen Rider ZX (1982)": "stealth_mute",
        "Kamen Rider Gaim (2013)": "lock_overlay",
        "Kamen Rider 555 (2003)": "code_unlock",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier3_effect == effect, name

    everyone_else = set(RIDER_THEMES) - set(expected)
    for name in everyone_else:
        assert RIDER_THEMES[name].tier3_effect == "none", name


def test_button_text_pair_is_readable_against_the_secondary_fill_both_modes():
    """The Henshin button's own text sits directly on secondary_pair --
    it needs to contrast against THAT color, not a tinted version of it."""
    for name, theme in RIDER_THEMES.items():
        light_fill, dark_fill = theme.secondary_pair
        light_text, dark_text = theme.button_text_pair
        # 150 matches readable_text_color()'s own perceived-brightness
        # cutoff, so this checks the choice is never a coin-flip-close
        # call, rather than an arbitrary made-up number.
        assert abs(_brightness(light_text) - _brightness(light_fill)) > 150, name
        assert abs(_brightness(dark_text) - _brightness(dark_fill)) > 150, name


def test_standard_theme_is_not_one_of_the_38_riders():
    """STANDARD_THEME lives outside RIDER_THEMES on purpose -- it isn't a
    Kamen Rider costume, it's Tier 0's neutral baseline."""
    assert STANDARD_THEME not in RIDER_THEMES.values()
    assert len(RIDER_THEMES) == 38  # unchanged by adding this constant


def test_standard_theme_has_no_tier_1_or_tier_3_effect():
    assert STANDARD_THEME.tier1_effect == "none"
    assert STANDARD_THEME.tier3_effect == "none"


def test_standard_theme_uses_the_approved_neutral_palette():
    assert STANDARD_THEME.primary == ("#475569", "#94a3b8")
    assert STANDARD_THEME.secondary == ("#1c7ed6", "#4dabf7")


def test_standard_theme_passes_the_same_contrast_check_every_rider_does():
    """Same shape as test_primary_text_pair_is_readable_against_its_own_surface_both_modes
    below, just for this one theme -- it gets the identical color-math
    guarantees every real Rider gets, for free, from the dataclass."""
    light_text, dark_text = STANDARD_THEME.primary_text_pair
    light_surface, dark_surface = STANDARD_THEME.surface_pair
    assert abs(_brightness(light_text) - _brightness(light_surface)) > 150
    assert abs(_brightness(dark_text) - _brightness(dark_surface)) > 150


def test_tier4_effect_defaults_to_none():
    from lock_in.rider_themes import RiderTheme
    theme = RiderTheme("Heisei", 2000, ("#000000", "#ffffff"), ("#111111", "#eeeeee"))
    assert theme.tier4_effect == "none"


def test_exactly_these_eight_riders_have_a_tier4_effect():
    from lock_in.rider_themes import RIDER_THEMES
    expected = {
        "Kamen Rider Black RX (1988)": "manual_break_toggle",
        "Kamen Rider Ryuki (2002)": "mirror_flip",
        "Kamen Rider Kabuto (2006)": "hidden_timer",
        "Kamen Rider Ex-Aid (2016)": "chiptune_alert",
        "Kamen Rider Hibiki (2005)": "ambient_loop",
        "Kamen Rider Zero-One (2019)": "dashboard_cards",
        "Kamen Rider Ghost (2015)": "ghost_widget",
        "Kamen Rider Zeztz (2025)": "hotkeys",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier4_effect == effect, name
    tier4_riders = {n for n, t in RIDER_THEMES.items() if t.tier4_effect != "none"}
    assert tier4_riders == set(expected)


def test_saber_is_a_tier1_bookmark_shape_not_a_tier4_effect():
    from lock_in.rider_themes import RIDER_THEMES
    saber = RIDER_THEMES["Kamen Rider Saber (2020)"]
    assert saber.tier1_effect == "bookmark"
    assert saber.tier4_effect == "none"


def test_tier5_effect_defaults_to_none():
    from lock_in.rider_themes import RiderTheme
    theme = RiderTheme("Heisei", 2000, ("#000000", "#ffffff"), ("#111111", "#eeeeee"))
    assert theme.tier5_effect == "none"


def test_exactly_these_ten_riders_have_a_tier5_effect():
    from lock_in.rider_themes import RIDER_THEMES
    expected = {
        "Kamen Rider V3 (1973)": "hours_tab",
        "Kamen Rider Den-O (2007)": "timeline_view",
        "Kamen Rider Decade (2009)": "analytics_dashboard",
        "Kamen Rider Zi-O (2018)": "history_editor",
        "Kamen Rider Blade (2004)": "kanban_board",
        "Kamen Rider W (2009)": "week_compare",
        "Kamen Rider Geats (2022)": "goal_streak",
        "Kamen Rider Gotchard (2023)": "badge_cards",
        "Kamen Rider OOO (2010)": "phase_combo",
        "Kamen Rider MY-TH (2026)": "priority_order",
    }
    for name, effect in expected.items():
        assert RIDER_THEMES[name].tier5_effect == effect, name
    tier5_riders = {n for n, t in RIDER_THEMES.items() if t.tier5_effect != "none"}
    assert tier5_riders == set(expected)


def test_standard_theme_has_no_tier5_effect():
    from lock_in.rider_themes import STANDARD_THEME
    assert STANDARD_THEME.tier5_effect == "none"
