"""
Checks that run on EVERY Rider, automatically.

Add a Rider to rider_themes.py and it is tested here straight away: its
colors, era, powers, id, and the parts of the app its powers switch on.
No new test needs writing just to check that a Rider is put together
properly.
"""

import re

import pytest

from lock_in.rider_effects import (
    EFFECT_TYPES,
    DisplayEffect,
    EnforcementEffect,
    Era,
    InteractionEffect,
    PresetEffect,
    ProductivityEffect,
    ProgressEffect,
)
from lock_in.rider_themes import (
    DEFAULT_RIDER_THEME,
    RIDER_THEMES,
    RIDERS,
    STANDARD_THEME,
    RiderAbilities,
    RiderTheme,
    rider_id_for,
    rider_named,
)
from lock_in.tier5 import TIER5_BUILDERS
from lock_in.ui.pages.settings import TIER2_PRESET_ROWS, rider_power_parts
from lock_in.ui.router import BUDDY_ROUTE_ID, RIDER_ROUTE_ID, build_routes, route_ids
from lock_in.ui.theme import resolve_palette
from lock_in.visuals import SHAPE_EFFECTS, apply_tier1_background_effect, render_progress

HEX = re.compile(r"^#[0-9a-f]{6}$")
ALL = sorted(RIDER_THEMES.items())
NAME_PATTERN = re.compile(r"^Kamen Rider( [^()]+)? \((19|20)\d\d\)$")


@pytest.mark.parametrize("name, theme", ALL)
def test_every_rider_has_valid_colors(name, theme):
    for pair in (theme.primary, theme.secondary):
        assert isinstance(pair, tuple) and len(pair) == 2
        for color in pair:
            assert HEX.match(color), f"{name}: {color!r} is not a #rrggbb color"


@pytest.mark.parametrize("name, theme", ALL)
def test_every_rider_has_a_real_era_and_year(name, theme):
    assert isinstance(theme.era, Era)
    assert theme.era is not Era.STANDARD
    assert 1971 <= theme.year <= 2100
    assert name.endswith(f"({theme.year})")


@pytest.mark.parametrize("name, theme", ALL)
def test_every_rider_name_is_well_formed(name, theme):
    assert name.strip() == name and name
    assert NAME_PATTERN.match(name), name


@pytest.mark.parametrize("name, theme", ALL)
def test_every_power_is_a_typed_value(name, theme):
    abilities = theme.abilities
    assert isinstance(abilities, RiderAbilities)
    assert isinstance(abilities.progress, ProgressEffect)
    assert isinstance(abilities.preset, PresetEffect)
    assert isinstance(abilities.enforcement, EnforcementEffect)
    assert isinstance(abilities.display, DisplayEffect)
    assert isinstance(abilities.productivity, ProductivityEffect)
    assert isinstance(abilities.interaction, InteractionEffect)


@pytest.mark.parametrize("name, theme", ALL)
def test_every_rider_has_at_most_one_power(name, theme):
    """Each Rider brings one gimmick (the Tier they belong to). Two at
    once would be a typo in the table."""
    assert len(theme.abilities.powers()) <= 1, (name, theme.abilities.powers())


@pytest.mark.parametrize("name, theme", ALL)
def test_every_riders_colors_make_a_full_palette(name, theme):
    palette = resolve_palette(theme)
    for pair in (palette.accent, palette.accent_text, palette.accent_on):
        assert len(pair) == 2 and all(HEX.match(color.lower()) for color in pair)


@pytest.mark.parametrize("name, theme", ALL)
def test_every_riders_pages_can_be_worked_out(name, theme):
    """The side bar for this Rider builds, and a Rider page only appears
    when there's really a page to draw."""
    ids = route_ids(
        build_routes(theme.tier5_effect, theme.tier6_effect, known_tier5_effects=TIER5_BUILDERS)
    )
    assert (RIDER_ROUTE_ID in ids) == (theme.tier5_effect is not ProductivityEffect.NONE)
    assert (BUDDY_ROUTE_ID in ids) == (theme.tier6_effect is InteractionEffect.BUDDY_LINK)
    rider_power_parts(theme)  # the Settings page's extra rows


