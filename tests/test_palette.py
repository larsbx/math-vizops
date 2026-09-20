"""Colour is assigned by declared position and never generated."""

import pytest

from vizops.palette import RING, PaletteError, assign, edge_key, edge_styles


def test_hues_are_distinct():
    assert len(set(RING)) == len(RING)


def test_assignment_follows_declared_position():
    assert assign(("a", "b", "c")) == {"a": RING[0], "b": RING[1], "c": RING[2]}


def test_a_class_keeps_its_hue_when_a_later_class_is_dropped():
    full = assign(("a", "b", "c"))
    assert assign(("a", "b"))["b"] == full["b"]


def test_a_ninth_class_is_not_a_generated_hue():
    with pytest.raises(PaletteError, match="not generated"):
        assign(tuple(str(i) for i in range(len(RING) + 1)))


def test_the_same_class_twice_is_refused():
    with pytest.raises(PaletteError, match="colour follows the entity"):
        assign(("a", "a"))


def test_edge_styles_distinguish_the_first_two_kinds():
    assert edge_styles(("implicative", "part-whole")) == {"implicative": "solid", "part-whole": "dashed"}


def test_kinds_past_the_second_share_a_style_and_the_key_says_so():
    assert edge_styles(("a", "b", "c"))["c"] == "dashed"
    assert edge_key(("a", "b", "c")) == "solid: a · dashed: b, c"


def test_a_single_kind_still_gets_a_key():
    assert edge_key(("related",)) == "solid: related"
