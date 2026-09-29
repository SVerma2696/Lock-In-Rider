"""The picture cache hands back copies, so a caller can never spoil a
remembered picture, and the same inputs always give the same picture."""

from lock_in import visuals


def test_same_inputs_give_an_equal_but_separate_picture():
    visuals.make_panel_divider.cache_clear()
    first = visuals.make_panel_divider(200, 4, "#ff0000", "#00ff00", era="Reiwa")
    second = visuals.make_panel_divider(200, 4, "#ff0000", "#00ff00", era="Reiwa")
    assert first is not second
    assert first.tobytes() == second.tobytes()
    assert visuals.make_panel_divider.cache_info().hits == 1


def test_changing_a_copy_does_not_change_the_remembered_picture():
    glow = visuals.make_glow(12, 12, "#123456")
    before = glow.getpixel((6, 6))
    glow.putpixel((6, 6), (1, 2, 3, 4))
    assert visuals.make_glow(12, 12, "#123456").getpixel((6, 6)) == before


def test_different_inputs_give_different_pictures():
    a = visuals.render_padlock_glyph(32)
    b = visuals.render_padlock_glyph(48)
    assert a.size == (32, 32) and b.size == (48, 48)
