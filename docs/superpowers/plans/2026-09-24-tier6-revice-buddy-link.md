# Tier 6 Revice (Buddy Link) Implementation Plan


**Goal:** When Kamen Rider Revice (2021) is the picked Rider on two computers on the same Wi-Fi, one can Share a 4-digit code and the other can Receive it. They then see each other's live timer and task in a "Buddy" tab, and either side can Pull History to copy the other's sessions and tasks in.

**Architecture:** Three new modules with one job each. `lock_in/revice_sync.py` is plain logic: messages, handshake proof, status cleaning, the merge. It has no socket and no Tk. `lock_in/revice_link.py` is the network: a `BuddyLink` class whose background threads only ever put events in a queue. `lock_in/revice_tab.py` holds the Buddy tab widgets. `ui.py` owns one `BuddyLink` for the app's whole life and reads its events in the existing `_pump()` loop. A new `tier6_effect="buddy_link"` on Revice gates everything.

**Tech Stack:** Python 3 stdlib (`socket`, `threading`, `queue`, `json`, `hmac`, `hashlib`, `secrets`), CustomTkinter (already used), pytest.

## Global Constraints

Copied from the spec (`docs/superpowers/specs/2026-09-24-tier6-revice-buddy-link-design.md`). Every task implicitly includes these.

- **Nothing touches the network until Share or Receive is pressed.** No listener at startup, no background service.
- **Only while Revice is picked.** Picking another Rider, Standard Mode, or closing the app closes the link.
- **Only standard-library modules.** No new entry in `requirements.txt`.
- **Pairing never changes a focus session.** Revice code never calls `session.start/pause/resume/toggle/skip/reset`.
- **Pull History only adds.** It never changes or deletes an existing task or session. Tasks are added before sessions.
- The code is **4 digits**, lasts **120 seconds**, is cancelled after **3 wrong tries**, and is **never sent** over the network (HMAC-SHA256 challenge/response both ways).
- Discovery UDP port **47821**. Find timeout **5 s**. Buddy-gone timeout **10 s**. Pull timeout **15 s**. Max line **5 MB**. Status sent about once a second.
- A `pull_reply` that wasn't asked for is **ignored**.
- Threads **never touch Tk**. The UI reads events with `BuddyLink.poll()` from `_pump()`.
- Everything Revice does in `ui.py` is inside `try/except Exception: pass`. It fails silently and never breaks the timer.
- Version is **2.6.1**.
- Plain, simple wording in every comment, README line, and Help-tab line (a young reader should be able to follow it).
- **No commits, pushes, or tags.** The project owner does all git steps. Do not run `git add`, `git commit`, `git push`, or `git tag`.
- Project files describe the software only: nothing about who or what wrote them.

---

## File Structure

| File | What it does |
|---|---|
| `lock_in/revice_sync.py` (new) | Constants, messages, `encode`/`decode`, `take_lines`, `make_code`, `proof`/`check_proof`, `status_from_session`, `clean_status`, `describe_status`, `session_from_dict`, `merge_pull`, `pull_result_text`. No socket, no Tk. |
| `lock_in/revice_link.py` (new) | `BuddyLink`: share, receive, handshake, paired reader/writer threads, `poll()`. |
| `lock_in/revice_tab.py` (new) | `BuddyTab`: the Buddy tab's widgets and `show()`. |
| `lock_in/tasks.py` | Pull the per-item parsing out of `load()` into `task_from_dict()`; add `TaskStore.add_existing()`. |
| `lock_in/rider_themes.py` | Revice gets `tier6_effect="buddy_link"`; comment names both Tier 6 Riders. |
| `lock_in/ui.py` | Own the link, add the Buddy tab, `_drain_buddy_link()` in `_pump()`, close on exit, Help bullet. |
| `lock_in/__init__.py` | Version 2.6.1; three layout-docstring lines. |
| `README.md`, `SECURITY.md`, `.gitignore` | Docs, as in Task 4. |
| `tests/test_revice_sync.py`, `tests/test_revice_link.py` (new) | Tests. |
| `tests/test_tasks.py`, `tests/test_rider_themes.py` | Grow. |

---

### Task 1: Plain logic (`revice_sync.py`) and `TaskStore.add_existing`

**Files:**
- Create: `lock_in/revice_sync.py`
- Modify: `lock_in/tasks.py` (`load()` loop body at about lines 115-160; new method after `add()`)
- Test: `tests/test_revice_sync.py` (new), `tests/test_tasks.py` (grows)

**Interfaces:**
- Consumes: `HistoryStore.all()`, `HistoryStore.record(SessionRecord)`, `SessionRecord`, `TaskStore.all()`, `Task`, `Phase`.
- Produces (used by Tasks 2 and 3):
  - `tasks.task_from_dict(item: object) -> Optional[Task]`
  - `TaskStore.add_existing(task: Task) -> bool`
  - `revice_sync` constants: `DISCOVERY_PORT`, `HELLO`, `CODE_LIFETIME_SECONDS`, `MAX_WRONG_TRIES`, `FIND_TIMEOUT_SECONDS`, `BUDDY_GONE_SECONDS`, `PULL_TIMEOUT_SECONDS`, `STATUS_EVERY_SECONDS`, `MAX_LINE_BYTES`, and the `MSG_*` texts.
  - `make_code() -> str`, `is_valid_code(text: str) -> bool`
  - `proof(code: str, challenge: bytes) -> bytes`, `check_proof(code: str, challenge: bytes, answer: bytes) -> bool`
  - `encode(message: dict) -> bytes`, `decode(line: bytes) -> Optional[dict]`, `take_lines(buf: bytearray) -> list[bytes]`
  - `status_from_session(session, task_name: Optional[str], name: str) -> dict`
  - `clean_status(message: dict) -> dict`, `describe_status(status: dict) -> tuple[str, str, str]`
  - `session_from_dict(item: object) -> Optional[SessionRecord]`
  - `merge_pull(history, tasks, their_sessions: list, their_tasks: list) -> tuple[int, int]` (sessions added, tasks added)
  - `pull_result_text(sessions_added: int, tasks_added: int) -> str`

- [ ] **Step 1: Write the failing task-store tests**

Add to the end of `tests/test_tasks.py`:

```python
def test_task_from_dict_reads_a_good_task():
    from lock_in.tasks import task_from_dict
    task = task_from_dict({"id": "abc12345", "name": "Read", "status": "done",
                           "created_at": "2026-09-01T10:00:00", "completed_at": None,
                           "subtasks": [{"id": "s1", "text": "Ch 1", "done": True}],
                           "phases": [True, False, False]})
    assert task.id == "abc12345"
    assert task.name == "Read"
    assert task.status == TaskStatus.DONE
    assert task.subtasks == [Subtask(id="s1", text="Ch 1", done=True)]
    assert task.phases == [True, False, False]


@pytest.mark.parametrize("item", [None, 5, "x", [], {}, {"id": "a"}, {"name": "b"},
                                  {"id": "a", "name": "b", "status": "flying"}])
def test_task_from_dict_returns_none_for_broken_items(item):
    from lock_in.tasks import task_from_dict
    assert task_from_dict(item) is None


def test_add_existing_keeps_the_id_and_saves(tmp_path):
    path = tmp_path / "tasks.json"
    store = TaskStore(path)
    task = Task(id="keepme01", name="From the other computer")
    assert store.add_existing(task) is True
    reloaded = TaskStore(path)
    assert reloaded.get("keepme01").name == "From the other computer"


def test_add_existing_refuses_a_duplicate_id(store):
    first = store.add("Mine")
    assert store.add_existing(Task(id=first.id, name="Theirs")) is False
    assert store.get(first.id).name == "Mine"
    assert len(store.all()) == 1
```

- [ ] **Step 2: Run them and see them fail**

Run: `pytest tests/test_tasks.py -v`
Expected: the new tests FAIL with `ImportError: cannot import name 'task_from_dict'` / `AttributeError: 'TaskStore' object has no attribute 'add_existing'`. Old tests still pass.

