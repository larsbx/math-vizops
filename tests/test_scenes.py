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
        for cls in (scenes.ClaimGraph, scenes.ObjectCatalogue, scenes.WakeCycleToMandelbrot)
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


def test_the_wake_scene_prints_the_upstream_pair_and_evidence_boundary(estate):
    scene = scenes.WakeCycleToMandelbrot()
    scene.construct()
    drawn = scenes.figure_for(scene.source_id)
    printed = _printed(scene)
    assert drawn.orbit == (21, 42, 84, 41, 82, 37, 74)
    assert drawn.angular == (21, 37, 41, 42, 74, 82, 84)
    assert "θ₋ = 41/127" in printed and "θ₊ = 42/127" in printed
    assert "[DH/Mil00] imported landing" in printed
    assert drawn.provenance.stamp in printed and drawn.caveat in printed
    assert any(isinstance(a, manimlib_stub.ShowCreation) for a in scene.played)
    assert scene.waited


def test_wake_wires_are_sent_behind_every_labelled_box(estate):
    scene = scenes.WakeCycleToMandelbrot()
    scene.construct()
    labels = {
        text.text
        for mobject in scene.fronted
        for text in _texts(mobject)
    }
    assert {"21", "42", "84", "41", "82", "37", "74"} <= labels
    assert "θ₋  41/127" in labels
    assert "θ₊  42/127" in labels
    assert "3/7 bulb root" in labels


def test_wake_final_annotations_stay_above_the_footer_band():
    assert scenes.WAKE_LANDING_NOTE_Y > scenes.WAKE_FOOTER_CEILING
    assert scenes.WAKE_COORDINATE_Y > scenes.WAKE_FOOTER_CEILING


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
