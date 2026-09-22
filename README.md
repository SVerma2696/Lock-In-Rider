# Lock In 🎭⏱️

**In one sentence:** Lock In is a work timer that notices when you drift
off to Discord or YouTube during a focus block, and gently — then not so
gently — nudges you back to work.

You pick how long you want to focus for, hit Start, and get to work. If
you open something distracting, Lock In notices and says something about
it. Ignore it for too long and it gets louder, then it minimizes the
distracting window for you, then (if you've turned on "hard mode") it
covers your whole screen until you get back to work. It's built so
leaving a focus block is always something you *decide* to do, not
something that just quietly happens.

Under the hood it's also a hand-built "is this study or is this a
distraction" learning system (no external AI library, so you can read
every line of how it decides), a 38-theme costume-changer for the app's
whole look, and a program that works the same way on Windows, Mac, and
Linux — three things the author built this project to learn by doing.

---

## 🚀 Releases

Don't want to install anything? Every tagged version (`vX.Y.Z`) is built
automatically for Windows, macOS, and Linux by a robot
([`.github/workflows/release.yml`](.github/workflows/release.yml)) and
published here:

**➡️ [Download the latest release](https://github.com/SVerma2696/Lock-In-Rider/releases/latest)**

Pick the file for your computer, download it, unzip/extract it (it comes
as a `.zip` on Windows/macOS or a `.tar.gz` on Linux), then open the app
inside. No Python, no `pip install`, no commands — just double-click it.

Your computer will probably show a warning the very first time you open
it. That's normal, not a sign anything is wrong — here's exactly what
each one means and the one-time click to get past it:

**Windows: "Windows protected your PC"**
This shows up because the app isn't signed with a paid certificate (those
cost money every year, and this is a free personal project) — it doesn't
mean the app is unsafe. Click **More info**, then **Run anyway**. It only
asks once per download.

**macOS: "cannot be opened because it is from an unidentified developer"**
Same idea as the Windows warning, macOS's version of it. Instead of
double-clicking, **right-click (or Control-click) the app → Open →
Open**. If that doesn't show an "Open" button, go to **System Settings
→ Privacy & Security**, scroll down, and click **Open Anyway** next to
the app's name. Also only asks once.

**Linux: "Permission denied"**
The downloaded file isn't marked as "allowed to run" yet — a normal
Linux safety default for any new file, not specific to this app. In a
terminal, in the folder where you extracted it:
```bash
chmod +x "Lock In"
./"Lock In"
```

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

**Want to ask right now?** Open the Settings tab and press **Check for
updates now**. The app asks GitHub right then and tells you, in a short
sentence right under the button, what it found:

- "You already have the newest Lock In" — nothing to do.
- "Found Lock In v… Press Restart now at the top" — the same notice and
  Restart button as above just appeared.
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
- Turn the automatic check off anytime: Settings tab → "Automatically
  check for updates." The "Check for updates now" button right under it
  still works when you want it.
- Only works for the app downloaded from Releases. Running it from
  source (`python main.py`)? Use `git pull` instead — you'll still see
  a small "update available" note, just without the restart button.

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
  its own over time. First it's just a gentle notification. Keep
  ignoring it and it gets louder, then it minimizes the window for you,
  then — if you've turned on "hard mode" — it covers your whole screen
  until you're back on track.
* **Learns your habits.** It watches which windows you open while
  focusing and slowly learns what counts as "working" for *you*
  specifically, not some generic list. You can correct it with one click
  any time it gets something wrong, and it learns from that instantly.
  No outside AI service is needed for this part — it's small enough to
  read and understand the whole thing yourself.
* **38 Kamen Rider costume changes.** Pick a Rider from the classic TV
  show and the whole app repaints itself in that Rider's colors — not
  just an accent color, but the header, every tab, the progress bar, and
  the background. **26 of those Riders unlock an extra surprise on top**
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

