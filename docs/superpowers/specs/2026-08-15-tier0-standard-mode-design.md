# Lock In: Tier 0 — Standard Mode (the baseline)

Date: 2026-08-15
Status: Approved, ready for implementation plan

## Goal

Tier 0 of the larger 38-Rider project (Tiers 1-3 shipped in
v2.0.0-v2.2.0). Unlike every other tier, this isn't a Rider gimmick —
it's a single app-wide "kill switch" that strips all Kamen Rider
flavor (colors, art, and every Tier 1/2/3 gimmick) down to a plain,
fast, generic productivity timer, for anyone who wants Lock In without
any tokusatsu theming at all.

One item, and nothing else: **Standard Mode.**

## Why an override switch, not a 39th theme-dropdown entry

Considered adding "Standard" as an entry in `RIDER_THEMES` itself,
selectable exactly like any Rider. Rejected: it would overwrite
`config_obj.rider_theme` when picked, silently forgetting your actual
favorite Rider until you reselect it by name, and it plants a
non-Kamen-Rider entry inside a dict whose own docstring says it's "a
big list of Kamen Rider costume colors."

Instead, Standard Mode is a `Config`-level override switch, the same
non-destructive read-side pattern already established three times
(Gavv's `micro_sprint_mode`, Amazon's `zero_grace_mode`, ZX's
`stealth_mute_mode`): a new `standard_mode: bool` field that changes
what gets *read*, never what gets *stored*. `rider_theme` and
`terminology` are untouched the whole time — turning the switch back
off needs no restore logic, because the real values were never
overwritten.

## The rendering intercept

`_apply_rider_theme()` is already the single choke point every Tier
1/3 gimmick reads from (`self.current_tier1_effect`,
`self.current_tier3_effect`, both set exactly once, there). When
`self.config_obj.standard_mode` is `True`, that method:

- substitutes a new `STANDARD_THEME` constant (see below) for whatever
  Rider is actually selected,
- forces `self.current_tier1_effect = "none"` and
  `self.current_tier3_effect = "none"` outright — this alone disables
  all 9 Tier 1 visual gimmicks and all 5 Tier 3 behaviors, since every
  one of them (and every future Tier 1/3 Rider added later) already
  keys off just those two attributes. No teardown code needed per
  gimmick, now or in the future.
- skips the Kuuga/Super-1/Gavv preset-button block in the Settings tab
  entirely (that block already only runs inside an `if
  self.config_obj.rider_theme == "..."` chain — wrap the whole chain
  in `if not self.config_obj.standard_mode`).

Nothing about *how* Tier 1/2/3 gimmicks work changes — Standard Mode
never has to know Kuuga's presets exist, or that 555 has a code-entry
field. It just makes the one flag they all already check come back
`"none"`/absent.

## Palette

A new `STANDARD_THEME` module-level constant in `rider_themes.py`,
built from the same `RiderTheme` dataclass every Rider uses — so
`surface_pair`, `primary_text_pair`, `secondary_text_pair`,
`button_text_pair`, and every contrast-safety guarantee already tested
in `tests/test_rider_themes.py` apply to it for free, with zero
duplicated color math. Declared **next to**, not inside,
`RIDER_THEMES`, with a comment explaining it's not a Kamen Rider.

- **Primary (slate grey):** `#475569` light mode / `#94a3b8` dark mode.
- **Secondary (blue):** `#1c7ed6` / `#4dabf7` — the exact blue already
  used for timer-length settings elsewhere in the app (`ui.py`'s
  `COLOR_TIMER_ACCENT`), reused rather than inventing a new hue, so
  Standard Mode's timer visually ties back to the app's own settings
  chrome instead of floating as an unrelated color.
- `era`: a value the era-pattern lookups don't recognize (e.g.
  `"Standard"`) — moot in practice, since the background renderer
  below never reaches the pattern-selection code for this theme.
- `tier1_effect` / `tier3_effect`: `"none"` (the intercept above
  forces this anyway; set correctly here too so `STANDARD_THEME` is
  never a footgun if read directly by future code).

## Pillow art: flat instead of textured

New small helper in `visuals.py`, `make_flat_fill(width, height,
hex_color, alpha=255) -> Image.Image` — an `RGBA` image filled with one
solid color at the given opacity, no pattern, no gradient. In
`_apply_rider_theme()`, when `standard_mode` is on:

- **Background wallpaper:** `make_flat_fill(..., STANDARD_THEME's
  surface color)` (default opaque) instead of
  `make_background_texture()` — no era scanlines/facets/circuit-grid.
- **Divider strip:** same `make_flat_fill()`, thin — instead of
  `make_panel_divider()`'s tick-marks/diamonds/dashed-circuit motifs.
