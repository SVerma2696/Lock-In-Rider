"""
Tests for config_validation.py: every bad value in config.json is
swapped for its default, every good one is kept, and old or newer files
still load.
"""

import json

import pytest

from lock_in.config import DAILY_GOAL_DEFAULT_MINUTES, Config
from lock_in.config_validation import clean_config_values
from lock_in.rider_themes import RIDER_THEMES

DEFAULTS = Config()


def load(tmp_path, raw):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return Config.load(path)


@pytest.mark.parametrize(
    "key, bad",
    [
        ("focus_minutes", -5),
        ("focus_minutes", 0),
        ("focus_minutes", "25"),
        ("focus_minutes", True),
        ("focus_minutes", 25.5),
        ("focus_minutes", None),
        ("short_break_minutes", 10_000),
        ("long_break_minutes", []),
        ("blocks_until_long_break", 0),
        ("grace_seconds", -1),
        ("strike_interval_seconds", 0),
        ("strike_decay_seconds", "soon"),
        ("lockdown_seconds", 0),
        ("classifier_threshold", 1.5),
        ("classifier_threshold", -0.1),
        ("classifier_threshold", "high"),
        ("classifier_threshold", True),
        ("claude_confidence_floor", 2),
        ("claude_cache_minutes", -3),
        ("claude_model", ""),
        ("claude_model", 4),
        ("daily_goal_minutes", 0),
        ("daily_goal_minutes", 99999),
        ("appearance", "purple"),
        ("appearance", 1),
        ("terminology", "pirate"),
        ("accent", "rainbow"),
        ("rider_theme", "Kamen Rider Nobody (1999)"),
        ("rider_theme", None),
        ("blocklist", "discord.exe"),
        ("allowlist", 7),
        ("badges_earned", {"a": 1}),
        ("hard_mode", "yes"),
        ("sound_enabled", 1),
        ("standard_mode", None),
    ],
)
def test_a_bad_value_becomes_the_default(tmp_path, key, bad):
    config = load(tmp_path, {key: bad})
    assert getattr(config, key) == getattr(DEFAULTS, key)


@pytest.mark.parametrize(
    "key, good, expected",
    [
        ("focus_minutes", 50, 50),
        ("focus_minutes", 50.0, 50),
        ("grace_seconds", 0, 0),
        ("classifier_threshold", 0.9, 0.9),
        ("classifier_threshold", 1, 1.0),
        ("appearance", "Light", "light"),
        ("terminology", " TOKUSATSU ", "tokusatsu"),
        ("accent", "green", "green"),
        ("rider_theme", "Kamen Rider Revice (2021)", "Kamen Rider Revice (2021)"),
        ("daily_goal_minutes", 120, 120),
        ("hard_mode", False, False),
    ],
)
def test_a_good_value_is_kept(tmp_path, key, good, expected):
    assert getattr(load(tmp_path, {key: good}), key) == expected


def test_lists_keep_words_and_drop_everything_else(tmp_path):
    config = load(tmp_path, {"blocklist": ["discord.exe", 5, None, "  ", " steam.exe "]})
    assert config.blocklist == ["discord.exe", "steam.exe"]


def test_one_bad_value_doesnt_touch_the_others(tmp_path):
    config = load(tmp_path, {"focus_minutes": -1, "short_break_minutes": 7})
    assert config.focus_minutes == DEFAULTS.focus_minutes
    assert config.short_break_minutes == 7


@pytest.mark.parametrize("content", ["[]", "5", "null", '"words"', "{broken", ""])
def test_a_file_that_isnt_settings_at_all_starts_fresh(tmp_path, content):
    """A config.json holding a list used to crash the app on opening."""
    path = tmp_path / "config.json"
    path.write_text(content, encoding="utf-8")
    assert Config.load(path) == Config()


def test_settings_from_a_newer_version_are_ignored(tmp_path):
    config = load(tmp_path, {"focus_minutes": 40, "setting_from_the_future": 1})
    assert config.focus_minutes == 40


def test_an_old_file_missing_new_settings_gets_their_defaults(tmp_path):
    config = load(tmp_path, {"focus_minutes": 30})
    assert config.mouse_gestures_enabled is True
    assert config.daily_goal_minutes == DAILY_GOAL_DEFAULT_MINUTES


def test_every_rider_name_is_allowed(tmp_path):
    for name in RIDER_THEMES:
        cleaned, rejected = clean_config_values(Config, {"rider_theme": name})
        assert cleaned == {"rider_theme": name} and rejected == []


def test_every_setting_has_a_rule_or_a_simple_type():
    """A new setting added to Config without a rule still gets checked:
    it must be the same kind of value as its default."""
    cleaned, rejected = clean_config_values(
        Config, {f: object() for f in Config.__dataclass_fields__}
    )
    assert cleaned == {}
    assert sorted(rejected) == sorted(Config.__dataclass_fields__)


def test_saving_and_loading_gives_back_the_same_settings(tmp_path):
    path = tmp_path / "config.json"
    config = Config(focus_minutes=42, appearance="light", blocklist=["a.exe"])
    config.save(path)
    assert Config.load(path) == config
