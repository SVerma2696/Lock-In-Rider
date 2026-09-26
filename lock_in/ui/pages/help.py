"""
ui/pages/help.py
================
The Help page: a plain-words guide to everything Lock In can do, split
into cards. Written so someone brand new -- or a five-year-old -- can
follow it.
"""

from __future__ import annotations

from .. import theme as t
from ... import __version__
from ..components import ModernCard
from .base import PAGE_PAD_X, Page

TIER1 = [
    ("Kamen Rider (1971)", "the progress bar becomes a spinning windmill."),
    ("Skyrider", "the progress bar climbs upward instead of filling sideways."),
    ("Fourze", "the progress bar becomes tiny stars that light up one by one."),
    ("Build", "the progress bar becomes two bottles that fill up together."),
    ("Stronger", "a soft red glow slowly grows around the edge of the window."),
    ("Kiva", "a warm amber glow tints the window's edges, like nighttime."),
    ("Agito", "the progress bar's color starts dim and slowly wakes up brighter."),
    ("Black", "dark mode gets extra dark, with extra bright, easy-to-read words."),
    ("Drive", "the progress bar starts slow, then speeds up and catches up near the end."),
    ("Saber", "the progress bar becomes a bookmark ribbon that fills in as you go."),
]

TIER2 = [
    ("Kuuga", "4 buttons that set a quick, medium, long, or extra-long focus block in one click."),
    ("Super-1", "5 buttons, one for each kind of task (coding, hardware, admin, thinking, research)."),
    ("Gavv", "one switch that turns on lots of short, repeated 10-minute sprints instead of one "
             "long block. Flip it off to go back to your own numbers, which are never erased."),
]

TIER3 = [
    ("Kamen Rider X", "before a focus block starts, it asks you to type what you're working "
                      "on. No rush — it waits until you type something."),
    ("Amazon", "during a focus block, the screen turns into a plain, draining green field, "
               "with zero warning time before a blocked app counts against you."),
    ("ZX", "the whole app turns black-and-white, and it hides itself the moment a focus "
           "block starts — no sounds or pop-ups either."),
    ("Gaim", "a padlock appears at the top and the window always stays on top of everything "
             "else while you focus."),
    ("555", "if you get the full-screen lockdown screen, you can type 555 to leave it early "
            "instead of waiting it out."),
]

TIER4 = [
    ("Black RX", "a switch that makes breaks always wait for you to press Start, instead of "
                 "starting on their own."),
    ("Ryuki", "the whole window — side bar too — flips left-to-right during a break, then "
              "flips right back the moment focus starts again."),
    ("Kabuto", "the timer digits are hidden while you focus. Hover over where they'd be to "
               "peek at the real time."),
    ("Ex-Aid", "the timer switches to a pixel font, and its alert sound becomes an 8-bit jingle."),
    ("Hibiki", "a soft ambient sound plays in the background for as long as a focus block runs."),
    ("Zero-One", "the timer restyles itself as a row of dashboard cards instead of the usual "
                 "big digits."),
    ("Ghost", "the main window hides itself and a small floating clock stays on top of "
              "everything else. Click it to bring the full window back."),
    ("Zeztz", "keyboard shortcuts take over: Space starts or pauses, S skips, R resets, as "
              "long as this window is the one you're using."),
]

