"""
ui/components/sidebar.py
========================
The bar down the left side of the window. One button per page, with a
little picture and a word. The page you're on gets a soft grey
background, a thin stripe in the Rider's color, and a Rider-colored
picture -- nothing louder than that.

Pages at the top: Focus, Tasks, Blocking, Activity, Insights.
Then the Rider's own page and Buddy, only when the picked Rider has one.
Pinned at the bottom: Help and Settings.

The side bar never decides anything itself. Clicking a button just
calls `on_select("tasks")` (or whichever page) and the app does the rest.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from .. import theme as t
from ..icons import icon_image
from ..router import Route
from .box import Box
from .text import Text


class SidebarButton(Box):
    def __init__(
        self, master, palette: t.Palette, *, layout, route: Route, on_click: Callable[[str], object]
    ) -> None:
        super().__init__(master)
        self.route = route
        self._palette = palette
        self._active: bool | None = None
        self._mirrored = False
        self._icon_idle = icon_image(route.icon, palette.text_secondary, t.ICON_SIZE)
        self._icon_active = icon_image(route.icon, palette.accent_text, t.ICON_SIZE)

        # The thin stripe that marks the page you're on.
        self.indicator = Box(self, width=3, height=22)
        layout.pack(self.indicator, side="left", padx=(0, t.SPACE_1))

        self.button = ctk.CTkButton(
            self,
            text=f"  {route.label}",
            image=self._icon_idle,
            compound="left",
            anchor="w",
            height=38,
            corner_radius=t.CONTROL_RADIUS,
            fg_color="transparent",
            hover_color=palette.control_hover,
            text_color=palette.text_secondary,
            font=t.font(size=t.FONT_BODY + 1),
            command=lambda: on_click(route.id),
        )
        layout.pack(self.button, side="left", fill="x", expand=True)
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        p = self._palette
        self.indicator.configure(fg_color=p.accent if active else "transparent")
        self.button.configure(
            fg_color=p.control_bg if active else "transparent",
            text_color=p.text_primary if active else p.text_secondary,
            image=self._icon_active if active else self._icon_idle,
        )

    def set_mirrored(self, mirrored: bool) -> None:
        """Ryuki's flip: the words and picture move to the right edge too,
        not just the button's place in the window."""
        if mirrored == self._mirrored:
            return
        self._mirrored = mirrored
        self.button.configure(
            anchor="e" if mirrored else "w",
            compound="right" if mirrored else "left",
            text=f"{self.route.label}  " if mirrored else f"  {self.route.label}",
        )


class Sidebar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        palette: t.Palette,
        *,
        layout,
        on_select: Callable[[str], object],
        rider_heading: str = "Rider",
    ) -> None:
        super().__init__(
            master, fg_color=palette.sidebar_bg, corner_radius=0, width=t.SIDEBAR_WIDTH
        )
        self._layout = layout
        self._palette = palette
        self._on_select = on_select
        self._rider_heading = rider_heading
        self.buttons: dict[str, SidebarButton] = {}
        self.pack_propagate(False)
        self.grid_propagate(False)

        self.top = Box(self)
        layout.pack(self.top, side="top", fill="x", padx=t.SPACE_3, pady=(t.SPACE_4, 0))
        self.bottom = Box(self)
        layout.pack(self.bottom, side="bottom", fill="x", padx=t.SPACE_3, pady=(0, t.SPACE_4))

    def set_routes(self, routes: list[Route], rider_heading: str | None = None) -> None:
        """Throw away the old buttons and make one per page."""
        if rider_heading is not None:
            self._rider_heading = rider_heading
        for holder in (self.top, self.bottom):
            for child in holder.winfo_children():
                child.destroy()
        self.buttons = {}
        heading_done = False
        for route in routes:
            holder = self.bottom if route.section == "bottom" else self.top
            if route.section == "rider" and not heading_done:
                heading = Text(
                    holder,
                    text=self._rider_heading.upper(),
                    anchor="w",
                    text_color=self._palette.text_muted,
                    font=t.font(size=10, weight="bold"),
                )
                self._layout.pack(
                    heading,
                    anchor="w",
                    fill="x",
                    padx=(t.SPACE_3, t.SPACE_3),
                    pady=(t.SPACE_4, t.SPACE_1),
                )
                heading_done = True
            button = SidebarButton(
                holder, self._palette, layout=self._layout, route=route, on_click=self._on_select
            )
            self._layout.pack(button, fill="x", pady=1)
            self.buttons[route.id] = button

    def set_active(self, route_id: str) -> None:
        for rid, button in self.buttons.items():
            button.set_active(rid == route_id)

    def set_mirrored(self, mirrored: bool) -> None:
        for button in self.buttons.values():
            button.set_mirrored(mirrored)
