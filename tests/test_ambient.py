"""Tests for AmbientPlayer's decision logic. The actual winsound/
subprocess calls are faked out -- no real audio plays anywhere in
this file, same philosophy as monitor.py's OS calls not being
unit-tested directly."""

from unittest.mock import patch

from lock_in.ambient import AmbientPlayer
from lock_in.config import Config


def test_does_nothing_for_a_rider_without_the_ambient_effect():
    config = Config(rider_theme="Kamen Rider Kuuga (2000)")
    player = AmbientPlayer(config)
    with patch.object(player, "_play_loop") as mock_play:
        player.start_if_applicable()
        mock_play.assert_not_called()


def test_plays_for_hibiki():
    config = Config(rider_theme="Kamen Rider Hibiki (2005)")
    player = AmbientPlayer(config)
    with patch.object(player, "_play_loop") as mock_play:
        player.start_if_applicable()
        mock_play.assert_called_once()


def test_does_nothing_for_hibiki_under_standard_mode():
    config = Config(rider_theme="Kamen Rider Hibiki (2005)", standard_mode=True)
    player = AmbientPlayer(config)
    with patch.object(player, "_play_loop") as mock_play:
        player.start_if_applicable()
        mock_play.assert_not_called()


def test_does_nothing_for_hibiki_when_sound_is_disabled():
    config = Config(rider_theme="Kamen Rider Hibiki (2005)", sound_enabled=False)
    player = AmbientPlayer(config)
    with patch.object(player, "_play_loop") as mock_play:
        player.start_if_applicable()
        mock_play.assert_not_called()


def test_stop_calls_the_stop_backend():
    config = Config(rider_theme="Kamen Rider Hibiki (2005)")
    player = AmbientPlayer(config)
    with patch.object(player, "_stop_loop") as mock_stop:
        player.stop()
        mock_stop.assert_called_once()
