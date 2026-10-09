"""The atlas page: exact sections read and refused like any artifact, positions
traced here, and the three outcomes reached for the reasons they name.

The exclusion oracle is upstream's and is not copied here, so these tests hand
`build` a stand-in with the same four names; the real one is exercised in
`test_estate.py` against the sibling checkout.
"""

import importlib
import hashlib
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
NAMES_FIXTURE = json.loads((ROOT / "tests/fixtures/atlas_structure_names.json").read_bytes())

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
    return {**base, "catalogues": list(catalogues), "tunings": [], **overrides}


@pytest.fixture
def estate(tmp_path):
    oracle = tmp_path / "estate" / PAGE.checkout / ORACLE
    oracle.parent.mkdir(parents=True)
    oracle.write_text(STUB_ORACLE, encoding="utf-8")
    emitter = tmp_path / "estate" / PAGE.checkout / PAGE.path
    emitter.parent.mkdir(parents=True, exist_ok=True)
    emitter.write_text("// test emitter\n", encoding="utf-8")
    crosswalk = tmp_path / "estate" / PAGE.checkout / NAMES_FIXTURE["source"]["crosswalk_path"]
    crosswalk.parent.mkdir(parents=True, exist_ok=True)
    crosswalk.write_text(json.dumps(NAMES_FIXTURE["crosswalk"]), encoding="utf-8")
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
    crosswalk_path = NAMES_FIXTURE["source"]["crosswalk_path"]
    raw_names = (estate / PAGE.checkout / crosswalk_path).read_bytes()
    assert f"{PAGE.repo}/{crosswalk_path} @ sha256:{hashlib.sha256(raw_names).hexdigest()[:12]}" in html
    embedded = json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])
    assert {"misiurewicz", "components", "certificates"} <= set(embedded)
    assert embedded["misiurewicz"][0]["agrees"] is True


def test_the_unreduced_satellite_is_named_by_the_upstream_crosswalk(estate, tmp_path):
    source = write(tmp_path, dataset(tunings=NAMES_FIXTURE["tunings"]))
    out = tmp_path / "atlas.html"
    assert isinstance(build(PAGE, estate, dataset=source, out=out), Rendered)
    embedded = json.loads(out.read_text().split("const DATA = ", 1)[1].split(";\n", 1)[0])
    satellite = next(c for c in embedded["components"] if c["rays"] == [[6, 15], [9, 15]])
    assert satellite.get("atlas_id") == "bulb-1/2.1/2"
    assert satellite["name"] == "period-4 bulb of the period-2 bulb"
    assert "satellite period 4" in satellite["names"]
    assert embedded["tunings"] == atlas_build.placed_tunings(NAMES_FIXTURE["tunings"])


def named(components, *, crosswalk=None, tunings=None):
    names = atlas_build.structure_names(json.dumps(crosswalk or NAMES_FIXTURE["crosswalk"]).encode(), PAGE.repo)
    return atlas_build.name_components(components, NAMES_FIXTURE["tunings"] if tunings is None else tunings, names)


@pytest.mark.parametrize("rays", [
    [[6, 15], [9, 15]], [[2, 5], [3, 5]], [[12, 30], [18, 30]], [[9, 15], [6, 15]],
])
def test_rational_normalization_and_ray_order_preserve_the_satellite_identity(rays):
    result, = named([{"period": 4, "rays": rays}])
    assert result["atlas_id"] == "bulb-1/2.1/2"
    assert result["name"] == "period-4 bulb of the period-2 bulb"
    assert result["rays"] == rays  # input representation remains intact


def test_unreduced_crosswalk_and_emitter_keys_are_normalized_too():
    crosswalk = json.loads(json.dumps(NAMES_FIXTURE["crosswalk"]))
    satellite = next(n for n in crosswalk["nodes"] if n["id"] == "bulb-1/2.1/2")
    satellite["key"]["root_angles"] = ["6/15", "9/15"]
    row = next(r for r in NAMES_FIXTURE["tunings"] if r["component"] == "satellite period 4")
    tuning = {**row, "lo": [12, 30], "hi": [18, 30]}
    result, = named([{"period": 4, "rays": [[2, 5], [3, 5]]}], crosswalk=crosswalk, tunings=[tuning])
    assert result["atlas_id"] == satellite["id"] and tuning["component"] in result["names"]


@pytest.mark.parametrize("period,rays", [
    (3, [[6, 15], [9, 15]]),  # same rational roots, different declared period
    (4, [[6, 15]]),          # one known ray is not the complete root pair
    (4, [[6, 15], [8, 15]]), # one ray from each of two components
    (4, [[11, 15], [12, 15]]),  # no conjugate entry: do not infer a name
    (4, [[13, 15], [14, 15]]),
])
def test_unknown_or_partial_pairs_do_not_borrow_an_atlas_name(period, rays):
    result, = named([{"period": period, "rays": rays}], tunings=[])
    assert result["name"] is None and result["atlas_id"] is None and result["names"] == []


@pytest.mark.parametrize("period,rays,identifier,label,alias", [
    (1, [[0, 1]], "main-cardioid", "main cardioid", "main cardioid"),
    (2, [[1, 3], [2, 3]], "bulb-1/2", "period-2 bulb", "doubling"),
    (3, [[1, 7], [2, 7]], "bulb-1/3", "1/3-bulb", "rabbit"),
    (3, [[3, 7], [4, 7]], "airplane-component", "period-3 window", "airplane"),
    (3, [[5, 7], [6, 7]], "bulb-2/3", "2/3-bulb", "co-rabbit bulb"),
    (4, [[7, 15], [8, 15]], None, "primitive period 4", "primitive period 4"),
])
def test_existing_names_and_the_declared_conjugate_are_transcribed(period, rays, identifier, label, alias):
    result, = named([{"period": period, "rays": rays}])
    assert result["atlas_id"] == identifier and result["name"] == label
    assert alias in result["names"]


