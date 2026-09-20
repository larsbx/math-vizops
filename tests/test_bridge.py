"""The bridge to manimgl, exercised without manimgl.

A stand-in executable stands in for the renderer, so each branch -- wrote a
file, wrote nothing, died, never finished, was never there -- is a case that
runs in CI rather than a case that is argued about.
"""

import hashlib
import stat
import sys
from pathlib import Path

import pytest

import artifacts
from vizops.outcome import Inconclusive, Refused, Rendered
from vizops.bridge import figure, figure_for, render, root, still
from vizops.sources import Scene, SourceError, load

FAKE = """\
#!{python}
import pathlib, sys
argv = sys.argv[1:]
out = pathlib.Path(argv[argv.index("--video_dir") + 1])
pathlib.Path({marker!r}).write_text(" ".join(argv) + "\\n" + __import__("os").environ.get("VIZOPS_SOURCES", ""))
{body}
"""


def stand_in(tmp_path, body, name="manimgl"):
    exe = tmp_path / name
    exe.write_text(FAKE.format(python=sys.executable, marker=str(tmp_path / "called"), body=body))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return exe


@pytest.fixture
def estate(tmp_path):
    return artifacts.estate(tmp_path / "estate")


@pytest.fixture
def scene():
    return load()[0]


def test_a_figure_is_read_from_the_checkout(estate, scene):
    drawn = figure(scene, estate)
    assert drawn.provenance.repo == scene.repo
    assert drawn.node("Block").badge == "SCAFFOLDED"


def test_a_scene_asks_for_its_figure_by_id(estate, monkeypatch):
    monkeypatch.setenv("VIZOPS_SOURCES", str(estate))
    assert figure_for("c1-claim-graph").title


def test_an_unknown_scene_id_is_refused(estate):
    with pytest.raises(SourceError, match="no scene 'nope'"):
        figure_for("nope", estate)


def test_an_unknown_adapter_is_refused(estate, scene):
    with pytest.raises(SourceError, match="no adapter named 'painter'"):
        figure(Scene(**{**vars_of(scene), "adapter": "painter"}), estate)


def vars_of(scene):
    return {f: getattr(scene, f) for f in Scene.__dataclass_fields__}


def test_the_root_falls_back_from_flag_to_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("VIZOPS_SOURCES", str(tmp_path))
    assert root() == tmp_path
    assert root(Path("/elsewhere")) == Path("/elsewhere")


def test_no_renderer_is_inconclusive_not_a_failure(estate, scene, monkeypatch, tmp_path):
    monkeypatch.setattr("vizops.bridge.renderer", lambda: None)
    outcome = render(scene, estate, out=tmp_path / "out")
    assert isinstance(outcome, Inconclusive) and outcome.exit_code == 2
    assert "manimgl" in outcome.reason


def test_a_written_file_is_a_render_with_its_digest(estate, scene, monkeypatch, tmp_path):
    body = 'out.mkdir(parents=True, exist_ok=True); (out / "scene.mp4").write_bytes(b"frames")'
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, body)))
    outcome = render(scene, estate, out=tmp_path / "out")
    assert isinstance(outcome, Rendered) and outcome.exit_code == 0
    assert outcome.output.endswith("scene.mp4")
    assert outcome.digest == hashlib.sha256(b"frames").hexdigest()


def test_a_clean_exit_that_wrote_nothing_is_inconclusive(estate, scene, monkeypatch, tmp_path):
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, "pass")))
    outcome = render(scene, estate, out=tmp_path / "out")
    assert isinstance(outcome, Inconclusive)
    assert "wrote a movie nowhere" in outcome.reason


def test_a_renderer_that_dies_is_a_refusal_carrying_its_last_words(estate, scene, monkeypatch, tmp_path):
    body = 'sys.stderr.write("quiet\\n\\nno GL context\\n"); sys.exit(3)'
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, body)))
    outcome = render(scene, estate, out=tmp_path / "out")
    assert isinstance(outcome, Refused) and outcome.exit_code == 1
    assert "exited 3" in outcome.reason and "no GL context" in outcome.reason


