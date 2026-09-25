"""Tests for Revice's plain logic: messages, the handshake proof, the
status shown in the Buddy tab, and the Pull History merge. No network,
no display."""

import json

import pytest

from lock_in import revice_sync as rs
from lock_in.config import Config
from lock_in.history import HistoryStore, SessionRecord
from lock_in.session import PomodoroSession
from lock_in.tasks import Task, TaskStore


# --- codes and the handshake ------------------------------------------------ #
def test_make_code_is_always_four_digits():
    for _ in range(200):
        code = rs.make_code()
        assert len(code) == 4 and code.isdigit()


@pytest.mark.parametrize("text,ok", [("0427", True), (" 4821 ", True), ("482", False),
                                     ("48211", False), ("48a1", False), ("", False)])
def test_is_valid_code(text, ok):
    assert rs.is_valid_code(text) is ok


def test_check_proof_accepts_the_right_code():
    challenge = b"0123456789abcdef"
    assert rs.check_proof("4821", challenge, rs.proof("4821", challenge))


def test_check_proof_rejects_a_wrong_code_or_changed_challenge():
    challenge = b"0123456789abcdef"
    answer = rs.proof("4821", challenge)
    assert not rs.check_proof("4822", challenge, answer)
    assert not rs.check_proof("4821", b"fedcba9876543210", answer)
    assert not rs.check_proof("4821", challenge, b"")


def test_proof_does_not_contain_the_code():
    assert b"4821" not in rs.proof("4821", b"challenge").hex().encode()


# --- messages --------------------------------------------------------------- #
@pytest.mark.parametrize("message", [
    {"type": "status", "phase": "focus", "remaining_seconds": 5},
    {"type": "pull_request"},
    {"type": "pull_reply", "sessions": [], "tasks": []},
    {"type": "bye"},
    {"type": "challenge", "value": "ab"},
])
def test_encode_decode_round_trip(message):
    raw = rs.encode(message)
    assert raw.endswith(b"\n") and raw.count(b"\n") == 1
    assert rs.decode(raw.rstrip(b"\n")) == message


@pytest.mark.parametrize("line", [b"not json", b"[1, 2]", b"5", b'{"no_type": 1}',
                                  b'{"type": "explode"}', b"\xff\xfe"])
def test_decode_returns_none_for_anything_odd(line):
    assert rs.decode(line) is None


def test_decode_survives_deeply_nested_json():
    # A pile of nested brackets parses fine as far as the JSON rules go,
    # but going that deep can blow Python's own call stack. decode()
    # should treat that the same as any other broken line: just None.
    line = b"[" * 20000 + b"]" * 20000
    assert rs.decode(line) is None


def test_take_lines_splits_whole_lines_and_keeps_the_rest():
    buf = bytearray(b'one\ntwo\npart')
    assert rs.take_lines(buf) == [b"one", b"two"]
    assert buf == bytearray(b"part")


# --- status ----------------------------------------------------------------- #
def test_status_from_session_when_idle():
    session = PomodoroSession(Config())
    status = rs.status_from_session(session, None, "DESK")
    assert status == {"type": "status", "name": "DESK", "phase": "idle", "paused": False,
                      "remaining_seconds": 0, "task_name": None}


def test_status_from_session_while_focusing_then_paused():
    session = PomodoroSession(Config())
    session.start()
    running = rs.status_from_session(session, "Read", "DESK")
    assert running["phase"] == "focus" and running["paused"] is False
    assert running["remaining_seconds"] > 0 and running["task_name"] == "Read"
    session.pause()
    assert rs.status_from_session(session, "Read", "DESK")["paused"] is True


def test_clean_status_fixes_odd_values():
    cleaned = rs.clean_status({"type": "status", "phase": "dance", "paused": "yes",
                               "remaining_seconds": -40, "task_name": 7, "name": None})
    assert cleaned == {"phase": "idle", "paused": True, "remaining_seconds": 0,
                       "task_name": None, "name": "Buddy"}


def test_clean_status_caps_long_text_and_huge_numbers():
    cleaned = rs.clean_status({"type": "status", "phase": "focus", "paused": False,
                               "remaining_seconds": 10 ** 9, "task_name": "x" * 500,
                               "name": "y" * 500})
    assert cleaned["remaining_seconds"] == 24 * 60 * 60
    assert len(cleaned["task_name"]) == 100 and len(cleaned["name"]) == 64


@pytest.mark.parametrize("status,expected", [
    ({"phase": "idle", "paused": False, "remaining_seconds": 0, "task_name": None},
     ("00:00", "Not running", "No task picked")),
    ({"phase": "focus", "paused": False, "remaining_seconds": 1112, "task_name": "Read"},
     ("18:32", "Focusing", "Read")),
    ({"phase": "short_break", "paused": False, "remaining_seconds": 300, "task_name": None},
     ("05:00", "On a break", "No task picked")),
    ({"phase": "long_break", "paused": False, "remaining_seconds": 61, "task_name": None},
     ("01:01", "On a break", "No task picked")),
    ({"phase": "focus", "paused": True, "remaining_seconds": 90, "task_name": "Read"},
     ("01:30", "Paused", "Read")),
])
def test_describe_status(status, expected):
    assert rs.describe_status(status) == expected


# --- merge ------------------------------------------------------------------ #
def _session(id_, task_id=None):
    return {"start": "2026-09-20T10:00:00", "end": "2026-09-20T10:25:00",
            "duration_seconds": 1500, "task_id": task_id, "completed": True, "id": id_}


def _task(id_, name):
    return {"id": id_, "name": name, "status": "todo", "created_at": "",
            "completed_at": None, "subtasks": [], "phases": [False, False, False]}