TIER5 = [
    ("V3", "Hours", "how long you've focused today, plus a bar chart of the last 14 days. "
                    "Every block counts, finished or not."),
    ("Den-O", "Timeline", "one day's focus blocks at a time (earliest first), with buttons to "
                          "flip a day forward or back. Each shows its time, how long it ran, "
                          "and which task it was for."),
    ("Decade", "Analytics", "a 30-day version of V3's bar chart, plus your top 10 tasks by "
                            "total time spent."),
    ("Zi-O", "History", "the same day list as Den-O, but you can fix mistakes: pick a "
                        "different task for a block, or delete it (tap Delete, then tap "
                        "Really delete? to be sure)."),
    ("Blade", "Board", "your tasks in three columns: To Do, In Progress and Done. Tap the "
                       "little arrow on a task to move it one column over."),
    ("W", "Week", "the last 7 days next to the 7 days before them: one total for each, a "
                  "little sentence about which is bigger, and a chart with two bars per day."),
    ("Geats", "Goal", "pick how many minutes you want to focus each day with the minus and "
                      "plus buttons. A bar fills up as you focus, and a streak counts the "
                      "days in a row you reached your goal."),
    ("Gotchard", "Badges", "9 cards to collect, for things like your first focus block, a "
                           "3-hour day, or a 7-day goal streak. A badge you win is yours "
                           "to keep."),
    ("OOO", "Combo", "every open task gets three boxes: Plan, Work, and Review. Check all "
                     "three and the task shows a \"Combo formed!\" mark — but only your own "
                     "tick on the Tasks page actually finishes it."),
    ("MY-TH", "Priority", "your open tasks, numbered, with the one you've gone the longest "
                          "without working on at the top. It's worked out fresh every time "
                          "you open the page. In light mode MY-TH is blue and silver; in "
                          "dark mode it becomes MY-TH ORIGIN, red and gunmetal."),
]


