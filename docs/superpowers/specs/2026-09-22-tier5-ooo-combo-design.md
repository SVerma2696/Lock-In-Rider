# Lock In: Tier 5 Rider #9 — OOO, the Combo tab

Date: 2026-09-22
Status: Approved

## Goal

The ninth of Tier 5's 10 Riders, built on the shared `tier5_effect` /
`lock_in/tier5/` plumbing that V3, Den-O, Decade, Zi-O, Blade, W, Geats,
and Gotchard already established. OOO's show is about three medals
(Head, Arms, Legs) combining into a "Combo." OOO's tab borrows that idea
in plain words: every open task gets three fixed checkboxes,
**Plan / Work / Review**, and checking all three shows a small "Combo
formed!" mark next to that task.

When Kamen Rider OOO (2010) is the picked Rider, a **"Combo"** tab shows
every open task (To Do and In Progress) as a card with its name and the
three checkboxes.

This is a different, smaller idea than two things that already exist,
on purpose:

- **The Tasks tab's subtask checklist** is freeform — any number of
  items, any wording, written by hand. OOO's three boxes are fixed:
  always exactly three, always the same three names, on every task.
- **Blade's Board** moves a whole task between three *columns*
  (To Do / In Progress / Done) — one task, one column at a time. OOO's
  three boxes are three things checked *inside* one task, all at once if
  you like, and checking them never moves or finishes the task.

## The rule

Decided during brainstorming.

- **Checking all three boxes never finishes the task.** The existing
  rule in `tasks.py` — a task is only ever marked done by your own click
  on the Tasks tab — is not touched. All three checked just changes how
  the card looks (see "The tab" below); the task keeps sitting in To Do
  or In Progress exactly as before.
- **Un-checking works the same as checking.** Every box is a toggle, so
  a "Combo formed!" card can go back to a plain card if you change your
  mind.
- **A brand new task starts with all three unchecked.**
- **A task's three boxes have no order.** You can check Review before
  Plan. Nothing is locked or graduated.

## The tab

Tab label **"Combo"**; `Kamen Rider OOO (2010)` gets
`tier5_effect="phase_combo"`. The tab sits next to Help like every other
Tier 5 tab, and is hidden by Standard Mode and by picking a non-Tier-5
Rider through the existing mechanism (no new code for that).

Layout, top to bottom, inside a `CTkScrollableFrame` (matching every
other tab):

1. **One card per open task** (`tasks.open()`, same list and same order
   the Tasks tab itself uses — task creation order). Each card:
   - The task's name, left-aligned.
   - Three checkbox buttons in a row, labelled `Plan`, `Work`, `Review`.
     Clicking one flips just that box and re-draws that one card in
     place (see `build()` below) — it never rebuilds the whole tab.
   - When all three are checked: a small `⭐ Combo formed!` line under
     the name, in `theme.secondary`. Not checked: nothing shown there
     (no placeholder text, so a plain card and a "getting there" card
     both look calm).
2. **Empty state.** No open tasks at all: one line,
   `"No open tasks yet. Add one on the Tasks tab."` — no cards, no
   checkboxes.
3. **Caption**, same small gray style as every other tab's caption:
   `"Plan, Work, Review — check them in any order. A full combo is just for fun; you still mark the task itself done on the Tasks tab."`

`history` and `appearance_mode` are part of every Tier 5 builder's
signature. OOO uses neither — it reads only `tasks`, the same posture
Blade already has toward `history`.

## Colors

OOO's `primary` is near-black in light mode / gray in dark mode, and
`secondary` is red (see `rider_themes.py`). So:

- **Task name and box labels:** `theme.primary_text_pair`.
- **A checked box:** filled with `theme.secondary`. An unchecked box:
  CustomTkinter's normal button look, so "checked" is unmistakable in
  both modes without needing a checkmark glyph to render correctly on
  every OS font.
- **The "Combo formed!" line:** `theme.secondary` text, matching the
  filled-box color so the two visually agree.

Both modes are checked by eye in the running app.

## New code

### `lock_in/tasks.py` (one new field, one new method)

- **`Task.phases: List[bool] = field(default_factory=lambda: [False, False, False])`**
  Always exactly three entries, index 0 = Plan, 1 = Work, 2 = Review.
  Placed on `Task` (not `Config`), since it is per-task state, the same
  reasoning that put `status` and `subtasks` on `Task` rather than
  anywhere global.
- **`TaskStore.load()`**, extended the same defensive way `subtasks` is
  already built: read `item.get("phases", [False, False, False])`;
  coerce to a plain list of `bool()` of each entry; if the result is not
  a list of length exactly 3 once coerced (wrong type, wrong length,
  garbage from hand-editing `tasks.json`), fall back to
  `[False, False, False]` rather than raising or truncating oddly. One
  bad task's `phases` never costs you the rest of the file — same
  posture as the existing malformed-subtask handling.
- **`TaskStore.toggle_phase(task_id: str, index: int) -> bool`**
  Flips `phases[index]` and saves immediately, mirroring
  `toggle_subtask()` exactly. Returns `False` (no save, no crash) if
  `task_id` doesn't exist or `index` is not `0`, `1`, or `2` — the same
  bounds-checked-return-False posture `toggle_subtask` already has for a
  missing subtask id.

### `lock_in/tier5/ooo.py` (new)

One small pure function, tested with no Tk and no display server, plus
the one Tk-dependent `build()`:

- **`combo_formed(phases: list[bool]) -> bool`**
  `all(phases)`. Pulled out as its own function (rather than an inline
  `all(...)` in `build()`) purely so it is unit-testable the same way
  every other Tier 5 Rider's small logic is, matching the project's
  established pattern of keeping `build()` as thin as possible.
