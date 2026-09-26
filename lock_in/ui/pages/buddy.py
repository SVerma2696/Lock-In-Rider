"""
ui/pages/buddy.py
=================
Kamen Rider Revice's Buddy page, in the side bar.

All the pairing screens (Share, Receive, the code, Pull History) are
still drawn by lock_in/revice_tab.py, and all the network work is still
done by lock_in/revice_link.py. This page just gives them a card to sit
in. The link itself belongs to the app, so opening other pages -- or
changing light/dark mode -- never drops the connection.
"""

from __future__ import annotations

from .. import theme as t
from ...revice_tab import BuddyTab
from ..components import ModernCard
from .base import PAGE_PAD_X, Page


class BuddyPage(Page):
    route_id = "buddy"

    def build(self) -> None:
        app = self.app
        p = self.palette
        self.page_header("Buddy", "Pair with a friend's computer on the same Wi-Fi, and see "
                                  "each other's timer. Only use this on Wi-Fi you trust.")
        card = ModernCard(self.body, p, layout=self.layout, icon=self.icon("buddy"),
                          title="Buddy link")
        self.pack(card, fill="x", padx=PAGE_PAD_X, pady=(0, t.SPACE_6))
        self.tab = BuddyTab(
            card.body, accent=p.accent, text_color=p.accent_on,
            on_share=app._on_buddy_share, on_receive=app._on_buddy_receive,
            on_cancel=app._on_buddy_cancel, on_pull=app._on_buddy_pull,
            on_unpair=app._on_buddy_cancel,
        )