class HelpPage(Page):
    route_id = "help"

    def build(self) -> None:
        app = self.app
        self.page_header("How to use Lock In",
                         "Lock In is a timer that helps you get work done by making distracting "
                         "apps annoying to open while you're focusing. Here's everything it can "
                         "do, and exactly how to turn each part on.")
        start_word = app._henshin_word()

        card = self._card("1. The quick start", "focus")
        for i, step in enumerate([
            "Open Settings (bottom of the side bar) and set how many minutes a focus block "
            "and a break should last.",
            "Open Blocking. Type apps that distract you (like a game) under \"Blocked apps\", "
            "and apps you trust under \"Always-allowed apps\" — one app name per line.",
            f"Go to Focus and press \"{start_word}\" to begin a focus block.",
            "Stay off blocked apps while the timer runs. Opening one warns you first, then "
            "gets stricter the longer you stay on it.",
            "When the block ends, open Activity and tell Lock In if it guessed right or wrong "
            "about any app — it gets smarter every time you correct it.",
        ], start=1):
            self._text(card, f"{i}.  {step}")

        card = self._card("2. Getting around", "list")
        self._text(card, "The side bar on the left has every page. Click a name to go there. "
                         "The page you're on is marked with a small colored stripe.")
        self._text(card, "Some heroes add their own page under the Rider heading. It shows up "
                         "the moment you pick that hero, and goes away when you pick another.")

        card = self._card("3. Change how it looks and talks", "palette")
        self._text(card, "All of these are in Settings, under Appearance, and change instantly "
                         "— nothing to save.")
        self._bullet(card, "\"Mode\" picks Light, Dark, or whatever your computer uses.")
        self._bullet(card, "\"Wording\" is a switch. Off keeps every word plain and simple "
                           "(\"Focus\", \"Start\"). On switches to fun Kamen Rider hero talk "
                           "(\"Henshin\", \"Off Mission\").")
        self._bullet(card, "The theme menu (it says \"Kamen Rider theme\" when Wording is on, or "
                           "\"Color theme\" when it's off) lets you pick any of the 38 heroes. "
                           "The app's main color changes to match. This never changes how "
                           "blocking or timers work.")
        self._bullet(card, "Want zero Rider flavor at all? Turn on \"Standard Mode\". It strips "
                           "every color, glow, and gimmick down to a plain grey-and-blue look, "
                           "no matter which Rider is picked underneath. It also switches "
                           "Wording to plain Professional while it's on. Turn it off and your "
                           "Rider — and your Wording setting — come right back.")

        card = self._card("4. Some heroes have a secret extra power", "star")
        self._text(card, "To turn one on, just pick that hero from the theme menu in Settings "
                         "— there's nothing else to click. As soon as you start your next "
                         "focus block, its power shows up by itself.")
        self._heading(card, "Heroes with a fancy progress bar")
        for name, what in TIER1:
            self._bullet(card, f"{name} — {what}")
        self._heading(card, "Heroes with quick-click buttons")
        self._text(card, "Pick one of these, and a \"Rider power\" card appears near the top "
                         "of Settings. Click a button and it fills in your focus/break "
                         "minutes for you — no typing needed.")
        for name, what in TIER2:
            self._bullet(card, f"{name} — {what}")
        self._heading(card, "Heroes that change what happens")
        for name, what in TIER3:
            self._bullet(card, f"{name} — {what}")

        card = self._card("5. Eight more heroes have their own display trick", "eye")
        self._text(card, "Turn one of these on and something about how the app looks, sounds, "
                         "or behaves changes, on top of its own color.")
        for name, what in TIER4:
            self._bullet(card, f"{name} — {what}")

        card = self._card("6. Some heroes read your own history", "chart")
        self._text(card, "Pick one of these and an extra page appears in the side bar, built "
                         "from your own past focus blocks and tasks.")
        for name, page, what in TIER5:
            self._bullet(card, f"{name} — a \"{page}\" page: {what}")

        card = self._card("7. Heroes that add something new", "buddy")
        self._bullet(card, "Wizard — hold the right mouse button and draw on this window. A "
                           "line to the left goes to the page above in the side bar. A line "
                           "to the right goes to the page below. A circle jumps to Focus. It "
                           "only works inside this window, it only changes pages, and if it "
                           "isn't sure what you drew, it does nothing. You can turn it off "
                           "with the \"Mouse gestures\" switch in Settings.")
        self._bullet(card, "Revice — pair with a friend's computer on the same Wi-Fi. You both "
                           "pick Revice. One of you opens the Buddy page and presses Share, "
                           "and the other presses Receive and types the 4 numbers. Then you "
                           "each see the other's timer and task, and your computer's name is "
                           "shown to them. Pull History copies their past focus blocks (and "
                           "the tasks those blocks belong to) into yours. It only adds things "
                           "— it never changes or deletes what you already have. Your buddy "
                           "can press Pull History too, any time you're paired — then your "
                           "focus blocks and their tasks go to them, and you're not asked "
                           "first. Nothing goes on the network until you press Share or "
                           "Receive. Only use it on Wi-Fi you trust.")

        card = self._card("8. Strict Camera Monitoring (optional)", "camera")
        self._text(card, "A separate extra, nothing to do with heroes: turn it on in Blocking, "
                         "and Lock In peeks at your webcam every few seconds during a focus "
                         "block to check for a phone. If it sees one, you get warned the same "
                         "way you would for a blocked app. It's off unless you turn it on. It "
                         "only watches during an actual focus block — the second a break "
                         "starts, or you flip the switch back off, the camera turns off too. "
                         "Watch the \"Phone check\" card on the Focus page: the camera is only "
                         "ever on when it says \"Camera monitoring active\".")

        card = self._card("9. Version", "refresh")
        self._text(card, f"You're running Lock In v{__version__}.")
        self._text(card, "Want to know if there's a newer Lock In? Open Settings and press "
                         "\"Check for updates now\" under Updates. It tells you what it found "
                         "in a short sentence right under the button.")

    # ------------------------------------------------------------------ #
    def _card(self, title: str, icon: str) -> ModernCard:
        card = ModernCard(self.body, self.palette, layout=self.layout, title=title,
                          icon=self.icon(icon))
        self.pack(card, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_4))
        return card

    def _text(self, card, text: str) -> None:
        self.pack(self.label(card.body, text, color=self.palette.text_secondary, wrap=600),
                  anchor="w", fill="x", pady=2)

    def _bullet(self, card, text: str) -> None:
        self.pack(self.label(card.body, f"•  {text}", color=self.palette.text_secondary,
                             wrap=600), anchor="w", fill="x", pady=2)

    def _heading(self, card, text: str) -> None:
        self.pack(self.label(card.body, text, bold=True), anchor="w", pady=(t.SPACE_3, 2))