- [ ] **Step 3: Move the parsing into `task_from_dict()` and add `add_existing()`**

In `lock_in/tasks.py`, add this module-level function just above `class TaskStore:`. The body is the existing loop body from `load()`, moved without changing its behavior:

```python
def task_from_dict(item: object) -> Optional[Task]:
    """Turn one saved task (a dict) back into a Task. Returns None if
    it's broken, so one bad entry never costs you the others. Used by
    TaskStore.load() and by Revice's Pull History."""
    if not isinstance(item, dict):
        return None
    try:
        # Build subtasks defensively, skipping any malformed entries.
        subtasks = []
        for s in item.get("subtasks", []):
            try:
                subtask = Subtask(
                    id=s.get("id", ""),
                    text=s.get("text", ""),
                    done=s.get("done", False),
                )
                # Only add valid subtasks (with non-empty id and text).
                if subtask.id and subtask.text:
                    subtasks.append(subtask)
            except (TypeError, AttributeError):
                # Skip malformed subtask entries.
                continue

        # phases: always exactly 3 booleans (Plan, Work, Review).
        # A hand-edited tasks.json could hold anything here --
        # anything that isn't a list of exactly 3 entries falls
        # back to all-unchecked rather than raising or guessing
        # which one was meant.
        raw_phases = item.get("phases", [False, False, False])
        if isinstance(raw_phases, list) and len(raw_phases) == 3:
            phases = [bool(p) for p in raw_phases]
        else:
            phases = [False, False, False]

        return Task(
            id=item["id"],
            name=item["name"],
            subtasks=subtasks,
            status=TaskStatus(item.get("status", "todo")),
            created_at=item.get("created_at", ""),
            completed_at=item.get("completed_at"),
            phases=phases,
        )
    except (KeyError, ValueError, TypeError):
        return None
```

Then replace the whole `for item in entries:` loop in `TaskStore.load()` with:

```python
        for item in entries:
            task = task_from_dict(item)
            if task is not None:
                self._tasks[task.id] = task
```

Add this method right after `add()`:

```python
    def add_existing(self, task: Task) -> bool:
        """Add a whole task that already has its own id -- Revice's Pull
        History uses this for tasks copied from another computer. Saves
        straight away. Returns False, with nothing changed, if a task
        with that id is already here."""
        if task.id in self._tasks:
            return False
        self._tasks[task.id] = task
        self.save()
        return True
```

- [ ] **Step 4: Run the task tests**

Run: `pytest tests/test_tasks.py -v`
Expected: all PASS (old and new).

- [ ] **Step 5: Write the failing `revice_sync` tests**

Create `tests/test_revice_sync.py`:

```python
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
```

- [ ] **Step 6: Run them and see them fail**

Run: `pytest tests/test_revice_sync.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lock_in.revice_sync'`.

- [ ] **Step 7: Write `lock_in/revice_sync.py`**

```python
"""
revice_sync.py
==============
Kamen Rider Revice's plain logic. Revice is two heroes sharing one body,
so its gimmick is two computers sharing one Lock In: pair them with a
4-digit code, see each other's timer in a "Buddy" tab, and pull the
other computer's history into yours. See
docs/superpowers/specs/2026-09-24-tier6-revice-buddy-link-design.md.

This file never opens a network connection and never draws anything.
revice_link.py does the network part and revice_tab.py draws the tab.
Keeping the rules here means they're all tested with no Wi-Fi and no
window.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from typing import Optional

from .history import SessionRecord
from .tasks import task_from_dict

# The port the "anyone sharing?" call goes to. Only listened on while a
# code is showing on screen.
DISCOVERY_PORT = 47821
# The "anyone sharing?" call itself. Has no code in it.
HELLO = b"lock-in-revice-hello-1"
# How long a code works for, in seconds (2 minutes).
CODE_LIFETIME_SECONDS = 120
# Wrong answers allowed before the code is thrown away, so nobody can try
# all 10,000 codes.
MAX_WRONG_TRIES = 3
# How long Receive keeps looking before giving up, in seconds.
FIND_TIMEOUT_SECONDS = 5
# If nothing at all arrives from the buddy for this long, they're gone.
BUDDY_GONE_SECONDS = 10
# How long to wait for the other side to answer Pull History.
PULL_TIMEOUT_SECONDS = 15
# How often to send our timer to the buddy, in seconds.
STATUS_EVERY_SECONDS = 1
# The biggest single message we'll accept (5 MB), so a bad sender can't
# fill up the computer's memory.
MAX_LINE_BYTES = 5 * 1024 * 1024
# The longest names we'll show, so odd data can't stretch the tab.
MAX_TASK_NAME = 100
MAX_BUDDY_NAME = 64
# No timer is ever longer than a day, so anything bigger is nonsense.
MAX_REMAINING_SECONDS = 24 * 60 * 60

# Every message has one of these types. Anything else is ignored.
MESSAGE_TYPES = {"status", "pull_request", "pull_reply", "bye",
                 "challenge", "proof", "welcome", "wrong"}

# What the Buddy tab says when something goes wrong.
MSG_NOT_FOUND = "Couldn't find it. Are you both on the same Wi-Fi?"
MSG_WRONG_CODE = "That code didn't work."
MSG_TOO_MANY = "Too many wrong tries. Press Share again."
MSG_CODE_RAN_OUT = "The code ran out. Press Share again."
MSG_CANT_SHARE = "Couldn't share right now. Try again in a moment."
MSG_BUDDY_LEFT = "Your buddy left."
MSG_PULL_FAILED = "Pull History didn't finish. Try again."
MSG_TYPE_FOUR = "Type the 4 numbers you see on the other computer."

_PHASES = {"idle", "focus", "short_break", "long_break"}


# --------------------------------------------------------------------------- #
# Codes and the secret handshake
# --------------------------------------------------------------------------- #
def make_code() -> str:
    """A random 4-digit code, like "0427"."""
    return f"{secrets.randbelow(10000):04d}"


def is_valid_code(text: str) -> bool:
    """True if `text` (spaces around it are fine) is exactly 4 digits."""
    text = text.strip()
    return len(text) == 4 and text.isdigit()


def proof(code: str, challenge: bytes) -> bytes:
    """The answer to a challenge. Only someone who knows the code can make
    it, and the code itself can't be worked out from it."""
    return hmac.new(code.encode("utf-8"), challenge, hashlib.sha256).digest()


def check_proof(code: str, challenge: bytes, answer: bytes) -> bool:
    """True if `answer` is the right answer for this code and challenge."""
    return hmac.compare_digest(proof(code, challenge), answer)


# --------------------------------------------------------------------------- #
# Messages: one JSON object per line
# --------------------------------------------------------------------------- #
def encode(message: dict) -> bytes:
    return (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")


def decode(line: bytes) -> Optional[dict]:
    """One line back into a message, or None if it's broken or unknown."""
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(message, dict) or message.get("type") not in MESSAGE_TYPES:
        return None
    return message


def take_lines(buf: bytearray) -> list[bytes]:
    """Take every whole line out of `buf` (without the newline). Whatever
    is left after the last newline stays in `buf` for next time."""
    lines = []
    while True:
        index = buf.find(b"\n")
        if index < 0:
            return lines
        lines.append(bytes(buf[:index]))
        del buf[:index + 1]


# --------------------------------------------------------------------------- #
# The timer we send, and how the Buddy tab shows theirs
# --------------------------------------------------------------------------- #
def status_from_session(session, task_name: Optional[str], name: str) -> dict:
    """Our timer as a `status` message. Only these few things are sent."""
    return {
        "type": "status",
        "name": name,
        "phase": session.phase.value,
        "paused": session.is_paused,
        "remaining_seconds": session.remaining_seconds,
        "task_name": task_name,
    }


def clean_status(message: dict) -> dict:
    """Make a received status safe to show, whatever the other side sent."""
    phase = message.get("phase")
    if phase not in _PHASES:
        phase = "idle"
    remaining = message.get("remaining_seconds")
    if not isinstance(remaining, int) or isinstance(remaining, bool):
        remaining = 0
    remaining = max(0, min(MAX_REMAINING_SECONDS, remaining))
    task_name = message.get("task_name")
    task_name = task_name[:MAX_TASK_NAME] if isinstance(task_name, str) and task_name else None
    name = message.get("name")
    name = name[:MAX_BUDDY_NAME] if isinstance(name, str) and name else "Buddy"
    return {"phase": phase, "paused": bool(message.get("paused")),
            "remaining_seconds": remaining, "task_name": task_name, "name": name}


def describe_status(status: dict) -> tuple[str, str, str]:
    """(time, what they're doing, task) as the Buddy tab shows them."""
    minutes, seconds = divmod(status["remaining_seconds"], 60)
    time_text = f"{minutes:02d}:{seconds:02d}"
    if status["phase"] == "idle":
        doing = "Not running"
    elif status["paused"]:
        doing = "Paused"
    elif status["phase"] == "focus":
        doing = "Focusing"
    else:
        doing = "On a break"
    return time_text, doing, status["task_name"] or "No task picked"


# --------------------------------------------------------------------------- #
# Pull History
# --------------------------------------------------------------------------- #
def session_from_dict(item: object) -> Optional[SessionRecord]:
    """One pulled session, or None if anything about it looks wrong."""
    if not isinstance(item, dict):
        return None
    record_id = item.get("id")
    start, end = item.get("start"), item.get("end")
    duration = item.get("duration_seconds")
    task_id = item.get("task_id")
    completed = item.get("completed")
    if not (isinstance(record_id, str) and record_id):
        return None
    if not (isinstance(start, str) and isinstance(end, str)):
        return None
    try:
        datetime.fromisoformat(start)
        datetime.fromisoformat(end)
    except ValueError:
        return None
    if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
        return None
    if task_id is not None and not isinstance(task_id, str):
        return None
    if not isinstance(completed, bool):
        return None
    return SessionRecord(start=start, end=end, duration_seconds=duration,
                         task_id=task_id, completed=completed, id=record_id)


def merge_pull(history, tasks, their_sessions, their_tasks) -> tuple[int, int]:
    """Add every pulled task, then every pulled session, whose id isn't
    already here. Never changes or deletes anything. Returns
    (sessions added, tasks added)."""
    tasks_added = 0
    if isinstance(their_tasks, list):
        for item in their_tasks:
            task = task_from_dict(item)
            if task is not None and tasks.add_existing(task):
                tasks_added += 1

    sessions_added = 0
    if isinstance(their_sessions, list):
        known = {record.id for record in history.all()}
        for item in their_sessions:
            record = session_from_dict(item)
            if record is None or record.id in known:
                continue
            history.record(record)
            known.add(record.id)
            sessions_added += 1
    return sessions_added, tasks_added


def pull_result_text(sessions_added: int, tasks_added: int) -> str:
    """What the Buddy tab says after Pull History finishes."""
    if sessions_added == 0 and tasks_added == 0:
        return "Nothing new to add."
    session_word = "session" if sessions_added == 1 else "sessions"
    task_word = "task" if tasks_added == 1 else "tasks"
    return f"Added {sessions_added} {session_word} and {tasks_added} {task_word}."
```

