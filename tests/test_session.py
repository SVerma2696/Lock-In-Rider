from lock_in.config import Config
from lock_in.session import DEFAULT_TERMINOLOGY, Event, Phase, label_for, PomodoroSession


def test_phase_labels_are_serious_tokusatsu_tone():
    assert Phase.IDLE.label == "Standing By"
    assert Phase.FOCUS.label == "Henshin"
    assert Phase.SHORT_BREAK.label == "Recovery"
    assert Phase.LONG_BREAK.label == "Stand Down"


def test_professional_phase_labels_are_plain():
    assert Phase.IDLE.professional_label == "Idle"
    assert Phase.FOCUS.professional_label == "Focus"
    assert Phase.SHORT_BREAK.professional_label == "Short Break"
    assert Phase.LONG_BREAK.professional_label == "Long Break"


def test_break_phases_are_still_flagged_as_breaks():
    assert Phase.SHORT_BREAK.is_break
    assert Phase.LONG_BREAK.is_break
    assert not Phase.FOCUS.is_break
    assert not Phase.IDLE.is_break


def test_default_terminology_is_professional():
    assert DEFAULT_TERMINOLOGY == "professional"
    assert label_for(Phase.FOCUS) == "Focus"


def test_label_for_tokusatsu_gives_the_flavored_name():
    assert label_for(Phase.FOCUS, "tokusatsu") == "Henshin"
    assert label_for(Phase.IDLE, "tokusatsu") == "Standing By"


def test_label_for_unknown_terminology_falls_back_to_professional():
    assert label_for(Phase.FOCUS, "not a real mode") == "Focus"


def test_blackrx_manual_breaks_prevents_auto_starting_the_next_break():
    config = Config(focus_minutes=1, short_break_minutes=1, blocks_until_long_break=4,
                     auto_start_breaks=True, blackrx_manual_breaks=True)

    # Use a controllable fake clock to drive the session forward
    clock_value = [0.0]  # Use a list so we can mutate it in the nested function

    def fake_clock():
        return clock_value[0]

    session = PomodoroSession(config, clock=fake_clock)
    session.toggle()  # start focus (enters FOCUS phase)

    # Drive the clock forward to just before the phase ends (60 seconds for 1 minute)
    clock_value[0] = 59.9
    session.tick()  # still ticking in the focus phase
    assert session.is_running
    assert session.phase == Phase.FOCUS

    # Drive the clock to the exact end time - this tick triggers _advance()
    clock_value[0] = 60.0
    events = session.tick()

    # _advance() always reports the focus block ending, then the break
    # being entered -- regardless of whether that break auto-starts.
    assert events == [Event.PHASE_ENDED, Event.PHASE_STARTED]

    # At this point, we should have entered the break phase without auto-starting
    assert session.phase == Phase.SHORT_BREAK
    assert not session.is_running  # break entered but NOT auto-started
