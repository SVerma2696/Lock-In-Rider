# Lock In: Tier 6 Rider #2 — Revice, buddy link

Date: 2026-09-24
Status: Draft, awaiting review

## Goal

The second and last of Tier 6's two Riders. Kamen Rider Revice (2021) is
two beings sharing one body, so Revice's gimmick is two computers sharing
one Lock In. When Revice is the picked Rider, you can pair with another
computer on the same Wi-Fi by typing a short code, then:

- see the other computer's **live timer and task** in a new **"Buddy"** tab, and
- press **Pull History** to copy the other computer's past focus sessions
  (and the tasks they belong to) into yours.

It is deliberately small and safe:

- **Nothing touches the network until you press Share or Receive.** No
  background service, no always-open port, no Settings switch needed.
- **Both computers must have Revice picked.** A computer on any other
  Rider can never be reached.
- **Only built-in Python.** `socket`, `threading`, `json`, `hmac`,
  `secrets`. No new library.
- **Pairing never changes a focus session.** It cannot start, pause, skip,
  or end either person's timer.
- **Pull History only adds.** It never changes or deletes anything already
  on your computer.

## What you see (the Buddy tab)

A **"Buddy"** tab is added at the end of the tab row while Revice is
picked, the same way Tier 5 Riders add a tab.

**Not paired yet**: two big buttons.

- **Share**: shows a big 4-digit code (e.g. **4821**) and "Waiting for
  your buddy… 1:52 left", counting down, with a **Cancel** button.
- **Receive**: shows a box for the 4 digits and a **Connect** button.

**Paired**:

- "Paired with **DESKTOP-ABC**" (the other computer's name, from
  `socket.gethostname()`).
- Their **timer**, e.g. "18:32", updated about once a second.
- What they're doing: **Focusing**, **On a break**, **Paused**, or
  **Not running**.
- Their **task**: the picked task's name, or "No task picked".
- **Pull History** button. When done: "Added 12 sessions and 3 tasks" or
  "Nothing new to add".
- **Unpair** button.

**Buddy goes away** (their app closes, they unpair, they pick another
Rider, or the Wi-Fi drops): the tab says "Your buddy left" and shows Share
and Receive again.

Both sides see each other. Each side can press Pull History for itself.

### What is sent

- **Live, about once a second:** remaining time, phase (focus, short
  break, long break, idle), paused or running, and the current task's
  name. Nothing else.
- **Only when the other side presses Pull History:** all saved sessions
  and all tasks.
- **Never:** the block list, allow list, activity/observations, settings,
  camera, or the trained model.

## How pairing works

1. **Share** picks a random 4-digit code with `secrets.randbelow(10000)`
   (shown with leading zeros, e.g. `0427`). It opens:
   - a **TCP listener** on a port the operating system picks, and
   - a **UDP listener** on the fixed discovery port **47821**.
2. **Receive** broadcasts a small "anyone sharing?" UDP message to port
   47821 on the local network. Every computer currently sharing replies
   with its TCP port. The code is **not** in this message.
3. The receiver connects over TCP to each reply in turn and does the
   **handshake**:
   - The sharer sends a random challenge. The receiver answers with
     `hmac(code, challenge)`. The receiver then sends its own challenge
     and the sharer answers the same way. So each side proves it knows
     the code, and the code itself is never sent.
   - A wrong answer closes that connection. After **3 wrong answers**
     the sharer cancels its code ("Too many wrong tries. Press Share
     again."), so the 10,000 codes can't be guessed one by one.
4. On success, the sharer stops listening on both UDP and TCP. Only the
   one paired connection stays open.
5. The code expires after **2 minutes** or once it has been used.
6. If nobody answers the broadcast within **5 seconds**, or no reply
   passes the handshake, the receiver shows "Couldn't find it. Are you
   both on the same Wi-Fi?"

Windows will probably ask "allow Lock In on the network?" the first time
Share is pressed. The README says so.

## Messages

One JSON object per line, UTF-8, over the paired TCP connection. Every
message has a `"type"`:

| type | sent when | contents |
|---|---|---|
| `status` | about once a second | `name`, `phase`, `paused`, `remaining_seconds`, `task_name` |
| `pull_request` | you press Pull History | nothing |
| `pull_reply` | answer to `pull_request` | `sessions` (list of session dicts), `tasks` (list of task dicts) |
| `bye` | Unpair, Rider change, or app close | nothing |

- A line longer than **5 MB** is refused and the connection closed, so a
  bad sender can't fill up memory.
- A line that isn't valid JSON, or has an unknown `type`, is ignored.
- If nothing at all arrives for **10 seconds**, the buddy counts as gone.

## Pull History merge

- Every session and every task already has an id. For each incoming task
  whose id is **not** already in the task list, add it as-is. Then for
  each incoming session whose id is **not** already in the history, add
  it.
- Tasks are added before sessions so a pulled session never points at a
  missing task.
- Nothing already here is changed or deleted, so pressing it twice adds
  nothing the second time.
- Any incoming item that is missing fields, has the wrong types, or
  otherwise can't be read is skipped. The count only includes what was
  actually added.
- New sessions are written with the history store's existing save path,
  and new tasks with the task store's, so the other tabs (Den-O, Decade,
  Zi-O, W, Geats, and the rest) see them straight away.