- [ ] **Step 8: Run the new and old tests**

Run: `pytest tests/test_revice_sync.py tests/test_tasks.py tests/test_history.py -v`
Expected: all PASS.

- [ ] **Step 9: No commit.** The project owner commits at the end.

---

### Task 2: The network (`revice_link.py`)

**Files:**
- Create: `lock_in/revice_link.py`
- Test: `tests/test_revice_link.py` (new)

**Interfaces:**
- Consumes (from Task 1): `revice_sync` constants, `MSG_*`, `make_code`, `proof`, `check_proof`, `encode`, `decode`, `take_lines`.
- Produces (used by Task 3):
  - `BuddyLink(name: str, discovery_port: Optional[int] = DISCOVERY_PORT, broadcast_address: str = "255.255.255.255", clock=time.monotonic)`
  - Attributes read by the UI: `state` (`"idle"`, `"sharing"`, `"finding"`, `"paired"`), `code: Optional[str]`, `code_deadline: float` (in `clock()` time), `buddy_name: Optional[str]`, `tcp_port: Optional[int]`, `pull_pending: bool`.
  - Methods: `share() -> Optional[str]`, `receive(code: str, address: Optional[tuple[str, int]] = None) -> None`, `send_status(status: dict) -> None`, `request_pull() -> bool`, `send_pull_reply(sessions: list, tasks: list) -> None`, `close() -> None`, `poll() -> list[tuple]`.
  - Events from `poll()`: `("paired", name)`, `("status", message_dict)`, `("pull_request",)`, `("pull_reply", sessions_list, tasks_list)`, `("pull_failed",)`, `("left",)`, `("error", text)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_revice_link.py`:

```python
"""Tests for Revice's network link. Both ends run on this computer
(127.0.0.1), so the tests never depend on the Wi-Fi. Discovery is
tested by sending the "anyone sharing?" call straight to 127.0.0.1
instead of to everyone."""

import socket
import time

import pytest

from lock_in import revice_sync as rs
from lock_in.revice_link import BuddyLink


def wait_for(link, kind, timeout=5.0):
    """Poll `link` until an event of `kind` shows up; return it."""
    seen = []
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        for event in link.poll():
            if event[0] == kind:
                return event
            seen.append(event)
        time.sleep(0.02)
    pytest.fail(f"no {kind!r} event; saw {seen}")


def free_udp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def links():
    made = []

    def make(name, **kwargs):
        kwargs.setdefault("discovery_port", None)
        link = BuddyLink(name, **kwargs)
        made.append(link)
        return link

    yield make
    for link in made:
        link.close()


def pair(make):
    a, b = make("A"), make("B")
    code = a.share()
    b.receive(code, address=("127.0.0.1", a.tcp_port))
    assert wait_for(a, "paired") == ("paired", "B")
    assert wait_for(b, "paired") == ("paired", "A")
    return a, b


def test_share_gives_a_code_and_starts_sharing(links):
    a = links("A")
    code = a.share()
    assert rs.is_valid_code(code)
    assert a.state == "sharing" and a.code == code and a.tcp_port


def test_share_and_receive_pair_up(links):
    a, b = pair(links)
    assert a.state == b.state == "paired"
    assert a.buddy_name == "B" and b.buddy_name == "A"
    assert a.code is None


def test_wrong_code_is_refused(links):
    a, b = links("A"), links("B")
    code = a.share()
    wrong = "0000" if code != "0000" else "1111"
    b.receive(wrong, address=("127.0.0.1", a.tcp_port))
    assert wait_for(b, "error") == ("error", rs.MSG_WRONG_CODE)
    assert a.state == "sharing"


def test_three_wrong_tries_cancel_the_code(links):
    a = links("A")
    code = a.share()
    wrong = "0000" if code != "0000" else "1111"
    for _ in range(rs.MAX_WRONG_TRIES):
        b = links("B")
        b.receive(wrong, address=("127.0.0.1", a.tcp_port))
        wait_for(b, "error")
    assert wait_for(a, "error") == ("error", rs.MSG_TOO_MANY)
    assert a.state == "idle" and a.code is None


def test_code_runs_out(links):
    now = [1000.0]
    a = links("A", clock=lambda: now[0])
    a.share()
    now[0] += rs.CODE_LIFETIME_SECONDS + 1
    assert wait_for(a, "error") == ("error", rs.MSG_CODE_RAN_OUT)
    assert a.state == "idle"


def test_nobody_there_means_not_found(links):
    b = links("B")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        closed_port = s.getsockname()[1]
    b.receive("1234", address=("127.0.0.1", closed_port))
    assert wait_for(b, "error") == ("error", rs.MSG_NOT_FOUND)
    assert b.state == "idle"


def test_status_arrives_on_the_other_side(links):
    a, b = pair(links)
    a.send_status({"type": "status", "phase": "focus", "remaining_seconds": 42})
    event = wait_for(b, "status")
    assert event[1]["remaining_seconds"] == 42


def test_pull_round_trip(links):
    a, b = pair(links)
    assert a.request_pull() is True
    assert a.pull_pending
    wait_for(b, "pull_request")
    b.send_pull_reply([{"id": "s1"}], [{"id": "t1"}])
    assert wait_for(a, "pull_reply") == ("pull_reply", [{"id": "s1"}], [{"id": "t1"}])
    assert not a.pull_pending


def test_pull_reply_that_was_not_asked_for_is_ignored(links):
    a, b = pair(links)
    b.send_pull_reply([{"id": "s1"}], [])
    b.send_status({"type": "status"})
    wait_for(a, "status")   # the status came through...
    assert all(e[0] != "pull_reply" for e in a.poll())   # ...the reply didn't


def test_pull_times_out(links):
    a, b = pair(links)
    a.request_pull()
    # Pretend the pull was asked for long ago. (Moving a fake clock
    # instead would also trip the "buddy left" check.)
    a._pull_started -= rs.PULL_TIMEOUT_SECONDS + 1
    wait_for(a, "pull_failed")
    assert not a.pull_pending and a.state == "paired"


def test_close_on_one_side_means_left_on_the_other(links):
    a, b = pair(links)
    a.close()
    assert wait_for(b, "left") == ("left",)
    assert a.state == b.state == "idle"


def test_silence_means_buddy_left(links):
    now = [1000.0]
    a = links("A", clock=lambda: now[0])
    b = links("B")
    code = a.share()
    b.receive(code, address=("127.0.0.1", a.tcp_port))
    wait_for(a, "paired")
    now[0] += rs.BUDDY_GONE_SECONDS + 1
    assert wait_for(a, "left") == ("left",)


def test_oversized_line_closes_the_link(links):
    a, b = pair(links)
    try:
        b._conn.settimeout(10)
        b._conn.sendall(b"x" * (rs.MAX_LINE_BYTES + 10))
    except OSError:
        pass   # a may hang up before all of it is sent -- that's the point
    assert wait_for(a, "left", timeout=10) == ("left",)


def test_discovery_finds_the_sharer(links):
    port = free_udp_port()
    a = links("A", discovery_port=port)
    b = links("B", discovery_port=port, broadcast_address="127.0.0.1")
    code = a.share()
    b.receive(code)
    assert wait_for(b, "paired") == ("paired", "A")


def test_busy_discovery_port_means_cant_share(links):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as blocker:
        blocker.bind(("", 0))
        port = blocker.getsockname()[1]
        a = links("A", discovery_port=port)
        assert a.share() is None
        assert wait_for(a, "error") == ("error", rs.MSG_CANT_SHARE)
        assert a.state == "idle"


def test_nothing_is_listening_before_share(links):
    a = links("A")
    assert a.state == "idle" and a.tcp_port is None


def test_send_when_not_paired_does_nothing(links):
    a = links("A")
    a.send_status({"type": "status"})
    assert a.request_pull() is False
    a.send_pull_reply([], [])
    assert a.poll() == []
```

