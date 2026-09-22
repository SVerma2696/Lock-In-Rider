from datetime import date, timedelta

from lock_in.tier5.gotchard import (
    BADGES,
    Progress,
    badge_sentence,
    earned_ids,
    longest_goal_run,
    newly_won,
    progress,
    saved_badges,
)

TODAY = date(2026, 9, 22)
HOUR = 3600
HARSH_WORDS = ("fail", "behind", "lost", "missed", "broke")


def _iso(days_ago: int, today: date = TODAY) -> str:
    return (today - timedelta(days=days_ago)).isoformat()


def _totals(*days_ago_and_seconds: tuple[int, int], today: date = TODAY) -> dict[str, int]:
    """_totals((0, 3600), (1, 3600)) -> today and yesterday, an hour each."""
    return {_iso(days_ago, today): seconds for days_ago, seconds in days_ago_and_seconds}


# --- BADGES -------------------------------------------------------------- #

def test_there_are_exactly_nine_badges():
    assert len(BADGES) == 9


def test_every_badge_has_a_different_id():
    ids = [badge.id for badge in BADGES]
    assert len(ids) == len(set(ids))


def test_the_badges_are_exactly_these_nine_ids_in_order():
    assert [badge.id for badge in BADGES] == [
        "first_step", "ten_blocks", "hour_day", "big_day", "ten_hours",
        "task_done", "goal_done", "three_days", "seven_days",
    ]


def test_every_badge_has_a_name_and_a_hint():
    for badge in BADGES:
        assert badge.name
        assert badge.hint


def test_no_badge_name_or_hint_is_harsh():
    for badge in BADGES:
        for word in HARSH_WORDS:
            assert word not in badge.name.lower(), badge.name
            assert word not in badge.hint.lower(), badge.hint


# --- longest_goal_run ------------------------------------------------------ #

def test_longest_goal_run_with_no_history_is_zero():
    assert longest_goal_run({}, HOUR) == 0


def test_longest_goal_run_counts_one_goal_day():
    assert longest_goal_run(_totals((0, HOUR)), HOUR) == 1


def test_longest_goal_run_counts_a_run_of_days_in_a_row():
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR))
    assert longest_goal_run(totals, HOUR) == 3


def test_longest_goal_run_picks_the_longer_of_two_runs_split_by_a_gap():
    totals = _totals(
        (0, HOUR), (1, HOUR),                # a 2-day run, ending today
        (5, HOUR), (6, HOUR), (7, HOUR),     # a 3-day run, further back
    )
    assert longest_goal_run(totals, HOUR) == 3


def test_a_day_exactly_at_the_goal_counts_and_one_second_under_does_not():
    totals = _totals((0, HOUR), (1, HOUR - 1))
    assert longest_goal_run(totals, HOUR) == 1


def test_longest_goal_run_across_a_month_boundary():
    today = date(2026, 10, 2)
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR), (3, HOUR), today=today)
    assert longest_goal_run(totals, HOUR) == 4


def test_longest_goal_run_across_a_year_boundary():
    today = date(2027, 1, 2)
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR), (3, HOUR), today=today)
    assert longest_goal_run(totals, HOUR) == 4


def test_longest_goal_run_over_a_very_long_history_does_not_loop_forever():
    totals = _totals(*[(days_ago, HOUR) for days_ago in range(400)])
    assert longest_goal_run(totals, HOUR) == 400


def test_a_bigger_goal_gives_a_shorter_run_for_the_same_history():
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR))
    assert longest_goal_run(totals, HOUR) == 3
    assert longest_goal_run(totals, 2 * HOUR) == 0


# --- progress ---------------------------------------------------------------- #

def test_progress_with_no_history_is_all_zero_except_tasks_done():
    result = progress({}, 0, HOUR, tasks_done=2)
    assert result == Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=0, tasks_done=2)


def test_progress_reads_blocks_best_day_and_total_from_a_small_history():
    totals = _totals((0, 30 * 60), (1, 2 * HOUR))
    result = progress(totals, block_count=5, goal_seconds=HOUR, tasks_done=1)
    assert result.blocks == 5
    assert result.best_day_seconds == 2 * HOUR
    assert result.total_seconds == 30 * 60 + 2 * HOUR
    assert result.longest_run == 1
    assert result.tasks_done == 1


# --- earned_ids --------------------------------------------------------------- #

def test_earned_ids_with_all_zero_progress_wins_nothing():
    assert earned_ids(Progress(0, 0, 0, 0, 0)) == []


def test_each_badge_turns_on_at_exactly_its_target():
    assert earned_ids(Progress(blocks=1, best_day_seconds=0, total_seconds=0, longest_run=0, tasks_done=0)) == ["first_step"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=3600, total_seconds=0, longest_run=0, tasks_done=0)) == ["hour_day"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=10800, total_seconds=0, longest_run=0, tasks_done=0)) == ["hour_day", "big_day"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=36000, longest_run=0, tasks_done=0)) == ["ten_hours"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=0, tasks_done=1)) == ["task_done"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=1, tasks_done=0)) == ["goal_done"]
    assert earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=3, tasks_done=0)) == ["goal_done", "three_days"]