def test_a_renderer_that_never_finishes_reaches_no_verdict(estate, scene, monkeypatch, tmp_path):
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, "import time; time.sleep(30)")))
    outcome = render(scene, estate, out=tmp_path / "out", timeout=0.6)
    assert isinstance(outcome, Inconclusive)
    assert "did not finish" in outcome.reason


def test_the_renderer_is_told_where_the_estate_is(estate, scene, monkeypatch, tmp_path):
    body = 'out.mkdir(parents=True, exist_ok=True); (out / "scene.mp4").write_bytes(b"f")'
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, body)))
    render(scene, estate, out=tmp_path / "out")
    called = (tmp_path / "called").read_text()
    assert scene.scene in called and str(estate) in called and "-w" in called


def test_a_malformed_source_is_refused_before_a_renderer_starts(tmp_path, scene, monkeypatch):
    broken = artifacts.estate(tmp_path / "estate", graph_bytes=artifacts.mutate("nodes.0.provenance", "invented"))
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, "pass")))
    outcome = render(scene, broken, out=tmp_path / "out")
    assert isinstance(outcome, Refused)
    assert "is not one the source declares" in outcome.reason
    assert not (tmp_path / "called").exists()


def test_an_unknown_quality_is_refused(estate, scene, tmp_path):
    outcome = render(scene, estate, out=tmp_path / "out", quality="cinematic")
    assert isinstance(outcome, Refused) and "cinematic" in outcome.reason


def test_a_figure_with_more_classes_than_hues_is_refused_before_the_renderer(tmp_path, scene, monkeypatch):
    crowded = artifacts.estate(
        tmp_path / "estate",
        graph_bytes=artifacts.graph(
            provenance_classes=[*artifacts.GRAPH["provenance_classes"], *(f"spare-{i}" for i in range(6))]
        ),
    )
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, "pass")))
    outcome = render(scene, crowded, out=tmp_path / "out")
    assert isinstance(outcome, Refused) and "not generated" in outcome.reason
    assert not (tmp_path / "called").exists()


def test_a_still_run_that_produced_only_video_produced_nothing_asked_for(estate, scene, monkeypatch, tmp_path):
    body = 'out.mkdir(parents=True, exist_ok=True); (out / "scene.mp4").write_bytes(b"frames")'
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, body)))
    outcome = render(scene, estate, out=tmp_path / "out", still=True)
    assert isinstance(outcome, Inconclusive) and "wrote an image nowhere" in outcome.reason


def test_a_still_is_filed_where_the_gallery_looks_for_it(estate, scene, monkeypatch, tmp_path):
    body = 'out.mkdir(parents=True, exist_ok=True); (out / "ClaimGraph.png").write_bytes(b"pixels")'
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, body)))
    outcome = still(scene, estate, into=tmp_path / "images")
    assert isinstance(outcome, Rendered)
    assert outcome.output == str(tmp_path / "images" / f"{scene.id}.png")
    assert (tmp_path / "images" / f"{scene.id}.png").read_bytes() == b"pixels"
    assert not (tmp_path / "images" / ".render").exists()
    assert "-s" in (tmp_path / "called").read_text()


def test_a_refused_still_leaves_no_scratch_behind(tmp_path, scene, monkeypatch):
    broken = artifacts.estate(tmp_path / "estate", graph_bytes=artifacts.mutate("edges.0.target", "Ghost"))
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, "pass")))
    outcome = still(scene, broken, into=tmp_path / "images")
    assert isinstance(outcome, Refused)
    assert not (tmp_path / "images" / ".render").exists()


def test_the_finished_movie_wins_over_manims_partial_files(estate, scene, monkeypatch, tmp_path):
    body = (
        'partials = out / "ClaimGraph"; partials.mkdir(parents=True, exist_ok=True);\n'
        '(partials / "0001.mp4").write_bytes(b"part");\n'
        '(out / "ClaimGraph.mp4").write_bytes(b"whole")'
    )
    monkeypatch.setattr("vizops.bridge.renderer", lambda: str(stand_in(tmp_path, body)))
    outcome = render(scene, estate, out=tmp_path / "out")
    assert isinstance(outcome, Rendered) and outcome.output.endswith("out/ClaimGraph.mp4")