- [ ] **Step 2: Run them and see them fail**

Run: `pytest tests/test_revice_link.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lock_in.revice_link'`.

- [ ] **Step 3: Write `lock_in/revice_link.py`**

```python
"""
revice_link.py
==============
The network part of Kamen Rider Revice's buddy link. See
docs/superpowers/specs/2026-09-24-tier6-revice-buddy-link-design.md.

How it works, in short:

- Share: show a 4-digit code, listen for "anyone sharing?" calls and
  for one connection. The code is never sent; both sides prove they
  know it with a challenge and answer (see revice_sync.proof()).
- Receive: call out "anyone sharing?", connect to whoever answers, and
  do the same challenge and answer.
- Paired: send each other our timers, and history when asked. If nothing
  arrives for a while, the buddy is gone.

All the waiting happens on background threads. They NEVER touch the
window -- they only drop news into a queue, and ui.py picks it up with
poll() on its normal timer tick. Nothing listens on the network until
share() is called, and close() stops everything.
"""

from __future__ import annotations

import json
import queue
import secrets
import socket
import threading
import time
from typing import Callable, Optional

from . import revice_sync as rs

_WRONG = "wrong"
_HANDSHAKE_LINE_LIMIT = 4096


class BuddyLink:
    def __init__(self, name: str, discovery_port: Optional[int] = rs.DISCOVERY_PORT,
                 broadcast_address: str = "255.255.255.255",
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.name = name
        # None means "don't use the call-out at all" (tests use this).
        self.discovery_port = discovery_port
        self.broadcast_address = broadcast_address
        self._clock = clock
        self._events: "queue.Queue[tuple]" = queue.Queue()
        self._lock = threading.Lock()
        # Each share/receive gets its own stop flag. Old threads see
        # their flag set and quietly finish, so they can't mix with new ones.
        self._stop = threading.Event()
        self._stop.set()
        self._sockets: list = []
        self._conn: Optional[socket.socket] = None
        self._outgoing: "queue.Queue[dict]" = queue.Queue()
        self._last_heard = 0.0
        self._pull_started: Optional[float] = None
        self.state = "idle"
        self.code: Optional[str] = None
        self.code_deadline = 0.0
        self.buddy_name: Optional[str] = None
        self.tcp_port: Optional[int] = None

    # ------------------------------------------------------------------ #
    # What the app calls
    # ------------------------------------------------------------------ #
    @property
    def pull_pending(self) -> bool:
        return self._pull_started is not None

    def poll(self) -> list:
        """Everything that happened since the last call."""
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    def share(self) -> Optional[str]:
        """Start sharing. Returns the code, or None if it couldn't start."""
        self.close()
        stop = self._fresh_stop()
        server = udp = None
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(("", 0))
            server.listen(4)
            server.settimeout(0.5)
            if self.discovery_port is not None:
                udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                udp.bind(("", self.discovery_port))
                udp.settimeout(0.5)
        except OSError:
            for sock in (server, udp):
                if sock is not None:
                    sock.close()
            stop.set()
            self._events.put(("error", rs.MSG_CANT_SHARE))
            return None
        self._track(server)
        if udp is not None:
            self._track(udp)
        code = rs.make_code()
        self.code = code
        self.code_deadline = self._clock() + rs.CODE_LIFETIME_SECONDS
        self.tcp_port = server.getsockname()[1]
        self.state = "sharing"
        self._thread(self._share_loop, stop, server, udp, code)
        if udp is not None:
            self._thread(self._answer_loop, stop, udp, self.tcp_port)
        return code

    def receive(self, code: str, address: Optional[tuple] = None) -> None:
        """Start looking for a sharer with this code. `address` skips the
        call-out and connects straight there (tests use this)."""
        self.close()
        stop = self._fresh_stop()
        self.state = "finding"
        self._thread(self._find_loop, stop, code.strip(), address)

    def send_status(self, status: dict) -> None:
        if self.state == "paired":
            self._outgoing.put(status)

    def request_pull(self) -> bool:
        """Ask the buddy for their history. False if not paired or
        already waiting."""
        if self.state != "paired" or self._pull_started is not None:
            return False
        self._pull_started = self._clock()
        self._outgoing.put({"type": "pull_request"})
        return True

    def send_pull_reply(self, sessions: list, tasks: list) -> None:
        if self.state == "paired":
            self._outgoing.put({"type": "pull_reply", "sessions": sessions, "tasks": tasks})

    def close(self) -> None:
        """Stop everything: cancel a code, stop looking, or unpair
        (telling the buddy "bye" first). Safe to call any time."""
        conn = self._conn
        if self.state == "paired" and conn is not None:
            try:
                conn.settimeout(1.0)
                conn.sendall(rs.encode({"type": "bye"}))
            except OSError:
                pass
        self._shutdown()

    # ------------------------------------------------------------------ #
    # Bookkeeping
    # ------------------------------------------------------------------ #
    def _fresh_stop(self) -> threading.Event:
        with self._lock:
            self._stop = threading.Event()
            self._sockets = []
            return self._stop

    def _track(self, sock: socket.socket) -> None:
        with self._lock:
            self._sockets.append(sock)

    def _thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def _shutdown(self) -> None:
        with self._lock:
            self._stop.set()
            sockets, self._sockets = self._sockets, []
        for sock in sockets:
            try:
                sock.close()
            except OSError:
                pass
        self._conn = None
        self._pull_started = None
        self.state = "idle"
        self.code = None
        self.buddy_name = None
        self.tcp_port = None

    def _end(self, stop: threading.Event, event: tuple) -> None:
        """A thread hit the end of the road. Only acts if it's still the
        current attempt, so a stale thread can't undo a newer one."""
        with self._lock:
            current = stop is self._stop and not stop.is_set()
        if current:
            self._shutdown()
            self._events.put(event)

    # ------------------------------------------------------------------ #
    # Share
    # ------------------------------------------------------------------ #
    def _answer_loop(self, stop, udp, tcp_port) -> None:
        """Answer every "anyone sharing?" call with where to connect."""
        reply = json.dumps({"port": tcp_port}).encode("utf-8")
        while not stop.is_set():
            try:
                data, addr = udp.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                return
            if data == rs.HELLO:
                try:
                    udp.sendto(reply, addr)
                except OSError:
                    pass

    def _share_loop(self, stop, server, udp, code) -> None:
        wrong_tries = 0
        while not stop.is_set():
            if self._clock() > self.code_deadline:
                self._end(stop, ("error", rs.MSG_CODE_RAN_OUT))
                return
            try:
                conn, _addr = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            conn.settimeout(5.0)
            buf = bytearray()
            try:
                result = self._handshake_as_sharer(conn, code, buf)
            except OSError:
                result = None
            if result is None or result == _WRONG:
                conn.close()
                if result == _WRONG:
                    wrong_tries += 1
                    if wrong_tries >= rs.MAX_WRONG_TRIES:
                        self._end(stop, ("error", rs.MSG_TOO_MANY))
                        return
                continue
            # Paired: stop listening, keep only this one connection.
            for sock in (server, udp):
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
            self._start_paired(stop, conn, buf, result)
            return

    def _handshake_as_sharer(self, conn, code, buf) -> Optional[str]:
        """Returns the buddy's name, _WRONG, or None if it broke."""
        challenge = secrets.token_bytes(16)
        conn.sendall(rs.encode({"type": "challenge", "value": challenge.hex()}))
        message = rs.decode(_read_line(conn, buf))
        if message is None or message["type"] != "proof":
            return None
        try:
            answer = bytes.fromhex(message["value"])
            their_challenge = bytes.fromhex(message["challenge"])
        except (KeyError, TypeError, ValueError):
            return None
        if not rs.check_proof(code, challenge, answer):
            conn.sendall(rs.encode({"type": "wrong"}))
            return _WRONG
        conn.sendall(rs.encode({"type": "welcome", "name": self.name,
                                "value": rs.proof(code, their_challenge).hex()}))
        name = message.get("name")
        return name[:rs.MAX_BUDDY_NAME] if isinstance(name, str) and name else "Buddy"

    # ------------------------------------------------------------------ #
    # Receive
    # ------------------------------------------------------------------ #
    def _find_loop(self, stop, code, address) -> None:
        saw_wrong = False
        if address is not None:
            outcome = self._try_pair(stop, address, code)
            if outcome == "paired":
                return
            saw_wrong = outcome == _WRONG
        elif self.discovery_port is not None:
            outcome = self._call_out(stop, code)
            if outcome == "paired":
                return
            saw_wrong = outcome == _WRONG
        self._end(stop, ("error", rs.MSG_WRONG_CODE if saw_wrong else rs.MSG_NOT_FOUND))

    def _call_out(self, stop, code) -> Optional[str]:
        """Ask the Wi-Fi "anyone sharing?" and try each answer."""
        try:
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp.settimeout(0.5)
        except OSError:
            return None
        self._track(udp)
        saw_wrong = False
        tried: set = set()
        deadline = self._clock() + rs.FIND_TIMEOUT_SECONDS
        next_hello = 0.0
        try:
            while not stop.is_set() and self._clock() < deadline:
                if self._clock() >= next_hello:
                    try:
                        udp.sendto(rs.HELLO, (self.broadcast_address, self.discovery_port))
                    except OSError:
                        pass
                    next_hello = self._clock() + 1.0
                try:
                    data, addr = udp.recvfrom(1024)
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    port = int(json.loads(data.decode("utf-8"))["port"])
                except (ValueError, KeyError, TypeError, UnicodeDecodeError):
                    continue
                target = (addr[0], port)
                if target in tried:
                    continue
                tried.add(target)
                outcome = self._try_pair(stop, target, code)
                if outcome == "paired":
                    return "paired"
                saw_wrong = saw_wrong or outcome == _WRONG
        finally:
            try:
                udp.close()
            except OSError:
                pass
        return _WRONG if saw_wrong else None

    def _try_pair(self, stop, address, code) -> Optional[str]:
        """Connect and do the handshake. "paired", _WRONG, or None."""
        try:
            conn = socket.create_connection(address, timeout=3.0)
        except OSError:
            return None
        buf = bytearray()
        try:
            conn.settimeout(5.0)
            message = rs.decode(_read_line(conn, buf))
            if message is None or message["type"] != "challenge":
                conn.close()
                return None
            challenge = bytes.fromhex(message["value"])
            mine = secrets.token_bytes(16)
            conn.sendall(rs.encode({"type": "proof", "name": self.name,
                                    "value": rs.proof(code, challenge).hex(),
                                    "challenge": mine.hex()}))
            reply = rs.decode(_read_line(conn, buf))
            if reply is not None and reply["type"] == "wrong":
                conn.close()
                return _WRONG
            if reply is None or reply["type"] != "welcome":
                conn.close()
                return None
            if not rs.check_proof(code, mine, bytes.fromhex(reply["value"])):
                conn.close()
                return None
        except (OSError, KeyError, TypeError, ValueError):
            conn.close()
            return None
        if stop.is_set():
            conn.close()
            return None
        name = reply.get("name")
        name = name[:rs.MAX_BUDDY_NAME] if isinstance(name, str) and name else "Buddy"
        self._start_paired(stop, conn, buf, name)
        return "paired"

    # ------------------------------------------------------------------ #
    # Paired
    # ------------------------------------------------------------------ #
    def _start_paired(self, stop, conn, buf, name) -> None:
        conn.settimeout(1.0)
        self._track(conn)
        if stop.is_set():
            conn.close()
            return
        self._conn = conn
        self._outgoing = queue.Queue()
        self._last_heard = self._clock()
        self._pull_started = None
        self.code = None
        self.buddy_name = name
        self.state = "paired"
        self._events.put(("paired", name))
        self._thread(self._reader, stop, conn, buf)
        self._thread(self._writer, stop, conn, self._outgoing)

    def _reader(self, stop, conn, buf) -> None:
        while not stop.is_set():
            for line in rs.take_lines(buf):
                if not self._handle(stop, rs.decode(line)):
                    return
            if len(buf) > rs.MAX_LINE_BYTES:
                self._end(stop, ("left",))
                return
            now = self._clock()
            if self._pull_started is not None and now - self._pull_started > rs.PULL_TIMEOUT_SECONDS:
                self._pull_started = None
                self._events.put(("pull_failed",))
            if now - self._last_heard > rs.BUDDY_GONE_SECONDS:
                self._end(stop, ("left",))
                return
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                self._end(stop, ("left",))
                return
            if not chunk:
                self._end(stop, ("left",))
                return
            self._last_heard = self._clock()
            buf += chunk

    def _handle(self, stop, message: Optional[dict]) -> bool:
        """Deal with one message. False means stop reading."""
        if message is None:
            return True
        kind = message["type"]
        if kind == "bye":
            self._end(stop, ("left",))
            return False
        if kind == "status":
            self._events.put(("status", message))
        elif kind == "pull_request":
            self._events.put(("pull_request",))
        elif kind == "pull_reply" and self._pull_started is not None:
            # Only a reply we asked for. Anything else is ignored.
            self._pull_started = None
            sessions = message.get("sessions")
            tasks = message.get("tasks")
            self._events.put(("pull_reply",
                              sessions if isinstance(sessions, list) else [],
                              tasks if isinstance(tasks, list) else []))
        return True

    def _writer(self, stop, conn, outgoing) -> None:
        while not stop.is_set():
            try:
                message = outgoing.get(timeout=0.5)
            except queue.Empty:
                continue
            # A big pull reply on slow Wi-Fi can take longer than the
            # usual 1-second wait, so give it longer. If sending still
            # stalls, end the link rather than send half a message.
            big = message.get("type") == "pull_reply"
            try:
                if big:
                    conn.settimeout(30.0)
                conn.sendall(rs.encode(message))
                if big:
                    conn.settimeout(1.0)
            except OSError:
                self._end(stop, ("left",))
                return


def _read_line(conn, buf: bytearray) -> bytes:
    """Read one handshake line. Leftover bytes stay in `buf` for the
    paired reader. Raises OSError if the line is too long or the
    connection ends."""
    while True:
        lines = rs.take_lines(buf)
        if lines:
            # Put any extra whole lines back in front of the leftovers.
            rest = b"".join(line + b"\n" for line in lines[1:])
            buf[:0] = rest
            return lines[0]
        if len(buf) > _HANDSHAKE_LINE_LIMIT:
            raise OSError("handshake line too long")
        chunk = conn.recv(4096)
        if not chunk:
            raise OSError("connection closed")
        buf += chunk
```

