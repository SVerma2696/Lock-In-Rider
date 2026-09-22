from lock_in.config import Config
from lock_in.presets import GAVV_MICRO_SPRINT


def test_phase_seconds_uses_normal_settings_by_default():
    config = Config(focus_minutes=25, short_break_minutes=5, long_break_minutes=15)
    assert config.phase_seconds("focus") == 25 * 60
    assert config.phase_seconds("short_break") == 5 * 60
    assert config.phase_seconds("long_break") == 15 * 60


def test_phase_seconds_uses_gavv_values_when_micro_sprint_mode_is_on():
    config = Config(focus_minutes=25, short_break_minutes=5, long_break_minutes=15,
                     micro_sprint_mode=True)
    assert config.phase_seconds("focus") == GAVV_MICRO_SPRINT.focus_minutes * 60
    assert config.phase_seconds("short_break") == GAVV_MICRO_SPRINT.short_break_minutes * 60
    assert config.phase_seconds("long_break") == GAVV_MICRO_SPRINT.long_break_minutes * 60


def test_micro_sprint_mode_defaults_to_off():
    assert Config().micro_sprint_mode is False


def test_turning_micro_sprint_mode_off_restores_normal_settings():
    """Flipping the switch back never has to "remember" anything -- your
    real settings were never touched in the first place."""
    config = Config(focus_minutes=25, micro_sprint_mode=True)
    assert config.phase_seconds("focus") == GAVV_MICRO_SPRINT.focus_minutes * 60
    config.micro_sprint_mode = False
    assert config.phase_seconds("focus") == 25 * 60


def test_effective_grace_seconds_uses_normal_value_by_default():
    config = Config(grace_seconds=8)
    assert config.effective_grace_seconds() == 8


def test_effective_grace_seconds_is_zero_when_zero_grace_mode_is_on():
    config = Config(grace_seconds=8, zero_grace_mode=True)
    assert config.effective_grace_seconds() == 0


def test_zero_grace_mode_defaults_to_off():
    assert Config().zero_grace_mode is False


def test_effective_sound_and_toast_use_normal_values_by_default():
    config = Config(sound_enabled=True, toast_enabled=True)
    assert config.effective_sound_enabled() is True
    assert config.effective_toast_enabled() is True


def test_effective_sound_and_toast_are_off_when_stealth_mute_mode_is_on():
    config = Config(sound_enabled=True, toast_enabled=True, stealth_mute_mode=True)
    assert config.effective_sound_enabled() is False
    assert config.effective_toast_enabled() is False


def test_stealth_mute_mode_defaults_to_off():
    assert Config().stealth_mute_mode is False


def test_turning_stealth_mute_mode_off_restores_normal_values():
    """Same non-destructive rule as micro_sprint_mode -- your real Sounds
    and Desktop notifications switches were never touched."""
    config = Config(sound_enabled=True, stealth_mute_mode=True)
    assert config.effective_sound_enabled() is False
    config.stealth_mute_mode = False
    assert config.effective_sound_enabled() is True


def test_standard_mode_defaults_to_off():
    assert Config().standard_mode is False


def test_standard_mode_round_trips_through_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    Config(standard_mode=True).save(path)
    assert Config.load(path).standard_mode is True


def test_camera_monitoring_enabled_defaults_to_off():
    assert Config().camera_monitoring_enabled is False


def test_camera_monitoring_enabled_round_trips_through_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    Config(camera_monitoring_enabled=True).save(path)
    assert Config.load(path).camera_monitoring_enabled is True


def test_blackrx_manual_breaks_defaults_to_off():
    assert Config().blackrx_manual_breaks is False


def test_effective_auto_start_breaks_is_false_when_blackrx_manual_breaks_is_on():
    config = Config(auto_start_breaks=True, blackrx_manual_breaks=True)
    assert config.effective_auto_start_breaks() is False


def test_effective_auto_start_breaks_matches_the_real_setting_when_off():
    config = Config(auto_start_breaks=True, blackrx_manual_breaks=False)
    assert config.effective_auto_start_breaks() is True


def test_turning_blackrx_manual_breaks_off_restores_the_real_setting():
    config = Config(auto_start_breaks=True, blackrx_manual_breaks=True)
    assert config.effective_auto_start_breaks() is False
    config.blackrx_manual_breaks = False
    assert config.effective_auto_start_breaks() is True


def test_check_for_updates_defaults_to_on():
    assert Config().check_for_updates is True


def test_daily_goal_minutes_defaults_to_one_hour():
    assert Config().daily_goal_minutes == 60


def test_daily_goal_minutes_round_trips_through_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    Config(daily_goal_minutes=90).save(path)
    assert Config.load(path).daily_goal_minutes == 90


def test_effective_daily_goal_minutes_gives_back_a_good_value_as_it_is():
    assert Config(daily_goal_minutes=90).effective_daily_goal_minutes() == 90
    assert Config().effective_daily_goal_minutes() == 60


def test_effective_daily_goal_minutes_allows_exactly_fifteen_minutes_and_twelve_hours():
    assert Config(daily_goal_minutes=15).effective_daily_goal_minutes() == 15
    assert Config(daily_goal_minutes=720).effective_daily_goal_minutes() == 720


def test_effective_daily_goal_minutes_keeps_a_number_that_is_not_a_multiple_of_fifteen():
    assert Config(daily_goal_minutes=20).effective_daily_goal_minutes() == 20


def test_effective_daily_goal_minutes_falls_back_to_sixty_for_a_bad_number():
    """config.json can be edited by hand, and Config.load() does not check
    it, so a silly goal must never reach the tab (it would divide by zero)."""
    for bad in (0, -5, 14, 721, 100000):
        assert Config(daily_goal_minutes=bad).effective_daily_goal_minutes() == 60, bad


def test_effective_daily_goal_minutes_falls_back_to_sixty_for_the_wrong_kind_of_value():
    for bad in ("abc", "60", 60.0, None, True, False, [60]):
        assert Config(daily_goal_minutes=bad).effective_daily_goal_minutes() == 60, bad
