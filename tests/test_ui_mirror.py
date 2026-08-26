"""Tests for the pure argument-flipping logic behind Ryuki's mirror
flip. No real Tk widget or display involved anywhere in this file --
these are plain functions that take a kwargs dict and return one."""

from lock_in.ui import flip_pack_kwargs, flip_place_kwargs, flip_grid_kwargs


def test_pack_side_left_becomes_right_when_mirrored():
    assert flip_pack_kwargs(True, {"side": "left"}) == {"side": "right"}


def test_pack_side_right_becomes_left_when_mirrored():
    assert flip_pack_kwargs(True, {"side": "right"}) == {"side": "left"}


def test_pack_side_top_is_unchanged_when_mirrored():
    assert flip_pack_kwargs(True, {"side": "top"}) == {"side": "top"}


def test_pack_anchor_w_becomes_e_when_mirrored():
    assert flip_pack_kwargs(True, {"anchor": "w"}) == {"anchor": "e"}


def test_pack_kwargs_unchanged_when_not_mirrored():
    kwargs = {"side": "left", "anchor": "w", "pady": 6}
    assert flip_pack_kwargs(False, kwargs) == kwargs


def test_pack_other_kwargs_pass_through_untouched():
    result = flip_pack_kwargs(True, {"side": "left", "pady": 6, "fill": "x"})
    assert result == {"side": "right", "pady": 6, "fill": "x"}


def test_place_relx_mirrors_around_the_center_when_mirrored():
    assert flip_place_kwargs(True, {"relx": 0.18}) == {"relx": 0.82}


def test_place_relx_at_center_is_unchanged_when_mirrored():
    result = flip_place_kwargs(True, {"relx": 0.5})
    assert result["relx"] == 0.5


def test_place_kwargs_unchanged_when_not_mirrored():
    kwargs = {"relx": 0.18, "anchor": "center"}
    assert flip_place_kwargs(False, kwargs) == kwargs


def test_place_anchor_w_becomes_e_when_mirrored():
    assert flip_place_kwargs(True, {"anchor": "w"})["anchor"] == "e"


def test_grid_column_mirrors_against_total_columns_when_mirrored():
    # 3 columns (0, 1, 2): column 0 <-> column 2, column 1 stays put
    assert flip_grid_kwargs(True, 3, {"column": 0}) == {"column": 2}
    assert flip_grid_kwargs(True, 3, {"column": 1}) == {"column": 1}
    assert flip_grid_kwargs(True, 3, {"column": 2}) == {"column": 0}


def test_grid_kwargs_unchanged_when_not_mirrored():
    kwargs = {"column": 0, "row": 0}
    assert flip_grid_kwargs(False, 3, kwargs) == kwargs


def test_grid_sticky_w_becomes_e_when_mirrored():
    assert flip_grid_kwargs(True, 3, {"sticky": "w"}) == {"sticky": "e"}