- If no `pull_reply` arrives within **15 seconds**, nothing is saved and
  the tab says "Pull History didn't finish. Try again."

## New code

### `lock_in/revice_sync.py` (new)

Plain logic. No socket, no Tk, so it is fully testable without a network
or display.

- `merge_pull(history, tasks, their_sessions, their_tasks) -> tuple[int, int]`:
  the merge above; returns (sessions added, tasks added).
- `encode(message: dict) -> bytes` and `decode(line: bytes) -> dict | None`:
  one JSON line per message; `decode` returns `None` for anything broken
  or of unknown type.
- `make_code() -> str`: a random 4-digit code.
- `proof(code: str, challenge: bytes) -> bytes` and
  `check_proof(code, challenge, answer) -> bool`: the handshake, using
  `hmac` with SHA-256 and `hmac.compare_digest`.
- `status_from_session(session, task_name, name) -> dict`: builds a
  `status` message from the app's `PomodoroSession`.
- Named constants at the top, each with a plain-words comment:
  `DISCOVERY_PORT = 47821`, `CODE_LIFETIME_SECONDS = 120`,
  `MAX_WRONG_TRIES = 3`, `FIND_TIMEOUT_SECONDS = 5`,
  `BUDDY_GONE_SECONDS = 10`, `PULL_TIMEOUT_SECONDS = 15`,
  `MAX_LINE_BYTES = 5 * 1024 * 1024`.

### `lock_in/revice_link.py` (new)

The network piece. Only standard-library modules.

- `BuddyLink` class:
  - `share() -> str`: starts sharing, returns the code.
  - `receive(code: str)`: starts looking for a sharer with that code.
  - `send_status(status: dict)`, `request_pull()`, `unpair()`,
    `close()`.
  - `poll() -> list[event]`: returns and clears the news since the last
    call. Events are small tuples such as `("paired", name)`,
    `("status", dict)`, `("pull_reply", sessions, tasks)`,
    `("pull_request",)`, `("left",)`, `("error", message)`.
- All socket work happens on background threads. The link **never
  touches Tk**: it only puts events into a thread-safe queue that the
  app's existing once-a-second tick reads with `poll()`.
- Discovery can be replaced by a direct address in tests, so tests don't
  depend on broadcast working on the machine running them.

### `lock_in/revice_tab.py` (new)

The Buddy tab's widgets (Part "What you see"). Given the app's
`BuddyLink` and the last status it received, it draws the right screen:
not paired, sharing, receiving, or paired. Checked in the running app,
like every other tab.

### `lock_in/rider_themes.py`

- `Kamen Rider Revice (2021)` gets `tier6_effect="buddy_link"`.
- The `tier6_effect` comment is updated to name both Tier 6 Riders.

### `lock_in/ui.py` (small)

- `_build_tabs()` adds a "Buddy" tab when `tier6_effect == "buddy_link"`.
- The `BuddyLink` lives on the app, not on the tab, so redrawing the tab
  (dark mode, Rider colors) never drops the connection.
- The existing once-a-second tick: while paired, send one `status`; read
  `poll()` and update the tab. On `pull_request`, reply with all
  sessions and tasks. On `pull_reply`, call `merge_pull()` and show the
  counts.
- Picking another Rider, entering Standard Mode, or closing the app sends
  `bye` and closes the link.
- Everything Revice does in the tick sits inside a `try/except` that does
  nothing on error, the app's usual fail-silent posture for extras.
- Help tab: one Revice bullet.

## Error handling

| Problem | What you see |
|---|---|
| Nobody answers within 5 seconds | "Couldn't find it. Are you both on the same Wi-Fi?" |
| Wrong code typed | "That code didn't work." |
| 3 wrong tries against one code | Sharer: "Too many wrong tries. Press Share again." |
| Code older than 2 minutes | "The code ran out. Press Share again." |
| Discovery port already busy | "Couldn't share right now. Try again in a moment." |
| Buddy closes, unpairs, switches Rider, or Wi-Fi drops | "Your buddy left." |
| Broken or odd items in a pull | Skipped; the count shows only what was added. |
| No pull reply within 15 seconds | "Pull History didn't finish. Try again." Nothing saved. |
| Any other network error | Caught quietly; the tab goes back to Share and Receive. |

