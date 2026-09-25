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


def test_broken_json_does_not_kill_the_link(links):
    a, b = pair(links)
    # A pile of nested brackets can blow Python's stack while parsing.
    # The reader should shrug that one line off and keep going.
    line = b"[" * 20000 + b"]" * 20000 + b"\n"
    b._conn.sendall(line)
    b.send_status({"type": "status", "remaining_seconds": 7})
    event = wait_for(a, "status")
    assert event[1]["remaining_seconds"] == 7


def test_discovery_finds_the_sharer(links):
    port = free_udp_port()
    a = links("A", discovery_port=port)
    b = links("B", discovery_port=port, broadcast_address="127.0.0.1")
    code = a.share()
    b.receive(code)
    assert wait_for(b, "paired") == ("paired", "A")


def test_discovery_survives_a_reset_from_a_gone_asker(links):
    """Answering a "anyone sharing?" call from someone who has already
    closed their socket can make Windows report the next recvfrom as a
    reset, as if something broke. It didn't -- keep answering calls."""
    port = free_udp_port()
    a = links("A", discovery_port=port)
    code = a.share()
    gone = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    gone.bind(("127.0.0.1", 0))
    gone.sendto(rs.HELLO, ("127.0.0.1", port))
    gone.close()
    b = links("B", discovery_port=port, broadcast_address="127.0.0.1")
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


def test_reader_reads_pull_started_only_once_per_check(links, monkeypatch):
    """Regression test: the pull-timeout check used to read
    self._pull_started twice without the lock, so _shutdown() clearing
    it to None in between (e.g. from a "bye") made `now - None` raise
    and killed the reader thread silently. A stand-in descriptor for
    the attribute returns the real value on the first read and None on
    every read after -- reproducing the crash if the check ever reads
    the attribute more than once, and passing if it reads it exactly
    once into a local."""

    class _FlipOnSecondRead:
        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            count = obj.__dict__.get("_flip_count", 0)
            obj.__dict__["_flip_count"] = count + 1
            if count >= 1:
                return None
            return obj.__dict__.get("_flip_value")

        def __set__(self, obj, value):
            obj.__dict__["_flip_value"] = value

    monkeypatch.setattr(BuddyLink, "_pull_started", _FlipOnSecondRead(), raising=False)

    a = links("A")
    a._pull_started = time.monotonic()
    a._last_heard = time.monotonic()

    class _BrokenConn:
        def recv(self, n):
            raise OSError("closed")

    stop = a._fresh_stop()
    a._reader(stop, _BrokenConn(), bytearray())  # must not raise
    assert wait_for(a, "left") == ("left",)


def test_share_loop_ends_with_cant_share_on_accept_error(links):
    """Regression test: a non-timeout OSError from accept() used to
    just `return`, leaving the link stuck in "sharing" state forever
    with no message shown."""

    class _BrokenServer:
        def accept(self):
            raise OSError("boom")

        def close(self):
            pass

    a = links("A")
    stop = a._fresh_stop()
    a.state = "sharing"
    a.code_deadline = time.monotonic() + 100
    a._share_loop(stop, _BrokenServer(), None, "1234")
    assert wait_for(a, "error", timeout=1.0) == ("error", rs.MSG_CANT_SHARE)
    assert a.state == "idle"
