"""
task_picker.py
==============
The words in the "current task" menu on the Focus page, and which task
each one points to. Kept apart from the window code so it can be tested
by itself (tests/test_task_picker.py).
"""

from __future__ import annotations

from .tasks import Task

# The first choice in the menu: focus blocks that count toward no task.
NO_TASK_LABEL = "No task"


def build_task_picker_entries(open_tasks: list[Task]) -> tuple[list[str], dict]:
    """Turns a list of open tasks into (dropdown values, label -> id map)
    for the current-task picker.

    `TaskStore.add()` has no uniqueness check on `name`, so two open
    tasks can legitimately share the same display name (e.g. "Reading"
    typed twice for two different sessions). A dict keyed by name alone
    would silently collapse those into whichever one was inserted last,
    so picking either one from the dropdown would resolve to the wrong
    task id. To keep the label -> id lookup unambiguous, a name that
    collides among the currently-open tasks gets a "(2)", "(3)", ...
    counter suffix appended to its displayed label -- the id mapping is
    otherwise untouched, and TaskStore itself is never involved.

    That generated suffix can itself collide with a DIFFERENT open task's
    literal name (nothing stops you naming a task "Reading (1)" by hand
    alongside two tasks both called "Reading"), so every label is checked
    against the ones already handed out and the counter keeps climbing
    until it lands on one nobody is using.

    Kept free of Tk (like flip_pack_kwargs et al. above) so it can be
    unit tested directly without a live LockInApp/Tk instance."""
    name_counts: dict = {}
    for t in open_tasks:
        name_counts[t.name] = name_counts.get(t.name, 0) + 1

    seen_so_far: dict = {}
    task_menu_ids: dict = {}
    values = [NO_TASK_LABEL]
    for t in open_tasks:
        if name_counts[t.name] > 1:
            seen_so_far[t.name] = seen_so_far.get(t.name, 0) + 1
            counter = seen_so_far[t.name]
            label = f"{t.name} ({counter})"
        else:
            counter = 0
            label = t.name
        # Whether the label came out of the suffix branch or is a plain
        # name, it only goes in the map once it's provably unused --
        # otherwise the later task would silently overwrite the earlier
        # one's entry and the dropdown would resolve to the wrong id.
        while label in task_menu_ids:
            counter += 1
            label = f"{t.name} ({counter})"
        task_menu_ids[label] = t.id
        values.append(label)
    return values, task_menu_ids