Note on the writer: the socket's timeout is shared with the reader, so while a big pull reply is being sent, the reader's `recv` just waits longer. That's harmless.

- [ ] **Step 4: Run the link tests**

Run: `pytest tests/test_revice_link.py -v`
Expected: all PASS. Windows may show a firewall pop-up the first time. Choosing either answer is fine, because the tests only use 127.0.0.1.

- [ ] **Step 5: Run them 5 more times to catch timing flakiness**

Run: `for i in 1 2 3 4 5; do pytest tests/test_revice_link.py -q || break; done`
Expected: 5 clean runs. If any test is flaky, fix the cause (usually a missing wait). Never add a `sleep` just to make a test pass.

- [ ] **Step 6: No commit.**

---

### Task 3: Revice's flag, the Buddy tab, and the app wiring

**Files:**
- Create: `lock_in/revice_tab.py`
- Modify: `lock_in/rider_themes.py` (the `tier6_effect` comment at about lines 130-135; Revice entry at about line 338)
- Modify: `lock_in/ui.py` (imports about line 67; `__init__` before `self._build_header()` about line 369; `_build_tabs()` about line 1223; `_pump()` about line 1940; Help tab Tier 6 section about line 1707; `_on_close()` about line 3480)
- Test: `tests/test_rider_themes.py` (grows)

