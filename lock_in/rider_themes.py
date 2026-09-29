"""
rider_themes.py
================
This file is a big list of Kamen Rider costume colors. When you pick a
Rider in Settings, the app paints itself with that Rider's two colors:
one main color (`primary`, used for the timer and the Henshin button)
and one helper color (`secondary`, used for a small label and the
button's outline). Nothing else changes — same buttons, same words,
just different colors, like changing a costume.

Each color is written down as a PAIR — one hex for light mode, one hex
for dark mode — instead of one hex with the other shade guessed by a
formula. A color that looks great on a white background can wash out or
vanish on a near-black one (and the other way around), so each shade
was hand-picked to stay easy to see in its own mode, not derived from
its twin.

Where these colors came from: checked each Rider's real suit and made a
list, then nudged each shade so it holds up against this app's own
light/dark backgrounds specifically. A few Riders had more than two
colors listed; where that happened, one color was picked to keep things
simple — see docs/superpowers/specs/2026-08-07-lock-in-rebrand-design.md
if a color here looks surprising.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from .rider_effects import (
    DisplayEffect,
    EnforcementEffect,
    Era,
    InteractionEffect,
    PresetEffect,
    ProductivityEffect,
    ProgressEffect,
)


def lighten(hex_color: str, factor: float = 0.35) -> str:
    """
    Mix a color with white to make a paler version of it.

    `factor` says how much white to mix in: 0 means "no change at all",
    1 means "turn it all the way to white". Used to push a color further
    toward white for text/surfaces that need extra contrast in dark mode.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r = round(r + (255 - r) * factor)
    g = round(g + (255 - g) * factor)
    b = round(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def darken(hex_color: str, factor: float = 0.35) -> str:
    """
    Mix a color with black to make a much dimmer version of it.

    `factor` says how much black to mix in: 0 means "no change at all",
    1 means "turn it all the way to black". This is `lighten()`'s
    opposite twin -- used for backgrounds instead of text, since a
    background needs to go the other way (darker, not paler) to stay
    readable behind light-colored text in dark mode.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r = round(r * (1 - factor))
    g = round(g * (1 - factor))
    b = round(b * (1 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def readable_text_color(hex_color: str) -> str:
    """
    Pick plain black or white, whichever one shows up more clearly on
    top of `hex_color`.

    This uses a well-known trick for "how bright does this color LOOK
    to a person" — green looks much brighter than blue even at the same
    number, so we weigh each color a different amount instead of just
    averaging them.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    perceived_brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "#000000" if perceived_brightness > 150 else "#ffffff"


def desaturate(hex_color: str) -> str:
    """
    Turn a color into its plain grey equivalent -- same perceived
    brightness as the original, but with all the color washed out.

    Uses the same "how bright does this look to a person" weights as
    readable_text_color() (green looks brighter than blue at the same
    number), so two different colors still end up as two different
    greys instead of collapsing to the exact same grey.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    gray = round((r * 299 + g * 587 + b * 114) / 1000)
    return f"#{gray:02x}{gray:02x}{gray:02x}"


@dataclass(frozen=True)
class RiderAbilities:
    """A Rider's powers, one per Tier. `NONE` means "no power of this kind".

    Code that needs to know about a power asks for it by kind:
    `rider.abilities.display is DisplayEffect.MIRROR_FLIP`, instead of
    comparing loose words."""

    progress: ProgressEffect = ProgressEffect.NONE  # Tier 1
    preset: PresetEffect = PresetEffect.NONE  # Tier 2
    enforcement: EnforcementEffect = EnforcementEffect.NONE  # Tier 3
    display: DisplayEffect = DisplayEffect.NONE  # Tier 4
    productivity: ProductivityEffect = ProductivityEffect.NONE  # Tier 5
    interaction: InteractionEffect = InteractionEffect.NONE  # Tier 6

    def powers(self) -> list[str]:
        """The powers this Rider really has, as their plain words."""
        return [
            str(effect)
            for effect in (
                self.progress,
                self.preset,
                self.enforcement,
                self.display,
                self.productivity,
                self.interaction,
            )
            if effect != "none"
        ]


# Which RiderTheme field holds which kind of power (checked in __post_init__).
_TYPED_FIELDS: tuple[tuple[str, type[StrEnum]], ...] = (
    ("era", Era),
    ("tier1_effect", ProgressEffect),
    ("tier2_effect", PresetEffect),
    ("tier3_effect", EnforcementEffect),
    ("tier4_effect", DisplayEffect),
    ("tier5_effect", ProductivityEffect),
    ("tier6_effect", InteractionEffect),
)


@dataclass(frozen=True)
class RiderTheme:
    """One Rider's two colors, plus which era and year they're from."""

    era: Era
    year: int
    # Each color is (light_mode_hex, dark_mode_hex) -- picked by hand for
    # each mode, not one color with the other guessed from it.
    primary: tuple[str, str]
    secondary: tuple[str, str]
    # "none" for every Rider except the 9 with a Tier 1 gimmick (see
    # docs/superpowers/specs/2026-08-10-tier1-rider-progress-variants-design.md).
    # visuals.py and lock_in/ui/ read this to decide what the progress bar or
    # background should look like for this Rider.
    tier1_effect: ProgressEffect = ProgressEffect.NONE
    # "none" for every Rider except the 3 with quick-pick timer buttons
    # (see docs/superpowers/specs/2026-08-10-tier2-settings-presets-design.md):
    # Kuuga's "interval_presets", Super-1's "task_presets", and Gavv's
    # "micro_sprint" switch. The Settings page reads this to decide which
    # extra row to show.
    tier2_effect: PresetEffect = PresetEffect.NONE
    # "none" for every Rider except the 5 with a Tier 3 gimmick (see
    # docs/superpowers/specs/2026-08-11-tier3-enforcement-interaction-design.md).
    # lock_in/ui/ reads this to decide what enforcement/interaction behavior
    # this Rider needs.
    tier3_effect: EnforcementEffect = EnforcementEffect.NONE
    # "none" for every Rider except the 8 with a Tier 4 gimmick (see
    # docs/superpowers/specs/2026-08-26-tier4-alternate-display-modes-design.md).
    # lock_in/ui/, notifier.py, and ambient.py all read this to decide what
    # display/audio/input behavior this Rider needs.
    tier4_effect: DisplayEffect = DisplayEffect.NONE
    # "none" for every Rider except the ones that read your tasks and
    # history -- all 10 planned Riders are now built: V3, Den-O, Decade,
    # Zi-O, Blade, W, Geats, Gotchard, OOO, and MY-TH. See
    # docs/superpowers/specs/2026-09-05-tier5-v3-daily-hours-design.md.
    # lock_in/ui/router.py reads this to decide whether the side bar gets
    # a Rider page at all, and lock_in/tier5/__init__.py's TIER5_BUILDERS
    # maps it to the module that draws that page.
    tier5_effect: ProductivityEffect = ProductivityEffect.NONE
    # "none" for every Rider except Tier 6's two "new infrastructure"
    # Riders. Wizard's "mouse_gestures": lock_in/ui/ listens for right-button
    # drags (a line left or right, or a circle) to switch pages, and
    # lock_in/wizard_gestures.py does the drawing math (see
    # docs/superpowers/specs/2026-09-23-tier6-wizard-mouse-gestures-design.md).
    # Revice's "buddy_link": the side bar gets a "Buddy" page for pairing with
    # another computer on the same Wi-Fi (see
    # docs/superpowers/specs/2026-09-24-tier6-revice-buddy-link-design.md).
    tier6_effect: InteractionEffect = InteractionEffect.NONE

    def __post_init__(self) -> None:
        """Turn plain words into the typed values from rider_effects.py.
        A misspelled power name stops here with a clear error, instead of
        that power quietly never turning on."""
        for name, kind in _TYPED_FIELDS:
            value = getattr(self, name)
            members: list[StrEnum] = list(kind)
            try:
                typed = kind(value)
            except ValueError:
                raise ValueError(
                    f"{value!r} isn't a known {kind.__name__} (the {name} field). "
                    f"Known ones: {', '.join(member.value for member in members)}"
                ) from None
            object.__setattr__(self, name, typed)

    @property
    def abilities(self) -> RiderAbilities:
        """This Rider's six powers, one per Tier, as one record."""
        return RiderAbilities(
            progress=self.tier1_effect,
            preset=self.tier2_effect,
            enforcement=self.tier3_effect,
            display=self.tier4_effect,
            productivity=self.tier5_effect,
            interaction=self.tier6_effect,
        )

    @property
    def primary_pair(self) -> tuple[str, str]:
        """The hand-picked (light mode, dark mode) pair, as-is."""
        return self.primary

    @property
    def secondary_pair(self) -> tuple[str, str]:
        return self.secondary

    @property
    def surface_pair(self) -> tuple[str, str]:
        """
        A panel-background color tinted by this Rider's primary color —
        pale for light mode, dark for dark mode. Each side starts from
        THAT mode's own primary shade, so a Rider's theme reads as "the
        same theme" whichever mode you're in, without the two modes
        having to share one single starting color.

        0.72 (not closer to 1.0) is chosen on purpose: push it much
        darker than that and almost every color collapses toward the
        same near-black, and dark mode stops looking like it has a
        theme applied at all.
        """
        light_primary, dark_primary = self.primary
        return (lighten(light_primary, 0.90), darken(dark_primary, 0.72))

    @property
    def primary_text_pair(self) -> tuple[str, str]:
        """
        A version of `primary` that's always safe to use as TEXT sitting
        on top of this theme's own `surface_pair` — unlike `primary_pair`
        (which is the plain, vivid color, meant for things like the
        progress bar), this one is always darkened for light mode and
        lightened for dark mode, starting from that mode's own shade.

        Without this, a Rider whose primary color is already very pale
        would have text that's too close to its own pale light-mode
        background — hard to read. Pushing the text color further in the
        opposite direction from the surface color fixes that for every
        Rider, not just the obviously pale ones.
        """
        light_primary, dark_primary = self.primary
        return (darken(light_primary, 0.35), lighten(dark_primary, self._dark_mode_text_factor))

    @property
    def secondary_text_pair(self) -> tuple[str, str]:
        """The same idea as `primary_text_pair`, but for `secondary`."""
        light_secondary, dark_secondary = self.secondary
        return (
            darken(light_secondary, 0.35),
            lighten(dark_secondary, self._dark_mode_text_factor),
        )

    @property
    def _dark_mode_text_factor(self) -> float:
        """
        How far dark-mode text gets pushed toward white. Every Rider
        uses the normal amount (0.35) EXCEPT Black, whose whole gimmick
        (see Tier 1) is stricter, higher contrast in dark mode -- so its
        words get pushed further toward pure white, standing out more
        sharply against its own already-near-black primary color.
        """
        return 0.55 if self.tier1_effect is ProgressEffect.HIGH_CONTRAST_DARK else 0.35

    @property
    def button_text_pair(self) -> tuple[str, str]:
        """
        The right text color to sit directly ON TOP of `secondary_pair`
        (used for the words on the Henshin button itself).

        This is a different problem than the two pairs above: those mix
        in some black or white to create a paler/darker VARIANT of a
        color for text to sit *near*. This one has to sit *directly on
        top of* secondary_pair's exact color, so a tinted variant isn't
        enough — it needs plain black or white, whichever actually
        shows up, picked separately for each of light and dark mode
        since secondary_pair itself is a different shade in each.
        """
        light_fill, dark_fill = self.secondary_pair
        return (readable_text_color(light_fill), readable_text_color(dark_fill))


RIDER_THEMES: dict[str, RiderTheme] = {
    "Kamen Rider (1971)": RiderTheme(
        Era.SHOWA,
        1971,
        ("#154a2e", "#237a4b"),
        ("#a83225", "#d94436"),
        tier1_effect=ProgressEffect.WINDMILL,
    ),
    "Kamen Rider V3 (1973)": RiderTheme(
        Era.SHOWA,
        1973,
        ("#225c25", "#4caf50"),
        ("#a83225", "#d94436"),
        tier5_effect=ProductivityEffect.HOURS_TAB,
    ),
    "Kamen Rider X (1974)": RiderTheme(
        Era.SHOWA,
        1974,
        ("#90a4ae", "#cfd8dc"),
        ("#0f4a8f", "#42a5f5"),
        tier3_effect=EnforcementEffect.GOAL_GATE,
    ),
    "Kamen Rider Amazon (1974)": RiderTheme(
        Era.SHOWA,
        1974,
        ("#224714", "#558b2f"),
        ("#b33f00", "#ff9800"),
        tier3_effect=EnforcementEffect.ZERO_UI,
    ),
    "Kamen Rider Stronger (1975)": RiderTheme(
        Era.SHOWA,
        1975,
        ("#9c1e1e", "#ef5350"),
        ("#1a1a1a", "#757575"),
        tier1_effect=ProgressEffect.BORDER_GLOW,
    ),
    "Kamen Rider Skyrider (1979)": RiderTheme(
        Era.SHOWA,
        1979,
        ("#225c25", "#4caf50"),
        ("#5d4037", "#8d6e63"),
        tier1_effect=ProgressEffect.RISING_BAR,
    ),
    "Kamen Rider Super-1 (1980)": RiderTheme(
        Era.SHOWA,
        1980,
        ("#9e9e9e", "#e0e0e0"),
        ("#1a1a1a", "#757575"),
        tier2_effect=PresetEffect.TASK_PRESETS,
    ),
    "Kamen Rider ZX (1982)": RiderTheme(
        Era.SHOWA,
        1982,
        ("#9c1e1e", "#ef5350"),
        ("#78909c", "#b0bec5"),
        tier3_effect=EnforcementEffect.STEALTH_MUTE,
    ),
    "Kamen Rider Black (1987)": RiderTheme(
        Era.SHOWA,
        1987,
        ("#111111", "#616161"),
        ("#00903b", "#00e676"),
        tier1_effect=ProgressEffect.HIGH_CONTRAST_DARK,
    ),
    "Kamen Rider Black RX (1988)": RiderTheme(
        Era.SHOWA,
        1988,
        ("#225c25", "#4caf50"),
        ("#111111", "#616161"),
        tier4_effect=DisplayEffect.MANUAL_BREAK_TOGGLE,
    ),
    "Kamen Rider Kuuga (2000)": RiderTheme(
        Era.HEISEI,
        2000,
        ("#961d22", "#ef5350"),
        ("#1a1a1a", "#757575"),
        tier2_effect=PresetEffect.INTERVAL_PRESETS,
    ),
    "Kamen Rider Agito (2001)": RiderTheme(
        Era.HEISEI,
        2001,
        ("#d49e15", "#ffca28"),
        ("#1a1a1a", "#757575"),
        tier1_effect=ProgressEffect.COLOR_INTERPOLATION,
    ),
    "Kamen Rider Ryuki (2002)": RiderTheme(
        Era.HEISEI,
        2002,
        ("#9c1e1e", "#ef5350"),
        ("#757575", "#b0bec5"),
        tier4_effect=DisplayEffect.MIRROR_FLIP,
    ),
    "Kamen Rider 555 (2003)": RiderTheme(
        Era.HEISEI,
        2003,
        ("#111111", "#424242"),
        ("#a60000", "#ff1744"),
        tier3_effect=EnforcementEffect.CODE_UNLOCK,
    ),
    "Kamen Rider Blade (2004)": RiderTheme(
        Era.HEISEI,
        2004,
        ("#0f4a8f", "#42a5f5"),
        ("#78909c", "#b0bec5"),
        tier5_effect=ProductivityEffect.KANBAN_BOARD,
    ),
    "Kamen Rider Hibiki (2005)": RiderTheme(
        Era.HEISEI,
        2005,
        ("#310d5e", "#7b1fa2"),
        ("#9c1e1e", "#ef5350"),
        tier4_effect=DisplayEffect.AMBIENT_LOOP,
    ),
    "Kamen Rider Kabuto (2006)": RiderTheme(
        Era.HEISEI,
        2006,
        ("#9c1e1e", "#ef5350"),
        ("#607d8b", "#b0bec5"),
        tier4_effect=DisplayEffect.HIDDEN_TIMER,
    ),
    "Kamen Rider Den-O (2007)": RiderTheme(
        Era.HEISEI,
        2007,
        ("#9c1e1e", "#ef5350"),
        ("#90a4ae", "#eceff1"),
        tier5_effect=ProductivityEffect.TIMELINE_VIEW,
    ),
    "Kamen Rider Kiva (2008)": RiderTheme(
        Era.HEISEI,
        2008,
        ("#660000", "#d32f2f"),
        ("#d49e15", "#ffca28"),
        tier1_effect=ProgressEffect.NIGHT_OVERLAY,
    ),
    "Kamen Rider Decade (2009)": RiderTheme(
        Era.HEISEI,
        2009,
        ("#9e1447", "#f06292"),
        ("#1a1a1a", "#757575"),
        tier5_effect=ProductivityEffect.ANALYTICS_DASHBOARD,
    ),
    "Kamen Rider W (2009)": RiderTheme(
        Era.HEISEI,
        2009,
        ("#225c25", "#4caf50"),
        ("#111111", "#616161"),
        tier5_effect=ProductivityEffect.WEEK_COMPARE,
    ),
    "Kamen Rider OOO (2010)": RiderTheme(
        Era.HEISEI,
        2010,
        ("#111111", "#616161"),
        ("#9c1e1e", "#ef5350"),
        tier5_effect=ProductivityEffect.PHASE_COMBO,
    ),
    "Kamen Rider Fourze (2011)": RiderTheme(
        Era.HEISEI,
        2011,
        ("#9e9e9e", "#ffffff"),
        ("#b33f00", "#ff9800"),
        tier1_effect=ProgressEffect.CONSTELLATION,
    ),
    "Kamen Rider Wizard (2012)": RiderTheme(
        Era.HEISEI,
        2012,
        ("#9c1e1e", "#ef5350"),
        ("#1a1a1a", "#757575"),
        tier6_effect=InteractionEffect.MOUSE_GESTURES,
    ),
    "Kamen Rider Gaim (2013)": RiderTheme(
        Era.HEISEI,
        2013,
        ("#b33f00", "#ff9800"),
        ("#96761c", "#e4c657"),
        tier3_effect=EnforcementEffect.LOCK_OVERLAY,
    ),
    "Kamen Rider Drive (2014)": RiderTheme(
        Era.HEISEI,
        2014,
        ("#9c1e1e", "#ef5350"),
        ("#1a1a1a", "#757575"),
        tier1_effect=ProgressEffect.ACCELERATING_FILL,
    ),
    "Kamen Rider Ghost (2015)": RiderTheme(
        Era.HEISEI,
        2015,
        ("#111111", "#616161"),
        ("#cc7a00", "#ffb74d"),
        tier4_effect=DisplayEffect.GHOST_WIDGET,
    ),
    "Kamen Rider Ex-Aid (2016)": RiderTheme(
        Era.HEISEI,
        2016,
        ("#b3154b", "#f06292"),
        ("#009e52", "#69f0ae"),
        tier4_effect=DisplayEffect.CHIPTUNE_ALERT,
    ),
    "Kamen Rider Build (2017)": RiderTheme(
        Era.HEISEI,
        2017,
        ("#9c1e1e", "#ef5350"),
        ("#0f4a8f", "#42a5f5"),
        tier1_effect=ProgressEffect.VIALS,
    ),
    "Kamen Rider Zi-O (2018)": RiderTheme(
        Era.HEISEI,
        2018,
        ("#1a1a1a", "#757575"),
        ("#9e1447", "#f06292"),
        tier5_effect=ProductivityEffect.HISTORY_EDITOR,
    ),
    "Kamen Rider Zero-One (2019)": RiderTheme(
        Era.REIWA,
        2019,
        ("#77a100", "#c6ff00"),
        ("#111111", "#616161"),
        tier4_effect=DisplayEffect.DASHBOARD_CARDS,
    ),
    "Kamen Rider Saber (2020)": RiderTheme(
        Era.REIWA,
        2020,
        ("#9c1e1e", "#ef5350"),
        ("#1a1a1a", "#757575"),
        tier1_effect=ProgressEffect.BOOKMARK,
    ),
    "Kamen Rider Revice (2021)": RiderTheme(
        Era.REIWA,
        2021,
        ("#b3154b", "#f06292"),
        ("#0097a7", "#18ffff"),
        tier6_effect=InteractionEffect.BUDDY_LINK,
    ),
    "Kamen Rider Geats (2022)": RiderTheme(
        Era.REIWA,
        2022,
        ("#9e9e9e", "#ffffff"),
        ("#9c1e1e", "#ef5350"),
        tier5_effect=ProductivityEffect.GOAL_STREAK,
    ),
    "Kamen Rider Gotchard (2023)": RiderTheme(
        Era.REIWA,
        2023,
        ("#008394", "#4dd0e1"),
        ("#b33f00", "#ffb74d"),
        tier5_effect=ProductivityEffect.BADGE_CARDS,
    ),
    "Kamen Rider Gavv (2024)": RiderTheme(
        Era.REIWA,
        2024,
        ("#571673", "#ab47bc"),
        ("#c48000", "#ffee58"),
        tier2_effect=PresetEffect.MICRO_SPRINT,
    ),
    "Kamen Rider Zeztz (2025)": RiderTheme(
        Era.REIWA,
        2025,
        ("#225c25", "#4caf50"),
        ("#111111", "#616161"),
        tier4_effect=DisplayEffect.HOTKEYS,
    ),
    # MY-TH is one pick with two looks. Light mode is normal MY-TH (blue
    # and silver). Dark mode is MY-TH ORIGIN (red and gunmetal). Both
    # pairs are picked by hand -- neither one is worked out from the other.
    "Kamen Rider MY-TH (2026)": RiderTheme(
        Era.REIWA,
        2026,
        ("#0f4a8f", "#ef5350"),
        ("#78909c", "#616161"),
        tier5_effect=ProductivityEffect.PRIORITY_ORDER,
    ),
}

# The very first Kamen Rider show. A good, neutral starting theme.
DEFAULT_RIDER_THEME = "Kamen Rider (1971)"

# Tier 0's baseline: NOT one of the 38 Kamen Rider costumes above, and
# deliberately kept out of RIDER_THEMES (see this file's own docstring —
# that dict is specifically "a big list of Kamen Rider costume colors").
# Reuses the same RiderTheme dataclass purely for its color math
# (surface tinting, contrast-safe text pairs) -- Standard Mode gets
# those guarantees for free instead of duplicating them.
STANDARD_THEME = RiderTheme(
    Era.STANDARD,
    0,
    ("#475569", "#94a3b8"),
    ("#1c7ed6", "#4dabf7"),
)


# --------------------------------------------------------------------------- #
# Who each Rider is, kept apart from what they can do
# --------------------------------------------------------------------------- #
RiderId = str


def rider_id_for(display_name: str) -> RiderId:
    """A short, stable id made from a Rider's name: "Kamen Rider Ex-Aid
    (2016)" -> "ex-aid-2016". The name is still what config.json saves;
    the id is for code and tests that want a plain handle."""
    words = display_name.lower().strip()
    # "Kamen Rider Ex-Aid (2016)" drops the shared "Kamen Rider" part, but
    # the very first "Kamen Rider (1971)" keeps it -- it's their whole name.
    if words.startswith("kamen rider ") and not words[len("kamen rider ") :].startswith("("):
        words = words[len("kamen rider ") :]
    return re.sub(r"[^a-z0-9]+", "-", words).strip("-")


@dataclass(frozen=True)
class RiderDefinition:
    """One Rider: who they are (id, name, era, year), how they look
    (theme), and what they can do (abilities). Powers are plain parts
    fitted together, not a family tree of Rider classes."""

    id: RiderId
    display_name: str
    theme: RiderTheme = field(repr=False)

    @property
    def era(self) -> Era:
        return self.theme.era

    @property
    def year(self) -> int:
        return self.theme.year

    @property
    def abilities(self) -> RiderAbilities:
        return self.theme.abilities


def _build_riders() -> dict[RiderId, RiderDefinition]:
    riders: dict[RiderId, RiderDefinition] = {}
    for name, theme in RIDER_THEMES.items():
        rider_id = rider_id_for(name)
        if rider_id in riders:
            raise ValueError(f"Two Riders share the id {rider_id!r}: {name!r}")
        riders[rider_id] = RiderDefinition(rider_id, name, theme)
    return riders


# Every Rider, by id. RIDER_THEMES (by display name) is still the table
# the rest of the app and config.json use.
RIDERS: dict[RiderId, RiderDefinition] = _build_riders()


def rider_named(display_name: str) -> RiderDefinition | None:
    """The Rider with this display name, or None."""
    theme = RIDER_THEMES.get(display_name)
    return (
        None if theme is None else RiderDefinition(rider_id_for(display_name), display_name, theme)
    )
