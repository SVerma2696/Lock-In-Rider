"""Tests for build_task_picker_entries(), the pure label/id-mapping
logic behind the Home header's current-task picker (lock_in/ui.py).

No real Tk widget or display involved anywhere in this file -- same
precedent as test_ui_mirror.py: this is a plain function that takes a
list of open tasks and returns (dropdown values, label -> id map), so
it's tested directly without instantiating LockInApp/Tk.
_on_current_task_selected() is just `self._task_menu_ids.get(name)`, so
proving the map returned here is unambiguous also proves that lookup
resolves to the correct task id."""

import pytest

from lock_in.tasks import TaskStore
from lock_in.ui import build_task_picker_entries


@pytest.fixture
def store(tmp_path) -> TaskStore:
    return TaskStore(tmp_path / "tasks.json")


def test_no_open_tasks_yields_just_no_task(store):
    values, task_menu_ids = build_task_picker_entries(store.open())
    assert values == ["No task"]
    assert task_menu_ids == {}


def test_distinct_names_map_straight_through(store):
    t1 = store.add("Write the report")
    t2 = store.add("Review PR")
    values, task_menu_ids = build_task_picker_entries(store.open())
    assert values == ["No task", "Write the report", "Review PR"]
    assert task_menu_ids == {"Write the report": t1.id, "Review PR": t2.id}


def test_duplicate_task_names_get_distinct_disambiguated_labels(store):
    """Regression test: TaskStore.add() has no uniqueness check on name,
    so two open tasks can legitimately share a name (e.g. "Reading"
    typed twice for two different sessions). Before this fix, the
    picker's label -> id map was keyed by name alone, so the second
    insert silently collapsed onto the first and picking either
    dropdown entry could resolve to the wrong task id. This confirms
    the two identically-named tasks now get two distinct labels, each
    resolving back to its own, correct, different task id."""
    t1 = store.add("Reading")
    t2 = store.add("Reading")
    assert t1.id != t2.id  # sanity: these really are two different tasks

    values, task_menu_ids = build_task_picker_entries(store.open())

    # Two distinct dropdown entries, not one collapsed entry.
    assert values == ["No task", "Reading (1)", "Reading (2)"]
    assert len(set(values)) == len(values)

    # Each label resolves back to its own, correct, different task id --
    # this is exactly what _on_current_task_selected looks up.
    assert task_menu_ids["Reading (1)"] == t1.id
    assert task_menu_ids["Reading (2)"] == t2.id
    assert task_menu_ids["Reading (1)"] != task_menu_ids["Reading (2)"]


def test_duplicate_names_do_not_disambiguate_an_unrelated_third_name(store):
    """Only the colliding name gets a counter suffix -- a third,
    uniquely-named open task keeps its plain, unsuffixed label."""
    store.add("Reading")
    store.add("Reading")
    t3 = store.add("Emails")

    values, task_menu_ids = build_task_picker_entries(store.open())

    assert values == ["No task", "Reading (1)", "Reading (2)", "Emails"]
    assert task_menu_ids["Emails"] == t3.id


def test_generated_suffix_does_not_collide_with_a_literal_task_name(store):
    """Regression test: the auto-generated "(1)" suffix can land on a
    label another open task already owns literally -- nothing stops you
    naming a task "Reading (1)" by hand next to two called "Reading".
    Before this fix the later one silently overwrote the earlier one in
    the label -> id map, so one dropdown entry resolved to the wrong
    task id (and the other task was unreachable)."""
    t1 = store.add("Reading")
    t2 = store.add("Reading")
    t3 = store.add("Reading (1)")

    values, task_menu_ids = build_task_picker_entries(store.open())

    # Every dropdown entry is distinct...
    assert len(set(values)) == len(values)
    # ...and all three tasks are still reachable, each by its own label.
    assert len(task_menu_ids) == 3
    assert set(task_menu_ids.values()) == {t1.id, t2.id, t3.id}


def test_a_completed_task_is_excluded_and_does_not_affect_disambiguation(store):
    """open() already excludes done tasks (Task 1's contract) -- confirm
    a completed same-named task drops out of the picker entirely rather
    than still occupying a disambiguated slot."""
    t1 = store.add("Reading")
    t2 = store.add("Reading")
    store.complete(t2.id)

    values, task_menu_ids = build_task_picker_entries(store.open())

    assert values == ["No task", "Reading"]
    assert task_menu_ids == {"Reading": t1.id}
