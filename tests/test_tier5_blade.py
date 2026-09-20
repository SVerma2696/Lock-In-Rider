from lock_in.tasks import Task, TaskStatus
from lock_in.tier5.blade import group_by_status


def _task(name: str, status: TaskStatus) -> Task:
    return Task(id=name, name=name, status=status)


def test_group_by_status_returns_all_three_keys_for_an_empty_list():
    result = group_by_status([])
    assert result == {TaskStatus.TODO: [], TaskStatus.IN_PROGRESS: [], TaskStatus.DONE: []}


def test_group_by_status_sorts_into_the_correct_buckets():
    todo = _task("a", TaskStatus.TODO)
    doing = _task("b", TaskStatus.IN_PROGRESS)
    done = _task("c", TaskStatus.DONE)
    result = group_by_status([todo, doing, done])
    assert result[TaskStatus.TODO] == [todo]
    assert result[TaskStatus.IN_PROGRESS] == [doing]
    assert result[TaskStatus.DONE] == [done]


def test_group_by_status_keeps_the_order_inside_a_bucket():
    first = _task("first", TaskStatus.TODO)
    second = _task("second", TaskStatus.TODO)
    result = group_by_status([first, second])
    assert result[TaskStatus.TODO] == [first, second]


def test_group_by_status_with_only_one_status_still_returns_all_three_keys():
    only = _task("only", TaskStatus.DONE)
    result = group_by_status([only])
    assert result[TaskStatus.TODO] == []
    assert result[TaskStatus.IN_PROGRESS] == []
    assert result[TaskStatus.DONE] == [only]