def test_class_and_nearby_centre_fields_do_not_supply_a_component_name():
    crosswalk = json.loads(json.dumps(NAMES_FIXTURE["crosswalk"]))
    satellite = next(n for n in crosswalk["nodes"] if n["id"] == "bulb-1/2.1/2")
    satellite["class"] = "atlas/julia-set"
    result, = named([{"period": 4, "rays": [[6, 15], [9, 15]], "re": -1.3107, "im": 0}],
                    crosswalk=crosswalk, tunings=[])
    assert result["name"] is None and result["atlas_id"] is None


def test_the_crosswalk_bytes_supply_the_label_and_its_stamp(estate, tmp_path):
    path = estate / PAGE.checkout / NAMES_FIXTURE["source"]["crosswalk_path"]
    crosswalk = json.loads(path.read_bytes())
    satellite = next(n for n in crosswalk["nodes"] if n["id"] == "bulb-1/2.1/2")
    satellite["label"] = "upstream label revision"
    path.write_text(json.dumps(crosswalk), encoding="utf-8")
    out = tmp_path / "atlas.html"
    assert isinstance(build(PAGE, estate, dataset=write(tmp_path, dataset()), out=out), Rendered)
    html = out.read_text()
    assert '"name":"upstream label revision"' in html
    assert hashlib.sha256(path.read_bytes()).hexdigest()[:12] in html


def test_upstream_names_are_text_and_cannot_terminate_the_inline_script(estate, tmp_path):
    path = estate / PAGE.checkout / NAMES_FIXTURE["source"]["crosswalk_path"]
    crosswalk = json.loads(path.read_bytes())
    label = '</script><em>upstream label</em>'
    crosswalk["nodes"][0]["label"] = label
    path.write_text(json.dumps(crosswalk), encoding="utf-8")
    out = tmp_path / "atlas.html"
    assert isinstance(build(PAGE, estate, dataset=write(tmp_path, dataset()), out=out), Rendered)
    html = out.read_text()
    assert html.count("</script>") == 1
    embedded = json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])
    assert next(c for c in embedded["components"] if c["atlas_id"] == crosswalk["nodes"][0]["id"])["name"] == label


@pytest.mark.parametrize("field,value", [
    ("format", "structure crosswalk 2"), ("repository", "larsbx/another-repo"),
    ("classes", []), ("nodes", []),
])
def test_wrong_crosswalk_contract_is_refused(field, value):
    crosswalk = {**NAMES_FIXTURE["crosswalk"], field: value}
    with pytest.raises(SourceError, match="structure crosswalk"):
        atlas_build.structure_names(json.dumps(crosswalk).encode(), PAGE.repo)


@pytest.mark.parametrize("change", [
    {"class": "undeclared"}, {"key": {"period": 4, "root_angles": ["2/5", "3/0"]}},
    {"key": {"period": 4, "root_angles": ["2/5", "6/15"]}},
    {"key": {"period": True, "root_angles": ["0/1"]}},
    {"key": {"period": 4, "root_angles": [0.4, 0.6]}}, {"label": None},
])
def test_malformed_component_names_are_refused(change):
    crosswalk = {**NAMES_FIXTURE["crosswalk"], "nodes": [
        {**NAMES_FIXTURE["crosswalk"]["nodes"][0], **change}
    ]}
    with pytest.raises(SourceError, match="structure crosswalk"):
        atlas_build.structure_names(json.dumps(crosswalk).encode(), PAGE.repo)


def test_conflicting_normalized_crosswalk_keys_are_refused():
    crosswalk = json.loads(json.dumps(NAMES_FIXTURE["crosswalk"]))
    original = next(n for n in crosswalk["nodes"] if n["id"] == "bulb-1/2.1/2")
    duplicate = {**original, "id": "conflicting-name", "key": {"period": 4, "root_angles": ["6/15", "9/15"]}}
    crosswalk["nodes"].append(duplicate)
    with pytest.raises(SourceError, match="duplicate component root angles"):
        atlas_build.structure_names(json.dumps(crosswalk).encode(), PAGE.repo)


@pytest.mark.parametrize("payload", [None, b"not json", b"{}"])
def test_missing_or_malformed_crosswalk_writes_nothing(estate, tmp_path, payload):
    path = estate / PAGE.checkout / NAMES_FIXTURE["source"]["crosswalk_path"]
    if payload is None:
        path.unlink()
    else:
        path.write_bytes(payload)
    out = tmp_path / "atlas.html"
    outcome = build(PAGE, estate, dataset=write(tmp_path, dataset()), out=out)
    assert isinstance(outcome, Refused) and not out.exists()


def test_conflicting_emitter_aliases_are_refused():
    row = NAMES_FIXTURE["tunings"][0]
    conflicting = {**row, "lo": [2 * row["lo"][0], 2 * row["lo"][1]], "component": "other label"}
    with pytest.raises(SourceError, match="conflicting tuning labels"):
        named([], tunings=[row, conflicting])


def test_the_registry_and_site_include_the_naming_source():
    from vizops.site import inputs

    expected = (PAGE.repo, NAMES_FIXTURE["source"]["crosswalk_path"])
    assert expected in PAGE.files()
    assert (*expected, None) in inputs(PAGE)


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
