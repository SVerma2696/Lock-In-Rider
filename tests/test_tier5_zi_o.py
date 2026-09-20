from lock_in.tasks import Task
from lock_in.tier5.zi_o import build_reassign_choices


def _task(task_id: str, name: str) -> Task:
    return Task(id=task_id, name=name)


def test_no_task_is_always_first_and_means_none():
    words, ids = build_reassign_choices([])
    assert words == ["No task"]
    assert ids == {"No task": None}


def test_each_task_gets_its_own_name_and_id():
    words, ids = build_reassign_choices([_task("a1", "Read"), _task("b2", "Write")])
    assert words == ["No task", "Read", "Write"]
    assert ids["Read"] == "a1"
    assert ids["Write"] == "b2"


def test_tasks_are_listed_in_name_order_ignoring_capitals():
    words, _ = build_reassign_choices([_task("a", "zebra"), _task("b", "Apple")])
    assert words == ["No task", "Apple", "zebra"]


def test_two_tasks_with_the_same_name_get_different_words():
    words, ids = build_reassign_choices([_task("a1", "Homework"), _task("b2", "Homework")])
    assert words == ["No task", "Homework", "Homework (2)"]
    # Picking the second one must give the SECOND task, not the first.
    assert ids["Homework"] == "a1"
    assert ids["Homework (2)"] == "b2"


def test_a_made_up_suffix_never_steals_a_real_task_name():
    tasks = [_task("a", "Homework"), _task("b", "Homework"), _task("c", "Homework (2)")]
    words, ids = build_reassign_choices(tasks)
    assert len(words) == len(set(words)) == 4
    assert sorted(v for v in ids.values() if v is not None) == ["a", "b", "c"]


def test_a_task_named_no_task_does_not_hide_the_real_no_task_choice():
    words, ids = build_reassign_choices([_task("a", "No task")])
    assert ids["No task"] is None
    assert ids["No task (2)"] == "a"
