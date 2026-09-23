from lock_in.tier5.ooo import combo_formed


def test_combo_formed_when_all_three_are_true():
    assert combo_formed([True, True, True]) is True


def test_combo_formed_false_when_any_one_is_false():
    assert combo_formed([False, True, True]) is False
    assert combo_formed([True, False, True]) is False
    assert combo_formed([True, True, False]) is False


def test_combo_formed_false_when_all_are_false():
    assert combo_formed([False, False, False]) is False


# --- wiring --------------------------------------------------------------- #

def test_phase_combo_is_registered_with_the_tier5_builders():
    from lock_in.tier5 import TIER5_BUILDERS, ooo
    assert TIER5_BUILDERS["phase_combo"] is ooo.build


def test_phase_combo_has_the_combo_tab_label():
    from lock_in.ui import _TIER5_TAB_LABELS
    assert _TIER5_TAB_LABELS["phase_combo"] == "Combo"


def test_ooo_builder_accepts_the_standard_tier5_signature():
    import inspect
    from lock_in.tier5 import ooo
    params = inspect.signature(ooo.build).parameters
    for name in ("parent", "history", "tasks", "theme", "appearance_mode", "config"):
        assert name in params
