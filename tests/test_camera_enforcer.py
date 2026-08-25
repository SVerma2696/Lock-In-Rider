"""Tests for CameraEnforcer -- the pure logic that feeds phone-sighting
samples through the same escalation ladder Enforcer already applies to
blocked apps. No real camera or model involved anywhere in this file."""

import pytest

from lock_in.config import Config
from lock_in.enforcer import Action, message_for
from lock_in.camera_enforcer import CameraEnforcer


class FakeClock:
    def __init__(self) -> None:
        self.now = 500.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def config() -> Config:
    return Config(grace_seconds=8, strike_interval_seconds=10,
                  strike_decay_seconds=30, hard_mode=False)


@pytest.fixture
def camera_enforcer(config, clock) -> CameraEnforcer:
    return CameraEnforcer(config, clock=clock)


def test_no_phone_seen_is_action_none(camera_enforcer):
    assert camera_enforcer.update(False) is Action.NONE


def test_grace_period_stays_silent(camera_enforcer, clock):
    assert camera_enforcer.update(True) is Action.NONE
    clock.advance(7)
    assert camera_enforcer.update(True) is Action.NONE


def test_first_strike_after_grace_is_a_warning(camera_enforcer, clock):
    camera_enforcer.update(True)
    clock.advance(9)
    assert camera_enforcer.update(True) is Action.WARN


def test_hard_mode_minimizes_then_locks_down(config, clock):
    config.hard_mode = True
    ce = CameraEnforcer(config, clock=clock)
    ce.update(True)
    clock.advance(9)
    assert ce.update(True) is Action.MINIMIZE
    clock.advance(11)
    assert ce.update(True) is Action.LOCKDOWN


def test_no_longer_seeing_a_phone_resets_the_grace_timer(camera_enforcer, clock):
    camera_enforcer.update(True)
    clock.advance(9)
    camera_enforcer.update(True)          # strike 1 (WARN)
    clock.advance(2)
    assert camera_enforcer.update(False) is Action.NONE
    assert camera_enforcer.seconds_on_phone == 0.0


def test_reset_clears_strikes_and_the_grace_period_starts_over(camera_enforcer, clock):
    camera_enforcer.update(True)
    clock.advance(9)
    camera_enforcer.update(True)          # strike 1 (WARN)
    camera_enforcer.reset()
    assert camera_enforcer.update(True) is Action.NONE   # back in grace period


def test_phone_window_reads_naturally_in_the_existing_messages():
    title, body = message_for(
        Action.WARN, app=CameraEnforcer.PHONE_WINDOW.display,
        remaining="20:00", seconds=5, lockdown=15,
    )
    assert "your phone" in body
