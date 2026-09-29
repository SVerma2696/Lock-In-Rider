"""
Tests for lock_in/application: the mailbox, clean shutdown, the focus
block record keeper, blocking decisions, and the whole controller --
all without opening a window.
"""

import threading
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from lock_in.application import (
    AppController,
    AppPaths,
    BannerRequested,
    EventBus,
    PhoneSample,
    WindowSeen,
)
from lock_in.application.buddy_controller import BuddyController
from lock_in.application.enforcement_controller import ActivityLog, EnforcementController
from lock_in.application.focus_controller import FocusController
from lock_in.application.lifecycle import ShutdownSteps
from lock_in.application.task_controller import TaskController
from lock_in.classifier import DISTRACTION, STUDY, NaiveBayesClassifier
from lock_in.claude_fallback import ClaudeVerdict
from lock_in.config import Config
from lock_in.enforcer import Action, Reason, Verdict, WindowInfo
from lock_in.history import HistoryStore
from lock_in.observations import ObservationStore
from lock_in.session import Phase, PomodoroSession
from lock_in.task_picker import NO_TASK_LABEL
from lock_in.tasks import TaskStatus, TaskStore

DISCORD = WindowInfo(process_name="discord.exe", title="general #chat", handle=None)
EDITOR = WindowInfo(process_name="code.exe", title="main.py", handle=None)


# ---------------------------------------------------------------------- #
# The mailbox
# ---------------------------------------------------------------------- #
def test_notes_go_to_their_own_handlers_in_order():
    bus = EventBus()
    seen, phones = [], []
    bus.subscribe(WindowSeen, lambda e: seen.append(e.window.process_name))
    bus.subscribe(PhoneSample, lambda e: phones.append(e.seen))
    bus.post(WindowSeen(DISCORD))
    bus.post(PhoneSample(True))
    bus.post(WindowSeen(EDITOR))
    assert bus.dispatch_pending() == 3
    assert seen == ["discord.exe", "code.exe"]
    assert phones == [True]


def test_a_failing_handler_does_not_stop_the_next_notes():
    bus = EventBus()
    got = []

    def broken(event):
        raise RuntimeError("boom")

    bus.subscribe(BannerRequested, broken)
    bus.subscribe(BannerRequested, lambda e: got.append(e.title))
    bus.post(BannerRequested("a", "b", "low"))
    bus.post(BannerRequested("c", "d", "low"))
    bus.dispatch_pending()
    assert got == ["a", "c"]


