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
from vizops import bulbs, wake
from vizops.atlas.build import oracle
from vizops.sources import load, module, pages
from vizops.wake.scene import WakeCycleFigure

REQUIRED = os.environ.get("VIZOPS_REQUIRE_SOURCES") == "1"


@pytest.mark.parametrize("scene", load(), ids=lambda s: s.id)
def test_the_real_artifact_draws(scene):
    if not scene.artifact(root()).is_file():
        message = f"no checkout of {scene.repo} under {root()}"
        pytest.fail(message) if REQUIRED else pytest.skip(message)
    drawn = figure(scene)
    if isinstance(drawn, WakeCycleFigure):
        assert drawn.orbit == (21, 42, 84, 41, 82, 37, 74)
        assert drawn.angular == (21, 37, 41, 42, 74, 82, 84)
        assert drawn.characteristic == (41, 42)
        return

    hues = palette.assign(tuple(t.id for t in drawn.terms))
    placed = layout.columns(tuple(t.id for t in drawn.populated()), drawn.members())
    assert drawn.nodes and drawn.edges
    assert set(placed) == {n.id for n in drawn.nodes}
    assert len(set(placed.values())) == len(placed)
    assert {n.term for n in drawn.nodes} <= set(hues)
    assert drawn.used_kinds()


PAGES = {p.builder: p for p in pages()}


def checkout_of(page):
    checkout = root() / page.checkout
    if not checkout.is_dir():
        message = f"no checkout of {page.repo} under {root()}"
        pytest.fail(message) if REQUIRED else pytest.skip(message)
    return checkout


def test_the_real_exclusion_oracle_decides_the_pinned_box():
    """The atlas borrows its box verdicts from upstream rather than copying the
    oracle, so this is where a renamed or reshaped oracle is caught."""
    ie = oracle(checkout_of(PAGES["atlas"]))
    excluded, forbidden, failures = ie.excluded_count(ie.c_minus_2_box(), 2, 1, 3)
    assert excluded == forbidden and not failures


def test_the_real_wake_module_tabulates_every_reduced_angle():
    page = PAGES["wake"]
    table = wake.rows(module(checkout_of(page), page.path))
    assert len(table) == 45  # sum of phi(q) for 2 <= q <= 12
    assert all(r["cycle"] == sorted(r["cycle"]) and r["hi"] - r["lo"] == 1 for r in table)


def test_the_committed_still_prints_what_the_module_says():
    """The 3/7 still is drawn by hand, so it is held to the module here: a
    change upstream that moves these numbers fails until the still is redrawn."""
    page = PAGES["wake"]
    (row,) = [r for r in wake.rows(module(checkout_of(page), page.path)) if (r["p"], r["q"]) == (3, 7)]
    claims = wake.still_claims(wake.STILL.read_text(encoding="utf-8"))
    assert claims == {k: row[k] for k in ("cycle", "lo", "hi", "den")}


def test_the_real_certificates_sweep_and_germ_transcribe():
    """Where an upstream file changes shape, this is what fails."""
    page = PAGES["bulbs"]
    missing = [repo for repo, _ in page.files() if not (root() / repo.split("/")[-1]).is_dir()]
    if missing:
        message = f"no checkout of {', '.join(sorted(set(missing)))} under {root()}"
        pytest.fail(message) if REQUIRED else pytest.skip(message)
    data = bulbs.transcribe(*(bulbs.read(root(), repo, path)[0] for repo, path in page.files()))
    assert len(data["bulbs"]) == 79 and len(data["dense"]) == 504 and len(data["iota"]) == 22
