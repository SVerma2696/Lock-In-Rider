from datetime import date, timedelta

from lock_in.tier5.geats import (
    days_in_a_row,
    goal_sentence,
    stepped_goal,
    streak_days,
    streak_sentence,
    week_dots,
)

TODAY = date(2026, 9, 21)
HOUR = 3600


def _iso(days_ago: int, today: date = TODAY) -> str:
    return (today - timedelta(days=days_ago)).isoformat()


def _totals(*days_ago_and_seconds: tuple[int, int], today: date = TODAY) -> dict[str, int]:
    """_totals((0, 3600), (1, 3600)) -> today and yesterday, an hour each."""
    return {_iso(days_ago, today): seconds for days_ago, seconds in days_ago_and_seconds}


# --- streak_days ------------------------------------------------------- #

def test_streak_with_no_history_is_zero():
    assert streak_days({}, TODAY, HOUR) == 0


def test_streak_counts_today_when_today_is_done():
    assert streak_days(_totals((0, HOUR)), TODAY, HOUR) == 1


def test_streak_counts_every_done_day_in_a_row_ending_today():
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 3


def test_streak_ends_yesterday_when_today_is_not_done_yet():
    """Part-way through the day must never show a scary zero."""
    totals = _totals((0, 600), (1, HOUR), (2, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 2


def test_streak_ends_yesterday_when_today_has_no_blocks_at_all():
    totals = _totals((1, HOUR), (2, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 2


def test_streak_is_zero_when_today_and_yesterday_both_missed():
    totals = _totals((0, 600), (2, HOUR), (3, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 0


def test_a_day_exactly_at_the_goal_is_done():
    assert streak_days(_totals((0, HOUR)), TODAY, HOUR) == 1


def test_a_day_one_second_under_the_goal_is_not_done():
    totals = _totals((0, HOUR - 1), (1, HOUR))
    # Today is not done yet, so the streak ends yesterday: 1, not 2.
    assert streak_days(totals, TODAY, HOUR) == 1


def test_a_missed_day_ends_the_streak():
    totals = _totals((0, HOUR), (1, HOUR), (3, HOUR))   # day 2 is missing
    assert streak_days(totals, TODAY, HOUR) == 2


def test_streak_across_a_month_boundary():
    today = date(2026, 10, 2)
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR), (3, HOUR), today=today)
    assert streak_days(totals, today, HOUR) == 4   # Oct 2, Oct 1, Sep 30, Sep 29


def test_streak_across_a_year_boundary():
    today = date(2027, 1, 2)
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR), (3, HOUR), today=today)
    assert streak_days(totals, today, HOUR) == 4   # Jan 2, Jan 1, Dec 31, Dec 30


def test_a_very_long_streak_is_counted_and_stops_at_the_first_day():
    totals = _totals(*[(days_ago, HOUR) for days_ago in range(400)])
    assert streak_days(totals, TODAY, HOUR) == 400


def test_a_bigger_goal_re_judges_old_days():
    """One goal number for every day: the same history gives a different
    streak at a different goal."""
    totals = _totals((0, HOUR), (1, HOUR), (2, HOUR))
    assert streak_days(totals, TODAY, HOUR) == 3
    assert streak_days(totals, TODAY, 2 * HOUR) == 0
    assert streak_days(totals, TODAY, HOUR // 2) == 3


# --- week_dots --------------------------------------------------------- #

def test_week_dots_always_returns_exactly_seven_entries():
    assert len(week_dots({}, TODAY, HOUR)) == 7


def test_week_dots_are_oldest_to_newest_ending_on_today():
    days = [day for day, _ in week_dots({}, TODAY, HOUR)]
    assert days[-1] == TODAY
    assert days[0] == TODAY - timedelta(days=6)
    assert days == sorted(days)


def test_week_dots_with_no_history_are_all_not_done():
    assert [done for _, done in week_dots({}, TODAY, HOUR)] == [False] * 7


def test_week_dots_mark_the_days_that_reached_the_goal():
    totals = _totals((0, HOUR), (1, 100), (2, 2 * HOUR), (6, HOUR))
    flags = [done for _, done in week_dots(totals, TODAY, HOUR)]
    # oldest -> newest: 6 ago, 5, 4, 3, 2, 1, today
    assert flags == [True, False, False, False, True, False, True]


def test_week_dots_exactly_at_the_goal_is_done_and_one_second_under_is_not():
    totals = _totals((0, HOUR), (1, HOUR - 1))
    flags = [done for _, done in week_dots(totals, TODAY, HOUR)]
    assert flags[-1] is True     # today, exactly at the goal
    assert flags[-2] is False    # yesterday, one second under


# --- goal_sentence ----------------------------------------------------- #

def test_goal_sentence_when_nothing_is_done_yet():
    assert goal_sentence(0, HOUR) == "Start a focus block to fill the bar."


def test_goal_sentence_part_way_says_how_much_is_left():
    assert goal_sentence(40 * 60, HOUR) == "20m to go. You can do it!"


def test_goal_sentence_shows_hours_when_a_lot_is_left():
    assert goal_sentence(10 * 60, 2 * HOUR) == "1h 50m to go. You can do it!"


def test_goal_sentence_rounds_the_time_left_up_to_a_whole_minute():
    # 30 seconds short: never "0m to go".
    assert goal_sentence(HOUR - 30, HOUR) == "1m to go. You can do it!"
    # 61 seconds short is 2 minutes, rounded up.
    assert goal_sentence(HOUR - 61, HOUR) == "2m to go. You can do it!"


def test_goal_sentence_when_the_goal_is_reached():
    assert goal_sentence(HOUR, HOUR) == "You did it! Goal done for today. Yay!"


def test_goal_sentence_when_the_goal_is_beaten():
    assert goal_sentence(2 * HOUR, HOUR) == "You did it! Goal done for today. Yay!"


# --- days_in_a_row ----------------------------------------------------- #

def test_days_in_a_row_is_singular_for_one():
    assert days_in_a_row(1) == "1 day in a row"


def test_days_in_a_row_is_plural_for_zero_and_many():
    assert days_in_a_row(0) == "0 days in a row"
    assert days_in_a_row(5) == "5 days in a row"


# --- streak_sentence --------------------------------------------------- #

def test_streak_sentence_with_no_streak():
    assert streak_sentence(0, False) == "No streak yet. Reach your goal today to start one!"


def test_streak_sentence_when_today_is_done():
    assert streak_sentence(5, True) == "5 days in a row. Wow!"
    assert streak_sentence(1, True) == "1 day in a row. Wow!"


def test_streak_sentence_when_today_is_not_done_yet():
    assert streak_sentence(5, False) == "5 days in a row. Do your goal today to keep it going!"
    assert streak_sentence(1, False) == "1 day in a row. Do your goal today to keep it going!"


def test_no_sentence_is_ever_harsh():
    words = ("fail", "behind", "lost", "broke", "worse")
    sentences = [streak_sentence(n, done) for n in range(0, 6) for done in (True, False)]
    sentences += [goal_sentence(s, HOUR) for s in (0, 1, 30, 1800, 3599, 3600, 7200)]
    for sentence in sentences:
        for word in words:
            assert word not in sentence.lower(), sentence


# --- stepped_goal ------------------------------------------------------ #

def test_stepped_goal_goes_up_and_down_by_fifteen_minutes():
    assert stepped_goal(60, +1) == 75
    assert stepped_goal(60, -1) == 45


def test_stepped_goal_stops_at_fifteen_minutes():
    assert stepped_goal(30, -1) == 15
    assert stepped_goal(15, -1) == 15


def test_stepped_goal_stops_at_twelve_hours():
    assert stepped_goal(705, +1) == 720
    assert stepped_goal(720, +1) == 720


def test_stepped_goal_from_a_number_that_is_not_a_multiple_of_fifteen():
    assert stepped_goal(20, +1) == 35
    assert stepped_goal(20, -1) == 15    # 5 is clamped up to the floor
    assert stepped_goal(718, +1) == 720  # 733 is clamped down to the ceiling


# --- wiring ------------------------------------------------------------ #

def test_every_tier5_builder_accepts_config():
    """ui.py passes config= to every builder, so all of them must take it."""
    import inspect
    from lock_in.tier5 import TIER5_BUILDERS
    for effect, builder in TIER5_BUILDERS.items():
        assert "config" in inspect.signature(builder).parameters, effect


def test_goal_streak_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, geats
    assert TIER5_BUILDERS["goal_streak"] is geats.build


def test_goal_streak_has_the_goal_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["goal_streak"] == "Goal"