The timer, blocking, lockdown, and saving never depend on Revice, so a
network problem can never affect a focus session.

## Honest limit

What is sent (timer, task names, pulled history) is **not encrypted**,
because Python has no built-in encryption and this feature adds no new
library. Someone snooping on the same Wi-Fi could read it. The README says
this in one plain sentence: fine on home Wi-Fi, not for café Wi-Fi.

The 3-wrong-tries limit stops someone guessing codes one by one against
the sharer. It does **not** stop a sneaky computer on the same Wi-Fi: by
answering the "anyone sharing?" call, or by watching one handshake, it
can work out the 4-digit code on its own in a moment, then pair on the
first try. A real fix needs a password-based key exchange, which Python
doesn't have built in. This is an accepted limit, for the same reason as
the one above: only use Revice on Wi-Fi you trust. The README and
SECURITY.md say so plainly.

## Testing

- `tests/test_revice_sync.py` (new), no network, no display:
  - `merge_pull` adds only new tasks and sessions; running it twice adds
    nothing; pulled sessions keep their task names; broken items are
    skipped; nothing already present changes.
  - `encode`/`decode` round-trip every message type; broken JSON, a
    non-object, and an unknown `type` all decode to `None`.
  - `make_code` is always 4 digits.
  - `check_proof` is true for the right code and false for any other code
    or a changed challenge.
  - `status_from_session` covers idle, focus, break, and paused.
- `tests/test_revice_link.py` (new), two links on `127.0.0.1` using the
  direct-address hook:
  - share + receive pair and both see `paired`;
  - a wrong code fails; 3 wrong tries cancel the code;
  - `status` arrives on the other side;
  - a pull round-trip delivers sessions and tasks;
  - `unpair()` or `close()` on one side gives `left` on the other;
  - an oversized line closes the connection.
- `tests/test_rider_themes.py` *(grows)*: exactly one Rider (Wizard) has
  `mouse_gestures`, exactly one (Revice) has `buddy_link`, every other
  Rider has `"none"`.
- **By hand**, with two computers on the same Wi-Fi: pick Revice on both,
  share, receive, watch the timer move, pause on one side, pull history
  and check it appears in the history tabs, pull again (nothing new),
  unpair, close one app mid-pair, try a wrong code three times, and check
  light and dark mode.

## Docs, version, and repo hygiene

- `README.md`: a **Revice** bullet under Tier 6 in plain words, including
  the Windows network pop-up and the not-encrypted sentence. "The other
  one, Revice, is still to come." becomes a line saying Tier 6 is
  complete. The file list gains the three new files.
- `lock_in/ui.py`, Help tab: as above.
- `__version__`: **2.6.1**.
- `.gitignore`: Revice creates no new file on disk, so no new rule. The
  comment above `.claude/`, `.superpowers/`, and `graphify-out/` is
  reworded to "Local scratch space and a generated code map", with the
  rules themselves unchanged.
- Project files describe the software only: nothing about who or what
  wrote them, and commit messages carry no trailer or credit line.
- Committing, pushing, and tagging are done by the project owner. The
  exact commands are handed over at the end, with a plain commit message.

## Out of scope for this pass

- Encryption.
- Pairing across the internet or across different networks.
- More than two computers at once.
- Pushing data to the other computer, or two-way merge.
- Syncing settings, block lists, or activity.
- Staying paired after either app closes, or pairing automatically.
- Controlling the other computer's timer.

## File-by-file change list

**New**
- `lock_in/revice_sync.py`
- `lock_in/revice_link.py`
- `lock_in/revice_tab.py`
- `tests/test_revice_sync.py`
- `tests/test_revice_link.py`
- `docs/superpowers/plans/2026-09-24-tier6-revice-buddy-link.md` (written
  after this spec is approved)

**Edit**
- `lock_in/rider_themes.py`: Revice's `tier6_effect`.
- `lock_in/tasks.py`: `TaskStore.add_existing(task)`, which adds a whole
  task (keeping its id) and saves, returning `False` if the id is already
  there. `add()` only takes a name, so the merge needs this.
- `lock_in/ui.py`: Buddy tab, link lifetime, tick wiring, Help bullet.
- `lock_in/__init__.py`: version 2.6.1.
- `tests/test_rider_themes.py`: as above.
- `tests/test_tasks.py`: `add_existing` adds, keeps the id, saves, and
  refuses a duplicate id.
- `README.md`: Revice bullet, Tier 6 complete, file list.
- `SECURITY.md`: its opening says the app's only network call is the
  Claude fallback. It is updated to list all three: that fallback, the
  update check, and Revice's local-network buddy link.
- `.gitignore`: comment reworded.