**Interfaces:**
- Consumes: `BuddyLink` (Task 2), `revice_sync` (Task 1).
- Produces: `BuddyTab(parent, *, accent: str, text_color: str, on_share, on_receive, on_cancel, on_pull, on_unpair)` with `show(link, status: Optional[dict], message: str, now: float) -> None`. Callbacks: `on_share()`, `on_receive(code: str)`, `on_cancel()`, `on_pull()`, `on_unpair()`.

- [ ] **Step 1: Write the failing theme test**

In `tests/test_rider_themes.py`, replace `test_only_wizard_has_a_tier6_effect` with:

```python
def test_only_wizard_and_revice_have_a_tier6_effect():
    from lock_in.rider_themes import RIDER_THEMES
    assert RIDER_THEMES["Kamen Rider Wizard (2012)"].tier6_effect == "mouse_gestures"
    assert RIDER_THEMES["Kamen Rider Revice (2021)"].tier6_effect == "buddy_link"
    tier6_riders = {n for n, t in RIDER_THEMES.items() if t.tier6_effect != "none"}
    assert tier6_riders == {"Kamen Rider Wizard (2012)", "Kamen Rider Revice (2021)"}
```

- [ ] **Step 2: Run it and see it fail**

Run: `pytest tests/test_rider_themes.py -v -k tier6`
Expected: FAIL, `'none' == 'buddy_link'`.

- [ ] **Step 3: Give Revice its flag**

In `lock_in/rider_themes.py`, change the Revice entry to:

```python
    "Kamen Rider Revice (2021)": RiderTheme(
        "Reiwa", 2021, ("#b3154b", "#f06292"), ("#0097a7", "#18ffff"),
        tier6_effect="buddy_link",
    ),
```

Replace the comment above `tier6_effect: str = "none"` with:

```python
    # "none" for every Rider except Tier 6's two "new infrastructure"
    # Riders. Wizard's "mouse_gestures": ui.py listens for right-button
    # drags (a line left or right, or a circle) to switch tabs, and
    # lock_in/wizard_gestures.py does the drawing math (see
    # docs/superpowers/specs/2026-09-23-tier6-wizard-mouse-gestures-design.md).
    # Revice's "buddy_link": ui.py adds a "Buddy" tab for pairing with
    # another computer on the same Wi-Fi (see
    # docs/superpowers/specs/2026-09-24-tier6-revice-buddy-link-design.md).
```

Run: `pytest tests/test_rider_themes.py -v`
Expected: all PASS.

- [ ] **Step 4: Write `lock_in/revice_tab.py`**