@pytest.fixture
def stores(tmp_path):
    return HistoryStore(tmp_path / "sessions.jsonl"), TaskStore(tmp_path / "tasks.json")


def test_merge_adds_new_tasks_and_sessions(stores):
    history, tasks = stores
    added = rs.merge_pull(history, tasks, [_session("s1", "t1"), _session("s2")],
                          [_task("t1", "Their task")])
    assert added == (2, 1)
    assert tasks.get("t1").name == "Their task"
    assert {r.id for r in history.all()} == {"s1", "s2"}
    assert [r.task_id for r in history.all() if r.id == "s1"] == ["t1"]


def test_merge_twice_adds_nothing_the_second_time(stores):
    history, tasks = stores
    rs.merge_pull(history, tasks, [_session("s1", "t1")], [_task("t1", "Theirs")])
    assert rs.merge_pull(history, tasks, [_session("s1", "t1")], [_task("t1", "Theirs")]) == (0, 0)
    assert len(history.all()) == 1 and len(tasks.all()) == 1


def test_merge_never_changes_what_is_already_here(stores):
    history, tasks = stores
    mine = tasks.add("Mine")
    history.record(SessionRecord(start="2026-09-19T09:00:00", end="2026-09-19T09:25:00",
                                 duration_seconds=1500, task_id=mine.id, completed=True,
                                 id="mine0001"))
    theirs_same_ids = [_task(mine.id, "Renamed by them")]
    sessions_same_id = [dict(_session("mine0001"), duration_seconds=1)]
    assert rs.merge_pull(history, tasks, sessions_same_id, theirs_same_ids) == (0, 0)
    assert tasks.get(mine.id).name == "Mine"
    assert history.all()[0].duration_seconds == 1500


def test_merge_skips_broken_items_and_counts_only_real_adds(stores):
    history, tasks = stores
    sessions = [_session("ok1"), None, "x", {"id": "bad"}, dict(_session("bad2"), start="nope"),
                dict(_session("bad3"), duration_seconds=-5), dict(_session("bad4"), completed="yes"),
                dict(_session("ok1"))]
    task_items = [_task("t1", "Good"), {"name": "no id"}, 7]
    assert rs.merge_pull(history, tasks, sessions, task_items) == (1, 1)


def test_merge_survives_non_list_inputs(stores):
    history, tasks = stores
    assert rs.merge_pull(history, tasks, "junk", {"a": 1}) == (0, 0)


def test_merged_history_is_saved_to_disk(tmp_path):
    history = HistoryStore(tmp_path / "sessions.jsonl")
    tasks = TaskStore(tmp_path / "tasks.json")
    rs.merge_pull(history, tasks, [_session("s1")], [])
    assert [r.id for r in HistoryStore(tmp_path / "sessions.jsonl").all()] == ["s1"]


@pytest.mark.parametrize("sessions,tasks_added,text", [
    (0, 0, "Nothing new to add."),
    (1, 0, "Added 1 session and 0 tasks."),
    (12, 3, "Added 12 sessions and 3 tasks."),
    (2, 1, "Added 2 sessions and 1 task."),
])
def test_pull_result_text(sessions, tasks_added, text):
    assert rs.pull_result_text(sessions, tasks_added) == text


def test_pull_reply_payload_is_plain_json(stores):
    # What ui.py sends back must be JSON-safe, including TaskStatus.
    from dataclasses import asdict
    history, tasks = stores
    tasks.add("A")
    json.dumps([asdict(t) for t in tasks.all()])


def test_merge_pull_skips_tasks_with_bad_field_types(stores):
    """Regression test: pulled tasks used to skip type checking entirely.
    A dict or None `name` (or any other bad-typed field) must not be
    saved, and must not raise partway through the merge -- an unhashable
    id (e.g. a list) used to blow up add_existing() mid-merge."""
    history, tasks = stores
    added = rs.merge_pull(history, tasks, [],
                          [{"id": "x", "name": {"a": 1}}, {"id": "y", "name": None}])
    assert added == (0, 0)
    assert tasks.all() == []


def test_merge_pull_skips_a_too_long_task_name(stores):
    history, tasks = stores
    long_name = "x" * (rs.MAX_TASK_NAME + 1)
    added = rs.merge_pull(history, tasks, [], [_task("t1", long_name)])
    assert added == (0, 0)
    assert tasks.all() == []


# --- pull_reply_payload ------------------------------------------------------ #
def test_pull_reply_payload_leaves_out_a_task_with_no_sessions(stores):
    history, tasks = stores
    tasks.add("No sessions")
    sessions, task_list = rs.pull_reply_payload(history, tasks)
    assert sessions == []
    assert task_list == []


def test_pull_reply_payload_includes_a_task_that_has_a_session(stores):
    history, tasks = stores
    task = tasks.add("Has a session")
    history.record(SessionRecord(start="2026-09-20T10:00:00", end="2026-09-20T10:25:00",
                                 duration_seconds=1500, task_id=task.id, completed=True,
                                 id="s1"))
    sessions, task_list = rs.pull_reply_payload(history, tasks)
    assert [s["id"] for s in sessions] == ["s1"]
    assert [t["id"] for t in task_list] == [task.id]


def test_pull_reply_payload_is_fine_with_a_session_that_has_no_task(stores):
    history, tasks = stores
    history.record(SessionRecord(start="2026-09-20T10:00:00", end="2026-09-20T10:25:00",
                                 duration_seconds=1500, task_id=None, completed=True,
                                 id="s1"))
    sessions, task_list = rs.pull_reply_payload(history, tasks)
    assert [s["id"] for s in sessions] == ["s1"]
    assert task_list == []