- **`build(parent, *, history, tasks, theme, appearance_mode, config) -> None`**
  Builds the tab described above. Every card and its three buttons are
  built once; clicking a box calls `tasks.toggle_phase(...)` and then
  re-configures just that card's three button colors and the
  "Combo formed!" line — no destroy-and-rebuild of the whole tab from
  inside a click, the same safety rule Geats' buttons and Gotchard's
  cards already follow.

`ooo.py` imports only from `customtkinter` and (for text-color pairs)
the `theme` object it's handed — no import from `_shared.py` is needed,
since none of `_shared.py`'s day-math or formatting helpers apply here.

### `lock_in/ui.py` (small)

- `_TIER5_TAB_LABELS` gains `"phase_combo": "Combo"`.
- The tab build, the refresh after a finished block, and the show/hide
  logic already handle any registered effect and need no change.
- Help tab: add an OOO bullet.

### Wiring summary

- `lock_in/tier5/__init__.py`: `TIER5_BUILDERS["phase_combo"] = ooo.build`,
  plus `ooo` in the import line.
- `lock_in/rider_themes.py`: `tier5_effect="phase_combo"` on
  `Kamen Rider OOO (2010)`, and the Rider count in the field's comment.
- No new file on disk: `phases` lives inside the existing `tasks.json`.

## Error handling

- No open tasks: the empty-state line, no cards.
- A hand-edited `tasks.json` with a broken `phases` value on one task:
  that task falls back to `[False, False, False]` and loads normally;
  every other task is unaffected (see `TaskStore.load()` above).
- `toggle_phase()` given a bad `task_id` or an out-of-range `index`:
  returns `False`, changes nothing, no crash. `build()` never calls it
  with an out-of-range index (the three buttons are wired to `0`, `1`,
  `2` literally), so this path only matters if something else on the
  Task model changes later.
- A task completed or deleted while the Combo tab is open: the tab
  redraws from `tasks.open()` on the next rebuild (a finished block,
  switching tabs, or reopening the app), the same refresh timing every
  other Tier 5 tab already has. A completed task's card simply stops
  appearing; its `phases` value stays in `tasks.json`, unused, exactly
  like a done task's `subtasks` already do.

## Testing

- `tests/test_tasks.py` *(grows)*:
  - A new `Task` defaults to `phases == [False, False, False]`.
  - `toggle_phase()` flips exactly the given index and saves; a second
    call flips it back; an out-of-range index and a missing task id both
    return `False` and change nothing.
  - Loading a `tasks.json` with `phases` missing, `phases` of the wrong
    length, `phases` holding non-boolean values, and `phases` as a
    non-list all fall back to `[False, False, False]` without dropping
    the task or any sibling task.
  - A saved task's `phases` round-trips through save/load unchanged.
- `tests/test_tier5_ooo.py` *(new)*:
  - `combo_formed()`: all three `True` is `True`; any mix with at least
    one `False` is `False`; all three `False` is `False`.
- `tests/test_rider_themes.py` *(grows)*: the tier5 completeness check
  now expects nine Riders, adding
  `"Kamen Rider OOO (2010)": "phase_combo"`. The test is renamed to say
  nine.
- **Manual, in the running app** (same as every other tab, no automated
  GUI test): the "Combo" tab appears only for OOO; a brand new task shows
  three unchecked boxes; checking all three shows "Combo formed!";
  un-checking one hides it again; a task finished on the Tasks tab drops
  off the Combo tab; a task deleted from the Tasks tab drops off too and
  doesn't error; light and dark mode both read clearly; the other eight
  Tier 5 tabs still open and look right.

## Docs, version, and repo hygiene

- `README.md`, two small edits: an **OOO** bullet in the Tier 5 section
  in the same plain words, and "these eight are just the first of ten
  planned" becomes "nine of ten."
- `lock_in/ui.py`, Help tab: as above.
- `__version__`: bumped alongside MY-TH in the same release (see that
  spec / the implementation plan for the exact number).
- `.gitignore`: OOO creates no new file (`phases` lives in the existing
  `tasks.json`, which is already ignored). No change is expected; it is
  re-checked when this ships.
- Project files describe the software only: nothing about who or what
  wrote them, and commit messages carry no trailer or credit line.
- Committing, pushing, and tagging are done by the project owner. The
  exact commands are handed over at the end, with a plain commit message.

## Out of scope for this pass

- Naming your own phases, or a different number of phases per task.
- Any reward, sound, or animation when a combo forms — just the text
  line.
- A combo "breaking" if you later uncheck a box on a task you'd already
  marked done — done tasks simply stop appearing on this tab at all.
- Gotchard-style permanent badges for forming combos (Gotchard's badges
  are their own separate, already-shipped system and are not extended
  here).
- The tenth Tier 5 Rider, MY-TH, which gets its own spec.

## File-by-file change list

**New**
- `lock_in/tier5/ooo.py`: `combo_formed()`, `build()`.
- `tests/test_tier5_ooo.py`.
- `docs/superpowers/plans/2026-09-22-tier5-ooo-combo.md`: the
  implementation plan (written after this spec is approved).

**Edit**
- `lock_in/tasks.py`: `Task.phases`, `TaskStore.load()`,
  `TaskStore.toggle_phase()`.
- `lock_in/tier5/__init__.py`: one registry entry.
- `lock_in/rider_themes.py`: `tier5_effect="phase_combo"` on OOO, and the
  comment count.
- `lock_in/ui.py`: `_TIER5_TAB_LABELS` entry, Help tab bullet.
- `tests/test_tasks.py`, `tests/test_rider_themes.py`: as described above.
- `README.md`: Tier 5 bullet, count wording.
