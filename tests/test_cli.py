"""`python -m vizops` reports without a renderer, scores what it did, and
fails when the README's table has drifted from the manifest."""

import pytest

import subprocess

import artifacts
from vizops import surfaces
from vizops.__main__ import main
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


def test_every_surface_matches_its_source(capsys):
    assert main(["--check"]) == 0
    assert "surface(s) match" in capsys.readouterr().out


def test_a_drifted_surface_is_caught_and_rewritten(tmp_path, monkeypatch, capsys):
    block = surfaces.BLOCKS[0]
    drifted = tmp_path / "README.md"
    drifted.write_text(f"{block.begin}\n| Scene | gone |\n{block.end}\n", encoding="utf-8")
    monkeypatch.setattr(surfaces, "README", drifted)
    assert main(["--check"]) == 1
    assert "drifted" in capsys.readouterr().out
    assert main(["--write"]) == 0
    assert main(["--check"]) == 0


def test_a_half_marked_surface_is_an_error(tmp_path, monkeypatch):
    broken = tmp_path / "README.md"
    broken.write_text(f"{surfaces.BLOCKS[0].begin}\nno end marker\n", encoding="utf-8")
    monkeypatch.setattr(surfaces, "README", broken)
    with pytest.raises(surfaces.DriftError, match="markers are missing"):
        main(["--check"])


def test_wiki_needs_a_verb(capsys):
    with pytest.raises(SystemExit):
        main(["wiki"])
    assert "--publish" in capsys.readouterr().err


def test_wiki_publish_mirrors_the_pages(tmp_path, capsys):
    bare = tmp_path / "math-vizops.wiki.git"
    subprocess.run(["git", "init", "--quiet", "--bare", str(bare)], check=True)
    assert main(["wiki", "--publish", "--remote", str(bare)]) == 0
    assert "published" in capsys.readouterr().out
    checkout = tmp_path / "checkout"
    subprocess.run(["git", "clone", "--quiet", str(bare), str(checkout)], check=True)
    assert (checkout / "Home.md").is_file() and (checkout / "_Sidebar.md").is_file()


def test_publishing_to_a_wiki_that_does_not_exist_is_an_error(tmp_path, capsys):
    assert main(["wiki", "--publish", "--remote", str(tmp_path / "absent.wiki.git")]) == 1
    assert "first page" in capsys.readouterr().err


def test_still_without_a_renderer_scores_inconclusive(estate, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("vizops.bridge.renderer", lambda: None)
    assert main(["still", "--sources", str(estate), "--into", str(tmp_path / "images")]) == 2
    assert "inconclusive" in capsys.readouterr().out


def test_render_without_a_renderer_scores_inconclusive(estate, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("vizops.bridge.renderer", lambda: None)
    assert main(["render", "--sources", str(estate), "--out", str(tmp_path / "out")]) == 2
    assert "inconclusive" in capsys.readouterr().out
