"""The layout is pure geometry: deterministic, centred, and refusing a column
it was asked to draw with nothing in it."""

import pytest

from vizops.layout import Frame, column_spacing, columns, pitch

MEMBERS = {"a": ("a1", "a2", "a3"), "b": ("b1",)}


def test_columns_are_deterministic():
    assert columns(("a", "b"), MEMBERS) == columns(("a", "b"), MEMBERS)


def test_columns_run_left_to_right_in_declared_order():
    placed = columns(("a", "b"), MEMBERS)
    assert placed["a1"][0] < placed["b1"][0]
    assert {placed[n][0] for n in ("a1", "a2", "a3")} == {placed["a1"][0]}


def test_members_run_top_to_bottom_in_figure_order():
    placed = columns(("a",), MEMBERS | {"a": ("a1", "a2", "a3")})
    assert placed["a1"][1] > placed["a2"][1] > placed["a3"][1]


def test_everything_is_centred_and_inside_the_frame():
    frame = Frame()
    placed = columns(("a", "b"), MEMBERS, frame)
    xs, ys = [p[0] for p in placed.values()], [p[1] for p in placed.values()]
    assert max(xs) == pytest.approx(-min(xs))
    assert max(ys) == pytest.approx(-min(ys))
    assert max(abs(x) for x in xs) <= frame.width / 2
    assert max(abs(y) for y in ys) <= frame.height / 2


def test_a_lone_node_sits_at_the_centre_of_its_column():
    assert columns(("b",), MEMBERS)["b1"] == (0.0, 0.0)


def test_no_two_nodes_share_a_point():
    placed = columns(("a", "b"), MEMBERS)
    assert len(set(placed.values())) == len(placed)


def test_a_column_with_no_members_is_refused_rather_than_drawn_empty():
    with pytest.raises(ValueError, match="no members for c"):
        columns(("a", "c"), MEMBERS)


def test_pitch_is_the_tightest_column():
    frame = Frame()
    assert pitch(MEMBERS, frame) == pytest.approx(frame.height / 2)
    assert pitch({"b": ("b1",)}, frame) == frame.height


def test_a_frame_with_no_area_lays_nothing_out():
    with pytest.raises(ValueError):
        Frame(width=0, height=3)


def test_column_spacing_gives_a_lone_column_the_whole_width():
    frame = Frame()
    assert column_spacing(1, frame) == frame.width
    assert column_spacing(3, frame) == pytest.approx(frame.width / 2)