def test_posting_from_many_threads_loses_nothing():
    bus = EventBus()
    got = []
    bus.subscribe(PhoneSample, lambda e: got.append(e))

    def spam():
        for _ in range(500):
            bus.post(PhoneSample(False))

    threads = [threading.Thread(target=spam) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    bus.dispatch_pending()
    assert len(got) == 2000


def test_limit_caps_one_dispatch():
    bus = EventBus()
    for _ in range(5):
        bus.post(PhoneSample(False))
    assert bus.dispatch_pending(limit=2) == 2
    assert bus.pending() == 3


def test_notes_after_close_are_dropped():
    bus = EventBus()
    got = []
    bus.subscribe(PhoneSample, got.append)
    bus.post(PhoneSample(True))
    bus.close()
    bus.post(PhoneSample(True))
    assert bus.dispatch_pending() == 0
    assert got == []
    assert bus.closed


# ---------------------------------------------------------------------- #
# Shutting down
# ---------------------------------------------------------------------- #
def test_every_shutdown_step_runs_even_after_a_failure():
    ran = []
    steps = ShutdownSteps()
    steps.add("one", lambda: ran.append(1))
    steps.add("two", lambda: (_ for _ in ()).throw(OSError("disk")))
    steps.add("three", lambda: ran.append(3))
    assert steps.run() == ["two"]
    assert ran == [1, 3]


def test_shutdown_runs_once():
    ran = []
    steps = ShutdownSteps()
    steps.add("one", lambda: ran.append(1))
    steps.run()
    assert steps.run() == []
    assert ran == [1]


# ---------------------------------------------------------------------- #
# Tasks and focus blocks
# ---------------------------------------------------------------------- #
class Clock:
    def __init__(self):
        self.now = datetime(2026, 9, 1, 10, 0, 0)

    def __call__(self):
        return self.now


@pytest.fixture
def focus_setup(tmp_path):
    config = Config(focus_minutes=25)
    seconds = [0.0]
    session = PomodoroSession(config, clock=lambda: seconds[0])
    tasks = TaskStore(tmp_path / "tasks.json")
    history = HistoryStore(tmp_path / "sessions.jsonl")
    tasks_ctl = TaskController(tasks)
    clock = Clock()
    focus = FocusController(session, history, tasks_ctl, now=clock)
    return SimpleNamespace(
        session=session,
        tasks=tasks,
        history=history,
        ctl=tasks_ctl,
        focus=focus,
        clock=clock,
        seconds=seconds,
    )


def test_task_menu_falls_back_to_no_task_when_the_task_is_done(focus_setup):
    task = focus_setup.tasks.add("Essay")
    values, showing = focus_setup.ctl.menu()
    assert values == [NO_TASK_LABEL, "Essay"] and showing == NO_TASK_LABEL
    focus_setup.ctl.select("Essay")
    assert focus_setup.ctl.current_task_id == task.id
    focus_setup.tasks.complete(task.id)
    assert focus_setup.ctl.menu() == ([NO_TASK_LABEL], NO_TASK_LABEL)
    assert focus_setup.ctl.current_task_id is None


def test_a_finished_focus_block_is_written_with_its_task(focus_setup):
    s = focus_setup
    task = s.tasks.add("Essay")
    s.ctl.menu()
    s.ctl.select("Essay")
    list(s.session.toggle())  # Start
    s.focus.phase_started()
    assert s.focus.work_resumed() is True
    assert s.tasks.get(task.id).status is TaskStatus.IN_PROGRESS
    s.clock.now += timedelta(minutes=25)
    record = s.focus.log_block(completed=True)
    assert record.duration_seconds == 25 * 60
    assert record.task_id == task.id
    assert [r.id for r in s.history.all()] == [record.id]


def test_skipping_before_starting_writes_nothing(focus_setup):
    s = focus_setup
    list(s.session.toggle())
    list(s.session.toggle())  # paused straight away, nothing counted down
    s.focus.phase_started()
    assert s.focus.log_block(completed=False) is None
    assert s.history.all() == []


def test_a_cut_short_block_counts_only_the_time_worked(focus_setup):
    s = focus_setup
    list(s.session.toggle())
    s.focus.phase_started()
    s.seconds[0] += 600
    list(s.session.tick())
    record = s.focus.log_block(completed=False)
    assert record.duration_seconds == 600 and record.completed is False


def test_a_disk_error_while_logging_never_escapes(focus_setup, monkeypatch):
    s = focus_setup
    list(s.session.toggle())
    s.focus.phase_started()
    monkeypatch.setattr(s.history, "record", lambda r: (_ for _ in ()).throw(OSError("full")))
    assert s.focus.log_block(completed=True) is None
    assert s.focus.block_start is None


# ---------------------------------------------------------------------- #
# Blocking decisions
# ---------------------------------------------------------------------- #
@pytest.fixture
def enforcement(tmp_path):
    config = Config(record_observations=True, claude_fallback_enabled=False)
    config._path = tmp_path / "config.json"
    model = NaiveBayesClassifier.load_seed()
    observations = ObservationStore(tmp_path / "observations.jsonl")
    claude = SimpleNamespace(judge_async=lambda text, cb: None, lookup=lambda text: None)
    return EnforcementController(
        config, model, claude, observations, tmp_path / "model.json", on_claude_answer=None
    )


def test_nothing_is_judged_outside_a_running_focus_block(enforcement):
    assert enforcement.judge_window(DISCORD, focus_running=False) is None
    assert enforcement.activity.entries == []


def test_a_blocked_app_is_judged_and_listed(enforcement):
    decision = enforcement.judge_window(DISCORD, focus_running=True)
    assert decision.verdict.blocked and decision.verdict.reason is Reason.BLOCKLIST
    assert decision.new_activity_row
    assert enforcement.activity.entries[0]["key"].startswith("discord.exe")
    assert len(enforcement.observations.all()) == 1


def test_lock_in_itself_is_never_judged(enforcement):
    own = WindowInfo(process_name="lock in.exe", title="12:00 · Focus — Lock In")
    assert enforcement.judge_window(own, focus_running=True) is None


def test_the_phone_is_only_judged_when_the_camera_switch_is_on(enforcement):
    assert enforcement.judge_phone(True, focus_running=True) is None
    enforcement.config.camera_monitoring_enabled = True
    decision = enforcement.judge_phone(True, focus_running=True)
    assert decision.verdict.reason is Reason.CAMERA
    assert decision.action in set(Action)


def test_correcting_to_study_allow_lists_the_program(enforcement):
    enforcement.judge_window(WindowInfo(process_name="newgame.exe", title="x"), True)
    entry = enforcement.activity.entries[0]
    assert enforcement.correct(entry, STUDY) == "newgame.exe"
    assert "newgame.exe" in enforcement.config.allowlist
    assert entry["corrected"] == STUDY
    assert enforcement.correct(entry, DISTRACTION) is None


def test_only_real_claude_answers_are_learned(enforcement):
    assert not enforcement.learn_from_claude("x", ClaudeVerdict(STUDY, 0.9, "error"))
    assert enforcement.learn_from_claude("chess.com", ClaudeVerdict(DISTRACTION, 0.9, "claude"))


def test_activity_log_folds_repeats_and_keeps_the_newest():
    log = ActivityLog(limit=3, now=lambda: datetime(2026, 1, 1, 9, 30))
    verdict = Verdict(True, Reason.BLOCKLIST, 1.0)
    assert log.add(DISCORD, verdict) is True
    assert log.add(DISCORD, verdict) is False
    assert log.entries[0]["count"] == 2
    for name in ("a.exe", "b.exe", "c.exe"):
        log.add(WindowInfo(process_name=name, title=""), verdict)
    assert [e["key"] for e in log.entries] == ["a.exe", "b.exe", "c.exe"]


# ---------------------------------------------------------------------- #
# Revice's buddy link, without a network
# ---------------------------------------------------------------------- #
class FakeLink:
    def __init__(self, events=()):
        self.state = "paired"
        self.name = "me"
        self.events = list(events)
        self.sent = []
        self.closed = 0

    def poll(self):
        out, self.events = self.events, []
        return out

    def send_status(self, status):
        self.sent.append(status)

    def close(self):
        self.closed += 1
        self.state = "idle"


def test_buddy_link_closes_when_revice_is_not_picked(focus_setup):
    link = FakeLink()
    buddy = BuddyController(link, focus_setup.session, focus_setup.history, focus_setup.ctl)
    buddy.message = "old words"
    assert buddy.tick(active=False) is False
    assert link.closed == 1 and buddy.message == ""


def test_buddy_link_sends_our_timer_and_shows_theirs(focus_setup):
    link = FakeLink([("status", {"phase": "focus", "remaining": 300})])
    t = [100.0]
    buddy = BuddyController(
        link, focus_setup.session, focus_setup.history, focus_setup.ctl, clock=lambda: t[0]
    )
    buddy.tick(active=True)
    assert link.sent, "our timer was sent"
    assert buddy.status is not None
    buddy.tick(active=True)
    assert len(link.sent) == 1  # not again within the same second


# ---------------------------------------------------------------------- #
# The whole controller
# ---------------------------------------------------------------------- #
def test_controller_uses_only_its_own_folder_and_shuts_down_cleanly(tmp_path):
    controller = AppController(AppPaths.inside(tmp_path), buddy_name="test")
    controller.start()
    assert controller.session.phase is Phase.IDLE
    controller.config.focus_minutes = 33
    assert controller.shutdown() == []
    assert controller.shutdown() == []  # twice is fine
    assert controller.is_shut_down and controller.events.closed
    assert Config.load(tmp_path / "config.json").focus_minutes == 33
    assert not controller.camera_watcher.is_capturing


def test_background_helpers_only_post_notes(tmp_path):
    controller = AppController(AppPaths.inside(tmp_path), buddy_name="test")
    controller.notifier.banner_callback("Title", "Body", "high")
    controller.monitor._callback(DISCORD)
    controller.camera_watcher._callback(True)
    kinds = []
    for kind in (BannerRequested, WindowSeen, PhoneSample):
        controller.events.subscribe(kind, lambda e: kinds.append(type(e).__name__))
    controller.events.dispatch_pending()
    assert kinds == ["BannerRequested", "WindowSeen", "PhoneSample"]
    controller.shutdown()
