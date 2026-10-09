"""The Mandelbrot Names Atlas page: the structure crosswalk transcribed, and
every way of the surface being malformed refused.

The fixture is a three-structure surface in the upstream shape; the real file is
read in `test_estate.py`.
"""

import json

import pytest

from vizops.crosswalk import FORMAT, TEMPLATE, build, transcribe
from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.sources import SourceError, pages

PAGE = next(p for p in pages() if p.id == "mandelbrot-names-atlas")


def surface(**change):
    base = {
        "format": FORMAT,
        "repository": "larsbx/finite-mandelbrot-research",
        "caveat": "A shared datum identifies symbols.",
        "classes": [{"id": "atlas/hyperbolic-component", "name": "atlas: hyperbolic-component"},
                    {"id": "atlas/julia-set", "name": "atlas: julia-set"},
                    {"id": "kernel", "name": "canonical executable code (Mojo)"}],
        "relations": [{"id": "same-datum", "name": "holds the atlas datum itself"},
                      {"id": "satellite-of", "name": "satellite"},
                      {"id": "julia-set-of", "name": "Julia set of"}],
        "nodes": [
            {"id": "main-cardioid", "class": "atlas/hyperbolic-component", "label": "main cardioid",
             "names": ["main cardioid"], "name_status": "field", "key": {"root_angles": ["0/1"]}},
            {"id": "bulb-1/3", "class": "atlas/hyperbolic-component", "label": "1/3-bulb",
             "names": ["1/3-bulb", "rabbit bulb"], "name_status": "field",
             "key": {"root_angles": ["1/7", "2/7"], "period": 3}},
            {"id": "douady-rabbit", "class": "atlas/julia-set", "label": "Douady rabbit",
             "names": ["Douady rabbit"], "name_status": "eponym"},
            {"id": "fmr-rabbit", "class": "kernel", "label": "tunings component \"rabbit\"",
             "relation": "same-datum", "repo": "larsbx/finite-mandelbrot-research",
             "path": "kernel/mojo/entrypoints/atlas_dataset.mojo", "anchor": "\"rabbit\"",
             "exactness": "exact", "emits": "atlas-dataset:tunings", "datum": {"root_angles": ["1/7", "2/7"]}},
        ],
        "edges": [{"source": "bulb-1/3", "relation": "satellite-of", "target": "main-cardioid"},
                  {"source": "douady-rabbit", "relation": "julia-set-of", "target": "bulb-1/3"},
                  {"source": "fmr-rabbit", "relation": "same-datum", "target": "bulb-1/3"}],
    }
    return {**base, **change}


@pytest.fixture
def estate(tmp_path):
    def make(content=None):
        target = tmp_path / "estate" / PAGE.checkout / PAGE.path
        target.parent.mkdir(parents=True, exist_ok=True)
        if content is not None:
            target.write_bytes(content if isinstance(content, bytes) else json.dumps(content).encode())
        return tmp_path / "estate"
    return make


def data_of(html: str) -> dict:
    return json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])


def test_the_template_takes_each_placeholder_once():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert all(text.count(mark) == 1 for mark in ("__DATA__", "__SOURCES__", "__CAVEAT__"))


def test_structures_occurrences_and_relations_are_transcribed_as_written():
    data = transcribe(surface())
    assert [s["id"] for s in data["structures"]] == ["main-cardioid", "bulb-1/3", "douady-rabbit"]
    rabbit_bulb = data["structures"][1]
    assert rabbit_bulb["key"] == {"root_angles": ["1/7", "2/7"], "period": 3}  # exact strings, untouched
    (occ,) = data["occurrences"]
    assert occ["atlas"] == ["bulb-1/3"] and occ["datum"] == {"root_angles": ["1/7", "2/7"]}
    assert ("douady-rabbit", "julia-set-of", "bulb-1/3") in {tuple(e) for e in data["links"]}
    assert data["relations"]["same-datum"] == "holds the atlas datum itself"


def test_the_page_carries_the_stamp_and_both_caveats(estate, tmp_path):
    out = tmp_path / "out.html"
    assert isinstance(build(PAGE, estate(surface()), out=out), Rendered)
    html = out.read_text(encoding="utf-8")
    assert f"{PAGE.repo}/{PAGE.path} @ sha256:" in html
    assert CAVEAT in html
    assert data_of(html)["caveat"] == "A shared datum identifies symbols."


@pytest.mark.parametrize("change, reason", [
    ({"format": "structure crosswalk 2"}, "structure crosswalk 2"),
    ({"classes": []}, "not declared"),
    ({"relations": [{"id": "same-datum", "name": "x"}]}, "satellite-of"),
    ({"edges": [{"source": "nowhere", "relation": "same-datum", "target": "bulb-1/3"}]}, "nowhere"),
])
def test_a_malformed_surface_is_refused(estate, tmp_path, change, reason):
    outcome = build(PAGE, estate(surface(**change)), out=tmp_path / "out.html")
    assert isinstance(outcome, Refused) and reason in outcome.reason
    assert not (tmp_path / "out.html").exists()


def test_a_float_anywhere_is_refused(estate):
    raw = json.dumps(surface()).replace('"period": 3', '"period": 3.0').encode()
    outcome = build(PAGE, estate(raw))
    assert isinstance(outcome, Refused) and "float" in outcome.reason


def test_a_missing_file_and_a_dataset_are_refused(estate):
    assert isinstance(build(PAGE, estate()), Refused)
    assert isinstance(build(PAGE, estate(surface()), dataset=estate(surface())), Refused)


def test_duplicate_ids_are_refused():
    nodes = surface()["nodes"]
    with pytest.raises(SourceError, match="twice"):
        transcribe(surface(nodes=nodes + nodes[:1]))
