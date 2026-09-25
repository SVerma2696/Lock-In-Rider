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
from dataclasses import asdict
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
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
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
            # task_from_dict already checks every field's type, but not
            # length -- a name longer than what the Buddy tab ever shows
            # is still "wrong shape" for our purposes, so it's skipped
            # here rather than saved and only capped when displayed.
            if task is None or len(task.name) > MAX_TASK_NAME:
                continue
            if tasks.add_existing(task):
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


def pull_reply_payload(history, tasks) -> tuple[list, list]:
    """What we send back when the buddy presses Pull History: every
    session, plus only the tasks those sessions actually belong to --
    not the whole task list. (The owner's call: "sessions and the tasks
    they belong to," not everything on the Tasks tab.)"""
    sessions = [asdict(record) for record in history.all()]
    their_task_ids = {record.task_id for record in history.all() if record.task_id is not None}
    task_list = [asdict(task) for task in tasks.all() if task.id in their_task_ids]
    return sessions, task_list


def pull_result_text(sessions_added: int, tasks_added: int) -> str:
    """What the Buddy tab says after Pull History finishes."""
    if sessions_added == 0 and tasks_added == 0:
        return "Nothing new to add."
    session_word = "session" if sessions_added == 1 else "sessions"
    task_word = "task" if tasks_added == 1 else "tasks"
    return f"Added {sessions_added} {session_word} and {tasks_added} {task_word}."
