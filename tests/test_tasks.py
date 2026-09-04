"""Tests for the task list backing the Tasks tab and Tier 5's Riders."""

import pytest

from lock_in.tasks import Subtask, Task, TaskStatus, TaskStore


@pytest.fixture
def store(tmp_path) -> TaskStore:
    return TaskStore(tmp_path / "tasks.json")


def test_new_task_store_starts_empty(store):
    assert store.all() == []


def test_add_creates_a_todo_task(store):
    task = store.add("Write the Tier 5 spec")
    assert task.name == "Write the Tier 5 spec"
    assert task.status == TaskStatus.TODO
    assert task.id
    assert task.subtasks == []
    assert len(store.all()) == 1


def test_add_persists_across_a_reload(tmp_path):
    path = tmp_path / "tasks.json"
    store1 = TaskStore(path)
    store1.add("Ship it")
    store2 = TaskStore(path)
    assert len(store2.all()) == 1
    assert store2.all()[0].name == "Ship it"


def test_add_subtask_appends_to_the_task(store):
    task = store.add("Big task")
    subtask = store.add_subtask(task.id, "First step")
    assert subtask is not None
    assert subtask.done is False
    reloaded = store.all()[0]
    assert len(reloaded.subtasks) == 1
    assert reloaded.subtasks[0].text == "First step"


def test_add_subtask_on_missing_task_returns_none(store):
    assert store.add_subtask("nope", "text") is None


def test_toggle_subtask_flips_done(store):
    task = store.add("Task")
    subtask = store.add_subtask(task.id, "Step")
    assert store.toggle_subtask(task.id, subtask.id) is True
    assert store.all()[0].subtasks[0].done is True
    store.toggle_subtask(task.id, subtask.id)
    assert store.all()[0].subtasks[0].done is False


def test_toggle_subtask_on_missing_ids_returns_false(store):
    assert store.toggle_subtask("nope", "nope") is False


def test_set_status_changes_status(store):
    task = store.add("Task")
    assert store.set_status(task.id, TaskStatus.IN_PROGRESS) is True
    assert store.all()[0].status == TaskStatus.IN_PROGRESS


def test_set_status_on_missing_task_returns_false(store):
    assert store.set_status("nope", TaskStatus.DONE) is False


def test_set_status_never_touches_completed_at(store):
    """Regression test: only complete() should ever set completed_at.
    A plain status change (e.g. todo -> in_progress on Start) must not."""
    task = store.add("Task")
    store.set_status(task.id, TaskStatus.IN_PROGRESS)
    assert store.all()[0].completed_at is None


def test_complete_sets_status_and_completed_at(store):
    task = store.add("Task")
    assert store.complete(task.id) is True
    reloaded = store.all()[0]
    assert reloaded.status == TaskStatus.DONE
    assert reloaded.completed_at is not None


def test_complete_on_missing_task_returns_false(store):
    assert store.complete("nope") is False


def test_delete_removes_the_task(store):
    task = store.add("Task")
    assert store.delete(task.id) is True
    assert store.all() == []


def test_delete_missing_task_returns_false(store):
    assert store.delete("nope") is False


def test_open_returns_todo_and_in_progress_only(store):
    t1 = store.add("Todo task")
    t2 = store.add("In progress task")
    store.set_status(t2.id, TaskStatus.IN_PROGRESS)
    t3 = store.add("Done task")
    store.complete(t3.id)
    open_ids = {t.id for t in store.open()}
    assert open_ids == {t1.id, t2.id}


def test_done_returns_only_completed_tasks(store):
    t1 = store.add("Todo")
    t2 = store.add("Done")
    store.complete(t2.id)
    assert [t.id for t in store.done()] == [t2.id]


def test_corrupted_file_starts_fresh(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text("{ not valid json", encoding="utf-8")
    store = TaskStore(path)
    assert store.all() == []


def test_missing_file_starts_empty(tmp_path):
    store = TaskStore(tmp_path / "does_not_exist.json")
    assert store.all() == []