```python
"""
revice_tab.py
=============
The "Buddy" tab Kamen Rider Revice adds. Draws one of five screens:

- start:    Share and Receive buttons
- typing:   a box for the 4-digit code, Connect, Back
- sharing:  the big code, a countdown, Cancel
- finding:  "Looking for your buddy...", Cancel
- paired:   their name, timer, what they're doing, task,
            Pull History, Unpair

All the widgets are made once; show() only switches which screen is
visible and changes text, so calling it on every timer tick is cheap.
The buttons just call the functions ui.py hands in -- this file never
touches the network itself. Checked by hand in the running app, like
every other tab.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from . import revice_sync as rs


class BuddyTab:
    def __init__(self, parent, *, accent: str, text_color: str,
                 on_share: Callable[[], None], on_receive: Callable[[str], None],
                 on_cancel: Callable[[], None], on_pull: Callable[[], None],
                 on_unpair: Callable[[], None]) -> None:
        self._on_receive = on_receive
        self._typing = False
        self._screen: Optional[str] = None

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.message_label = ctk.CTkLabel(self.frame, text="", wraplength=420)
        self.message_label.pack(anchor="w", pady=(0, 8))

        def button(master, text, command):
            return ctk.CTkButton(master, text=text, command=command,
                                 fg_color=accent, text_color=text_color)

        # start
        self.start_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctk.CTkLabel(self.start_frame, justify="left", wraplength=420, text=(
            "Pair with a friend's computer on the same Wi-Fi. They need "
            "Revice picked too. One of you presses Share, the other "
            "presses Receive and types the code.")).pack(anchor="w", pady=(0, 10))
        button(self.start_frame, "Share", on_share).pack(anchor="w", pady=4)
        button(self.start_frame, "Receive", self._start_typing).pack(anchor="w", pady=4)

        # typing
        self.typing_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctk.CTkLabel(self.typing_frame, text="Type the 4 numbers from the other computer:"
                     ).pack(anchor="w", pady=(0, 6))
        self.code_entry = ctk.CTkEntry(self.typing_frame, width=120,
                                       font=ctk.CTkFont(size=24, weight="bold"))
        self.code_entry.pack(anchor="w", pady=4)
        self.code_entry.bind("<Return>", lambda _e: self._connect())
        button(self.typing_frame, "Connect", self._connect).pack(anchor="w", pady=4)
        ctk.CTkButton(self.typing_frame, text="Back", fg_color="transparent", border_width=1,
                      command=self._stop_typing).pack(anchor="w", pady=4)

        # sharing
        self.sharing_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctk.CTkLabel(self.sharing_frame, text="Type this code on the other computer:"
                     ).pack(anchor="w")
        self.code_label = ctk.CTkLabel(self.sharing_frame, text="",
                                       font=ctk.CTkFont(size=48, weight="bold"))
        self.code_label.pack(anchor="w", pady=6)
        self.countdown_label = ctk.CTkLabel(self.sharing_frame, text="")
        self.countdown_label.pack(anchor="w", pady=(0, 8))
        button(self.sharing_frame, "Cancel", on_cancel).pack(anchor="w")

        # finding
        self.finding_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctk.CTkLabel(self.finding_frame, text="Looking for your buddy…").pack(anchor="w", pady=(0, 8))
        button(self.finding_frame, "Cancel", on_cancel).pack(anchor="w")

        # paired
        self.paired_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.paired_label = ctk.CTkLabel(self.paired_frame, text="",
                                         font=ctk.CTkFont(size=16, weight="bold"))
        self.paired_label.pack(anchor="w")
        self.time_label = ctk.CTkLabel(self.paired_frame, text="--:--",
                                       font=ctk.CTkFont(size=40, weight="bold"))
        self.time_label.pack(anchor="w", pady=(6, 0))
        self.doing_label = ctk.CTkLabel(self.paired_frame, text="")
        self.doing_label.pack(anchor="w")
        self.task_label = ctk.CTkLabel(self.paired_frame, text="", wraplength=420)
        self.task_label.pack(anchor="w", pady=(0, 10))
        self.pull_button = button(self.paired_frame, "Pull History", on_pull)
        self.pull_button.pack(anchor="w", pady=4)
        button(self.paired_frame, "Unpair", on_unpair).pack(anchor="w", pady=4)

        self._frames = {"start": self.start_frame, "typing": self.typing_frame,
                        "sharing": self.sharing_frame, "finding": self.finding_frame,
                        "paired": self.paired_frame}

    # ------------------------------------------------------------------ #
    def _start_typing(self) -> None:
        self._typing = True
        self.code_entry.delete(0, "end")

    def _stop_typing(self) -> None:
        self._typing = False

    def _connect(self) -> None:
        code = self.code_entry.get()
        self._on_receive(code)
        if rs.is_valid_code(code):
            self._typing = False

    def _switch(self, screen: str) -> None:
        if screen == self._screen:
            return
        for frame in self._frames.values():
            frame.pack_forget()
        self._frames[screen].pack(fill="both", expand=True)
        self._screen = screen
        if screen == "typing":
            self.code_entry.focus_set()

    def _set(self, label, text: str) -> None:
        if label.cget("text") != text:
            label.configure(text=text)

    # ------------------------------------------------------------------ #
    def show(self, link, status: Optional[dict], message: str, now: float) -> None:
        """Bring the tab up to date with the link. `now` is in the same
        clock as link.code_deadline."""
        if link.state == "paired":
            self._typing = False
            screen = "paired"
        elif link.state == "sharing":
            screen = "sharing"
        elif link.state == "finding":
            screen = "finding"
        else:
            screen = "typing" if self._typing else "start"
        self._switch(screen)
        self._set(self.message_label, message)

        if screen == "sharing":
            self._set(self.code_label, link.code or "")
            left = max(0, int(link.code_deadline - now))
            self._set(self.countdown_label,
                      f"Waiting for your buddy… {left // 60}:{left % 60:02d} left")
        elif screen == "paired":
            self._set(self.paired_label, f"Paired with {link.buddy_name or 'Buddy'}")
            if status is None:
                time_text, doing, task = "--:--", "Waiting for their timer…", ""
            else:
                time_text, doing, task = rs.describe_status(status)
                task = f"Task: {task}"
            self._set(self.time_label, time_text)
            self._set(self.doing_label, doing)
            self._set(self.task_label, task)
            pull_text = "Pulling…" if link.pull_pending else "Pull History"
            if self.pull_button.cget("text") != pull_text:
                self.pull_button.configure(
                    text=pull_text, state="disabled" if link.pull_pending else "normal")
```

- [ ] **Step 5: Wire it into `ui.py`**

5a. Imports. Add after `from .wizard_gestures import next_tab_name, recognize` (line 67):

```python
from . import revice_sync
from .revice_link import BuddyLink
from .revice_tab import BuddyTab
```

Add `import socket` to the stdlib imports (alphabetical order, after `import shutil`).

5b. In `__init__`, just before `self._build_header()` (about line 369), add:

```python
        # Revice's buddy link. Made once for the app's whole life, so
        # redrawing the tabs (dark mode, a Rider switch) never drops the
        # connection. It doesn't touch the network until Share or Receive
        # is pressed -- see lock_in/revice_link.py.
        self.buddy_link = BuddyLink(socket.gethostname() or "Buddy")
        self._buddy_tab: Optional[BuddyTab] = None
        self._buddy_status: Optional[dict] = None
        self._buddy_message = ""
        self._buddy_last_sent = 0.0
```

5c. In `_build_tabs()`, right after the Tier 5 `if` that appends to `self._tab_names`, add:

```python
        if self.current_tier6_effect == "buddy_link":
            self._tab_names.append("Buddy")
```

And at the end of `_build_tabs()`, after the `_build_tier5_tab()` call, add:

```python
        self._buddy_tab = None
        if self.current_tier6_effect == "buddy_link":
            self._buddy_tab = BuddyTab(
                self.tabs.tab("Buddy"),
                accent=self.color_rider_accent, text_color=self.color_button_text,
                on_share=self._on_buddy_share, on_receive=self._on_buddy_receive,
                on_cancel=self._on_buddy_cancel, on_pull=self._on_buddy_pull,
                on_unpair=self._on_buddy_cancel,
            )
```

5d. In `_pump()`, add `self._drain_buddy_link()` right after `self._drain_update_queue()`.

5e. Add these methods to `LockInApp`, right after the Wizard mouse-gesture section (after `_on_wizard_release` and its helpers, about line 2660):

```python
    # ================================================================== #
    # Revice's buddy link (see lock_in/revice_link.py)
    # ================================================================== #
    def _on_buddy_share(self) -> None:
        self._buddy_message = ""
        self._buddy_status = None
        self.buddy_link.share()

    def _on_buddy_receive(self, code: str) -> None:
        if not revice_sync.is_valid_code(code):
            self._buddy_message = revice_sync.MSG_TYPE_FOUR
            return
        self._buddy_message = ""
        self._buddy_status = None
        self.buddy_link.receive(code)

    def _on_buddy_cancel(self) -> None:
        self._buddy_message = ""
        self._buddy_status = None
        self.buddy_link.close()

    def _on_buddy_pull(self) -> None:
        if self.buddy_link.request_pull():
            self._buddy_message = ""

    def _drain_buddy_link(self) -> None:
        """Called every tick from _pump(). Reads what the link heard,
        sends our timer about once a second, and redraws the Buddy tab.
        Closes the link as soon as Revice isn't the Rider any more
        (another Rider, or Standard Mode). Never lets an error reach the
        timer."""
        try:
            link = self.buddy_link
            if self.current_tier6_effect != "buddy_link":
                if link.state != "idle":
                    link.close()
                link.poll()
                self._buddy_status = None
                self._buddy_message = ""
                return
            for event in link.poll():
                kind = event[0]
                if kind == "paired":
                    self._buddy_message = ""
                    self._buddy_status = None
                elif kind == "status":
                    self._buddy_status = revice_sync.clean_status(event[1])
                elif kind == "pull_request":
                    link.send_pull_reply(
                        [dataclasses.asdict(r) for r in self.history.all()],
                        [dataclasses.asdict(t) for t in self.tasks.all()],
                    )
                elif kind == "pull_reply":
                    added = revice_sync.merge_pull(self.history, self.tasks, event[1], event[2])
                    self._buddy_message = revice_sync.pull_result_text(*added)
                    if added[1]:
                        self._render_tasks()
                        self._refresh_current_task_picker()
                elif kind == "pull_failed":
                    self._buddy_message = revice_sync.MSG_PULL_FAILED
                elif kind == "left":
                    self._buddy_message = revice_sync.MSG_BUDDY_LEFT
                    self._buddy_status = None
                elif kind == "error":
                    self._buddy_message = event[1]
            now = time.monotonic()
            if link.state == "paired" and now - self._buddy_last_sent >= revice_sync.STATUS_EVERY_SECONDS:
                self._buddy_last_sent = now
                task = self.tasks.get(self.current_task_id) if self.current_task_id else None
                link.send_status(revice_sync.status_from_session(
                    self.session, task.name if task else None, link.name))
            if self._buddy_tab is not None:
                self._buddy_tab.show(link, self._buddy_status, self._buddy_message, now)
        except Exception:
            pass
```

