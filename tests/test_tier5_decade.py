from lock_in.tasks import TaskStore
from lock_in.tier5.decade import ranked_tasks


def test_ranked_tasks_sorts_by_seconds_descending(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    t1 = tasks.add("Small task")
    t2 = tasks.add("Big task")
    totals = {t1.id: 300, t2.id: 1500}
    assert ranked_tasks(totals, tasks) == [("Big task", 1500), ("Small task", 300)]


def test_ranked_tasks_resolves_untagged_time_as_no_task(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    totals = {None: 600}
    assert ranked_tasks(totals, tasks) == [("No task", 600)]


def test_ranked_tasks_empty_input_returns_empty_list(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    assert ranked_tasks({}, tasks) == []


def test_ranked_tasks_keeps_two_deleted_tasks_as_separate_rows(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    totals = {"gone-1": 400, "gone-2": 900}
    result = ranked_tasks(totals, tasks)
    assert result == [("Deleted task", 900), ("Deleted task", 400)]


def test_ranked_tasks_caps_at_ten(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    totals = {f"task-{i}": (20 - i) * 60 for i in range(15)}
    result = ranked_tasks(totals, tasks)
    assert len(result) == 10
    # The 11th-highest (task-10, 10*60=600s) and everything smaller must
    # not appear -- only the top 10 by seconds do.
    assert all(seconds >= 11 * 60 for _, seconds in result)
