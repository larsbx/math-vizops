"""The atlas page: exact sections read and refused like any artifact, positions
traced here, and the three outcomes reached for the reasons they name.

The exclusion oracle is upstream's and is not copied here, so these tests hand
`build` a stand-in with the same four names; the real one is exercised in
`test_estate.py` against the sibling checkout.
"""

import importlib
import json
from fractions import Fraction
from pathlib import Path

import pytest

from vizops.__main__ import main
from vizops.atlas import SECTIONS, TEMPLATES, build, exact
from vizops.atlas import trace
from vizops.atlas.build import ORACLE
from vizops.figure import CAVEAT
from vizops.outcome import Inconclusive, Refused, Rendered
from vizops.sources import SourceError, pages, vendored_package

#: The module, not the `build` function `vizops.atlas` exports under that name.
atlas_build = importlib.import_module("vizops.atlas.build")
ROOT = Path(__file__).resolve().parents[1]

PAGE = next(p for p in pages() if p.id == "mandelbrot-atlas")
STUB_ORACLE = '''
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True)
class I:
    lo: Fraction
    hi: Fraction


@dataclass(frozen=True)
class CI:
    re: I
    im: I


def dyadic_box(re_num, im_num, centre_exp, half_exp):
    h = Fraction(1, 2 ** half_exp)
    re, im = Fraction(re_num, 2 ** centre_exp), Fraction(im_num, 2 ** centre_exp)
    return CI(I(re - h, re + h), I(im - h, im + h))


def c_minus_2_box():
    return dyadic_box(-2, 0, 0, 4)


def m41_box():
    return dyadic_box(0, 0, 0, 25)


def excluded_count(box, ell, period, horizon):
    return 1, 1, []
'''


def dataset(catalogues=({"l": 1, "k": 1, "den": 2, "addresses": [1]},), **overrides) -> dict:
    """The smallest emitter output the page draws: one address, c = -2."""
    base = {section: [] for section in SECTIONS}
    return {**base, "catalogues": list(catalogues), "tunings": [{"tuned": None, "period": 0}], **overrides}


@pytest.fixture
def estate(tmp_path):
    oracle = tmp_path / "estate" / PAGE.checkout / ORACLE
    oracle.parent.mkdir(parents=True)
    oracle.write_text(STUB_ORACLE, encoding="utf-8")
    emitter = tmp_path / "estate" / PAGE.checkout / PAGE.path
    emitter.parent.mkdir(parents=True, exist_ok=True)
    emitter.write_text("// test emitter\n", encoding="utf-8")
    return tmp_path / "estate"


def write(tmp_path, content) -> Path:
    path = tmp_path / "dataset.json"
    path.write_bytes(content if isinstance(content, bytes) else json.dumps(content).encode())
    return path


# --- the tracer -----------------------------------------------------------------


def test_the_half_ray_lands_at_minus_two_and_satisfies_its_type():
    c = trace.trace_ray(Fraction(1, 2), depth=22)
    assert abs(c + 2) < 1e-6
    assert trace.satisfies_type(c, 1, 1)
    assert not trace.satisfies_type(c, 0, 1)  # a negative control: -2 is not periodic


def test_the_third_ray_names_the_period_two_component():
    centre = trace.newton_center(trace.trace_ray(Fraction(1, 3), depth=18), 2)
    assert abs(centre + 1) < 1e-12


@pytest.mark.parametrize("theta, kind", [
    (Fraction(1, 7), (0, 3)), (Fraction(1, 3), (0, 2)),
    (Fraction(1, 2), (1, 1)),               # preperiodic: an exact type, not "None"
    (Fraction(1, 2 ** 33 - 1), (0, 33)),    # the old cap of 32 admitted 33 ...
    (Fraction(1, 2 ** 34 - 1), (0, 34)),    # ... and answered None past it; there is no cap now
    (Fraction(5, 24), (3, 2)),
])
def test_the_type_under_doubling_is_the_vendored_exact_one(theta, kind):
    assert vendored_package(atlas_build.EXACT).module.exact_type(theta) == kind


def test_root_rays_are_chosen_by_the_verified_vendored_package_and_no_local_copy():
    package = vendored_package(atlas_build.EXACT)
    assert Path(package.module.__file__).resolve().parent == ROOT / "vendor" / "python" / "rational_dynamics_py"
    assert not hasattr(trace, "period_of")
    assert "rational_dynamics_py" not in atlas_build.__dict__ and "exact_type" not in atlas_build.__dict__


# --- the dataset, read fail-closed ----------------------------------------------


def test_the_templates_take_the_dataset_and_the_stamp_once():
    assert (TEMPLATES / "script.html").read_text(encoding="utf-8").count("__DATA__") == 1
    assert (TEMPLATES / "body.html").read_text(encoding="utf-8").count("__STAMP__") == 1


def test_a_well_formed_dataset_is_read_as_is():
    assert exact(json.dumps(dataset()).encode()) == dataset()


