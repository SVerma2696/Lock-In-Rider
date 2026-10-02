# Lock In 🎭⏱️

**In one sentence:** Lock In is a work timer that notices when you drift
off to Discord or YouTube during a focus block, and gently — then not so
gently — nudges you back to work.

You pick how long you want to focus for, hit Start, and get to work. If
you open something distracting, Lock In notices and says something about
it. Ignore it for too long and it minimizes the distracting window for
you, then covers your whole screen until you get back to work — that's
"hard mode," on by default (turn it off in Settings if you'd rather get
gentler warnings first instead). It's built so leaving a focus block is
always something you *decide* to do, not something that just quietly
happens.

Under the hood it's also a hand-built "is this study or is this a
distraction" learning system (no external AI library, so you can read
every line of how it decides), a 38-theme costume-changer for the app's
whole look, and a program that works the same way on Windows, Mac, and
Linux — three things the author built this project to learn by doing.

---

## 📥 How to Download

You don't need to install Python or type any code. You download one
file, open it up, and double-click the app inside.

**Step 1 for everyone:** go to the
**[Download page](https://github.com/SVerma2696/Lock-In-Rider/releases/latest)**.
Scroll down to the part called **Assets**. You'll see a few files there.
Click the one for your computer:

| Your computer | The file to click | What's inside |
| --- | --- | --- |
| Windows 10 or 11 | `LockIn-Windows.zip` | `Lock In.exe` |
| Mac with an Apple chip (M1, M2, M3, M4 or newer) | `LockIn-macOS.zip` | `Lock In.app` |
| Linux (newer, like Ubuntu 24.04 or later) | `LockIn-Linux.tar.gz` | `Lock In` |

You can ignore the files ending in `.sha256` and the "Source code"
files. Those are for checking and building, not for running.

Then follow the steps for your computer below.

### 🪟 Windows

1. **Download** `LockIn-Windows.zip`. It goes into your **Downloads**
   folder.
2. **Make a home for it.** Open **File Explorer**, go to **Documents**,
   right-click an empty spot, pick **New → Folder**, and name it
   `Lock In`. (Don't use `Program Files`: Lock In updates itself, and
   Windows doesn't let apps change things in there.)
3. **Unzip it.** In **Downloads**, right-click `LockIn-Windows.zip` and
   pick **Extract All...**. Click **Browse**, choose the `Lock In` folder
   you just made, then click **Extract**.
4. **Open it.** Double-click `Lock In.exe`.
5. **A blue box says "Windows protected your PC"?** That's normal for a
   free app (see [why](#-releases)). Click **More info**, then **Run
   anyway**. Windows only asks this once.
6. **Make it easy to find (optional).** Right-click `Lock In.exe` and
   pick **Pin to Start** or **Show more options → Send to → Desktop
   (create shortcut)**.

That's it. Blocking works right away on Windows.

### 🍎 Mac

1. **Download** `LockIn-macOS.zip`. It goes into your **Downloads**
   folder. (Safari often unzips it by itself. If you already see
   `Lock In.app` in Downloads, skip step 2.)
2. **Unzip it.** Double-click `LockIn-macOS.zip`. A `Lock In` app
   appears next to it.
3. **Move it into Applications.** Open a new **Finder** window, click
   **Applications** on the left, and drag `Lock In` from Downloads into
   it.
4. **Open it the first time like this:** in Applications, **right-click
   (or Control-click) `Lock In` → Open → Open**. A normal double-click
   won't work the first time, because the app isn't paid-signed by
   Apple. (See [why](#-releases).)
   - **No "Open" button?** Open **System Settings → Privacy &
     Security**, scroll down, and click **Open Anyway** next to
     Lock In.
   - **It says the app "is damaged"?** It isn't. That's how macOS
     sometimes talks about apps from the internet. Open the **Terminal**
     app (Applications → Utilities → Terminal), paste this line, and
     press Return:
     ```bash
     xattr -dr com.apple.quarantine "/Applications/Lock In.app"
     ```
     Then open Lock In again.
5. **Say yes to two questions.** So Lock In can see which app you're in
   and hide distractions, your Mac will ask:
   - "Lock In wants access to control **System Events**" → click **OK**.
   - "Lock In would like to control this computer using
     **Accessibility**" → click **Open System Settings**, then turn on
     the switch next to Lock In.

   Missed one? Go to **System Settings → Privacy & Security**, open
   **Automation** and **Accessibility**, and turn Lock In on in both.
6. **Keep it in the Dock (optional).** While it's open, right-click its
   icon in the Dock and pick **Options → Keep in Dock**.

**Got an older Mac with an Intel chip?** The ready-made app won't run
on it. You can still run Lock In from its code instead. See
[How to Run](#-how-to-run). (To check your chip: click the apple in
the top-left corner → **About This Mac**. It says "Chip: Apple M..." or "Processor: Intel".)

### 🐧 Linux

1. **Download** `LockIn-Linux.tar.gz`. It goes into your **Downloads**
   folder.
2. **Open a terminal** (on Ubuntu, press **Ctrl + Alt + T**).
3. **Make a home for it and unpack it.** Paste these lines one at a
   time, pressing Enter after each:
   ```bash
   mkdir -p ~/Apps/LockIn
   tar -xzf ~/Downloads/LockIn-Linux.tar.gz -C ~/Apps/LockIn
   chmod +x ~/Apps/LockIn/"Lock In"
   ```
   The last line tells Linux "this file is allowed to run". New files
   aren't, for safety.
4. **Add the helpers blocking needs.** Lock In uses three small free
   tools to see windows, hide them, and show pop-ups and sounds. On
   Ubuntu or Debian:
   ```bash
   sudo apt install xdotool libnotify-bin pulseaudio-utils
   ```
   (On Fedora: `sudo dnf install xdotool libnotify pulseaudio-utils`.)
   Lock In still opens without them, but it can't hide distracting
   windows.
5. **Open it:**
   ```bash
   ~/Apps/LockIn/"Lock In"
   ```
6. **Check your screen type.** Hiding windows only works on the older
   "X11" kind of screen, not the newer "Wayland" kind. To check, run
   `echo $XDG_SESSION_TYPE`. If it says `wayland`, log out, click the
   gear ⚙️ on the login screen, pick **Ubuntu on Xorg**, and log back in.
   (On Wayland, Lock In still notices distractions and warns you. It
   just can't hide them.)

**Older Linux?** If it won't start and talks about `GLIBC`, your Linux
is older than the one the app was built on. Run Lock In from its code
instead. See [How to Run](#-how-to-run).

### ✔️ Check your download (optional)

Each download has a "fingerprint" file next to it (for example
`LockIn-Windows.zip.sha256`). A fingerprint is a long code worked out
from every bit of the file. If even one bit changes, the code changes.
To check yours, download the matching `.sha256` file too, open it with
any text editor, and compare its long code with the one your computer
works out:

- **Windows** (in PowerShell, in your Downloads folder):
  `Get-FileHash LockIn-Windows.zip -Algorithm SHA256`
- **Mac** (in Terminal, in your Downloads folder):
  `shasum -a 256 LockIn-macOS.zip`
- **Linux** (in your Downloads folder):
  `sha256sum -c LockIn-Linux.tar.gz.sha256` (it just says `OK`)

The two codes must match exactly. Lock In does this check by itself for
every update, so you only need to do it for the first download.

### 🔄 Getting new versions

You only download by hand once. After that, Lock In tells you when a
new version is out and puts a **Restart now** button at the top. See
[Auto-Update](#-auto-update).

### 🗑️ Removing it

Delete the app (`Lock In.exe`, `Lock In.app`, or `~/Apps/LockIn`).
Your settings, tasks, and history live in their own folder. Delete that
too if you want them gone:

- **Windows:** `%APPDATA%\Lock In` (paste it into File Explorer's
  address bar)
- **Mac:** `~/Library/Application Support/Lock In` (in Finder, press
  **Cmd + Shift + G** and paste it)
- **Linux:** `~/.config/Lock In`

---

## 🧹 New in v3.0.5: the type check really is green now

v3.0.4 fixed the Mac window test, and it passes now. But the type check
still failed. Here's why, and the fix:

- **What happened.** GitHub always grabbed the *newest* type checker.
  A new one came out and started giving one old problem a new name.
  That line of code had a note saying "ignore this problem", but the
  note used the old name. So the new checker said "that note is wrong"
  *and* "there's a problem here". The app worked fine. Only the check
  failed.
- **The fix.** That line no longer needs an "ignore" note at all. It
  now says plainly: "use the setting's normal value if it has one,
  otherwise make one". Old and new type checkers both agree it's fine.
- **So it can't happen again.** GitHub now uses exact, fixed versions
  of the two checkers (Ruff for style, mypy for types) instead of
  "whatever is newest". A new version only gets used when it's changed
  on purpose. See [Checking your changes](#checking-your-changes) to
  use the same versions on your own computer.

The app looks and works the same as v3.0.4.

---

## ✅ New in v3.0.4: the checks are green again

Every time new code goes up, GitHub runs a set of checks on it, like a
teacher marking homework. Two kept failing. Both are fixed:

- **The type check.** It checks that every piece of the code fits
  together, like puzzle pieces. Two Windows-only pieces didn't fit when
  the check ran on Linux. The app worked fine, but the check said no.
  Now they fit on every computer.
- **The Mac window test.** It opens the real app and clicks through it.
  On a Mac it failed only sometimes. A Mac is slow to answer "which
  window is in front?", and that answer sometimes landed in the middle
  of the test and mixed things up. Now:
  - The app throws away a late answer once watching has stopped. This
    was a small real bug too: a slow answer could arrive just after a
    focus block ended.
  - The test uses a pretend answer, so the real screen can't get in its
    way.

Housekeeping, so the checks keep working:

- The helpers the checks use (for getting the code and setting up
  Python) are updated to their newest versions. The old ones ran on an
  old version of Node.js, which GitHub is retiring.
- The Linux checks now ask for Ubuntu 24.04 by name instead of "the
  latest Ubuntu". On October 19, 2026, "latest" becomes Ubuntu 26. Now
  that switch can't break things by surprise. It can be moved up later
  on purpose.

- **A new [How to Download](#-how-to-download) guide** at the top of
  this page, with step-by-step help for Windows, Mac, and Linux.

The app looks and works the same as v3.0.3.

---

## 🔒 New in v3.0.3: the buddy link stays on your home Wi-Fi

Think of your computer as a house with many doors: one for the Wi-Fi,
one for a cable, maybe one for a VPN. Before, when you pressed **Share**
on Revice's Buddy page, Lock In opened its door on *every* one of
them at once. Now it opens only the Wi-Fi door, the one your buddy
actually uses. The other doors stay shut.

- Share and Receive work just like before. You won't see any change.
- Your buddy can still find you with the 4-number code, the same way.
- **Both of you should update to v3.0.3**, especially on a Mac or
  Linux. A Mac or Linux computer on v3.0.3 can't be found by a buddy
  still using an older version. (Windows can still be found by older
  versions.)
- If your buddy can't find you, turn off any VPN and try again. A VPN
  can make Lock In pick the VPN's door instead of the Wi-Fi one.

---

## 🧰 New in v3.0.2: sturdier on the inside

Everything looks and works the same as before: all 38 Riders, every
power in Tiers 0–6, Standard Mode, and light and dark mode. This update
tidied up the inside of the app so it's safer and easier to build on.

- **Updates are checked before they're installed.** Every release now
  comes with a fingerprint of its download. Lock In downloads the
  update, works out the fingerprint of what it got, and only installs it
  if the two match exactly. A download that was cut short or changed on
  the way is thrown away.
- **Saving can't leave a broken file behind.** Your settings, tasks,
  history, and the learned model are written into a spare file first,
  then swapped in with one quick step. If the computer crashes midway,
  you keep the last complete copy.
- **A broken settings file can't crash the app.** Every value in
  `config.json` is checked when Lock In opens. A value that makes no
  sense (like a focus block of -5 minutes) is swapped for its normal
  default, and everything else is kept.
- **Fixed some crashes on opening.** Lock In used to crash at start-up
  if `config.json`, `model.json`, or `observations.jsonl` held the wrong
  kind of data. It now just starts fresh for that one file.
- **Fixed losing a focus block after a crash.** If the app crashed while
  saving a focus block, the next block used to be lost too. Now only
  the one that was cut off is lost.
- **A small private log file.** If something goes wrong quietly (an
  update, the camera, the buddy link), it's noted in a small log file in
  Lock In's settings folder, so it can be looked into later. The log
  never records window titles, task names, or anything you typed. See
  [Config](#-config).
- **Closing is always clean.** Every background helper stops, the camera
  is always let go, and closing twice is harmless.
- **Picking a new Rider is safer to build on.** Each Rider's powers are
  now named values instead of loose words, so a typo is caught straight
  away instead of a power silently not working. Every Rider is checked
  automatically by the tests.

---

## 🛠️ New in v3.0.1: two fixes

- **"Restart now" works again.** Before, pressing the blue Restart now
  button closed Lock In, and the new version never opened. Now Lock In
  closes, swaps in the new version, and opens it again by itself. If
  anything goes wrong during the swap, your old Lock In is put back, so
  you're never left without the app.
- **Picking a new Rider shows it right away.** If Standard Mode was on,
  picking a Rider used to change nothing you could see, because Standard
  Mode hides every Rider's colors. Then "Save settings" said the change
  would come later, but it never did. Now picking a Rider turns Standard
  Mode off, so you see your Rider straight away. Only the number boxes
  (like how long a focus block is) wait for the next focus block or
  break, and the app now says exactly that.

**Coming from v3.0.0 or older?** Your copy still has the old Restart
button, so update by hand this one time. See
[If an update didn't work](#if-an-update-didnt-work) below. After that,
Restart now works on its own.

---

## ✨ New in v3.0.0: a brand-new look

Lock In got a whole new coat of paint. **Everything it could do before,
it still does** — only the look and the layout changed.

- **A side bar on the left.** Every page has its own button with a small
  picture: Focus, Tasks, Blocking, Activity, Insights, then Help and
  Settings at the bottom. Click one to go there. (Before, the pages were
  tabs squeezed along the bottom.)
- **A bigger window** — 960 × 680 to start — so nothing feels cramped.
- **Clean cards.** Things that belong together sit in the same rounded
  box, like the switches on the Blocking page or each task on the Tasks
  page.
- **One Rider color, used with care.** The rest of the app stays calm
  grey (or white in light mode). Your Rider's color marks the important
  things: the big Start button, the progress bar, and the page you're on.
  Green, amber, and red only ever mean "good", "careful", and "blocked".
- **A new Insights page** that adds up your focus time: today, this week,
  all time, and how many blocks you finished.
- **Rider pages live in the side bar.** Pick a Rider like V3 or Blade and
  their page shows up under a small "Rider" heading. Revice's Buddy page
  shows up there too.
- **MY-TH has two looks.** Light mode shows normal MY-TH (blue and
  silver). Dark mode shows MY-TH ORIGIN (red and gunmetal). It's still
  one Rider to pick.
- **Quicker and lighter.** Pages open faster, switching between them is
  almost instant, picking a new Rider takes a moment instead of many
  seconds, and the app uses less memory. The camera part (OpenCV) only
  loads if you turn Strict Camera Monitoring on.
- **Your stuff is safe.** Your settings, tasks, and focus history are
  saved in exactly the same files as before, so updating loses nothing.

---

## 🚀 Releases

Every new version (`vX.Y.Z`) is built for Windows, macOS, and Linux by a
robot ([`.github/workflows/release.yml`](.github/workflows/release.yml))
and put on the
[Download page](https://github.com/SVerma2696/Lock-In-Rider/releases/latest).
The step-by-step guide for each computer is in
[How to Download](#-how-to-download) at the top.

**Why does my computer warn me the first time?**
Big companies pay Microsoft and Apple every year to "sign" their apps,
like a name tag. This is a free project, so its app has no paid name
tag. Windows and macOS warn about any app without one. It doesn't mean
the app is unsafe. You click past the warning once, and it never asks
again. (On Linux, a new file just isn't allowed to run until you say
so with `chmod +x`. That's a normal safety rule for every file.)

**My antivirus flagged it / a red warning popped up**
This is a well-known false alarm that affects a lot of small, free apps
packaged the way this one is (a tool called PyInstaller, which bundles
Python and this app's code into one file) — antivirus tools sometimes
flag *how* an app was packaged, not anything it actually does. You don't
have to take that on faith: every release is built automatically, in the
open, straight from this exact source code by
[`.github/workflows/release.yml`](.github/workflows/release.yml) — a
script anyone can read line by line — and every single change to this
project runs the full automated test suite on Windows, macOS, and Linux
before it's ever allowed to reach a release
([`.github/workflows/tests.yml`](.github/workflows/tests.yml)).

Want to see everything it can do, peek at how the code is organized, or
run it from source and make your own changes? Keep reading below.

---

## 🔄 Auto-Update

**In plain words:** the app quietly checks once when it opens whether a
newer version exists. If it does, a small notice appears at the top
telling you which version is ready, with a button next to it to restart.
Click that button whenever you're ready — never while you're
mid-focus-block, it simply won't do anything until you finish — and the
app closes, swaps itself for the new version, and reopens, same as if
you'd downloaded it by hand.

**Want to ask right now?** Open the Settings page and press **Check for
updates now**. The app asks GitHub right then and tells you, in a short
sentence right under the button, what it found:

- "You already have the newest Lock In" — nothing to do.
- "Found Lock In v… Press Restart now at the top" — the same notice and
  Restart button as above just appeared.
- "Found Lock In v…, but its safety check didn't pass" — the download
  didn't match its fingerprint (see below), so it wasn't installed. You
  can still get that version from the Releases page.
- "Couldn't check just now" — usually no internet. Try again later.

The button works even if you turned the automatic check off. It only
asks when you press it.

- Only checks when you're online; if it can't reach GitHub, nothing
  happens and the app works exactly as it did before.
- The only thing it asks GitHub is "what's your newest release?" —
  nothing about you or your machine is sent.
- Once it finds a newer version, it also quietly downloads it in the
  background, before you click anything — worth knowing if you're on a
  slow or metered connection. (Turn the setting off below if you'd
  rather it didn't.)
- Turn the automatic check off anytime: Settings page → "Automatically
  check for updates." The "Check for updates now" button right under it
  still works when you want it.
- Only works for the app downloaded from Releases. Running it from
  source (`python main.py`)? Use `git pull` instead — you'll still see
  a small "update available" note, just without the restart button.
- After an update, a file called `Lock In.exe.old` sits next to the app.
  That's the old version, kept just in case. You can delete it.
- **Every update is checked before it's installed.** Each release comes
  with a small fingerprint file (for example `LockIn-Windows.zip.sha256`).
  A fingerprint is a long code worked out from every byte of a file, so
  changing even one byte changes it completely. Lock In works out the
  fingerprint of the download itself and only installs the update if it
  matches exactly. If the fingerprint file is missing, unreadable, or
  doesn't match, the update is thrown away. An unchecked update is never
  installed.

### If an update didn't work

This happens with v3.0.0 and older: you press **Restart now**, Lock In
closes, and it doesn't come back. Here's how to fix it on Windows:

1. Open the folder where you keep `Lock In.exe`.
2. Look at the files there:
   - **You see `Lock In.exe`:** double-click it. The first start after
     an update can take up to half a minute, so wait a little before
     clicking again.
   - **You only see `Lock In.exe.old`:** Windows can't open that file.
     Rename it back to `Lock In.exe` (right-click → Rename), then
     double-click it.
3. Still stuck? Get the newest version by hand: open the
   [Releases page](https://github.com/SVerma2696/Lock-In-Rider/releases/latest), download
   `LockIn-Windows.zip`, unzip it, and put its `Lock In.exe` in place of
   the old one.

Your settings, tasks, and history aren't stored next to the app, so
none of these steps touch them.

---

## ⚙️ Features

* **A timer that works in cycles** — focus for a while, then a short
  break, then eventually a longer break. You can pause, skip, and it
  keeps count of your streak.
* **A simple task list.** Jot down what you're working on, break it into
  smaller checklist steps, and pick one before you hit Start — the app
  remembers it and quietly keeps a record of every focus block you
  actually finish, so you can look back later at what you got done.
* **Notices distracting apps and does something about it.** You tell it
  what's always allowed and what's always blocked, and it also learns on
  its own over time. "Hard mode" — on by default — minimizes the window
  right away and then covers your whole screen until you're back on
  track; turn it off in Settings if you'd rather get a gentle
  notification first, then a louder one, before anything happens to
  your windows.
* **Learns your habits.** It watches which windows you open while
  focusing and slowly learns what counts as "working" for *you*
  specifically, not some generic list. You can correct it with one click
  any time it gets something wrong, and it learns from that instantly.
  No outside AI service is needed for this part — it's small enough to
  read and understand the whole thing yourself.
* **38 Kamen Rider costume changes.** Pick a Rider from the classic TV
  show and the app takes on that Rider's color — on the big Start
  button, the progress bar, the page you're on in the side bar, and a
  thin strip under the top bar. **26 of those Riders unlock an extra surprise on top**
  — a differently-shaped progress bar, a special sound, a screen effect,
  or a new keyboard shortcut, unique to that Rider.
* **A plain, no-costume mode** if you'd rather skip all of that — one
  switch turns every color and effect off for a fast, simple look, and
  turning it back off brings your Rider pick right back.
* **Two ways of talking to you** — plain, ordinary words, or the
  Kamen-Rider-flavored version — pick whichever one you like, any time.
* **An optional second opinion from Claude** (Anthropic's AI) for the
  rare case its own model genuinely can't decide. Off unless you turn it
  on, and even then it only ever sees a window's title — never a
  screenshot or anything else about what you're doing.
* **Works the same way on Windows, Mac, and Linux** — it detects your
  windows, minimizes them, and plays sounds a little differently on each
  one under the hood, so it just works wherever you run it.

---

## 📂 Project Structure

Already got the app from [How to Download](#-how-to-download) above? You can skip this
part — it's just a map of the code, file by file, for anyone curious how
it's organized under the hood.

```
Lock In/
│
├── main.py                     Entry point. Checks dependencies, launches the UI.
├── train.py                    Training CLI (record / label / rebuild / eval / …).
│
├── lock_in/                    The application package.
│   ├── __init__.py             The version number, and a map of this folder.
│   │
│   │   ── the "deciding" layer: no screen code, fully tested ──
│   ├── application/
│   │   ├── controller.py        AppController: builds and owns the timer, tasks,
│   │   │                        history, blocking, camera, Claude helper,
│   │   │                        notifications, and Revice's link.
│   │   ├── events.py            The one mailbox background helpers post notes to
│   │   │                        (WindowSeen, PhoneSample, BannerRequested, …).
│   │   ├── lifecycle.py         Stopping every helper cleanly, even if one fails.
│   │   ├── task_controller.py   Which task the next focus block is for.
│   │   ├── focus_controller.py  Writing each focus block into history.
│   │   ├── enforcement_controller.py  Judging windows and phones; the Activity list.
│   │   ├── buddy_controller.py  Revice's buddy link, without the screen.
│   │   └── update_service.py    One update check: fetch, fingerprint, download,
│   │                            check, unpack.
│   ├── storage/                 Crash-safe saving: write a spare file, then swap.
│   │   ├── json_store.py        Whole files (settings, tasks, the model).
│   │   └── jsonl_store.py       One-line-per-entry files (history, observations).
│   │
│   │   ── pure logic, stdlib only, fully unit-tested ──
│   ├── config.py               Settings dataclass, JSON persistence, block/allow
│   │                           defaults, and the %APPDATA% path resolution.
│   ├── config_validation.py    One rule per setting; a bad value becomes its default.
│   ├── session.py              Pomodoro state machine. Injectable clock, so tests
│   │                           run four-hour sessions instantly.
│   ├── classifier.py           Naive Bayes study/distraction model, tokenizer,
│   │                           seed corpus, explain(), JSON persistence.
│   ├── enforcer.py             judge() applies allowlist → blocklist → model.
│   │                           Enforcer() runs the strike/escalation ladder.
│   ├── observations.py         Records every window seen during focus and tracks
│   │                           which have been labelled. Backs train.py.
│   ├── tasks.py                 The task list: add/edit/complete tasks and their
│   │                           checklist subtasks, saved as tasks.json.
│   ├── task_picker.py           The Focus page's "current task" menu words.
│   ├── history.py               The diary of every completed, skipped, or reset
│   │                           focus block, saved as sessions.jsonl. Each block
│   │                           has its own id so Zi-O can fix or delete it.
│   ├── rider_effects.py         The typed names of every Rider power, one list
│   │                           per Tier (ProgressEffect … InteractionEffect).
│   ├── rider_themes.py         Every Rider: colors, era, year, and powers
│   │                           (RiderTheme, RiderAbilities, RiderDefinition).
│   ├── wizard_gestures.py      Draws-a-line-or-circle math for Wizard's mouse gestures.
│   ├── revice_sync.py           Revice's rules: the code check, messages, and
│   │                           the Pull History merge (no network, no window).
│   ├── visuals.py               Display font pick, plus Pillow-generated pictures
│   │                           (the slow ones are remembered, see cached_picture).
│   ├── updater.py               Pure version-compare/asset-pick logic for
│   │                           auto-update, plus the plain-words answer the
│   │                           "Check for updates now" button shows
│   │                           (no network, no filesystem).
│   ├── update_verify.py         The SHA-256 fingerprint check every update must pass.
│   ├── diagnostics.py           The small private log file.
│   ├── assets/
│   │   └── app_icon.png         The app's own picture — window/taskbar icon
│   │                           and notification icon.
│   │
│   │   ── platform-facing shells, thin by design ──
│   ├── monitor.py              Foreground-window polling on a daemon thread.
│   │                           Win32 backend, macOS (osascript), Linux (xdotool).
│   ├── notifier.py             Toasts and sounds: winotify/winsound (Windows),
│   │                           osascript/afplay (macOS), notify-send/paplay (Linux).
│   ├── update_fetch.py          The only network calls in auto-update: asks GitHub
│   │                           for the latest release, downloads the files.
│   ├── update_apply.py          Unpacks the downloaded release and writes/launches
│   │                           the per-OS relaunch script that swaps files.
│   ├── revice_link.py           Revice's connection to a buddy's computer on
│   │                           the same Wi-Fi. Only runs after Share/Receive.
│   ├── revice_tab.py            The screens on Revice's Buddy page.
│   └── ui/                     Everything you see on screen (CustomTkinter).
│       ├── app.py              The main window: top bar, side bar, page area,
│       │                       and the heartbeat. Asks the AppController for
│       │                       everything it shows.
│       ├── effects.py          The Rider pictures: glow, era strip, progress
│       │                       shapes, Amazon's field.
│       ├── host.py             What the window's add-on parts may use (types only).
│       ├── theme.py            Every base color, size, and space, in one place.
│       ├── router.py           The side bar's list of pages (no window needed).
│       ├── mirror.py           Ryuki's left-right flip helpers.
│       ├── icons.py            Small line pictures, drawn with Pillow.
│       ├── overlays.py         Lockdown screen, X's goal screen, Ghost's clock.
│       ├── updates.py          "Check for updates" and the update strip.
│       ├── gestures.py         Wizard's mouse gestures.
│       ├── revice.py           Revice's buddy link, from the window's side.
│       ├── preferences.py      What happens when you change a setting.
│       ├── insights_data.py    The Insights page's totals (no window needed).
│       ├── components/         Cards, buttons, badges, setting rows, the side
│       │                       bar, and the timer.
│       └── pages/              One file per page: Focus, Tasks, Blocking,
│                               Activity, Insights, Help, Settings, the Rider
│                               page, and Buddy.
│
├── tests/                      About 1,500 fast tests, plus the window smoke test.
│   ├── test_rider_registry.py  Checks EVERY Rider automatically: colors, era,
│   │                           powers, id, pages, progress pictures.
│   ├── test_application.py     The mailbox, clean shutdown, focus records,
│   │                           blocking decisions, the buddy link.
│   ├── test_storage.py         Crash-safe saving and broken-file reading.
│   ├── test_config_validation.py  Every setting's rule.
│   ├── test_update_verify.py   Valid, wrong, missing, and garbled fingerprints.
│   ├── test_diagnostics.py     The log file stays small and private.
│   ├── test_packaging.py       requirements.txt and pyproject.toml agree.
│   ├── test_*.py               One file per part of the app (session, classifier,
│   │                           enforcer, tasks, history, themes, pages, …).
│   └── smoke_ui.py             Opens the real window and clicks through it
│                               (not pytest). Point your data folder somewhere
│                               safe first -- it saves settings.
│
├── scripts/
│   └── write_checksum.py       Writes a release download's fingerprint file.
│
├── .github/workflows/
│   ├── tests.yml               Ruff, mypy, tests on Python 3.11–3.13, coverage,
│   │                           the window smoke test on Windows/macOS/Linux, and
│   │                           a check of the libraries for known problems.
│   ├── codeql.yml              GitHub's security scan.
│   └── release.yml             Builds and publishes installers (and their
│                               fingerprints) on a version tag.
│
├── pyproject.toml              The project's description, its libraries in groups,
│                               and the settings for pytest, coverage, Ruff, mypy.
├── requirements.txt            Every library a full copy uses, in one list.
├── run.bat                     Launches with pythonw (no console window).
└── build.bat                   PyInstaller one-file build.
```

Runtime data lives outside the project, in `%APPDATA%\Lock In\` (see
[Config](#-config) below) — deliberately, so a PyInstaller build still
writes correctly even if its own install folder is read-only.

---

## 🚀 How to Run

### 1. Clone this repository
```bat
git clone https://github.com/SVerma2696/Lock-In-Rider.git
cd Lock-In-Rider
```

### 2. Install dependencies
Make sure you have Python 3.11+ installed, then run:
```bat
pip install -r requirements.txt
```
That installs everything a full copy uses. If you'd rather pick, the
same libraries are split into groups in `pyproject.toml`:
```bat
pip install -e .                  the app itself
pip install -e ".[camera]"        plus Strict Camera Monitoring
pip install -e ".[claude]"        plus the optional Claude helper
pip install -e ".[dev]"           plus the tools for testing and checking
```

### 3. Run it
```bat
python main.py
```
Or double-click `run.bat` (launches with `pythonw`, no console window).
To produce a standalone `.exe`, run `build.bat` — or just grab a
[prebuilt release](#-how-to-download) for your OS instead of building from
source.

Once it's open, the app's own **Help page** has a full, plain-language
walkthrough of every feature — including exactly how to turn on each
of the 26 Kamen Riders' special extra powers (Tiers 1/2/3/4 below). Start
there before this README if you just want to use the app.

*(Optional step 4: turn on the [Claude fallback](#claude-fallback-optional-off-by-default)
if you want a second opinion on ambiguous windows — entirely optional,
and off by default.)*

`customtkinter` and `Pillow` are required for the app to *open* — Pillow
draws the glow and background art. On Windows, `pywin32` and `psutil` are
what let it actually see which window you're in — without them, blocking
silently does nothing at all, all day, and the app just becomes a plain
(very good) timer.

This is an easy trap to fall into: `run.bat` launches with `pythonw.exe` on
purpose, so no black console window sits behind the app — but that also
means the "these packages are missing" warning that normally prints to the
console is thrown away and nobody ever sees it. If blocking doesn't seem to
be doing anything, run `pip install -r requirements.txt` again and make sure
it installs `pywin32` and `psutil` without errors. The app also now shows a
red banner on startup, and a note on the Blocking page, if it can't detect
windows — but it's worth checking directly if you're not sure.

### Checking your changes

These are the same checks GitHub runs on every push
(`.github/workflows/tests.yml`). Install the tools once with
`pip install -e ".[dev]"`. GitHub uses exact versions of the two
checkers, so get the same ones, or yours may disagree with GitHub's:
`pip install "ruff==0.16.10" "mypy==2.4.0"`. Then:
```bat
ruff check .                     style problems
ruff format --check .            formatting
mypy                             types
pytest                           the tests
pytest --cov=lock_in             the tests, plus how much of the app they run
```
And the real-window smoke test, with a throwaway settings folder so it
never touches your own (four separate lines on Windows). The first line
empties that folder: the test saves settings as it goes, and leftovers
from an earlier run can make it fail.
```bat
if exist .smoke-data rmdir /s /q .smoke-data
set APPDATA=%CD%\.smoke-data
set PYTHONPATH=.
python tests\smoke_ui.py
```

---

## 🔌 System Integrations (Data Flow)

This section is for developers who want to see exactly how the pieces
talk to each other. In plain words: the app watches what window is in
front, asks "should this be allowed?", and if the answer is no, it warns
you and eventually acts. Separately, everything it sees gets saved so
the model can learn from it later. The diagrams below spell out exactly
which file does which step.

### Enforcement loop
```
Foreground window (title + process) -> judge() [lock_in/enforcer.py] -> Verdict
Verdict -> Enforcer.update()                    -> Action (warn/nag/minimize/lockdown)
Action  -> Notifier (toast + sound) and lock_in/ui -> banner / full-screen lockdown
```

### Training loop
```
Every window seen during focus -> ObservationStore (observations.jsonl)
Corrections (Activity page, or `train.py label`) -> NaiveBayesClassifier.learn() -> model.json
```

### Claude fallback (optional, off by default)
```
Ambiguous window title ONLY (never a screenshot) -> Claude API (claude-haiku-4-5)
Claude's answer -> also folded into observations.jsonl, so the local model
                   needs Claude less and less over time
```

**Note:** the Claude tier only ever sees a window title/process-name
string — see [What actually gets sent](#what-actually-gets-sent) for the
test that pins this down.

---

## 📘 Concepts Demonstrated

This section is a quick tour of the interesting engineering ideas inside
the app, for anyone reading the code rather than just using it:

* **A "study or distraction" guesser built completely from scratch** —
  no AI library, just counting words and doing the math by hand
  (Naive Bayes with Laplace smoothing), plus a way to ask it *why* it
  guessed what it guessed, one word at a time.
* **A window that never freezes.** The part that watches for your
  active window runs on its own background thread and does one simple
  job; the part that decides things and updates what you see always
  happens on the main thread, on a steady heartbeat — so the two never
  step on each other.
* **The same features, three different operating systems.** Windows,
  macOS, and Linux each need their own way to find the active window,
  minimize it, and play a sound — and if a machine is missing what it
  needs for one of those, the app says so honestly instead of silently
  doing nothing.
* **All the art is drawn, not shipped as pictures.** The glow, the
  background patterns, the little divider lines, even the padding around
  the app icon — all of it is generated by code every time, using a
  drawing library called Pillow.
* **One small color toolkit powers 38 themes.** Instead of hand-picking
  colors for every Rider/voice/era combination one by one, a handful of
  tiny color-math building blocks (lighten this, darken that, pick
  readable text automatically) combine to produce all of them.
* **Tests written alongside the code, not after.** The parts with no
  on-screen window are fully covered by fast, automatic tests. The
  visual parts are checked by actually running the real app and looking
  at what it draws.

---

## 🔧 Requirements

* Python 3.11+
* `customtkinter`, `Pillow` (required — the app won't open without them)
* **Windows:** `pywin32`, `psutil` (blocking), `winotify` (toasts) —
  optional, but blocking silently does nothing without them
* **macOS:** `osascript`, `afplay` (both built in)
* **Linux:** `xdotool` (X11 only — no Wayland equivalent), `notify-send`,
  `paplay`/`aplay` (all optional, install via your package manager)
* Optional: the `anthropic` SDK + an API key, only if you turn on the
  [Claude fallback](#claude-fallback-optional-off-by-default)
* Auto-update needs no new dependency — it's built entirely from the
  standard library already required to run Python at all.

---

## How the blocking actually works

Every second during a focus block, Lock In reads the foreground window's
process name and title and runs it through three layers, in strict order:

```
allow list  →  block list  →  learned model  →  allowed
```

Explicit rules always beat the model. If you allow-list `chrome.exe`, the
classifier never gets to veto that.

When a window is judged blocked, escalation is by **intensity, not frequency**,
and the ladder depends on whether Hard mode is on:

**Hard mode (default — Blocking page → "Hard mode"):** no warnings first — it
acts immediately, since the whole point of this mode is that you don't want
to be asked nicely.

| Time on the app | What happens |
|---|---|
| 0–8s | Nothing. You might be closing it. |
| first strike | Window minimised, timer pulled to the front. |
| every strike after that | Full-screen cover for 15 seconds. |

**Soft mode (Blocking page → turn "Hard mode" off):**

| Time on the app | What happens |
|---|---|
| 0–8s | Nothing. You might be closing it. |
| first strike | Toast notification. |
| every strike after that | Toast + alert sound. |

Strikes decay after 45 seconds of clean work, so one slip at minute 3 doesn't
leave you one click from a screen takeover at minute 20. Hopping between two
blocked apps restarts the grace period but *keeps* your strikes — app-hopping
to dodge the nag isn't a valid strategy.

All timings are configurable in the Settings page.

### If a window's program name can't be read

A few programs (Steam is a common one, when it's running "as administrator")
hide their process name from a program that isn't also elevated. When that
happens, Lock In still checks the *window's title text* for the name of a
listed program before falling back to the guessing model — so `steam.exe`
being on the block list still catches a window titled "Steam" even if we
never learned its process name. If blocking still doesn't seem to be working
at all, check the Blocking page: if it says "App detection unavailable" (or
you see a red banner about `pywin32`/`psutil` when the app starts), those two
packages aren't installed and nothing can be detected — see How to Run.

### On "spam notifications"

Firing a toast every second is the intuitive read of the idea and the wrong
implementation: it trains you to dismiss notifications, which burns the exact
channel the app depends on, and Windows starts collapsing rapid toasts into
Action Center anyway. So there's one alert per strike interval, each louder
than the last.

### On "stop me from leaving"

Windows has no supported way for an ordinary user-space program to genuinely
prevent app switching — the APIs that could (global input hooks that swallow
Alt-Tab, foreground locks) need elevation, are what malware uses, and can wedge
a machine if the process dies at the wrong moment.

So Lock In enforces through **friction and attention**, not force. It makes
opening Discord annoying and impossible to do absentmindedly, which is the
actual failure mode — nobody deliberately decides to lose forty minutes.

Every escalation rung, including the full-screen lockdown, has a visible exit.
That's deliberate. An app that can trap you is an app you uninstall the first
time it misfires during something that mattered.

---

## The model

**In plain words:** imagine you'd read the titles of a hundred windows
someone had open, half while they were studying and half while they were
goofing off. Pretty quickly you'd notice patterns — "lecture," "pdf," and
"docs" show up a lot in the studying pile; "chat," "stream," and "clip"
show up a lot in the other one. That's basically all this does: it
counts which words show up in which pile, and uses those counts to guess
about a brand new window it's never seen before. `classifier.py` is that
idea written out in code (technically: a multinomial Naive Bayes
classifier over the active window title plus process name, with Laplace
smoothing so a word it's never seen doesn't break the math).

**Why titles instead of screenshots.** The original idea was to train a vision
model on screen captures. Titles win on all three axes that matter:

- **Signal.** `"Lecture 12: Pipelining.pdf - Adobe Acrobat"` vs
  `"general #chat - Discord"` — the OS hands you a near-perfect description of
  what you're doing for free. A CNN on raw pixels would burn enormous capacity
  rediscovering text.
- **Cost.** Titles are a handful of tokens once a second. Screenshots are
  megabytes per second through a vision model.
- **Privacy.** Your window titles never leave your machine. An app you run *all day while
  working* becomes a very different thing to trust the moment it starts
  shipping screenshots anywhere.

**Why Naive Bayes instead of something bigger.** It trains on 40 examples,
updates online in microseconds, needs zero dependencies, and its per-token
weights are directly inspectable — `model.explain()` tells you a window was
flagged because of `youtube`, `mv`, `official`. When the app's entire job is to
be trusted enough to interrupt you, a black box is a liability.

It ships pre-trained on a 64-example seed corpus so it's useful on first
launch, and every correction is a real online update — the next poll already
uses the new model.

If you *do* want pixels later, the seam is clean: swap in anything that returns
`(label, confidence)` from `judge()` and nothing downstream changes.

---

## Tasks & session history

**In plain words:** a simple to-do list lives right in the app now.
Write down what you're working on, break it into smaller steps if you
want, pick it from a dropdown above the Start button, and the app quietly
keeps a diary of every focus block you actually finish.

- **Adding a task.** The Tasks page has a plain text box — type a name,
  hit Add. Click into a task to add smaller checklist steps under it,
  and check them off as you go.
- **Picking what you're working on.** A dropdown above the Start button
  lists your open tasks. Pick one before you start a block, or leave it
  on "No task" — the timer works exactly the same either way.
- **Hitting Start marks your task "in progress" on its own.** But the
  app never ticks a task *done* for you — that's always your own click
  on its checkbox. One job usually takes more than one timer, so "the
  timer ran out" and "the job is finished" are kept as two separate
  facts on purpose. Ending a block, skipping it, or resetting it never
  checks anything off.
- **The diary.** Every focus block gets written down the moment it ends
  — whether it finished, was skipped, or was reset — along with how long
  it ran and which task (if any) it was for. Nothing shows this to you
  yet. Later features (an "hours today" view, a timeline, simple stats)
  will read from it, so the app keeps the record now and loses nothing
  while those get built.

Both files stay on your machine right next to `config.json` (see
[Config](#-config) below), unless you pick Revice. While you're paired
with a buddy, either of you can press Pull History to copy focus blocks
(and the tasks they belong to) onto the other's computer — it's not
one-way, and it doesn't ask again each time (see Tier 6 below).

---

## Wording

Settings → "Wording" switches the app's words between two voices:

- **Professional** (the default) — plain, ordinary words: "Focus", "Start",
  "Off Task", "Screen Locked". Nothing Kamen-Rider-specific about it, and
  it reads the same no matter which Rider theme is picked.
- **Tokusatsu** — the Kamen-Rider-flavored voice this app shipped with
  originally: "Henshin", "Off Mission", "LOCKDOWN ENGAGED.", and so on.
  This is the one that further changes per era (see the table below).

This only changes words — colors, patterns, and sounds from the Kamen
Rider theme (below) apply either way. `lock_in/session.py` (`label_for`)
and `lock_in/enforcer.py` (`MESSAGES_PROFESSIONAL` vs `MESSAGES_BY_ERA`)
hold the two voices; an unrecognized value in a corrupted `config.json`
quietly falls back to professional rather than crashing.

---

## Kamen Rider theme

**In plain words:** pick a superhero, and the whole app changes color to
match their costume — not just a small accent, the *whole thing*.

Settings → "Kamen Rider theme" (called "Color theme" when Wording is set
to Professional) picks from all 38 Rider series (Showa, Heisei, and Reiwa
era), each with its own primary/secondary color pair pulled from that
Rider's actual suit colors — hand-tuned as a *separate* hex for light
mode and dark mode (not one color with the other guessed from it), so
nothing washes out on a pale background or vanishes on a near-black one.
Since v3.0.0 the app uses **one** Rider color at a time, on purpose: the
big Start/Henshin button, the progress bar, the marker on the page you're
on, the switches, and the thin era strip under the top bar. Everything
else stays a calm grey (dark mode) or white (light mode), so the app
looks tidy no matter which Rider you pick. Green, amber, and red are
kept for things that *mean* something (allowed, careful, blocked) and
never used as decoration. Defaults to the original 1971 series. See
`lock_in/rider_themes.py` for the full palette, and `lock_in/ui/theme.py`
for the calm base colors.

**MY-TH is special:** it's one Rider with two looks. In **light mode**
you get normal Kamen Rider MY-TH — blue and silver. In **dark mode** you
get Kamen Rider MY-TH ORIGIN — red and gunmetal. There is still only one
"MY-TH" to pick; the light/dark switch decides which one shows up.

Picking a Rider also picks its **era**, and — when Wording is set to
Tokusatsu — the era changes more than color, too:

| | Showa (1971–1994) | Heisei (2000–2019) | Reiwa (2019–present) |
|---|---|---|---|
| **Voice** | Blunt base-alarm ("Intruder Alert", "Base Lockdown") | Tactical mission briefing ("Off Mission", "Full Lockdown") | Crisp digital system alert ("Focus Breach", "System Lockdown") |
| **Divider strip** | Tick marks, like a gauge | A row of tiny diamonds | A dashed line with square nodes |
| **Sound cue** | A plain two-tone alarm | The original beep sequence this app shipped with | A quicker, higher-pitched digital-sounding sequence |

In Professional wording, the Voice column above doesn't apply — there's
one plain voice for every era. The divider strip and sound cue still
vary by era either way. Heisei is the fallback
voice/pattern/sound if the app is ever handed a Rider name it doesn't
recognize, so nothing crashes on a corrupted `config.json`. All three
eras of tokusatsu copy live in `lock_in/enforcer.py` (`MESSAGES_BY_ERA`),
the patterns in `lock_in/visuals.py`, and the sound tables in
`lock_in/notifier.py`.

### Tier 0: Standard Mode (no Rider flavor at all)

Settings → "Standard Mode" is a single switch, independent of which
Rider is picked below it. Turning it on swaps in a plain slate-grey and
blue palette, turns off every Rider gimmick from Tier 1 all the way to
Tier 6 (no Rider page, no Buddy page, no gestures), forces Wording to
Professional, and uses the plain progress bar and a plain grey line
instead of the era strip. It's the cleanest, lightest look in the app. Your actual Rider and Wording choices
are never overwritten; turning Standard Mode back off restores both
instantly. Picking a Rider from the menu also turns Standard Mode off,
so the Rider you picked shows up straight away.

### Tier 1: 10 Riders with their own gimmick

On top of the era/color system above, 10 Riders each get their own extra
treatment during a focus block:

- **Kamen Rider (1971)** — the progress bar becomes a 4-bladed windmill,
  its blades lighting up one at a time.
- **Skyrider** — the progress bar rises vertically instead of filling
  left-to-right, like a glider's altimeter climbing.
- **Fourze** — the progress bar becomes a small star-field, lighting up
  and connecting one star at a time.
- **Build** — the progress bar becomes two vials that fill together and
  visually combine once the block is nearly done.
- **Stronger** — a soft red glow builds around the edge of the page as
  the block goes on, like charging up electricity.
- **Kiva** — a translucent amber wash tints the edge around the page
  during a focus block, evoking its night/vampire motif.
- **Agito** — the progress bar's color starts muted and gradually
  brightens to its true gold, like a dormant power waking up.
- **Black** — dark mode gets stricter and higher-contrast for this Rider:
  a pure black background, darker cards, and brighter words.
- **Drive** — the progress bar appears to lag behind early on, then
  visibly speeds up and catches up right near the end.
- **Saber** — the progress bar becomes a bookmark ribbon hanging from
  the top, filling in as the block goes on -- like marking how far
  you've read.

Every other Rider keeps the plain progress bar. See
`docs/superpowers/specs/2026-08-10-tier1-rider-progress-variants-design.md`
for the full design, and `docs/superpowers/plans/2026-08-10-tier1-rider-progress-variants.md`
for the implementation plan.

### Tier 2: 3 Riders with quick-access settings presets

Three more Riders add a **Rider power** card to the Settings page, right
under the Focus card:

- **Kuuga** — 4 buttons (Mighty/Dragon/Pegasus/Titan) that each set
  focus/break lengths in one click, from a quick 10-minute sprint to a
  90-minute endurance block.
- **Super-1** — 5 task-type buttons (Super Hand/Power Hand/Elek Hand/
  Cold-Thermal Hand/Radar Hand), each tuned for a different kind of
  work (development, hardware, admin, logic/AI, research).
- **Gavv** — a toggle that overrides your timer lengths toward repeated
  10-minute "snackable" sprints with longer, more frequent breaks, for
  days when a normal-length focus block isn't realistic. Stays on until
  you turn it back off; your real settings are never overwritten.

See `docs/superpowers/specs/2026-08-10-tier2-settings-presets-design.md`
for the full design, and `docs/superpowers/plans/2026-08-10-tier2-settings-presets.md`
for the implementation plan.

### Tier 3: 5 Riders with enforcement/interaction tweaks

Five more Riders change actual behavior, not just looks:

- **X** — before a fresh focus block can start, a full-screen prompt
  asks what you're working on. No timeout — type when you're ready.
  Your answer replaces the Rider-name label for that block.
- **Amazon** — during a focus block, the whole UI strips down to a
  solid draining green field (the side bar hides, and Pause/Skip/Reset
  shrink to icons instead of disappearing), and the grace period drops
  to 0 seconds.
- **ZX** — the whole app renders in monochrome for as long as ZX is
  selected, and auto-minimizes the moment a focus block starts, with
  Sounds and Desktop notifications silenced for that block.
- **Gaim** — during a focus block, the window stays always-on-top, the
  edge around the page dims, and a "Locked on top" badge appears in the
  top bar — a strong visual deterrent, never a real block on switching
  windows.
- **555** — the existing Lockdown screen gets a second way out: type
  `555` to skip the rest of the countdown and return to work early.

See `docs/superpowers/specs/2026-08-11-tier3-enforcement-interaction-design.md`
for the full design, and `docs/superpowers/plans/2026-08-11-tier3-enforcement-interaction.md`
for the implementation plan.

### Tier 4: Alternate display modes

Eight more Riders each change how the app looks, sounds, or acts during a focus
block — completely separate from the Tier 1 progress-bar gimmicks above:

- **Black RX** — makes breaks wait for you to press Start instead of starting
  on their own.
- **Ryuki** — the whole window flips left-to-right during breaks (the side
  bar jumps to the right side too) and flips back when focus starts again.
- **Kabuto** — the timer digits hide while you focus; hover to peek at the
  real time.
- **Ex-Aid** — the timer switches to a pixel font and the alert sound becomes
  an 8-bit jingle.
- **Hibiki** — soft ambient background sound plays for the whole focus block.
- **Zero-One** — the timer changes into a row of dashboard cards instead of
  the big digits.
- **Ghost** — the main window hides and a small floating clock stays on top of
  everything; click it to bring the full window back.
- **Zeztz** — keyboard shortcuts take over: Space to start/pause, S to skip,
  R to reset.

One more, Saber, joins the Tier 1 progress-bar list instead — its
bookmark-ribbon shape uses the same drawing code as Fourze and Build.

### Tier 5: Riders that read your own history

A new kind of Rider gimmick, separate from every tier above: picking one
of these Riders adds a whole new page to the side bar (under a small
"Rider" heading), built from your own
tasks and past focus blocks instead of just changing colors, sounds, or
behavior.

- **V3** — adds an "Hours" page: a big number showing how long you've
  focused today, plus a simple bar chart of the last 14 days. Every
  block counts toward it, whether you finished it, skipped it, or reset
  it early.
- **Den-O** — adds a "Timeline" page: one day's focus blocks at a time,
  earliest first, with buttons to flip a day forward or back. Each block
  shows its time, how long it ran, whether it finished naturally or got
  cut short, and which task (if any) it was for.
- **Decade** — adds an "Analytics" page: a 30-day version of V3's bar
  chart, plus your top 10 tasks ranked by how much total time you've
  spent on each.
- **Zi-O** — adds a "History" page. It shows the same day-by-day list as
  Den-O, but now you can fix mistakes. Every block has a little menu for
  picking a different task, and a Delete button. Delete asks you to tap
  twice ("Delete", then "Really delete?") so you can't do it by
  accident, and there's no pop-up. Only the task can change; when the
  block started, when it ended and how long it was stay exactly as the
  timer measured them.
- **Blade** — adds a "Board" page: your tasks as three columns, To Do, In
  Progress and Done, like sticky notes on a wall. Each note has a small
  arrow button that moves it one column over. It shows the same tasks as
  the Tasks page, so a move on the Board shows up there too.

- **W** — adds a "Week" page. It puts two weeks side by side: the last 7
  days, and the 7 days right before them. You see one total for each, a
  short sentence that says which one is bigger, and a chart with two
  bars for every day, one for last week and one for this week. Every
  block counts, finished or not.

- **Geats** — adds a "Goal" page. You pick how many minutes you want to
  focus each day with a minus and a plus button (each press is 15
  minutes, and the app remembers your pick). A bar fills up as you
  focus, and a streak counts how many days in a row you reached your
  goal. Seven little boxes show the last 7 days, filled in for the days
  you made it. Every block counts, finished or not.
- **Gotchard** — adds a "Badges" page: 9 cards to collect, for things
  like your first focus block, doing 10 blocks, a 1-hour day, a 3-hour
  day, 10 hours in all, checking off a task, and reaching your daily
  goal once, 3 days in a row, or 7 days in a row. A card you haven't
  won yet shows a gray hint so you know what to aim for; once you win a
  badge, it's yours to keep.
- **OOO** — adds a "Combo" page: every open task gets three boxes, Plan,
  Work, and Review, that you can check in any order. Check all three
  and the task shows a small "Combo formed!" mark. It's just for fun —
  you still mark the task itself done on the Tasks page, the same as
  always.
- **MY-TH** — adds a "Priority" page: your open tasks, numbered, with the
  one you've gone the longest without working on at the top. A task
  you've never started outranks every task you have, no matter how
  stale. Nothing is saved here — the order is worked out fresh every
  time you open the page. MY-TH also has two looks — see
  [Kamen Rider theme](#kamen-rider-theme) above.

All ten Tier 5 Riders now read your tasks and history this way.

### Tier 6: Riders that add something new

The last two Riders do things no earlier Rider does. Both are built:

- **Wizard** — you can move between pages with your mouse, like
  drawing a magic spell. Hold the **right mouse button** and drag on the
  Lock In window:
  - Draw a line to the **left** to go to the page above in the side bar.
  - Draw a line to the **right** to go to the page below in the side bar.
  - Draw a **circle** to jump to the first page (Focus).

  A quick right-click does nothing, and if the app isn't sure what you
  drew, it does nothing too. Small dots follow your mouse while you
  draw and disappear a moment later. Gestures only ever change pages — they can't start,
  pause, or end a focus block. They only work inside the Lock In window;
  the app never watches your mouse anywhere else on your computer, and
  nothing is recorded or sent anywhere. When Wizard is your Rider, a
  "Mouse gestures" switch appears in Settings (on by default) if you'd
  rather turn it off.

- **Revice** — Revice is two heroes sharing one body, so it lets two
  computers share one Lock In. Both of you pick Revice, then open the
  new **Buddy** page in the side bar:
  - One of you presses **Share**. A 4-number code shows up.
  - The other presses **Receive** and types those 4 numbers.

  Now you're paired. Each of you sees the other's timer, whether
  they're focusing or on a break, and what task they picked — and your
  computer's name is what they see for yours. Press **Pull History** to
  copy their past focus blocks, and the tasks those blocks belong to,
  into yours. It only adds what you don't already have. It never
  changes or deletes anything, so pressing it twice is fine. Your buddy
  can press Pull History too, any time you're paired — then your focus
  blocks and their tasks go to them, and you aren't asked each time.
  Press **Unpair** when you're done.

  A few things to know:
  - Both computers must be on the **same Wi-Fi**. Some school, office,
    or café Wi-Fi blocks this. Home Wi-Fi almost always works.
  - The code lasts 2 minutes. After 3 wrong tries it stops working, and
    you press Share again. That stops someone guessing, but a sneaky
    computer on the same Wi-Fi could still figure the code out. Only use
    Revice on Wi-Fi you trust, like at home.
  - Nothing goes on the network until you press Share or Receive, and
    it stops when either of you unpairs, closes Lock In, picks
    another Rider, or turns on Standard Mode.
  - Windows may ask whether to let Lock In use the network the first
    time you press Share. Say yes, or pairing can't work.
  - What's sent between the two computers is **not scrambled**
    (encrypted). Someone snooping on the same Wi-Fi could read your
    timer, task names, and pulled history. That's fine at home, but
    don't use it on café Wi-Fi.
  - Lock In only listens on your Wi-Fi (or cable), never on every
    network your computer is on at once. If you use a VPN and your
    buddy can't find you, turn the VPN off and try again.
  - Pairing can never start, pause, or stop anyone's timer.

Tier 6 is complete.

### Adding a new Rider

A Rider is made of two parts: **who they are** (name, era, year,
colors) and **what they can do** (their powers). Adding one takes a few
small steps:

1. **Add them to the table** in `lock_in/rider_themes.py`: their name,
   era, year, and a light-mode and dark-mode color for `primary` and
   `secondary`.
2. **Give them a power, if they have one.** Pick it by name from
   `lock_in/rider_effects.py`, like
   `tier4_effect=DisplayEffect.MIRROR_FLIP`. A misspelled power stops
   the app straight away with a clear message, instead of the power
   quietly not working.
3. **A brand-new power** gets its own name in `rider_effects.py` first,
   in the list for its Tier, then the code that makes it happen. For
   example, a new Tier 5 page gets a builder in `lock_in/tier5/` and a
   line in `TIER5_BUILDERS`, plus its side bar words and icon in
   `lock_in/ui/router.py`.
4. **Run the tests.** `tests/test_rider_registry.py` checks every Rider
   automatically: valid colors, a real era, typed powers, a unique id,
   a side bar that builds, and a progress picture that draws. It also
   checks that every power belongs to exactly one Rider. A new Rider is
   covered the moment it's in the table, with no new test needed.

In code, ask about a power by its kind, not by comparing words:
`if app.abilities.display is DisplayEffect.MIRROR_FLIP:`.
`RIDERS` (by a short id like `"ex-aid-2016"`) and `RIDER_THEMES` (by
display name, which is what `config.json` saves) both list every Rider.

### Look and feel

Since v3.0.0 the screen is built from a few simple parts, all in
`lock_in/ui/`:

- **A side bar** on the left with one button per page. Each button has a
  small line picture drawn by the app itself with Pillow
  (`lock_in/ui/icons.py`) — no emoji, so they look the same on every
  computer.
- **A top bar** with the app's name on the left and a small status badge
  on the right, like "● Focus active" or "Short Break".
- **Cards** (`ModernCard`) — rounded boxes with a thin border. Almost
  everything sits in one.
- **Three kinds of button.** The main one is filled with the Rider's
  color. The others are plain grey. Red is only for things you can't
  easily undo.
- **Calm base colors** (`lock_in/ui/theme.py`), picked separately for
  light and dark mode, so both look like they were designed on purpose.
- **A display font** for the timer digits and headings, instead of the
  toolkit's plain default — a different one per OS (`Bahnschrift` on
  Windows, `Avenir Next` on macOS, `Noto Sans` on Linux), falling back
  quietly to the system default if that font isn't installed.
- **A thin era strip** under the top bar: tick marks for Showa, tiny
  diamonds for Heisei, a dashed circuit trace for Reiwa
  (`make_panel_divider()` in `lock_in/visuals.py`). Standard Mode shows a
  plain grey line instead.

The Pillow art from earlier versions (glows, era wallpapers) is still in
`lock_in/visuals.py`, because some Rider gimmicks and Tier 5 charts use
it. The everyday screen just doesn't paint it behind everything any
more.

**Contrast safety.** A Rider's `primary`/`secondary` are also used
directly as *text* colors in a few places (the phase name, the Rider
name label, the Henshin button, the page you're on).
Even with every color hand-tuned per mode (see above), a color that's
already fairly pale or fairly dark can still end up too close to its
own tinted background to read comfortably — so those specific spots use
`RiderTheme.primary_text_pair` / `secondary_text_pair` /
`button_text_pair` instead of the raw color: darkened further for light
mode and lightened further for dark mode (or, for text sitting directly
on a filled button, plain black or white chosen by perceived
brightness). All 38 Riders are checked for this in
`tests/test_rider_themes.py`, in both appearance modes, so a future
palette edit can't quietly reintroduce hard-to-read text.

### App icon

`lock_in/assets/app_icon.png` is the app's own picture — used for the
title-bar/taskbar icon and shown on desktop notifications. It isn't
square, so `visuals.load_app_icon()` pads it onto a see-through square
canvas rather than stretching it. On Windows, the taskbar specifically
needs a real `.ico` file (not a `.png`) and its own "app ID" separate
from `python.exe`'s — both are handled automatically
(`main.py`'s `_detach_from_python_exe_on_windows()`, and
`lock_in/ui/app.py`'s `_set_app_icon()`).

---

## Training it

There are three ways in, in increasing order of how much data they get you.

### 1. The correction buttons

The Activity page logs **every** window seen during a focus block, not just
the ones that got blocked — each row has a colored dot (red = blocked, green
= allowed) and says why. Click **distraction** / **was studying** on any row
to correct it. Writes `model.json` immediately; no retrain step. Correcting
to "was studying" also auto-allow-lists that process, since that's almost
always what you meant.

Because it shows everything, not just flagged windows, you can catch both
kinds of mistake here: something that got wrongly blocked, *and* something
distracting that slipped through as "allowed" — like Steam showing up green
when it should've been red, which tells you the block list or model needs a
correction. For bulk labelling instead of one-off corrections, use `train.py`.

### 2. `train.py` — the real loop

Recording is on by default, so the app logs every distinct window it sees during
focus (not just flagged ones) to `observations.jsonl`. Then:

```bat
python train.py label      :: one keypress each, most-seen windows first
python train.py rebuild    :: fold your labels into the model
python train.py eval       :: check you didn't make it worse
```

`label` shows you the model's current guess and the tokens behind it, so you can
sanity-check before agreeing:

```
[3/47] chrome.exe — Khan Academy linear algebra practice
     seen 22×  ·  model says study (89%)
     signal: khan-, academy-, algebra-, practice-
     > _
```

`s` = study, `d` = distraction, `enter` = accept the guess, `k` = skip,
`q` = quit. Saves after every answer, so quitting halfway loses nothing.

Full command list:

| Command | What it does |
|---|---|
| `record` | Poll and log windows without running Pomodoro blocks |
| `label` | Interactive labelling loop |
| `rebuild` | Retrain from seed + all your labels (`--no-seed` to use yours alone) |
| `stats` | Model size, class balance, most informative tokens |
| `eval` | Hold-out accuracy, per-class precision/recall, vocabulary overlap |
| `test "<title>"` | Predict one string and show why |
| `import <file>` | Bulk import `label,text` rows from CSV/TSV |
| `export <file>` | Dump your labelled data to CSV |
| `purge` | Drop unlabelled observations, keep the labels |

### 3. Bulk import (fastest start)

Writing forty lines in a text editor beats waiting to encounter forty apps:

```csv
label,text
d,"Ryujinnie bot server - Discord discord.exe"
d,"F1 2026 Silverstone highlights - YouTube chrome.exe"
s,"ECE 232 Lecture 9 pipelining.pdf sumatrapdf.exe"
s,"Overleaf honors thesis draft - Google Chrome chrome.exe"
```

```bat
python train.py import mine.csv && python train.py rebuild
```

Or edit `SEED_DATA` in `classifier.py` directly, if you want your examples to
ship with the app rather than live in your profile.

### Reading `eval` honestly

```
Accuracy:              81.8%
distraction   precision 90.5%   recall 77.3%
study         precision 80.0%   recall 90.3%
Vocabulary overlap:    41%
```

**Overlap is the number to watch first.** It's the share of test-title words the
model had seen before. Below ~60%, the model is guessing on vocabulary it has
never encountered, and no amount of threshold tuning fixes that — you just need
more labelled windows. `eval` says so explicitly when it detects this.

**Accuracy alone is misleading**, which is why it's not reported alone. During
development an earlier configuration scored *higher* accuracy (63% vs 59%) while
flagging 70% of legitimate work — high distraction recall, catastrophic study
recall. It looked better and was unusable. The per-class split is what caught it.
The two fixes that followed (skipping out-of-vocabulary tokens, and dropping
browser boilerplate like `chrome`/`google` from the tokenizer) traded a little
accuracy for balance, then thickening the seed corpus took accuracy to 82%.
The ablation is documented in the comments in `classifier.py`.

Rough guide:

- **Low distraction recall** → it's missing things. Label more distraction
  examples, or lower `classifier_threshold` in `config.json`.
- **Low study precision** → it's interrupting you while you work. Label more
  study examples, or raise the threshold.
- **Low overlap** → neither. Collect more data.

Until the model has a few hundred examples, the block and allow lists carry the
real load — they're exact matches and need no training at all.

---

## Claude fallback (optional, off by default)

**In plain words:** for the rare window the built-in guesser truly can't
decide about, you can (optionally) let it ask Claude, an AI from
Anthropic, for a second opinion — sending nothing but the window's
title, never a picture of your screen.

A fourth tier, behind everything else:

```
allowlist  →  blocklist  →  Naive Bayes (confident)  →  Claude  →  allowed
```

When the local model has no confident opinion — confidence below
`classifier_threshold` either way — that's the genuinely ambiguous case Claude
exists for. Confidently-judged windows (the vast majority) never touch it.

### Setup

**1. Get an API key.** [console.anthropic.com](https://console.anthropic.com) →
Settings → API Keys → Create Key. Copy it immediately; you can't view it again.

**2. Set it as an environment variable — never in a file.**

```powershell
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'your-key-here', 'User')
```

Or Windows Settings → search "environment variables" → Edit environment
variables for your account → New. Restart any open terminal or VS Code window
afterward.

**3. Install the SDK.**

```bat
pip install anthropic
```

**4. Turn it on.** Blocking page → "Enable Claude fallback for ambiguous
windows". The status line underneath tells you immediately if something's
missing (`no ANTHROPIC_API_KEY environment variable found`,
`anthropic package not installed`, or `ready (claude-haiku-4-5-20251001)`).

The model is `claude-haiku-4-5-20251001` — fast and cheap, which is what
"study or distraction" needs. Not user-configurable from the UI on purpose;
edit `Config.claude_model` in `config.json` if you want a different one.

### What actually gets sent

One string: the window title plus process name, e.g.
`"Overleaf thesis draft - Google Chrome chrome.exe"`. Nothing else — no
history, no other window titles, no identifying information. `test_judge_sends_only_the_window_text`
in `tests/test_claude_fallback.py` pins this down so a future edit can't
accidentally widen it.

### How it stays out of the way

- **Non-blocking.** The enforcer polls once a second; an API call is never
  fast enough to sit in that loop. `judge()` only ever peeks an in-memory
  cache — a dict read. On a cache miss, `lock_in/ui/app.py` fires a background thread and
  uses the local model's answer for *that* poll. Since a window you're on for
  one second is usually still open a second later, the real answer is
  typically ready by the next poll.
- **Cached per session.** Same ambiguous title won't be billed twice within
  `claude_cache_minutes` (default 30).
- **Teaches the local model.** Every real answer is folded into
  `observations.jsonl` as a labelled example — same mechanism `train.py` uses.
  Run `python train.py rebuild` afterward and the local model absorbs it,
  needing Claude less over time.
- **Fails silent, not broken.** No key, no package, rate-limited, network
  down, malformed reply — all of it degrades to "no opinion, allow it," never
  a crash. A misconfigured key can't turn into a broken Pomodoro timer.

---

### Why it's split this way

**In plain words:** the "thinking" parts of the app (should this be
blocked? how much time is left? was that a distraction?) are kept
completely separate from the "doing" parts (showing a window, playing a
sound, talking to Windows/Mac/Linux). That way the thinking parts can be
tested in a fraction of a second without ever opening a window, and
nothing about *what decision gets made* depends on *which computer it's
running on*.

More precisely: the five "pure logic" modules import nothing outside the
standard library. No tkinter, no Win32, no network. That's what makes the
unit test suite (run `pytest` to see the current count) run in a fraction
of a second with no display server — and it means the escalation policy,
the model, and the state machine can all be reasoned about without
booting a GUI. `claude_fallback.py` sits just outside that boundary — it
needs the `anthropic` package and, when enabled, the network — but its
own tests never make a real call; a fake client swapped into `_client`
exercises every branch offline.

Everything platform-specific is pushed into `monitor.py`, `notifier.py`, and
`lock_in/ui/`, which are deliberately thin: they perform actions and marshal data, but
make no decisions. `enforcer.py` decides that a window warrants `Action.MINIMIZE`;
`lock_in/ui/` just calls the minimise function.

**Threading.** `ActiveWindowMonitor` polls on a background daemon thread.
Tkinter is not thread-safe, so that thread does exactly one thing:
`queue.put(window_info)`. The UI thread drains the queue from an `after()` loop
and does all judging, enforcement, and widget updates. Nothing else crosses the
boundary.

```bat
pytest                                   :: runs the unit test suite
xvfb-run -a python tests/smoke_ui.py     :: end-to-end, needs a display (Linux)
:: On Windows, use a throwaway .smoke-data folder so your real settings are
:: never touched -- four separate lines (the first empties it, since
:: leftovers from an earlier run can make the test fail):
::   if exist .smoke-data rmdir /s /q .smoke-data
::   set APPDATA=%CD%\.smoke-data
::   set PYTHONPATH=.
::   python tests\smoke_ui.py
```

---

## Strict Camera Monitoring (optional, off by default)

A separate extra thing, nothing to do with Claude fallback: turn it on
and Lock In watches your webcam during a focus block. If it spots a
phone, you get warned the same way you'd get warned for opening a
blocked app -- with Hard mode on (the default), that's a minimised
window and then a full-screen lockdown right away; with it off, a
gentle nudge first, then louder -- just like already happens for
blocked apps.

### Setup

**1. Install OpenCV** (the tool that lets the app look through your webcam).

```bat
pip install opencv-python-headless
```

**2. Turn it on.** Blocking page → "Strict Camera Monitoring (uses your
webcam to catch phones)". If the switch is greyed out, the message
underneath tells you exactly what's missing.

### What actually happens to a picture from your camera

Roughly every 4 seconds during a focus block, the app grabs one
picture from your default webcam, checks it for a phone, and then
throws that picture away right away. Nothing is ever saved to your
computer, shown on screen, or sent anywhere over the internet -- this
whole feature never goes online at all. The thing it uses to recognize
a phone is built into the app itself, so it doesn't need to download
anything either.

### How it stays out of the way

- **Off unless you turn it on. One switch. Your choice.**
- **Only watches during an actual focus block.** It stops on every
  break, when the timer is idle, and the moment the session ends --
  exactly like the part of the app that blocks distracting apps.
- **The camera turns off the second monitoring pauses.** The little
  helper that recognizes phones stays ready in memory (so turning the
  switch back on doesn't have to reload anything), but the actual
  webcam turns off right away on every break, pause, or toggle-off --
  so your laptop's little camera light always matches what the app's
  own on-screen "Camera monitoring active" words say. It's never on
  when those words aren't showing.
- **If something goes wrong, it just quietly stops -- it never
  crashes.** No webcam, `opencv-python-headless` not installed, the
  camera being used by another app -- any of those just turn the
  feature off for now, with no crash and no confusing lockdown screen.

---

## 🔧 Config

Settings, the trained model, and your training data all live in
`%APPDATA%\Lock In\` — outside the project directory, so a PyInstaller build
(where the app folder may be read-only) still writes correctly.

| File | What it is |
|---|---|
| `config.json` | Every setting, pretty-printed and hand-editable |
| `model.json` | The trained classifier — plain counts, worth opening once |
| `observations.jsonl` | Windows seen during focus, one JSON object per line |
| `tasks.json` | Your task list and their checklist subtasks |
| `sessions.jsonl` | A log of every completed, skipped, or reset focus block |
| `logs/lock_in.log` | A small note of anything that went wrong (see below) |

Every one of these files is saved safely: the new copy is written into a
spare file first, then swapped in with one quick step, so a crash can
never leave a half-written file behind.

**When you edit `config.json` by hand:** every value is checked when
Lock In opens. A value that makes no sense (a focus block of -5 minutes,
a Rider that doesn't exist, a list that isn't a list) is swapped for its
normal default, and every other setting is kept. Settings from a newer
version that this one doesn't know are simply ignored.

**The log file** keeps at most three small files (about 256 KB each)
and throws the oldest away. It notes what went wrong, like an update or
the camera failing, and never what you were doing: no window titles, no
task names, nothing you typed, and nothing sent to the Claude helper. If
you ever need more detail to track a problem down, start Lock In with
the setting `LOCKIN_DEBUG_LOG=1`; it's off unless you turn it on.

Deleting any of them regenerates it. Deleting `model.json` costs you nothing if
your labels are still in `observations.jsonl` — just run `python train.py
rebuild`. Deleting `observations.jsonl` is the one that actually loses work, so
`train.py export` it first if you've put real time into labelling.

Recording can be switched off entirely (Blocking page → "Record windows for
training"). Nothing ever leaves your machine either way — except, if you've
opted into it, the Claude fallback's ambiguous-window titles (see above).

`ANTHROPIC_API_KEY` lives in your OS environment, never in any of these files.
`config.json` only stores whether the fallback is *enabled* and which model to
use — never the key itself.

---

## Known limits

- **Windows, macOS, and Linux are all supported**, though Windows has the
  most mileage. macOS minimizing simulates Cmd+M via System Events, which
  needs Accessibility permission — macOS prompts for it the first time
  blocking tries to act. Linux detection and minimizing need `xdotool`
  installed and an X11 session — there's no Wayland equivalent, so
  blocking silently can't minimize windows under Wayland (detection still
  works). Toasts and sounds use `notify-send`/`paplay`/`aplay` on Linux
  and `osascript`/`afplay` on macOS, falling back to the in-app banner if
  those tools aren't present, exactly like the Windows toast falls back
  when `winotify` isn't installed.
- **Browser tabs are one window.** The title tells you the *active* tab, so a
  YouTube tab sitting in the background won't be flagged. Catching that needs a
  browser extension, which is a separate build.
- **Nothing survives task-killing the app.** By design.
- **The model needs data before it's much use.** Out of the box it knows the
  seed corpus and not your habits. The block and allow lists work perfectly from
  minute one; the classifier is the part that earns its keep over a few weeks.
- Strict Camera Monitoring only looks through your main, default webcam --
  no picker for a second camera, and no setting to change how often it
  checks or how sure it needs to be.
- If the camera stops working partway through a focus block (unplugged,
  grabbed by another app), monitoring just quietly stops until the next
  focus block, instead of trying to fix itself right away.
- **Tasks can't be deleted or un-marked done from the app yet** — once
  something is checked off, hiding it again means editing `tasks.json`
  by hand. That's on the list for later.
- **Fixing the session diary only works with Zi-O picked** — the History
  page can change a block's task or delete it, but it can't change when a
  block started or how long it was. Once you delete a block there's no
  undo.
- **The Board can only move a task forward** — the arrow on a Blade Board
  note goes To Do → In Progress → Done. There's no dragging, and no arrow
  to send a note back.
- **W only compares two fixed weeks** — the last 7 days against the 7
  days right before them. There are no buttons to pick other weeks.
- **Geats judges every day by the goal you have now** — there is one
  goal number, not a different one for each day. Making the goal bigger
  can make your streak shorter, and making it smaller can make it longer.
- **Gotchard's badges are yours to keep, forever** — even if you delete a
  focus block in Zi-O or change your goal on Geats' page afterward. That
  also means a very small daily goal makes the streak badges quick to
  win, on purpose — the goal is yours to set however you like.
- **Only Geats can change the daily goal** — Gotchard's Badges page has no
  goal buttons of its own; it just reads whatever goal is set.
- **The update check proves the download is complete and unchanged, not
  who made it.** The fingerprint file comes from the same GitHub release
  as the download. It catches a download that was cut short or altered
  on the way. It would not catch someone who took over the GitHub
  account itself and replaced both files. A signed release (with a
  private key only the author holds) would cover that, and is a
  possible later step.
- **Screen-code tests are mostly by hand.** About 83% of the non-screen
  code is covered by the automatic tests, but only about a third of
  the screen code. The rest is checked by `tests/smoke_ui.py` (which
  opens the real window) and by looking at the app.
- **Auto-update only replaces the downloaded app** — a source checkout
  (`python main.py`) shows the same "update available" note but needs
  `git pull` instead of a restart button.

---

## 🎓 Credits & Professional Attributions

This is a personal project built for learning and portfolio purposes.
**Kamen Rider**, the names of all 38 series referenced in the theme
picker, and all associated characters and likenesses are trademarks of
**Ishimori Productions** and **TV Asahi**. They're used here strictly as
color and flavor-text inspiration for a personal productivity tool, with
no commercial intent — no official footage, artwork, or trademarked
imagery is bundled with this app or its source. Every visual element
(the side bar pictures, the era strip, the progress shapes, the
app-icon padding) is drawn at runtime from plain hex color codes in
`lock_in/visuals.py` and `lock_in/ui/icons.py`, not from any
copyrighted asset.

The app icon (`lock_in/assets/app_icon.png`) was supplied by the
project's author.

---

## Security

Found a security issue? Please don't open a public issue for it — see
[SECURITY.md](SECURITY.md) for how to report it privately.

---

## License

MIT — see [LICENSE](LICENSE).
