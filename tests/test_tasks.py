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


def test_malformed_subtask_entry_is_skipped_and_task_is_kept(tmp_path):
    """Regression test: a malformed subtask entry should not crash load()
    or cause the parent task to be lost. The malformed subtask is skipped,
    but the task itself and its valid subtasks are preserved."""
    import json

    path = tmp_path / "tasks.json"
    # Write a valid task plus one task with a malformed subtask (missing "text").
    payload = {
        "tasks": [
            {
                "id": "task1",
                "name": "Valid task",
                "subtasks": [{"id": "sub1", "text": "Good subtask", "done": False}],
                "status": "todo",
                "created_at": "2024-01-01T10:00:00",
                "completed_at": None,
            },
            {
                "id": "task2",
                "name": "Task with malformed subtask",
                "subtasks": [
                    {"id": "sub2", "text": "Good subtask", "done": False},
                    {"id": "sub3"},  # Missing "text" -- malformed
                ],
                "status": "todo",
                "created_at": "2024-01-01T10:00:00",
                "completed_at": None,
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    # TaskStore should load successfully without raising,
    # skipping the malformed subtask but keeping the task.
    store = TaskStore(path)
    tasks = store.all()
    assert len(tasks) == 2
    assert tasks[0].name == "Valid task"
    assert len(tasks[0].subtasks) == 1
    assert tasks[1].name == "Task with malformed subtask"
    # Only the good subtask is kept; the malformed one is skipped.
    assert len(tasks[1].subtasks) == 1
    assert tasks[1].subtasks[0].text == "Good subtask"


@pytest.mark.parametrize("root", ["[]", "5", '"hello"', "null", "true"])
def test_non_dict_root_starts_fresh_instead_of_crashing(tmp_path, root):
    """Regression test: valid JSON of the wrong SHAPE used to raise an
    uncaught AttributeError out of load() (raw.get() on a list/int),
    which crashed LockInApp.__init__ -- the app simply wouldn't open.
    The module's promise is 'a missing or broken file just means start
    empty', so a non-dict root has to land there too."""
    path = tmp_path / "tasks.json"
    path.write_text(root, encoding="utf-8")
    store = TaskStore(path)  # must not raise
    assert store.all() == []


def test_non_dict_task_entry_is_skipped_and_valid_tasks_are_kept(tmp_path):
    """Regression test: a null/string/number sitting in the tasks list
    used to raise AttributeError from item.get(), losing every other
    task with it (and crashing startup). The junk entries are skipped;
    the real tasks around them survive."""
    import json

    path = tmp_path / "tasks.json"
    payload = {
        "tasks": [
            None,
            {
                "id": "task1",
                "name": "Valid task",
                "subtasks": [],
                "status": "todo",
                "created_at": "2024-01-01T10:00:00",
                "completed_at": None,
            },
            "hello",
            42,
            {
                "id": "task2",
                "name": "Second valid task",
                "subtasks": [],
                "status": "in_progress",
                "created_at": "2024-01-01T11:00:00",
                "completed_at": None,
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    store = TaskStore(path)  # must not raise
    tasks = store.all()
    assert [t.name for t in tasks] == ["Valid task", "Second valid task"]
    assert tasks[1].status == TaskStatus.IN_PROGRESS


def test_non_list_tasks_value_starts_fresh_instead_of_crashing(tmp_path):
    """Same family: {"tasks": 5} would blow up iterating an int."""
    path = tmp_path / "tasks.json"
    path.write_text('{"tasks": 5}', encoding="utf-8")
    store = TaskStore(path)  # must not raise
    assert store.all() == []


def test_starting_a_focus_block_on_a_task_flips_it_to_in_progress(store):
    """Mirrors what ui.py's _on_toggle does: set_status(..., IN_PROGRESS)
    is called when a task is picked and Start is pressed. This test
    pins down the store-level contract that wiring depends on."""
    task = store.add("Write the report")
    store.set_status(task.id, TaskStatus.IN_PROGRESS)
    assert store.all()[0].status == TaskStatus.IN_PROGRESS


def test_a_completed_block_does_not_move_an_in_progress_task_to_done(store):
    """The other half of the same rule: nothing about a block finishing
    should ever call complete() on its own. This test simply asserts
    that calling set_status(IN_PROGRESS) alone -- with no complete()
    call -- leaves the task shy of done, documenting that ui.py's
    phase-ended code path (Task 6) must never call complete()."""
    task = store.add("Write the report")
    store.set_status(task.id, TaskStatus.IN_PROGRESS)
    assert store.all()[0].status != TaskStatus.DONE