@pytest.mark.parametrize("raw, reason", [
    (b"not json", "not JSON"),
    (json.dumps({k: v for k, v in dataset().items() if k != "graphs"}).encode(), "sections"),
    (json.dumps({**dataset(), "positions": []}).encode(), "sections"),
    (json.dumps(dataset(density=[{"value": 0.5}])).encode(), r"float reached .*density\[0\]\.value"),
])
def test_a_malformed_dataset_is_refused(raw, reason):
    with pytest.raises(SourceError, match=reason):
        exact(raw)


# --- the three outcomes -----------------------------------------------------------


def test_a_dataset_renders_a_page_stamped_with_every_input_digest(estate, tmp_path):
    source = write(tmp_path, dataset())
    outcome = build(PAGE, estate, dataset=source, out=tmp_path / "out" / "atlas.html")
    assert isinstance(outcome, Rendered)
    html = (tmp_path / "out" / "atlas.html").read_text(encoding="utf-8")
    assert "__DATA__" not in html and "__STAMP__" not in html
    assert CAVEAT in html
    assert f"{PAGE.repo}/{PAGE.path} @ sha256:" in html
    assert f"{PAGE.repo}/{ORACLE} @ sha256:" in html
    assert f"dataset/{source.name} @ sha256:" in html
    assert f"rational_dynamics_py (vendored at " in html
    assert vendored_package(atlas_build.EXACT).digest[:12] in html
    embedded = json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])
    assert {"misiurewicz", "components", "certificates"} <= set(embedded)
    assert embedded["misiurewicz"][0]["agrees"] is True


def test_a_missing_checkout_is_refused(tmp_path):
    assert isinstance(build(PAGE, tmp_path / "nothing"), Refused)


def test_a_checkout_without_the_oracle_is_refused(tmp_path):
    (tmp_path / PAGE.checkout).mkdir()
    outcome = build(PAGE, tmp_path, dataset=write(tmp_path, dataset()))
    assert isinstance(outcome, Refused) and "exclusion oracle" in outcome.reason


def test_a_missing_dataset_file_is_refused(estate, tmp_path):
    assert isinstance(build(PAGE, estate, dataset=tmp_path / "absent.json"), Refused)


def test_a_malformed_nested_record_is_refused_without_writing(estate, tmp_path):
    out = tmp_path / "atlas.html"
    malformed = dataset(catalogues=[{"k": 1, "den": 2, "addresses": [1]}])
    outcome = build(PAGE, estate, dataset=write(tmp_path, malformed), out=out)
    assert isinstance(outcome, Refused) and "nested records" in outcome.reason
    assert not out.exists()


def test_nullable_tuning_is_rendered_as_unavailable():
    # Keep the browser-side table builder from indexing the accepted null value.
    script = (TEMPLATES / "script.html").read_text(encoding="utf-8")
    assert 't.tuned === null ? "—"' in script


def test_a_position_that_disagrees_with_its_type_is_refused_and_nothing_is_written(estate, tmp_path, monkeypatch):
    # With no polish, the ray at 1/2 stays at -2, whose critical value is not fixed.
    monkeypatch.setattr(trace, "polish_misiurewicz", lambda *_: None)
    lying = dataset(catalogues=[{"l": 0, "k": 1, "den": 2, "addresses": [1]}])
    out = tmp_path / "atlas.html"
    outcome = build(PAGE, estate, dataset=write(tmp_path, lying), out=out)
    assert isinstance(outcome, Refused) and "1/2" in outcome.reason
    assert not out.exists()


def test_no_pixi_and_no_dataset_is_inconclusive(estate, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    outcome = build(PAGE, estate)
    assert isinstance(outcome, Inconclusive) and "--dataset" in outcome.reason


def test_an_emitter_that_fails_is_refused(estate, tmp_path, monkeypatch):
    pixi = tmp_path / "bin" / "pixi"
    pixi.parent.mkdir()
    pixi.write_text("#!/bin/sh\necho 'mojo: no such module' >&2\nexit 3\n")
    pixi.chmod(0o755)
    monkeypatch.setenv("PATH", str(pixi.parent))
    outcome = build(PAGE, estate)
    assert isinstance(outcome, Refused) and "exited 3" in outcome.reason and "no such module" in outcome.reason


def test_the_cli_scores_the_atlas_like_a_render(estate, tmp_path, capsys):
    assert main(["page", PAGE.id, "--sources", str(estate), "--dataset", str(write(tmp_path, dataset())),
                 "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / f"{PAGE.id}.html").is_file()
    assert main(["page", PAGE.id, "--sources", str(tmp_path / "nothing")]) == 1
    assert "refused" in capsys.readouterr().out


@pytest.mark.parametrize("file", ["__init__.py", "doubling.py"])
def test_a_drifted_vendored_package_is_refused_and_nothing_is_written(estate, tmp_path, monkeypatch, file):
    """Root rays are chosen by `exact_type`; a modified or shadowing install
    would move them silently, so the atlas refuses it."""
    import artifacts

    artifacts.drifted_vendor(tmp_path, monkeypatch, file=file)
    out = tmp_path / "atlas.html"
    outcome = build(PAGE, estate, dataset=write(tmp_path, dataset()), out=out)
    assert isinstance(outcome, Refused) and f"rational_dynamics_py/{file}" in outcome.reason
    assert not out.exists()
