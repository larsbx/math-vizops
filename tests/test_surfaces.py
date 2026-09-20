"""Generated blocks: rendered from one source, spliced into every surface
that carries them, and checkable."""

import pytest

from vizops import surfaces
from vizops.outcome import EXIT_CODES
from vizops.sources import load

SCENES = load()


def test_every_block_renders_something():
    assert all(block.render(SCENES).strip() for block in surfaces.BLOCKS)


def test_the_shipped_surfaces_match_their_sources():
    assert surfaces.drifted(SCENES) == ()


def test_the_readme_and_every_wiki_page_are_surfaces():
    names = {p.name for p in surfaces.surfaces()}
    assert "README.md" in names and "Home.md" in names and "_Footer.md" in names


def test_rendering_is_idempotent():
    for path in surfaces.surfaces():
        once = surfaces.rendered(path, SCENES)
        assert once == surfaces.rendered(path, SCENES)


def test_the_outcome_table_has_a_row_per_verdict_in_exit_code_order():
    rows = [line for line in surfaces.outcome_table().splitlines() if line.startswith("| `")]
    assert len(rows) == len(EXIT_CODES)
    assert [r.split("`")[1] for r in rows] == sorted(EXIT_CODES, key=EXIT_CODES.get)


def test_the_module_table_names_every_module_and_finds_every_docstring():
    table = surfaces.module_table()
    assert all(f"`vizops/{name}`" in table for name in surfaces.MODULES)
    assert "—" not in table, "a listed module is missing or has no docstring"


def test_drift_is_found_and_fixed(tmp_path, monkeypatch):
    stale = tmp_path / "README.md"
    block = surfaces.BLOCKS[0]
    stale.write_text(f"# x\n\n{block.begin}\n| Scene | gone |\n{block.end}\n", encoding="utf-8")
    monkeypatch.setattr(surfaces, "README", stale)
    assert stale in surfaces.drifted(SCENES)
    assert stale in surfaces.write(SCENES)
    assert surfaces.drifted(SCENES) == ()
    assert SCENES[0].id in stale.read_text(encoding="utf-8")


def test_a_half_marked_surface_is_an_error(tmp_path, monkeypatch):
    broken = tmp_path / "README.md"
    broken.write_text(f"{surfaces.BLOCKS[0].begin}\nno end marker\n", encoding="utf-8")
    monkeypatch.setattr(surfaces, "README", broken)
    with pytest.raises(surfaces.DriftError, match="markers are missing"):
        surfaces.rendered(broken, SCENES)


def test_a_surface_carrying_no_block_is_left_alone(tmp_path, monkeypatch):
    plain = tmp_path / "README.md"
    plain.write_text("# just prose\n", encoding="utf-8")
    monkeypatch.setattr(surfaces, "README", plain)
    assert surfaces.rendered(plain, SCENES) == "# just prose\n"
    assert surfaces.drifted(SCENES) == ()


def test_the_gallery_says_so_when_a_scene_has_no_still(tmp_path, monkeypatch):
    monkeypatch.setattr(surfaces, "WIKI", tmp_path)
    rendered = surfaces.gallery(SCENES)
    assert "No still published yet" in rendered
    assert "![" not in rendered


def test_the_gallery_embeds_a_still_that_has_been_committed(tmp_path, monkeypatch):
    monkeypatch.setattr(surfaces, "WIKI", tmp_path)
    (tmp_path / surfaces.IMAGES).mkdir()
    (tmp_path / surfaces.IMAGES / f"{SCENES[0].id}.png").write_bytes(b"pixels")
    rendered = surfaces.gallery(SCENES)
    assert f"({surfaces.IMAGES}/{SCENES[0].id}.png)" in rendered
    assert "No still published yet" in rendered  # the other scene still has none
