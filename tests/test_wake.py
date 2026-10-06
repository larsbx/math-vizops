"""The wake page and scene: exact rows are the vendored `rational_dynamics_py`'s,
the page embeds them, and a vendored copy that has drifted from its pin is a
refusal.

The package is finite-math-kernels', copied byte-for-byte under vendor/python/
and pinned in vendored.toml, so these tests run against the real thing and
need no sibling checkout.
"""

import dataclasses
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
from vizops.sources import SourceError, load, pages
from vizops.wake import QMAX, STILL, TEMPLATE, WakeCycleFigure, build, rows, scene_figure, still_claims

#: The module, not the `build` function `vizops.wake` exports under that name.
wake_build = importlib.import_module("vizops.wake.build")

ROOT = Path(__file__).resolve().parents[1]
VENDORED = ROOT / "vendored.toml"
PAGE = next(p for p in pages() if p.id == "wake-to-mandelbrot")
SCENE = next(s for s in load() if s.id == "wake-cycle-3-7")
UPSTREAM = "larsbx/finite-math-kernels"


def pinned(rel: str) -> str:
    (entry,) = [p for p in tomllib.loads(VENDORED.read_text(encoding="utf-8"))["package"]
                if p["name"] == "rational_dynamics_py"]
    return entry["files"][rel]


def embedded(html: str) -> list[dict]:
    return json.loads(html.split("var DATA=", 1)[1].split(";\n", 1)[0])


def test_the_wake_data_comes_from_the_vendored_package():
    assert wake_build.rd is rational_dynamics_py
    vendored = ROOT / "vendor" / "python" / "rational_dynamics_py"
    assert Path(rational_dynamics_py.__file__).resolve().parent == vendored
    for entry in (PAGE, SCENE):
        copy = entry.copy()
        assert entry.vendored == "rational_dynamics_py" and entry.repo == UPSTREAM
        assert copy.local.resolve() == vendored / "doubling.py"
        assert copy.digest == pinned("rational_dynamics_py/doubling.py")
        assert len(copy.commit) == 40


def test_the_rows_are_the_package_answers():
    for row in rows():
        p, q, den = row["p"], row["q"], row["den"]
        lo, hi = rational_dynamics_py.wake(p, q)
        assert (Fraction(row["lo"], den), Fraction(row["hi"], den)) == (lo, hi)
        assert row["word"] == rational_dynamics_py.mechanical_word(p, q, 0)
        assert [Fraction(n, den) for n in row["cycle"]] == list(rational_dynamics_py.rotation_cycle(p, q))


def test_every_reduced_angle_is_tabulated():
    table = rows()
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
    assert drawn.provenance.digest == pinned("rational_dynamics_py/doubling.py")
    assert -0.607 < drawn.root_re < -0.606
    assert 0.412 < drawn.root_im < 0.413


def test_the_page_embeds_every_reduced_angle_with_its_stamp(tmp_path):
    out = tmp_path / "out" / "wake.html"
    assert isinstance(build(PAGE, tmp_path / "no-estate-needed", out=out), Rendered)
    html = out.read_text(encoding="utf-8")
    digest = pinned("rational_dynamics_py/doubling.py")
    assert CAVEAT in html and f"{PAGE.repo}/{PAGE.path} @ sha256:{digest[:12]}" in html
    assert f'max="{QMAX}"' in html
    table = embedded(html)
    assert table == rows()
    assert {(r["p"], r["q"]) for r in table} == {(p, q) for q in range(2, QMAX + 1) for p in range(1, q)
                                                 if all(p % d or q % d for d in range(2, q + 1))}
    (row,) = [r for r in table if (r["p"], r["q"]) == (3, 7)]
    assert row == {"p": 3, "q": 7, "den": 127, "word": 21,
                   "cycle": [21, 37, 41, 42, 74, 82, 84], "lo": 41, "hi": 42}


def test_a_vendored_copy_that_drifted_from_its_pin_is_refused(tmp_path, monkeypatch):
    artifacts.drifted_vendor(tmp_path, monkeypatch)
    out = tmp_path / "wake.html"
    outcome = build(PAGE, tmp_path, out=out)
    assert isinstance(outcome, Refused) and "differs from" in outcome.reason and "pinned" in outcome.reason
    assert not out.exists()
    with pytest.raises(SourceError, match="differs from"):
        scene_figure(SCENE, tmp_path)


def test_a_pinned_copy_that_is_not_the_imported_one_is_refused(tmp_path, monkeypatch):
    artifacts.drifted_vendor(tmp_path, monkeypatch, change=b"")
    outcome = build(PAGE, tmp_path, out=tmp_path / "wake.html")
    assert isinstance(outcome, Refused) and "imported from" in outcome.reason


def test_a_page_entry_that_is_not_vendored_is_refused(tmp_path):
    checkout = tmp_path / "finite-math-kernels" / PAGE.path
    checkout.parent.mkdir(parents=True)
    checkout.write_text("anything\n", encoding="utf-8")
    outcome = build(dataclasses.replace(PAGE, vendored=""), tmp_path, out=tmp_path / "wake.html")
    assert isinstance(outcome, Refused) and 'vendored = "rational_dynamics_py"' in outcome.reason


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
    (row,) = [r for r in rows() if (r["p"], r["q"]) == (3, 7)]
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
    assert all(type(v) is int for row in rows() for k, v in row.items() if k != "cycle")
    assert all(type(n) is int for row in rows() for n in row["cycle"])
