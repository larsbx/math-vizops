"""`python -m vizops` reports without a renderer, scores what it did, and
fails when the README's table has drifted from the manifest."""

import pytest

import artifacts
from vizops.__main__ import main, table
from vizops.sources import load


@pytest.fixture
def estate(tmp_path):
    return artifacts.estate(tmp_path / "estate")


def test_the_report_reads_every_artifact_without_a_renderer(estate, capsys, monkeypatch):
    monkeypatch.setattr("vizops.bridge.renderer", lambda: None)
    assert main(["--sources", str(estate)]) == 0
    out = capsys.readouterr().out
    assert out.count("ready") == len(load())
    assert "inconclusive, not failure" in out


def test_a_missing_checkout_makes_the_report_fail(tmp_path, capsys):
    assert main(["--sources", str(tmp_path / "nothing")]) == 1
    assert "refused" in capsys.readouterr().out


def test_a_malformed_artifact_makes_the_report_fail(tmp_path, capsys):
    broken = artifacts.estate(tmp_path / "estate", graph_bytes=artifacts.mutate("edges.0.target", "Ghost"))
    assert main(["--sources", str(broken)]) == 1
    assert "not a node in this figure" in capsys.readouterr().out


def test_an_unknown_scene_id_is_an_error(estate, capsys):
    assert main(["report", "no-such-scene", "--sources", str(estate)]) == 1
    assert "no such scene" in capsys.readouterr().err


def test_the_readme_table_matches_the_manifest(capsys):
    assert main(["--check"]) == 0
    assert "matches sources.toml" in capsys.readouterr().out


def test_a_drifted_readme_is_caught_and_rewritten(tmp_path, monkeypatch, capsys):
    drifted = tmp_path / "README.md"
    drifted.write_text(table(load()).replace("| `c1-claim-graph` |", "| `renamed` |"), encoding="utf-8")
    monkeypatch.setattr("vizops.__main__.README", drifted)
    assert main(["--check"]) == 1
    assert "drifted" in capsys.readouterr().out
    assert main(["--write"]) == 0
    assert main(["--check"]) == 0


def test_a_readme_without_markers_is_an_error(tmp_path, monkeypatch):
    bare = tmp_path / "README.md"
    bare.write_text("# nothing generated here\n", encoding="utf-8")
    monkeypatch.setattr("vizops.__main__.README", bare)
    with pytest.raises(SystemExit, match="markers are missing"):
        main(["--check"])


def test_render_without_a_renderer_scores_inconclusive(estate, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("vizops.bridge.renderer", lambda: None)
    assert main(["render", "--sources", str(estate), "--out", str(tmp_path / "out")]) == 2
    assert "inconclusive" in capsys.readouterr().out