`BuddyLink` uses `time.monotonic` by default, the same clock as `now` above, so the countdown matches `link.code_deadline`.

5f. In `_on_close()`, make the `finally:` block start with:

```python
            try:
                self.buddy_link.close()
            except Exception:
                pass
```

5g. Help tab. Change the Tier 6 heading and add a Revice bullet after the Wizard bullet:

```python
        heading("6. Heroes that add something new", COLOR_ENFORCE_ACCENT)
```

```python
        bullet(
            "Revice — pair with a friend's computer on the same Wi-Fi. "
            "You both pick Revice. One of you opens the Buddy tab and "
            "presses Share, and the other presses Receive and types the "
            "4 numbers. Then you each see the other's timer and task. "
            "Pull History copies their past focus blocks (and those "
            "blocks' tasks) into yours. It only adds things -- it never "
            "changes or deletes what you already have. Nothing goes on "
            "the network until you press Share or Receive."
        )
```

- [ ] **Step 6: Run the whole test suite**

Run: `pytest -q`
Expected: all pass. There were 657 passed and 1 skipped before, plus the new tests. No failures.

- [ ] **Step 7: Check the app starts**

Run: `python -c "import lock_in.ui"`
Expected: no error.

- [ ] **Step 8: No commit.**

---

### Task 4: Docs, version, and repo files

**Files:**
- Modify: `lock_in/__init__.py`, `README.md`, `SECURITY.md`, `.gitignore`

- [ ] **Step 1: Version and layout docstring**

In `lock_in/__init__.py`, set `__version__ = "2.6.1"` and add under the `wizard_gestures.py` line:

```
    revice_sync.py   Revice's buddy-link rules and merge     (no deps, pure logic)
    revice_link.py   Revice's local-network connection       (stdlib sockets)
    revice_tab.py    Revice's Buddy tab                      (customtkinter)
```

- [ ] **Step 2: README, Tier 6 section**

In `README.md`, change "The last two Riders do things no earlier Rider does. The first one is built:" to "The last two Riders do things no earlier Rider does. Both are built:". Then replace the line "The other one, Revice, is still to come." with:

```markdown
- **Revice** — Revice is two heroes sharing one body, so it lets two
  computers share one Lock In. Both of you pick Revice, then open the
  new **Buddy** tab:
  - One of you presses **Share**. A 4-number code shows up.
  - The other presses **Receive** and types those 4 numbers.

  Now you're paired. Each of you sees the other's timer, whether
  they're focusing or on a break, and what task they picked. Press
  **Pull History** to copy their past focus blocks, and the tasks those
  blocks belong to, into yours. It only adds what you don't already
  have. It never changes or deletes anything, so pressing it twice is
  fine. Press **Unpair** when you're done.

  A few things to know:
  - Both computers must be on the **same Wi-Fi**. Some school, office,
    or café Wi-Fi blocks this. Home Wi-Fi almost always works.
  - The code lasts 2 minutes. After 3 wrong tries it stops working, and
    you press Share again.
  - Nothing goes on the network until you press Share or Receive, and
    it stops when either of you unpairs, closes Lock In, or picks
    another Rider.
  - Windows may ask whether to let Lock In use the network the first
    time you press Share. Say yes, or pairing can't work.
  - What's sent between the two computers is **not scrambled**
    (encrypted). Someone snooping on the same Wi-Fi could read your
    timer, task names, and pulled history. That's fine at home, but
    don't use it on café Wi-Fi.
  - Pairing can never start, pause, or stop anyone's timer.

Tier 6 is complete.
```

- [ ] **Step 3: README, the one privacy line and the file list**

At about line 491, the "Privacy. Nothing leaves your machine." bullet is about window titles vs screenshots. Change its first sentence to: "Privacy. Your window titles never leave your machine." The rest stays.

In the file tree, after the `wizard_gestures.py` line, add:

```
│   ├── revice_sync.py           Revice's rules: the code check, messages, and
│   │                           the Pull History merge (no network, no window).
```

After the `update_apply.py` entry (in the "platform-facing shells" group), add:

```
│   ├── revice_link.py           Revice's connection to a buddy's computer on
│   │                           the same Wi-Fi. Only runs after Share/Receive.
│   ├── revice_tab.py            Revice's Buddy tab.
```

In the tests tree, after the `test_wizard_gestures.py` entry, add:

```
│   ├── test_revice_sync.py     Codes, the handshake, messages, status text,
│   │                           and the add-only Pull History merge.
│   ├── test_revice_link.py     Pairing, wrong codes, time-outs, status and
│   │                           pull round-trips, all on 127.0.0.1.
```

Search the README for any other sentence saying the app never uses the network (`grep -n -i "network\|leaves your\|sent anywhere" README.md`). Leave sentences that are about one specific feature (Wizard's "nothing is recorded or sent anywhere" is still true for Wizard). Only fix whole-app claims.

- [ ] **Step 4: SECURITY.md**

Replace the first paragraph with:

```markdown
Lock In is a personal desktop app (Pomodoro timer + app blocker). It
runs on your own machine. It only uses the network in these ways, and
each one is either off by default or only happens when you press a
button:

- The Claude fallback (off by default) sends a single window title
  string and nothing else. See the README's "Claude fallback" section.
- The update check asks GitHub for the latest release.
- Revice's buddy link (only while Revice is the picked Rider, and only
  after you press Share or Receive) talks to one other computer on the
  same local network. Pairing uses a 4-digit code that is never sent
  over the network, and it is locked after 3 wrong tries. What's sent
  after pairing is not encrypted. See the README's Tier 6 section.
```

Before writing, check that the update check really exists and is described correctly by reading the README's auto-update section. Adjust the wording to match what it says.

- [ ] **Step 5: .gitignore**

Revice makes no files, so there are no new rules. Replace the comment above `.claude/`, `.superpowers/`, `graphify-out/` with:

```
# Local scratch space and a generated code map. They're just working
# files on this machine and don't belong in the project. The app itself
# never reads this folder.
```

The three rules below it stay exactly as they are.

- [ ] **Step 6: Final checks**

Run: `pytest -q`
Expected: all pass.

Run: `git status --short`
Expected: only the files listed in this plan (plus the spec and this plan) show as changed or new.

Run: `git diff | grep -i -E "claude code|co-authored|generated with|assistant|\bAI\b"`
Expected: no hits in the new lines except the existing "Claude fallback" feature name in SECURITY.md.

- [ ] **Step 7: No commit.** Hand the owner these commands:

```bash
git add lock_in/revice_sync.py lock_in/revice_link.py lock_in/revice_tab.py \
        lock_in/tasks.py lock_in/rider_themes.py lock_in/ui.py lock_in/__init__.py \
        tests/test_revice_sync.py tests/test_revice_link.py tests/test_tasks.py \
        tests/test_rider_themes.py README.md SECURITY.md .gitignore \
        docs/superpowers/specs/2026-09-24-tier6-revice-buddy-link-design.md \
        docs/superpowers/plans/2026-09-24-tier6-revice-buddy-link.md
git commit -m "v2.6.1: add Revice (Tier 6 Rider 2, buddy link) -- Tier 6 Complete"
git push origin main
git tag v2.6.1
git push origin v2.6.1
```
