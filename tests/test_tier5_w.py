from datetime import date, timedelta

from lock_in.tier5.w import compare_sentence, week_pairs

TODAY = date(2026, 9, 21)


def _iso(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).isoformat()


# --- week_pairs -------------------------------------------------------- #

def test_week_pairs_always_returns_exactly_seven_entries():
    assert len(week_pairs({}, TODAY)) == 7


def test_week_pairs_are_oldest_to_newest_ending_on_today():
    days = [day for day, _, _ in week_pairs({}, TODAY)]
    assert days[-1] == TODAY
    assert days[0] == TODAY - timedelta(days=6)
    assert days == sorted(days)


def test_week_pairs_with_no_history_are_all_zero():
    assert all(last == 0 and this == 0 for _, last, this in week_pairs({}, TODAY))


def test_week_pairs_a_block_today_lands_in_the_this_week_column():
    assert week_pairs({_iso(0): 600}, TODAY)[-1] == (TODAY, 0, 600)


def test_week_pairs_a_block_seven_days_ago_lands_in_the_last_week_column():
    assert week_pairs({_iso(7): 900}, TODAY)[-1] == (TODAY, 900, 0)


def test_week_pairs_each_day_pairs_with_the_same_day_a_week_earlier():
    totals = {_iso(3): 100, _iso(10): 200}
    day, last, this = week_pairs(totals, TODAY)[3]
    assert day == TODAY - timedelta(days=3)
    assert (last, this) == (200, 100)


def test_week_pairs_the_oldest_day_counted_is_thirteen_days_back():
    assert week_pairs({_iso(13): 42}, TODAY)[0] == (TODAY - timedelta(days=6), 42, 0)


def test_week_pairs_ignores_blocks_older_than_fourteen_days():
    pairs = week_pairs({_iso(14): 5000, _iso(20): 5000}, TODAY)
    assert all(last == 0 and this == 0 for _, last, this in pairs)


def test_week_pairs_pairs_correctly_across_a_month_boundary():
    today = date(2026, 3, 3)
    pairs = week_pairs({"2026-02-28": 100, "2026-02-21": 300}, today)
    assert pairs[3] == (date(2026, 2, 28), 300, 100)


def test_week_pairs_pairs_correctly_across_a_year_boundary():
    today = date(2027, 1, 2)
    pairs = week_pairs({"2026-12-31": 100, "2026-12-24": 300}, today)
    assert pairs[4] == (date(2026, 12, 31), 300, 100)


# --- compare_sentence -------------------------------------------------- #

def test_compare_sentence_when_this_week_is_more():
    assert compare_sentence(this_seconds=6000, last_seconds=0) == (
        "You did 1h 40m MORE than last week. Yay!"
    )


def test_compare_sentence_when_this_week_is_less():
    assert compare_sentence(this_seconds=3600, last_seconds=5400) == (
        "That's 30m less than last week. You can do it!"
    )


def test_compare_sentence_when_this_week_is_zero_but_last_week_was_not():
    assert compare_sentence(this_seconds=0, last_seconds=16200) == (
        "That's 4h 30m less than last week. You can do it!"
    )


def test_compare_sentence_when_the_weeks_are_equal():
    assert compare_sentence(this_seconds=3600, last_seconds=3600) == (
        "Same as last week. Nice and steady!"
    )


def test_compare_sentence_a_gap_of_59_seconds_counts_as_the_same():
    assert compare_sentence(this_seconds=3659, last_seconds=3600) == (
        "Same as last week. Nice and steady!"
    )
    assert compare_sentence(this_seconds=3600, last_seconds=3659) == (
        "Same as last week. Nice and steady!"
    )


def test_compare_sentence_a_gap_of_exactly_60_seconds_is_more_or_less():
    assert compare_sentence(this_seconds=3660, last_seconds=3600) == (
        "You did 1m MORE than last week. Yay!"
    )
    assert compare_sentence(this_seconds=3600, last_seconds=3660) == (
        "That's 1m less than last week. You can do it!"
    )


def test_compare_sentence_when_both_weeks_are_empty():
    assert compare_sentence(this_seconds=0, last_seconds=0) == (
        "No focus blocks in the last 14 days. Start one and it shows up here."
    )


def test_compare_sentence_is_never_harsh():
    for this_seconds, last_seconds in [(0, 9000), (60, 9000), (100, 5000), (0, 61)]:
        text = compare_sentence(this_seconds, last_seconds).lower()
        for scary_word in ("behind", "worse", "fail"):
            assert scary_word not in text


# --- wiring ------------------------------------------------------------- #

def test_week_compare_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, w
    assert TIER5_BUILDERS["week_compare"] is w.build


def test_week_compare_has_the_week_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["week_compare"] == "Week"
