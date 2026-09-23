"""
tier5/ooo.py
============
Kamen Rider OOO's Tier 5 gimmick: a "Combo" tab. Every open task gets
three fixed checkboxes -- Plan, Work, Review -- and checking all three
shows a "Combo formed!" mark next to that task's name. The ninth of
Tier 5's 10 Riders -- see
docs/superpowers/specs/2026-09-22-tier5-ooo-combo-design.md.

Checking all three boxes never finishes the task -- that's still always
your own click on the Tasks tab. See build() below.

combo_formed() is plain logic, tested with no Tk and no display server.
build() is the only Tk-dependent piece; it's checked in the running app
instead, matching every other tab.
"""

from __future__ import annotations

import customtkinter as ctk

PHASE_LABELS = ("Plan", "Work", "Review")

# What an unchecked phase button looks like -- CustomTkinter's own gray,
# picked for light and dark mode. A checked one uses theme.secondary.
_EMPTY_BOX = ("gray80", "gray30")


def combo_formed(phases: list[bool]) -> bool:
    """True once all three of a task's phases are checked."""
    return all(phases)


def build(parent, *, history, tasks, theme, appearance_mode, config) -> None:
    """
    Populate `parent` with OOO's Combo view: one card per open task,
    each with three Plan/Work/Review buttons.

    Every card and its three buttons are built once. Clicking a button
    calls tasks.toggle_phase(...) and then re-configures just that one
    card in place -- it never destroys and rebuilds the whole tab from
    inside a click, the same safety rule Geats' and Gotchard's widgets
    already follow.

    `history`, `appearance_mode`, and `config` are part of every Tier 5
    builder's signature for consistency -- OOO needs none of them.
    """
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True)

    open_tasks = tasks.open()
    if not open_tasks:
        ctk.CTkLabel(
            frame, text="No open tasks yet. Add one on the Tasks tab.",
            text_color=theme.primary_text_pair,
        ).pack(anchor="w", pady=(4, 0))
        return

    text_color = theme.primary_text_pair

    for task in open_tasks:
        card = ctk.CTkFrame(frame, fg_color="transparent")
        card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            card, text=task.name, text_color=text_color,
            font=ctk.CTkFont(weight="bold"), anchor="w",
        ).pack(anchor="w")

        combo_label = ctk.CTkLabel(
            card, text="", text_color=theme.secondary,
            font=ctk.CTkFont(size=11, weight="bold"), anchor="w",
        )
        combo_label.pack(anchor="w")

        buttons_row = ctk.CTkFrame(card, fg_color="transparent")
        buttons_row.pack(anchor="w", pady=(4, 0))

        buttons: list = []

        def refresh_card(task_id=task.id, combo_label=combo_label, buttons=buttons) -> None:
            current = tasks.get(task_id)
            if current is None:
                return
            for button, checked in zip(buttons, current.phases):
                button.configure(
                    fg_color=theme.secondary if checked else _EMPTY_BOX,
                    hover_color=theme.secondary if checked else _EMPTY_BOX,
                )
            combo_label.configure(text="⭐ Combo formed!" if combo_formed(current.phases) else "")

        def make_toggle(task_id, index, refresh):
            def toggle() -> None:
                tasks.toggle_phase(task_id, index)
                refresh()
            return toggle

        for index, label in enumerate(PHASE_LABELS):
            button = ctk.CTkButton(
                buttons_row, text=label, width=80,
                fg_color=_EMPTY_BOX, hover_color=_EMPTY_BOX, text_color=text_color,
                command=make_toggle(task.id, index, refresh_card),
            )
            button.pack(side="left", padx=(0, 6))
            buttons.append(button)

        refresh_card()

    ctk.CTkLabel(
        frame,
        text="Plan, Work, Review — check them in any order. A full combo "
             "is just for fun; you still mark the task itself done on the "
             "Tasks tab.",
        text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11),
        justify="left", wraplength=400,
    ).pack(anchor="w", pady=(6, 0))
