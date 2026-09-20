"""A figure carries its provenance, uses only the vocabulary its source
declares, and names every defect in one refusal."""

import pytest

from vizops.figure import CAVEAT, Edge, Figure, FigureError, Node, Provenance, Term

PROV = Provenance("larsbx/example", "docs/graph.json", "b" * 64)
TERMS = (Term("open", "open"), Term("closed", "closed"))


def figure(**overrides):
    base = dict(
        title="Example",
        provenance=PROV,
        terms=TERMS,
        kinds=("implicative",),
        nodes=(Node("A", "A", "open"), Node("B", "B", "closed")),
        edges=(Edge("A", "B", "implicative"),),
    )
    return Figure(**{**base, **overrides})


def test_a_well_formed_figure_stands():
    drawn = figure()
    assert drawn.caveat == CAVEAT
    assert drawn.provenance.stamp == "larsbx/example/docs/graph.json @ sha256:bbbbbbbbbbbb"


def test_a_figure_names_every_defect_at_once():
    with pytest.raises(FigureError) as refusal:
        figure(
            terms=(*TERMS, Term("open", "open")),
            nodes=(Node("A", "A", "invented"), Node("A", "A", "open"), Node("B", "", "closed")),
            edges=(Edge("A", "Ghost", "implicative"), Edge("A", "B", "analogous"), Edge("B", "B", "implicative")),
        )
    message = str(refusal.value)
    for expected in (
        "term 'open': declared twice",
        "node 'A': declared twice",
        "term 'invented' is not one the source declares",
        "node B: no label",
        "'Ghost' is not a node in this figure",
        "kind 'analogous' is not one the source declares",
        "an edge from a node to itself",
    ):
        assert expected in message


@pytest.mark.parametrize("field,value", [("terms", ()), ("nodes", ()), ("title", "  ")])
def test_an_empty_figure_is_refused(field, value):
    with pytest.raises(FigureError):
        figure(**{field: value})


@pytest.mark.parametrize("digest", ["", "deadbeef", "z" * 64])
def test_provenance_without_a_digest_is_refused(digest):
    with pytest.raises(FigureError, match="sha256"):
        Provenance("larsbx/example", "docs/graph.json", digest)


@pytest.mark.parametrize("field", ["repo", "path"])
def test_provenance_names_a_repository_and_a_path(field):
    fields = {"repo": "larsbx/example", "path": "docs/graph.json", "digest": "b" * 64, field: ""}
    with pytest.raises(FigureError, match=f"{field} is empty"):
        Provenance(**fields)


def test_a_class_with_no_members_leaves_the_frame_but_keeps_its_place():
    drawn = figure(nodes=(Node("A", "A", "closed"),), edges=())
    assert tuple(t.id for t in drawn.populated()) == ("closed",)
    assert tuple(t.id for t in drawn.terms) == ("open", "closed")
    assert drawn.members() == {"closed": ("A",)}


def test_only_the_kinds_on_the_frame_are_reported_as_used():
    drawn = figure(kinds=("implicative", "part-whole", "analogous"))
    assert drawn.used_kinds() == ("implicative",)


def test_figures_are_immutable():
    with pytest.raises(AttributeError):
        figure().title = "other"