def test_earned_ids_does_not_win_a_badge_one_below_its_target():
    assert "ten_blocks" not in earned_ids(Progress(blocks=9, best_day_seconds=0, total_seconds=0, longest_run=0, tasks_done=0))
    assert "hour_day" not in earned_ids(Progress(blocks=0, best_day_seconds=3599, total_seconds=0, longest_run=0, tasks_done=0))
    assert "big_day" not in earned_ids(Progress(blocks=0, best_day_seconds=10799, total_seconds=0, longest_run=0, tasks_done=0))
    assert "ten_hours" not in earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=35999, longest_run=0, tasks_done=0))
    assert "three_days" not in earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=2, tasks_done=0))
    assert "seven_days" not in earned_ids(Progress(blocks=0, best_day_seconds=0, total_seconds=0, longest_run=6, tasks_done=0))


def test_earned_ids_come_back_in_badge_order():
    rich = Progress(blocks=10, best_day_seconds=10800, total_seconds=36000, longest_run=7, tasks_done=1)
    assert earned_ids(rich) == [badge.id for badge in BADGES]


# --- saved_badges -------------------------------------------------------------- #

def test_saved_badges_returns_a_good_list_as_it_is():
    assert saved_badges(["first_step", "ten_blocks"]) == ["first_step", "ten_blocks"]


def test_saved_badges_gives_an_empty_list_for_the_wrong_kind_of_value():
    for bad in (None, 5, "first_step", {"first_step": True}, True, False):
        assert saved_badges(bad) == [], bad


def test_saved_badges_drops_entries_that_are_not_text():
    assert saved_badges(["first_step", 5, None, "ten_blocks"]) == ["first_step", "ten_blocks"]


def test_saved_badges_drops_repeats_keeping_the_first():
    assert saved_badges(["first_step", "ten_blocks", "first_step"]) == ["first_step", "ten_blocks"]


def test_saved_badges_keeps_names_it_does_not_recognize():
    assert saved_badges(["first_step", "made_up_badge"]) == ["first_step", "made_up_badge"]


# --- newly_won ----------------------------------------------------------------- #

def test_newly_won_is_empty_when_nothing_is_new():
    assert newly_won(["first_step"], ["first_step"]) == []


def test_newly_won_finds_the_new_ones():
    assert newly_won(["first_step", "ten_blocks"], ["first_step"]) == ["ten_blocks"]


def test_newly_won_when_everything_is_new():
    assert newly_won(["first_step", "ten_blocks"], []) == ["first_step", "ten_blocks"]


def test_newly_won_keeps_badge_order():
    assert newly_won(["ten_blocks", "first_step"], []) == ["ten_blocks", "first_step"]


# --- badge_sentence -------------------------------------------------------------- #

def test_badge_sentence_for_exactly_one_new_badge():
    assert badge_sentence(3, 9, ["Big Day"]) == "New! You won Big Day!"


def test_badge_sentence_for_more_than_one_new_badge():
    assert badge_sentence(4, 9, ["Big Day", "Task Done"]) == "New! You won 2 badges!"


def test_badge_sentence_with_none_won_and_nothing_new():
    assert badge_sentence(0, 9, []) == "Do a focus block to win your first badge."


def test_badge_sentence_with_everything_won_and_nothing_new():
    assert badge_sentence(9, 9, []) == "You got them all! Wow!"


def test_badge_sentence_with_some_won_and_nothing_new():
    assert badge_sentence(3, 9, []) == "You have 3 of 9. Keep going!"


def test_badge_sentence_new_beats_having_everything():
    assert badge_sentence(9, 9, ["Seven in a Row"]) == "New! You won Seven in a Row!"


def test_no_badge_sentence_is_ever_harsh():
    sentences = [badge_sentence(have, 9, []) for have in range(0, 10)]
    sentences += [badge_sentence(1, 9, ["X"]), badge_sentence(2, 9, ["X", "Y"])]
    for sentence in sentences:
        for word in HARSH_WORDS:
            assert word not in sentence.lower(), sentence


# --- wiring --------------------------------------------------------------- #

def test_badge_cards_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, gotchard
    assert TIER5_BUILDERS["badge_cards"] is gotchard.build


def test_badge_cards_has_the_badges_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["badge_cards"] == "Badges"


def test_gotchard_builder_accepts_config():
    """ui.py passes config= to every builder, same check Geats' plan
    added for the other seven -- this pins Gotchard to the same rule."""
    import inspect
    from lock_in.tier5 import gotchard
    assert "config" in inspect.signature(gotchard.build).parameters
