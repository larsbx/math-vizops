"""`vizops/scenes.py` against a stand-in manimlib: one box per node, one wire
per edge, a header per class on the frame, and the stamp on every frame."""

import pytest

import artifacts
import manimlib_stub
from vizops.sources import load

STOOD_IN = manimlib_stub.install()

from vizops import scenes  # noqa: E402  (imports manimlib, real or stood in)


@pytest.fixture
def estate(tmp_path, monkeypatch):
    root = artifacts.estate(tmp_path / "estate")
    monkeypatch.setenv("VIZOPS_SOURCES", str(root))
    return root


@pytest.fixture(params=[scenes.ClaimGraph, scenes.ObjectCatalogue], ids=lambda c: c.source_id)
def drawn(request, estate):
    scene = request.param()
    scene.construct()
    scene.figure = scenes.figure_for(scene.source_id)
    return scene


def test_the_scene_ids_are_the_manifest_ids():
    assert {s.scene: s.id for s in load()} == {
        cls.__name__: cls.source_id
        for cls in (scenes.ClaimGraph, scenes.ObjectCatalogue)
    }


def test_every_node_gets_its_own_box(drawn):
    boxed = [m for anim in drawn.played for m in getattr(anim.mobject, "children", ()) if _boxes(m)]
    assert len(boxed) == len(drawn.figure.nodes)
    assert len({m.get_center() for m in boxed}) == len(drawn.figure.nodes)


def test_every_edge_is_drawn_once(drawn):
    wires = [a for a in drawn.played if isinstance(a, manimlib_stub.ShowCreation)]
    assert len(wires) == 1
    assert len(wires[0].mobject.children) == len(drawn.figure.edges)


def test_every_class_on_the_frame_is_headed_by_the_source_word(drawn):
    printed = _printed(drawn)
    for term in drawn.figure.populated():
        assert term.name in printed


def test_the_frame_carries_the_stamp_and_the_caveat_and_the_edge_key(drawn):
    printed = _printed(drawn)
    assert drawn.figure.provenance.stamp in printed
    assert drawn.figure.caveat in printed
    assert drawn.figure.used_kinds()[0] in printed


def test_the_scene_settles_rather_than_ending_on_a_move(drawn):
    assert drawn.waited


def test_the_stand_in_refuses_a_method_manim_does_not_have():
    with pytest.raises(AttributeError, match="has no"):
        manimlib_stub.Text("x").set_sparkle("bright")


def _printed(scene) -> str:
    return " ".join(t.text for group in scene.added for t in _texts(group))


def _boxes(mobject) -> bool:
    return any(isinstance(c, manimlib_stub.RoundedRectangle) for c in getattr(mobject, "children", ()))


def _texts(mobject):
    if isinstance(mobject, manimlib_stub.Text):
        yield mobject
    for child in getattr(mobject, "children", ()):
        yield from _texts(child)
