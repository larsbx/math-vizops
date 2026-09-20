"""The manifest is the only place a source is named, and a missing artifact is
a refusal that says where it looked."""

import pytest

from vizops.adapters import ADAPTERS
from vizops.sources import MANIFEST, Scene, SourceError, by_id, load

MANIFEST_HEAD = 'format = "vizops sources 1"\n'
ENTRY = """
[[scene]]
id = "{id}"
title = "T"
repo = "larsbx/example"
path = "docs/graph.json"
adapter = "typed_graph"
scene = "ClaimGraph"
"""


def write(tmp_path, text):
    manifest = tmp_path / "sources.toml"
    manifest.write_text(text, encoding="utf-8")
    return manifest


def test_the_shipped_manifest_loads_and_every_adapter_exists():
    scenes = load()
    assert scenes
    assert len(by_id(scenes)) == len(scenes)
    assert {s.adapter for s in scenes} <= set(ADAPTERS)


def test_a_checkout_directory_is_the_repository_name():
    scene = Scene("i", "T", "larsbx/finite-mandelbrot-research", "docs/g.json", "typed_graph", "ClaimGraph")
    assert scene.artifact("/estate").as_posix() == "/estate/finite-mandelbrot-research/docs/g.json"


def test_a_missing_artifact_names_the_path_it_looked_for(tmp_path):
    scene = load()[0]
    with pytest.raises(SourceError, match=str(scene.artifact(tmp_path))):
        scene.read(tmp_path)


def test_an_empty_artifact_is_refused_rather_than_drawn(tmp_path):
    scene = load()[0]
    artifact = scene.artifact(tmp_path)
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"")
    with pytest.raises(SourceError, match="is empty"):
        scene.read(tmp_path)


def test_bytes_come_back_with_their_digest(tmp_path):
    scene = load()[0]
    artifact = scene.artifact(tmp_path)
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"{}")
    raw, digest = scene.read(tmp_path)
    assert raw == b"{}"
    assert digest == "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"


@pytest.mark.parametrize(
    "text,expected",
    [
        ('format = "vizops sources 0"\n', "expected 'vizops sources 1'"),
        (MANIFEST_HEAD, "no scenes"),
        (MANIFEST_HEAD + ENTRY.format(id="a") + ENTRY.format(id="a"), "declared twice"),
        (MANIFEST_HEAD + '[[scene]]\nid = "a"\n', "lacks title, repo, path, adapter, scene"),
        (MANIFEST_HEAD + ENTRY.format(id="a") + 'colour = "blue"\n', "unknown field(s) colour"),
    ],
)
def test_a_malformed_manifest_is_refused(tmp_path, text, expected):
    with pytest.raises(SourceError, match=expected.replace("(", r"\(").replace(")", r"\)")):
        load(write(tmp_path, text))
