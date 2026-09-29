"""
config_validation.py
====================
Checks every value read from config.json before the app uses it.

config.json is a plain text file, so anything can end up in it: an old
version's leftovers, a typo, a number where words should be. A bad value
used to be accepted as-is and could crash the app much later (a focus
block of -5 minutes, a color theme that doesn't exist, a block list that
is a number).

The rule is simple: every setting has one rule below. A value that
follows its rule is kept. A value that doesn't is replaced by that
setting's normal default. Settings this version doesn't know are still
ignored, so a config.json from a newer Lock In never breaks an older one.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

# A rule turns a raw value into a clean one, or raises Invalid.
Rule = Callable[[Any], Any]


class Invalid(ValueError):
    """This value doesn't follow its setting's rule."""


@dataclass(frozen=True)
class IntRange:
    """A whole number from `low` to `high`, both included. 25.0 counts as
    25; true/false never count as numbers."""

    low: int
    high: int

    def __call__(self, value: Any) -> int:
        if isinstance(value, bool):
            raise Invalid(value)
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if not isinstance(value, int) or not self.low <= value <= self.high:
            raise Invalid(value)
        return value


@dataclass(frozen=True)
class FloatRange:
    """A number from `low` to `high`, both included."""

    low: float
    high: float

    def __call__(self, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise Invalid(value)
        value = float(value)
        if math.isnan(value) or not self.low <= value <= self.high:
            raise Invalid(value)
        return value


@dataclass(frozen=True)
class OneOf:
    """One of a fixed set of words. Capital letters don't matter."""

    choices: frozenset[str]

    def __call__(self, value: Any) -> str:
        if not isinstance(value, str) or value.strip().lower() not in self.choices:
            raise Invalid(value)
        return value.strip().lower()


def boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise Invalid(value)
    return value


def text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Invalid(value)
    return value


def word_list(value: Any) -> list[str]:
    """A list of words. Anything in it that isn't words is dropped; blank
    entries are dropped too."""
    if not isinstance(value, list):
        raise Invalid(value)
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def known_rider(value: Any) -> str:
    from .rider_themes import RIDER_THEMES

    if not isinstance(value, str) or value not in RIDER_THEMES:
        raise Invalid(value)
    return value


# The daily goal is checked here too, with the same limits Geats' page uses.
def _daily_goal() -> IntRange:
    from .config import DAILY_GOAL_MAX_MINUTES, DAILY_GOAL_MIN_MINUTES

    return IntRange(DAILY_GOAL_MIN_MINUTES, DAILY_GOAL_MAX_MINUTES)


# CustomTkinter's own built-in color themes. Any other name crashes it.
ACCENT_THEMES = frozenset({"blue", "green", "dark-blue"})
APPEARANCES = frozenset({"dark", "light", "system"})
TERMINOLOGIES = frozenset({"professional", "tokusatsu"})


def rules() -> dict[str, Rule]:
    """The one rule for each setting that needs more than "same kind of
    value as its default" (see `_rule_for`)."""
    return {
        "focus_minutes": IntRange(1, 600),
        "short_break_minutes": IntRange(1, 240),
        "long_break_minutes": IntRange(1, 480),
        "blocks_until_long_break": IntRange(1, 20),
        "grace_seconds": IntRange(0, 3600),
        "strike_interval_seconds": IntRange(1, 3600),
        "strike_decay_seconds": IntRange(1, 86400),
        "lockdown_seconds": IntRange(1, 3600),
        "classifier_threshold": FloatRange(0.0, 1.0),
        "claude_confidence_floor": FloatRange(0.0, 1.0),
        "claude_cache_minutes": IntRange(0, 7 * 24 * 60),
        "claude_model": text,
        "daily_goal_minutes": _daily_goal(),
        "blocklist": word_list,
        "allowlist": word_list,
        "badges_earned": word_list,
        "appearance": OneOf(APPEARANCES),
        "terminology": OneOf(TERMINOLOGIES),
        "accent": OneOf(ACCENT_THEMES),
        "rider_theme": known_rider,
    }


def _rule_for(name: str, default: Any, explicit: Mapping[str, Rule]) -> Rule | None:
    if name in explicit:
        return explicit[name]
    if isinstance(default, bool):
        return boolean
    return None


def clean_config_values(config_class: type, raw: Any) -> tuple[dict[str, Any], list[str]]:
    """The values from `raw` that are safe to pass to `config_class(...)`,
    and the names of the settings that were replaced by their default.

    `raw` is whatever json.loads() gave back. If it isn't even a dict
    (a list, a number), every setting uses its default."""
    if not isinstance(raw, dict):
        return {}, []
    explicit = rules()
    cleaned: dict[str, Any] = {}
    rejected: list[str] = []
    for field in dataclasses.fields(config_class):
        if field.name not in raw:
            continue
        default = (
            field.default if field.default is not dataclasses.MISSING else field.default_factory()  # type: ignore[misc]
        )
        rule = _rule_for(field.name, default, explicit)
        value = raw[field.name]
        if rule is None:
            if type(value) is not type(default):
                rejected.append(field.name)
                continue
            cleaned[field.name] = value
            continue
        try:
            cleaned[field.name] = rule(value)
        except Invalid:
            rejected.append(field.name)
    return cleaned, rejected