Already got the app from [Releases](#-releases) above? You can skip this
part — it's just a map of the code, file by file, for anyone curious how
it's organized under the hood.

```
Lock In/
│
├── main.py                     Entry point. Checks dependencies, launches the UI.
├── train.py                    Training CLI (record / label / rebuild / eval / …).
│
├── lock_in/                    The application package.
│   ├── __init__.py             Marks this folder as a package.
│   │
│   │   ── pure logic, stdlib only, fully unit-tested ──
│   ├── config.py               Settings dataclass, JSON persistence, block/allow
│   │                           defaults, and the %APPDATA% path resolution.
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
│   ├── history.py               The diary of every completed, skipped, or reset
│   │                           focus block, saved as sessions.jsonl. Each block
│   │                           has its own id so Zi-O can fix or delete it.
│   ├── rider_themes.py         Kamen Rider color palettes for the theme toggle.
│   ├── visuals.py               Display font pick, plus Pillow-generated glow,
│   │                           background art, and app-icon loading.
│   ├── updater.py               Pure version-compare/asset-pick logic for
│   │                           auto-update, plus the plain-words answer the
│   │                           "Check for updates now" button shows
│   │                           (no network, no filesystem).
│   ├── assets/
│   │   └── app_icon.png         The app's own picture — window/taskbar icon
│   │                           and notification icon.
│   │
│   │   ── platform-facing shells, thin by design ──
│   ├── monitor.py              Foreground-window polling on a daemon thread.
│   │                           Win32 backend, macOS (osascript), Linux (xdotool).
│   ├── notifier.py             Toasts and sounds: winotify/winsound (Windows),
│   │                           osascript/afplay (macOS), notify-send/paplay (Linux).
│   ├── update_fetch.py          The one network call in auto-update: asks GitHub
│   │                           for the latest release, downloads the matching file.
│   ├── update_apply.py          Unpacks the downloaded release and writes/launches
│   │                           the per-OS relaunch script that swaps files.
│   └── ui.py                   CustomTkinter front end. The only module that
│                               imports tkinter.
│
├── tests/
│   ├── test_session.py         State machine: transitions, pause, skip, formatting,
│   │                           and both wording voices' phase labels.
│   ├── test_classifier.py      Tokenizer, prediction, online learning, persistence.
│   ├── test_enforcer.py        Rule precedence, full escalation ladder, decay,
│   │                           per-era and per-wording notification copy,
│   │                           cross-platform process matching.
│   ├── test_observations.py    De-duplication, labelling, JSONL round-trip.
│   ├── test_tasks.py            Add/edit/complete tasks and subtasks, JSON round-trip.
│   ├── test_history.py          Recording, filtering by day/task, JSONL round-trip,
│   │                           block ids, and changing/deleting a block.
│   ├── test_claude_fallback.py Caching, async lookup, failure handling — no
│   │                           real network calls, a fake client stands in.
│   ├── test_rider_themes.py    Palette completeness, color validity, dark-mode
│   │                           shade generation, contrast-safe text colors.
│   ├── test_visuals.py         Font lookup, glow shape/fade, per-era background
│   │                           and divider differences, light/dark contrast,
│   │                           app-icon loading/padding.
│   ├── test_notifier.py        Era-to-sound-cue selection logic (Windows tones,
│   │                           macOS/Linux sound tables).
│   └── smoke_ui.py             Headless end-to-end run under Xvfb (not pytest).
│
├── .github/workflows/
│   ├── tests.yml               Runs pytest on Windows, macOS, and Linux on every push.
│   └── release.yml             Builds and publishes installers on a version tag.
│
├── requirements.txt
├── pytest.ini
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

### 3. Run it
```bat
python main.py
```
Or double-click `run.bat` (launches with `pythonw`, no console window).
To produce a standalone `.exe`, run `build.bat` — or just grab a
[prebuilt release](#-releases) for your OS instead of building from
source.

Once it's open, the app's own **Help tab** has a full, plain-language
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
red banner on startup, and a note on the Blocking tab, if it can't detect
windows — but it's worth checking directly if you're not sure.

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
Action  -> Notifier (toast + sound) and ui.py    -> banner / full-screen lockdown
```

### Training loop
```
Every window seen during focus -> ObservationStore (observations.jsonl)
Corrections (Activity tab, or `train.py label`) -> NaiveBayesClassifier.learn() -> model.json
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

**Soft mode (default — Hard mode off):**

| Time on the app | What happens |
|---|---|
| 0–8s | Nothing. You might be closing it. |
| first strike | Toast notification. |
| every strike after that | Toast + alert sound. |

**Hard mode (Blocking tab → "Hard mode"):** no warnings first — it acts
immediately, since the whole point of turning this on is that you don't
want to be asked nicely.

| Time on the app | What happens |
|---|---|
| 0–8s | Nothing. You might be closing it. |
| first strike | Window minimised, timer pulled to the front. |
| every strike after that | Full-screen cover for 15 seconds. |

Strikes decay after 45 seconds of clean work, so one slip at minute 3 doesn't
leave you one click from a screen takeover at minute 20. Hopping between two
blocked apps restarts the grace period but *keeps* your strikes — app-hopping
to dodge the nag isn't a valid strategy.

All timings are configurable in the Settings tab.

### If a window's program name can't be read

A few programs (Steam is a common one, when it's running "as administrator")
hide their process name from a program that isn't also elevated. When that
happens, Lock In still checks the *window's title text* for the name of a
listed program before falling back to the guessing model — so `steam.exe`
being on the block list still catches a window titled "Steam" even if we
never learned its process name. If blocking still doesn't seem to be working
at all, check the Blocking tab: if it says "App detection unavailable" (or
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
- **Privacy.** Nothing leaves your machine. An app you run *all day while
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

- **Adding a task.** The Tasks tab has a plain text box — type a name,
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

Nothing here is sent anywhere; both files stay on your machine right
next to `config.json` (see [Config](#-config) below).

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
This isn't just a couple of small accents — the header panel, the tab
bar, and every tab's content panel are tinted toward the Rider's primary
color too, along with the Henshin/Start button, the selected-tab
highlight, the timer digits/progress bar during a focus block, and the
Rider name shown under the timer. The fixed per-section colors (pink for
Claude fallback, teal for sound/notification settings, and so on) stay
as they are, since those work like a legend to tell sections apart
regardless of theme. Defaults to the original 1971 series. See
`lock_in/rider_themes.py` for the full palette.

Picking a Rider also picks its **era**, and — when Wording is set to
Tokusatsu — the era changes more than color, too:

| | Showa (1971–1994) | Heisei (2000–2019) | Reiwa (2019–present) |
|---|---|---|---|
| **Voice** | Blunt base-alarm ("Intruder Alert", "Base Lockdown") | Tactical mission briefing ("Off Mission", "Full Lockdown") | Crisp digital system alert ("Focus Breach", "System Lockdown") |
| **Background pattern** | Faint scanlines + film grain | Diamond-facet grid, like a cut gem | Circuit-board grid of lines and node dots |
| **Divider strip** | Tick marks, like a gauge | A row of tiny diamonds | A dashed line with square nodes |
| **Sound cue** | A plain two-tone alarm | The original beep sequence this app shipped with | A quicker, higher-pitched digital-sounding sequence |

In Professional wording, the Voice column above doesn't apply — there's
one plain voice for every era. The background pattern, divider strip,
and sound cue still vary by era either way. Heisei is the fallback
voice/pattern/sound if the app is ever handed a Rider name it doesn't
recognize, so nothing crashes on a corrupted `config.json`. All three
eras of tokusatsu copy live in `lock_in/enforcer.py` (`MESSAGES_BY_ERA`),
the patterns in `lock_in/visuals.py`, and the sound tables in
`lock_in/notifier.py`.

### Tier 0: Standard Mode (no Rider flavor at all)

Settings → "Standard Mode" is a single switch, independent of which
Rider is picked below it. Turning it on swaps in a plain slate-grey and
blue palette, turns off every Tier 1/2/3 Rider gimmick, forces Wording
to Professional, and replaces every piece of Pillow-rendered art (the
timer/button glow, the background wallpaper, the divider strip) with a
flat, patternless fill — the same rendering pipeline, just fed a
neutral color and no texture, which is what makes it the lightest,
fastest-drawing look in the app. Your actual Rider and Wording choices
are never overwritten; turning Standard Mode back off restores both
instantly.

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
- **Stronger** — a soft red glow builds around the outer window edge as
  the block goes on, like charging up electricity.
- **Kiva** — a translucent amber wash tints the whole app during a focus
  block, evoking its night/vampire motif.
- **Agito** — the progress bar's color starts muted and gradually
  brightens to its true gold, like a dormant power waking up.
- **Black** — dark mode gets stricter, higher-contrast text specifically
  for this Rider.
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

Three more Riders add controls to the Settings tab itself, above the
Timer lengths section:

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
  solid draining green field (Pause/Skip/Reset shrink to icons instead
  of disappearing), and the grace period drops to 0 seconds.
- **ZX** — the whole app renders in monochrome for as long as ZX is
  selected, and auto-minimizes the moment a focus block starts, with
  Sounds and Desktop notifications silenced for that block.
- **Gaim** — during a focus block, the window stays always-on-top, the
  background dims, and a padlock appears — a strong visual deterrent,
  never a real block on switching windows.
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
- **Ryuki** — the whole window flips left-to-right during breaks and flips back
  when focus starts again.
- **Kabuto** — the timer digits hide while you focus; hover to peek at the
  real time.
- **Ex-Aid** — the timer switches to a pixel font and the alert sound becomes
  an 8-bit jingle.
- **Hibiki** — soft ambient background sound plays for the whole focus block.
- **Zero-One** — the timer changes into a row of dashboard cards instead of
  centered digits.
- **Ghost** — the main window hides and a small floating clock stays on top of
  everything; click it to bring the full window back.
- **Zeztz** — keyboard shortcuts take over: Space to start/pause, S to skip,
  R to reset.

One more, Saber, joins the Tier 1 progress-bar list instead — its
bookmark-ribbon shape uses the same drawing code as Fourze and Build.

### Tier 5: Riders that read your own history

A new kind of Rider gimmick, separate from every tier above: picking one
of these Riders adds a whole new tab next to Help, built from your own
tasks and past focus blocks instead of just changing colors, sounds, or
behavior.

- **V3** — adds an "Hours" tab: a big number showing how long you've
  focused today, plus a simple bar chart of the last 14 days. Every
  block counts toward it, whether you finished it, skipped it, or reset
  it early.
- **Den-O** — adds a "Timeline" tab: one day's focus blocks at a time,
  earliest first, with buttons to flip a day forward or back. Each block
  shows its time, how long it ran, whether it finished naturally or got
  cut short, and which task (if any) it was for.
- **Decade** — adds an "Analytics" tab: a 30-day version of V3's bar
  chart, plus your top 10 tasks ranked by how much total time you've
  spent on each.
- **Zi-O** — adds a "History" tab. It shows the same day-by-day list as
  Den-O, but now you can fix mistakes. Every block has a little menu for
  picking a different task, and a Delete button. Delete asks you to tap
  twice ("Delete", then "Really delete?") so you can't do it by
  accident, and there's no pop-up. Only the task can change; when the
  block started, when it ended and how long it was stay exactly as the
  timer measured them.
- **Blade** — adds a "Board" tab: your tasks as three columns, To Do, In
  Progress and Done, like sticky notes on a wall. Each note has a small
  arrow button that moves it one column over. It shows the same tasks as
  the Tasks tab, so a move on the Board shows up there too.

- **W** — adds a "Week" tab. It puts two weeks side by side: the last 7
  days, and the 7 days right before them. You see one total for each, a
  short sentence that says which one is bigger, and a chart with two
  bars for every day, one for last week and one for this week. Every
  block counts, finished or not.

- **Geats** — adds a "Goal" tab. You pick how many minutes you want to
  focus each day with a minus and a plus button (each press is 15
  minutes, and the app remembers your pick). A bar fills up as you
  focus, and a streak counts how many days in a row you reached your
  goal. Seven little boxes show the last 7 days, filled in for the days
  you made it. Every block counts, finished or not.

More Riders will read your tasks and history this way over time — these
seven are just the first of ten planned.

### Look and feel

`lock_in/visuals.py` generates the app's art at runtime with Pillow, tinted
to whichever Rider is picked:

- **A display font** for the timer digits and headings, instead of the
  toolkit's plain default — a different one per OS (`Bahnschrift` on
  Windows, `Avenir Next` on macOS, `Noto Sans` on Linux), falling back
  quietly to the system default if that font isn't installed.
- **A soft glow** behind the timer digits (the Rider's primary color) and
  behind the Henshin button (its secondary color).
- **A faint background wallpaper** behind the whole window, tinted with
  both of the Rider's colors and shaped by its era (see the table above),
  with separate light- and dark-mode versions so it never fights with the
  appearance-mode setting.
- **Tinted panel backgrounds** (`RiderTheme.surface_pair` in
  `lock_in/rider_themes.py`) for the header and every tab — a pale and a
  near-black shade of the same primary color, so the panels themselves
  change with the theme instead of staying a fixed neutral grey.
- **A themed divider strip** in the gap between the timer panel and the
  tab panel. The background wallpaper's patterns are too large to show
  up in a strip that thin, so this is its own small-scale motif per era:
  tick marks for Showa, tiny diamonds for Heisei, a dashed circuit trace
  for Reiwa (`make_panel_divider()` in `lock_in/visuals.py`).

**Contrast safety.** A Rider's `primary`/`secondary` are also used
directly as *text* colors in a few places (the phase name and timer
digits, the Rider name label, the Henshin button, the selected tab).
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
`ui.py`'s `_set_app_icon()`).

---

## Training it

There are three ways in, in increasing order of how much data they get you.

### 1. The correction buttons

The Activity tab logs **every** window seen during a focus block, not just
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

**4. Turn it on.** Blocking tab → "Enable Claude fallback for ambiguous
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
  cache — a dict read. On a cache miss, `ui.py` fires a background thread and
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
`ui.py`, which are deliberately thin: they perform actions and marshal data, but
make no decisions. `enforcer.py` decides that a window warrants `Action.MINIMIZE`;
`ui.py` just calls the minimise function.

**Threading.** `ActiveWindowMonitor` polls on a background daemon thread.
Tkinter is not thread-safe, so that thread does exactly one thing:
`queue.put(window_info)`. The UI thread drains the queue from an `after()` loop
and does all judging, enforcement, and widget updates. Nothing else crosses the
boundary.

```bat
pytest                                   :: runs the unit test suite
xvfb-run -a python tests/smoke_ui.py     :: end-to-end, needs a display
```

---

## Strict Camera Monitoring (optional, off by default)

A separate extra thing, nothing to do with Claude fallback: turn it on
and Lock In watches your webcam during a focus block. If it spots a
phone, you get warned the same way you'd get warned for opening a
blocked app -- first a gentle nudge, then louder, and (if you've also
turned on hard mode) eventually a full-screen lockdown, just like
already happens for blocked apps.

### Setup

**1. Install OpenCV** (the tool that lets the app look through your webcam).

```bat
pip install opencv-python-headless
```

**2. Turn it on.** Blocking tab → "Strict Camera Monitoring (uses your
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

Deleting any of them regenerates it. Deleting `model.json` costs you nothing if
your labels are still in `observations.jsonl` — just run `python train.py
rebuild`. Deleting `observations.jsonl` is the one that actually loses work, so
`train.py export` it first if you've put real time into labelling.

Recording can be switched off entirely (Blocking tab → "Record windows for
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
  tab can change a block's task or delete it, but it can't change when a
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
(glow, background pattern, divider strip, app-icon padding) is generated
at runtime from plain hex color codes in `lock_in/visuals.py`, not from
any copyrighted asset.

The app icon (`lock_in/assets/app_icon.png`) was supplied by the
project's author.

---

## Security

Found a security issue? Please don't open a public issue for it — see
[SECURITY.md](SECURITY.md) for how to report it privately.

---

## License

MIT — see [LICENSE](LICENSE).
