"""
Tests for the era-picking logic in notifier.py.

The actual sound-playing and pop-up code shells out to OS tools
(winsound, afplay, notify-send, ...), which these tests deliberately
don't touch — they only check the pure logic that picks WHICH sound
goes with which Kamen Rider era, since that part needs no real OS calls
to verify.
"""

from lock_in.config import Config
from lock_in.notifier import (
    DEFAULT_ERA,
    _LINUX_ALERT_CANDIDATES,
    _LINUX_CHIME_CANDIDATES,
    _MAC_ALERT_SOUND,
    _MAC_CHIME_SOUND,
    _WINDOWS_ALERT_TONES,
    _WINDOWS_CHIME_TONES,
    Notifier,
)


def make_notifier(rider_theme: str) -> Notifier:
    return Notifier(Config(rider_theme=rider_theme))


def test_era_matches_the_configured_riders_era():
    assert make_notifier("Kamen Rider (1971)")._sound_key() == "Showa"
    assert make_notifier("Kamen Rider Kuuga (2000)")._sound_key() == "Heisei"
    assert make_notifier("Kamen Rider Saber (2020)")._sound_key() == "Reiwa"


def test_era_falls_back_for_an_unrecognised_rider_name():
    # The fallback Rider is the very first one, which is a Showa Rider.
    from lock_in.rider_themes import DEFAULT_RIDER_THEME, RIDER_THEMES
    assert make_notifier("Not A Real Rider")._sound_key() == RIDER_THEMES[DEFAULT_RIDER_THEME].era


# "ExAid" isn't a real Kamen Rider era (Ex-Aid's own era is Heisei) --
# it's the synthetic key _sound_key() returns when Ex-Aid's chiptune
# gimmick is active, so every sound table needs an entry for it too,
# alongside the three real eras.
_ALL_SOUND_KEYS = ("Showa", "Heisei", "Reiwa", "ExAid")


def test_every_era_has_windows_tones():
    for era in _ALL_SOUND_KEYS:
        assert era in _WINDOWS_CHIME_TONES
        assert era in _WINDOWS_ALERT_TONES
        assert _WINDOWS_CHIME_TONES[era]     # non-empty list of (freq, ms) tones
        assert _WINDOWS_ALERT_TONES[era]


def test_every_era_has_mac_sounds():
    for era in _ALL_SOUND_KEYS:
        assert era in _MAC_CHIME_SOUND
        assert era in _MAC_ALERT_SOUND


def test_every_era_has_linux_sound_candidates():
    for era in _ALL_SOUND_KEYS:
        assert era in _LINUX_CHIME_CANDIDATES
        assert era in _LINUX_ALERT_CANDIDATES
        assert _LINUX_CHIME_CANDIDATES[era]
        assert _LINUX_ALERT_CANDIDATES[era]


def test_eras_sound_different_from_each_other():
    """The whole point is that they're not all the same beep pattern."""
    assert len({tuple(_WINDOWS_CHIME_TONES[e]) for e in _ALL_SOUND_KEYS}) == 4
    assert len({tuple(_WINDOWS_ALERT_TONES[e]) for e in _ALL_SOUND_KEYS}) == 4
    assert len({_MAC_CHIME_SOUND[e] for e in _ALL_SOUND_KEYS}) == 4
    assert len({_MAC_ALERT_SOUND[e] for e in _ALL_SOUND_KEYS}) == 4


def test_default_era_is_heisei():
    assert DEFAULT_ERA == "Heisei"


def test_stealth_mute_mode_silences_sound_and_toast_checks():
    """
    notify()/phase_chime()/alert_sound() all gate on
    effective_sound_enabled()/effective_toast_enabled() now, not the
    raw sound_enabled/toast_enabled fields -- this confirms those
    methods themselves report muted when ZX's stealth mode is on, which
    is the actual switch Notifier's real code reads.
    """
    config = Config(sound_enabled=True, toast_enabled=True, stealth_mute_mode=True)
    assert config.effective_sound_enabled() is False
    assert config.effective_toast_enabled() is False


def test_sound_key_is_exaid_when_the_current_rider_has_the_chiptune_effect():
    config = Config(rider_theme="Kamen Rider Ex-Aid (2016)")
    notifier = Notifier(config)
    assert notifier._sound_key() == "ExAid"


def test_sound_key_falls_back_to_era_for_every_other_rider():
    config = Config(rider_theme="Kamen Rider Kuuga (2000)")
    notifier = Notifier(config)
    assert notifier._sound_key() == "Heisei"


def test_sound_key_ignores_exaid_under_standard_mode():
    config = Config(rider_theme="Kamen Rider Ex-Aid (2016)", standard_mode=True)
    notifier = Notifier(config)
    assert notifier._sound_key() != "ExAid"
