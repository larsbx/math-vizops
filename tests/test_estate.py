"""The scenes, against the estate's real artifacts.

This is the check that catches an upstream generator changing shape: a new
provenance class, a renamed taxonomy, an edge type that was not declared. It
needs the sibling checkouts, so it reports inconclusive where they are absent
-- and CI sets `VIZOPS_REQUIRE_SOURCES=1`, which turns that absence into a
failure, because a check that silently skips in the one place it was meant to
run is not a check.
"""

import os

import pytest

from vizops import layout, palette
from vizops.bridge import figure, root
from vizops.sources import load

REQUIRED = os.environ.get("VIZOPS_REQUIRE_SOURCES") == "1"


@pytest.mark.parametrize("scene", load(), ids=lambda s: s.id)
def test_the_real_artifact_draws(scene):
    if not scene.artifact(root()).is_file():
        message = f"no checkout of {scene.repo} under {root()}"
        pytest.fail(message) if REQUIRED else pytest.skip(message)
    drawn = figure(scene)
    hues = palette.assign(tuple(t.id for t in drawn.terms))
    placed = layout.columns(tuple(t.id for t in drawn.populated()), drawn.members())
    assert drawn.nodes and drawn.edges
    assert set(placed) == {n.id for n in drawn.nodes}
    assert len(set(placed.values())) == len(placed)
    assert {n.term for n in drawn.nodes} <= set(hues)
    assert drawn.used_kinds()
