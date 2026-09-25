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
            # Try to say "bye" so the buddy finds out right away, but
            # never wait for it -- this can run on the window's own
            # thread, and closing the socket right after tells the
            # buddy we're gone even if this send doesn't land.
            try:
                conn.setblocking(False)
                conn.send(rs.encode({"type": "bye"}))
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

    def _shutdown(self, only_if: Optional[threading.Event] = None) -> bool:
        """Stop everything and go back to idle. If `only_if` is given,
        this only happens when that is still the current attempt, checked
        and acted on in one locked step so a stale thread can't undo a
        newer attempt that started in between. Returns whether it
        actually happened."""
        with self._lock:
            if only_if is not None and (only_if is not self._stop or only_if.is_set()):
                return False
            self._stop.set()
            sockets, self._sockets = self._sockets, []
            self._conn = None
            self._pull_started = None
            self.state = "idle"
            self.code = None
            self.buddy_name = None
            self.tcp_port = None
        for sock in sockets:
            try:
                sock.close()
            except OSError:
                pass
        return True

    def _end(self, stop: threading.Event, event: tuple) -> None:
        """A thread hit the end of the road. Only acts if it's still the
        current attempt, so a stale thread can't undo a newer one."""
        if self._shutdown(only_if=stop):
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
            except ConnectionResetError:
                # Windows can report an old reply to someone who has
                # already gone as a "reset" on our own socket. It isn't
                # really an error here -- just keep listening.
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
                # Something went wrong with the listening socket itself
                # (not just "nobody's connected yet"). _end is a no-op
                # if this attempt was already stopped, so a normal
                # Cancel still produces no message.
                self._end(stop, ("error", rs.MSG_CANT_SHARE))
                return
            conn.settimeout(5.0)
            buf = bytearray()
            try:
                result = self._handshake_as_sharer(conn, code, buf)
            except Exception:
                # A broken connection or a strange message during the
                # handshake -- treat it like a failed try, not a crash.
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
                except ConnectionResetError:
                    # Same Windows quirk as in _answer_loop -- not a real
                    # error, just keep calling out and listening.
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
        except Exception:
            # A broken connection or a strange message during the
            # handshake -- treat it like a failed try, not a crash.
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
        """Switch to paired, unless close() got here first. The check and
        every change it makes happen in one locked step, so close()
        running in between can't be missed or overwritten."""
        conn.settimeout(1.0)
        with self._lock:
            current = stop is self._stop and not stop.is_set()
            if current:
                self._sockets.append(conn)
                self._conn = conn
                self._outgoing = queue.Queue()
                self._last_heard = self._clock()
                self._pull_started = None
                self.code = None
                self.buddy_name = name
                self.state = "paired"
                self._events.put(("paired", name))
        if not current:
            conn.close()
            return
        self._thread(self._reader, stop, conn, buf)
        self._thread(self._writer, stop, conn, self._outgoing)

    def _reader(self, stop, conn, buf) -> None:
        while not stop.is_set():
            try:
                for line in rs.take_lines(buf):
                    if not self._handle(stop, rs.decode(line)):
                        return
            except Exception:
                # Something in a message was too strange to deal with.
                # Treat it the same as the buddy going away, not a crash.
                self._end(stop, ("left",))
                return
            if len(buf) > rs.MAX_LINE_BYTES:
                self._end(stop, ("left",))
                return
            now = self._clock()
            # Read once into a local: this isn't under the lock, and
            # _shutdown() (from another thread, e.g. the buddy saying
            # "bye" right now) can clear _pull_started to None between
            # two separate reads, which used to make `now - None` raise.
            pull_started = self._pull_started
            if pull_started is not None and now - pull_started > rs.PULL_TIMEOUT_SECONDS:
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
