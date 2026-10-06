"""The wake page and scene: exact rows are the vendored `rational_dynamics_py`'s,
reached only through `sources.vendored_package`, the page embeds them, and a
package with any file drifted from its pin is a refusal.

The package is finite-math-kernels', copied byte-for-byte under vendor/python/
and pinned in vendored.toml, so these tests run against the real thing and
need no sibling checkout.
"""

import dataclasses
import hashlib
import importlib
import json
import tomllib
from fractions import Fraction
from pathlib import Path

import pytest
import rational_dynamics_py

import artifacts
from vizops.__main__ import main
from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.sources import SourceError, load, pages, vendored_package
from vizops.wake import QMAX, STILL, TEMPLATE, WakeCycleFigure, build, rows, scene_figure, still_claims

#: The module, not the `build` function `vizops.wake` exports under that name.
wake_build = importlib.import_module("vizops.wake.build")

ROOT = Path(__file__).resolve().parents[1]
VENDORED = ROOT / "vendored.toml"
PAGE = next(p for p in pages() if p.id == "wake-to-mandelbrot")
SCENE = next(s for s in load() if s.id == "wake-cycle-3-7")
UPSTREAM = "larsbx/finite-math-kernels"


def pinned_set_digest() -> str:
    """The digest of the package's whole pinned file set, from vendored.toml directly."""
    (entry,) = [p for p in tomllib.loads(VENDORED.read_text(encoding="utf-8"))["package"]
                if p["name"] == "rational_dynamics_py"]
    listing = "".join(f"{d}  {rel}\n" for rel, d in sorted(entry["files"].items()))
    return hashlib.sha256(listing.encode()).hexdigest()


RD = vendored_package("rational_dynamics_py").module


def embedded(html: str) -> list[dict]:
    return json.loads(html.split("var DATA=", 1)[1].split(";\n", 1)[0])


def test_the_wake_data_comes_from_the_vendored_package():
    vendored = ROOT / "vendor" / "python" / "rational_dynamics_py"
    assert RD is rational_dynamics_py
    assert Path(rational_dynamics_py.__file__).resolve().parent == vendored
    for entry in (PAGE, SCENE):
        package = entry.package()
        assert entry.vendored == "rational_dynamics_py" and entry.repo == UPSTREAM
        assert package.module is rational_dynamics_py
        assert package.digest == pinned_set_digest()
        assert {rel for rel, _ in package.pin.files} >= {
            "rational_dynamics_py/__init__.py", "rational_dynamics_py/doubling.py", "rational_dynamics_py/farey.py"}
        assert len(package.pin.commit) == 40
    # No module of vizops imports the package except through the accessor.
    for source in (ROOT / "vizops").rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "import rational_dynamics_py" not in text and "from rational_dynamics_py" not in text, source


def test_the_rows_are_the_package_answers():
    for row in rows(RD):
        p, q, den = row["p"], row["q"], row["den"]
        lo, hi = rational_dynamics_py.wake(p, q)
        assert (Fraction(row["lo"], den), Fraction(row["hi"], den)) == (lo, hi)
        assert row["word"] == rational_dynamics_py.mechanical_word(p, q, 0)
        assert [Fraction(n, den) for n in row["cycle"]] == list(rational_dynamics_py.rotation_cycle(p, q))


def test_every_reduced_angle_is_tabulated():
    table = rows(RD)
    assert len(table) == 45  # sum of phi(q) for 2 <= q <= 12
    assert all(r["cycle"] == sorted(r["cycle"]) and r["hi"] - r["lo"] == 1 for r in table)


def test_the_template_takes_each_placeholder_once_and_computes_no_angle():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert all(text.count(mark) == 1 for mark in ("__DATA__", "__STAMP__", "__QMAX__"))
    assert "mechanical" not in text and "cycleNums" not in text  # the page looks up; it does not derive


def test_the_manim_payload_is_the_vendored_3_7_specimen(tmp_path):
    drawn = scene_figure(SCENE, tmp_path / "no-estate-needed")
    assert isinstance(drawn, WakeCycleFigure)
    assert drawn.word == 21 and drawn.denominator == 127
    assert drawn.orbit == (21, 42, 84, 41, 82, 37, 74)
    assert drawn.angular == (21, 37, 41, 42, 74, 82, 84)
    assert drawn.characteristic == (41, 42)
    assert drawn.provenance.repo == UPSTREAM
    assert drawn.provenance.digest == pinned_set_digest()
    assert -0.607 < drawn.root_re < -0.606
    assert 0.412 < drawn.root_im < 0.413