- **Timer glow / button glow:** `make_flat_fill(..., alpha=0)` — fully
  transparent, same size the real glow would have been — instead of
  `make_glow()`. No soft glow at all behind the digits or the Start
  button.

This is what actually satisfies "bypass the Pillow art for a
lightweight, professional look": a flat fill is a single solid-color
`Image.new()` call, versus alpha-composited procedural patterns. The
progress bar itself needs no separate change — `tier1_effect="none"`
already means every non-Tier-1 Rider renders the plain native
`ctk.CTkProgressBar`, so Standard Mode gets that for free the same way
29 of the 38 Riders already do today.

## Wording

`_is_tokusatsu()` gets one extra condition: `self.config_obj.terminology
== "tokusatsu" and not self.config_obj.standard_mode`. Standard Mode
always reads as Professional wording, regardless of the Wording
switch's saved value — consistent with the name ("Standard
*Professional* Mode") and it means no tokusatsu copy ever needs to be
written for a theme that isn't a real Rider. The Wording switch itself
stays interactive and its real value is never overwritten, exactly
like `rider_theme`.

## Driver label

The label under the timer digits (normally the selected Rider's name,
uppercased) shows **"STANDARD MODE"** while active, instead of the
underlying Rider's name — showing a Rider name while its colors and
effects are suppressed would be confusing. Reverts to the real Rider
name the instant the switch is turned off.

## Settings tab UI

A new switch, placed directly above the "Kamen Rider theme"/"Color
theme" dropdown, styled like the existing feature blurbs (Claude
fallback, Gavv's toggle): a short description plus the switch itself.
The Rider dropdown and Wording switch both stay interactive while
Standard Mode is on — not greyed out or disabled — matching the
existing philosophy (Gavv's timer-length fields stay editable while
overridden too). Toggling Standard Mode triggers the same
`_rebuild_tabs()` full-Settings-tab rebuild already used when the
Rider selection changes, so the Tier 2 preset row appears/disappears
correctly with no new plumbing.

## Docs

- Help tab: one more paragraph, alongside the existing Wording/theme
  explanation, describing what Standard Mode does and exactly how to
  turn it on (the new Settings switch).
- `README.md`: one-line feature mention, matching how Tiers 1-3 were
  each documented.

## Architecture summary (files)

- **`lock_in/rider_themes.py`**: `STANDARD_THEME` constant.
- **`lock_in/config.py`**: `standard_mode: bool = False` field.
- **`lock_in/visuals.py`**: `make_flat_fill()` helper.
- **`lock_in/ui.py`**: the `standard_mode` branch inside
  `_apply_rider_theme()` (theme substitution, forced tier1/tier3
  `"none"`, flat art, driver-label override), the `_is_tokusatsu()`
  one-line change, the Settings-tab switch + skipped preset-row block,
  Help tab paragraph.

## Testing

- `Config`: `standard_mode` defaults to `False`, round-trips through
  `load`/`save`, same shape as the existing `micro_sprint_mode` tests.
- `visuals.py`: `make_flat_fill()` — returns a solid-color image of the
  requested size, no pattern, same test style as every other `visuals.py`
  render function.
- `rider_themes.py`: `STANDARD_THEME` passes the same completeness/
  contrast checks `tests/test_rider_themes.py` already runs across all
  38 real Riders (palette validity, dark-mode text-color safety).
- `ui.py` wiring (theme substitution, forced `"none"` effects, flat
  art, driver label, wording override, preset-row skip): screenshot-
  driven manual verification of the real running app — same approach
  every prior tier used, no automated GUI test. Specifically verify
  Standard Mode suppresses a Tier 1/2/3 Rider's gimmick when turned on
  *on top of* one (e.g. select Build or Kuuga or 555, then flip
  Standard Mode on) — that's the actual point of the feature.

## Out of scope for this pass

- Tiers 4-6 — separate specs, explicitly deferred for now.
- Any literal removal of Pillow as a dependency or rendering pathway —
  `make_flat_fill()` still uses Pillow, just does far less work than a
  textured render. "Bypass Pillow" is about the art being flat, not
  about not calling PIL.
- Disabling/greying out the Rider dropdown or Wording switch while
  Standard Mode is active — explicitly rejected during design.
- Any git/GitHub action — every command runs manually, at the end.

## File-by-file change list

- Edit: `lock_in/rider_themes.py`, `lock_in/config.py`,
  `lock_in/visuals.py`, `lock_in/ui.py`.
- Edit: `tests/test_config.py`, `tests/test_visuals.py`,
  `tests/test_rider_themes.py`.
- Edit: `README.md`, `.gitignore` as needed once implementation lands.