@pytest.mark.parametrize("name, theme", ALL)
def test_every_riders_progress_look_draws(name, theme):
    """A Tier 1 shape or background effect that can't draw would break the
    Focus page as soon as that Rider is picked."""
    effect = theme.tier1_effect
    for dark, primary, secondary in (
        (False, theme.primary[0], theme.secondary[0]),
        (True, theme.primary[1], theme.secondary[1]),
    ):
        if effect in SHAPE_EFFECTS:
            image = render_progress(effect, 120, 40, 0.5, primary, secondary, dark)
            assert image.size == (120, 40)
    if effect in (ProgressEffect.BORDER_GLOW, ProgressEffect.NIGHT_OVERLAY):
        from PIL import Image

        base = Image.new("RGBA", (60, 80), "#101010")
        assert apply_tier1_background_effect(base, effect, theme.primary[1], 0.5).size == (60, 80)


# ---------------------------------------------------------------------- #
# The table as a whole
# ---------------------------------------------------------------------- #
def test_there_are_38_riders_and_ids_never_repeat():
    assert len(RIDER_THEMES) == 38
    assert len(RIDERS) == 38
    assert len({rider_id_for(name) for name in RIDER_THEMES}) == 38


def test_ids_are_short_and_plain():
    for rider_id in RIDERS:
        assert re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", rider_id), rider_id
    assert rider_id_for("Kamen Rider (1971)") == "kamen-rider-1971"
    assert rider_id_for("Kamen Rider Ex-Aid (2016)") == "ex-aid-2016"
    assert rider_id_for("Kamen Rider MY-TH (2026)") == "my-th-2026"


def test_definitions_match_the_table():
    for rider_id, rider in RIDERS.items():
        assert RIDER_THEMES[rider.display_name] is rider.theme
        assert rider.id == rider_id
        assert rider.era is rider.theme.era
        assert rider_named(rider.display_name) == rider
    assert rider_named("Kamen Rider Nobody (1999)") is None


def test_the_default_rider_exists():
    assert DEFAULT_RIDER_THEME in RIDER_THEMES


def test_every_power_is_used_by_exactly_one_rider():
    """Each named power belongs to one Rider. A power nobody has, or two
    Riders with the same power, means the table and the code disagree."""
    used = [effect for theme in RIDER_THEMES.values() for effect in theme.abilities.powers()]
    every_power = [m.value for kind in EFFECT_TYPES for m in kind if m.value != "none"]
    assert sorted(used) == sorted(every_power)


def test_every_tier5_power_has_a_page_and_every_tier2_power_has_rows():
    for theme in RIDER_THEMES.values():
        if theme.tier5_effect is not ProductivityEffect.NONE:
            assert theme.tier5_effect in TIER5_BUILDERS
    assert set(TIER5_BUILDERS) == {
        m for m in ProductivityEffect if m is not ProductivityEffect.NONE
    }
    assert set(TIER2_PRESET_ROWS) <= set(PresetEffect)


def test_standard_mode_has_no_powers_at_all():
    assert STANDARD_THEME.era is Era.STANDARD
    assert STANDARD_THEME.abilities == RiderAbilities()
    assert STANDARD_THEME.abilities.powers() == []
    assert STANDARD_THEME not in RIDER_THEMES.values()


def test_a_misspelled_power_is_caught_straight_away():
    with pytest.raises(ValueError, match="mirorr_flip"):
        RiderTheme(Era.HEISEI, 2002, ("#000000",) * 2, ("#ffffff",) * 2, tier4_effect="mirorr_flip")


def test_a_misspelled_era_is_caught_straight_away():
    with pytest.raises(ValueError, match="Heisay"):
        RiderTheme("Heisay", 2002, ("#000000",) * 2, ("#ffffff",) * 2)


def test_plain_words_still_work_and_become_typed():
    theme = RiderTheme(
        "Heisei", 2002, ("#000000",) * 2, ("#ffffff",) * 2, tier4_effect="mirror_flip"
    )
    assert theme.tier4_effect is DisplayEffect.MIRROR_FLIP
    assert theme.tier4_effect == "mirror_flip"  # still equal to the old word
