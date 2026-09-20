"""Each adapter transcribes its format and refuses anything else.

The negative controls are the point: an artifact whose declared format changed,
a node in a class its own file never declared, an edge to a node that is not
there. Each is an input the adapter is known to reject.
"""

import pytest

import artifacts
from vizops.adapters import AdapterError, object_catalogue, typed_graph
from vizops.figure import FigureError, Provenance

PROV = Provenance("larsbx/example", "docs/graph.json", "c" * 64)


def graph(raw=None):
    return typed_graph(raw or artifacts.graph(), PROV, "Given title")


def catalogue(text=None):
    return object_catalogue((text or artifacts.CATALOGUE).encode("utf-8"), PROV, "Given title")


def test_a_typed_graph_is_transcribed_field_for_field():
    drawn = graph()
    assert drawn.title == "Given title"
    assert tuple(t.id for t in drawn.terms) == ("theorem-backed", "open", "declared")
    assert drawn.kinds == ("implicative", "part-whole")
    block = drawn.node("Block")
    assert (block.term, block.badge, block.note) == ("open", "SCAFFOLDED", "a block holds")


def test_a_graph_of_another_format_is_refused():
    with pytest.raises(AdapterError, match="expected 'finite typed relationship graph 1'"):
        graph(artifacts.graph(format="finite typed relationship graph 2"))


@pytest.mark.parametrize("key", ["provenance_classes", "edge_types", "nodes", "edges"])
def test_a_graph_missing_a_declaration_is_refused(key):
    data = {k: v for k, v in artifacts.GRAPH.items() if k != key}
    with pytest.raises(AdapterError, match=f"lacks {key}"):
        typed_graph(__import__("json").dumps(data).encode("utf-8"), PROV, "T")


def test_a_node_in_an_undeclared_class_is_refused():
    with pytest.raises(FigureError, match="term 'invented' is not one the source declares"):
        graph(artifacts.mutate("nodes.0.provenance", "invented"))


def test_an_edge_to_a_node_that_is_not_there_is_refused():
    with pytest.raises(FigureError, match="'Ghost' is not a node in this figure"):
        graph(artifacts.mutate("edges.0.target", "Ghost"))


def test_an_edge_of_an_undeclared_kind_is_refused():
    with pytest.raises(FigureError, match="kind 'causal' is not one the source declares"):
        graph(artifacts.mutate("edges.0.type", "causal"))


def test_a_catalogue_is_classed_by_its_own_taxonomy_and_titled_by_its_own_title():
    drawn = catalogue()
    assert drawn.title == "Example catalogue"
    assert tuple(t.id for t in drawn.terms) == ("dynamics", "algebra")
    assert drawn.node("substitution").badge == "definition"
    assert drawn.terms[0].description == "Words and their finite symbolic dynamics."


def test_a_catalogue_of_another_schema_is_refused():
    with pytest.raises(AdapterError, match="expected 1"):
        catalogue(artifacts.CATALOGUE.replace("schema_version = 1", "schema_version = 2"))


def test_an_object_in_an_undeclared_taxonomy_is_refused():
    with pytest.raises(FigureError, match="term 'numeration' is not one the source declares"):
        catalogue(artifacts.CATALOGUE.replace('taxonomy = "algebra"\nstatus = "open-boundary"', 'taxonomy = "numeration"\nstatus = "open-boundary"'))


def test_a_related_entry_pointing_nowhere_is_refused():
    with pytest.raises(FigureError, match="'ghost' is not a node in this figure"):
        catalogue(artifacts.CATALOGUE.replace('related = ["incidence-matrix"]', 'related = ["ghost"]'))


def test_a_pair_stated_on_both_sides_is_drawn_once():
    drawn = catalogue(artifacts.CATALOGUE.replace(
        'name = "Incidence matrix"\ntaxonomy = "algebra"\nstatus = "definition"',
        'name = "Incidence matrix"\ntaxonomy = "algebra"\nstatus = "definition"\nrelated = ["substitution"]',
    ))
    assert sorted((e.source, e.target) for e in drawn.edges) == [
        ("incidence-matrix", "substitution"),
        ("substitution", "wedge-defect"),
    ]


def test_a_pair_stated_on_one_side_only_is_still_drawn():
    assert ("substitution", "wedge-defect") in [(e.source, e.target) for e in catalogue().edges]


def test_an_object_related_to_itself_draws_no_edge():
    drawn = catalogue(artifacts.CATALOGUE.replace('related = ["incidence-matrix"]', 'related = ["substitution"]'))
    assert all(e.source != e.target for e in drawn.edges)