def test_the_page_embeds_every_reduced_angle_with_its_stamp(tmp_path):
    out = tmp_path / "out" / "wake.html"
    assert isinstance(build(PAGE, tmp_path / "no-estate-needed", out=out), Rendered)
    html = out.read_text(encoding="utf-8")
    digest = pinned_set_digest()
    assert CAVEAT in html and f"{PAGE.repo}/{PAGE.path} @ sha256:{digest[:12]}" in html
    assert f'max="{QMAX}"' in html
    table = embedded(html)
    assert table == rows(RD)
    assert {(r["p"], r["q"]) for r in table} == {(p, q) for q in range(2, QMAX + 1) for p in range(1, q)
                                                 if all(p % d or q % d for d in range(2, q + 1))}
    (row,) = [r for r in table if (r["p"], r["q"]) == (3, 7)]
    assert row == {"p": 3, "q": 7, "den": 127, "word": 21,
                   "cycle": [21, 37, 41, 42, 74, 82, 84], "lo": 41, "hi": 42}


@pytest.mark.parametrize("file", ["doubling.py", "__init__.py", "farey.py"])
def test_any_drifted_file_of_the_package_is_refused(tmp_path, monkeypatch, file):
    """`rows` calls `wake` and friends through `__init__.py`, so a drifted
    `__init__.py` is refused like a drifted `doubling.py`."""
    artifacts.drifted_vendor(tmp_path, monkeypatch, file=file)
    out = tmp_path / "wake.html"
    outcome = build(PAGE, tmp_path, out=out)
    assert isinstance(outcome, Refused)
    assert f"rational_dynamics_py/{file}" in outcome.reason and "differs from" in outcome.reason
    assert not out.exists()
    with pytest.raises(SourceError, match="differs from"):
        scene_figure(SCENE, tmp_path)


def test_an_undrifted_install_elsewhere_is_accepted_and_a_missing_or_extra_file_is_not(tmp_path, monkeypatch):
    copy = artifacts.drifted_vendor(tmp_path, monkeypatch, change=b"")
    assert vendored_package("rational_dynamics_py").digest == pinned_set_digest()
    (copy.parent / "extra.py").write_text("PATCH = 1\n", encoding="utf-8")
    with pytest.raises(SourceError, match="rational_dynamics_py/extra.py is not pinned"):
        vendored_package("rational_dynamics_py")
    (copy.parent / "extra.py").unlink()
    (copy.parent / "arithmetic.py").unlink()
    with pytest.raises(SourceError, match="arithmetic.py is missing"):
        vendored_package("rational_dynamics_py")


def test_a_page_entry_that_is_not_vendored_is_refused(tmp_path):
    checkout = tmp_path / "finite-math-kernels" / PAGE.path
    checkout.parent.mkdir(parents=True)
    checkout.write_text("anything\n", encoding="utf-8")
    outcome = build(dataclasses.replace(PAGE, vendored=""), tmp_path, out=tmp_path / "wake.html")
    assert isinstance(outcome, Refused) and "not a vendored package" in outcome.reason


def test_a_package_that_no_longer_answers_is_refused_and_nothing_is_written(tmp_path, monkeypatch):
    def renamed(p, q):
        raise ValueError("renamed")

    monkeypatch.setattr(rational_dynamics_py, "wake", renamed)
    out = tmp_path / "wake.html"
    outcome = build(PAGE, tmp_path, out=out)
    assert isinstance(outcome, Refused) and "no longer answers" in outcome.reason
    assert not out.exists()


def test_a_dataset_is_refused_rather_than_ignored(tmp_path):
    outcome = build(PAGE, tmp_path, dataset=tmp_path / "dataset.json")
    assert isinstance(outcome, Refused) and "--dataset" in outcome.reason


def test_the_committed_still_prints_the_3_7_pair():
    assert still_claims(STILL.read_text(encoding="utf-8")) == {
        "cycle": [21, 37, 41, 42, 74, 82, 84], "lo": 41, "hi": 42, "den": 127}


def test_the_committed_still_prints_what_the_package_says():
    """The 3/7 still is drawn by hand, so it is held to the package here: a
    re-vendored package that moves these numbers fails until the still is redrawn."""
    (row,) = [r for r in rows(RD) if (r["p"], r["q"]) == (3, 7)]
    claims = still_claims(STILL.read_text(encoding="utf-8"))
    assert claims == {k: row[k] for k in ("cycle", "lo", "hi", "den")}


def test_a_still_that_prints_no_pair_is_refused():
    with pytest.raises(SourceError, match="no angular order"):
        still_claims("<svg><text>3/7</text></svg>")


def test_the_cli_builds_one_page_by_id(tmp_path, capsys):
    assert main(["page", PAGE.id, "--sources", str(tmp_path / "estate"), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / f"{PAGE.id}.html").is_file()
    assert main(["page", "no-such-page"]) == 1
    assert "no such page" in capsys.readouterr().err


def test_the_package_refuses_non_integers_and_vizops_passes_none():
    """The pinned package refuses floats and bools rather than coercing them;
    every call vizops makes passes ints, so the table builds."""
    for bad in ((3.0, 7), (True, 7), (3, 7.0)):
        with pytest.raises(TypeError):
            rational_dynamics_py.wake(*bad)
    assert all(type(v) is int for row in rows(RD) for k, v in row.items() if k != "cycle")
    assert all(type(n) is int for row in rows(RD) for n in row["cycle"])
