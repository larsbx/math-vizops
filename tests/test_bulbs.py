"""The Bulbs & Ford Circles page: four committed files transcribed field for
field, and every way of not having them -- or of their disagreeing -- refused.

The fixtures are two bulbs in the upstream shapes; the real files are read in
`test_estate.py`.
"""

import json
from fractions import Fraction

import pytest

from vizops.__main__ import main
from vizops.bulbs import SCHEMAS, TEMPLATE, build, transcribe
from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.sources import SourceError, pages

PAGE = next(p for p in pages() if p.id == "bulbs-and-ford-circles")
PREC = 4  # boxes over 2^4, so the midpoints below are easy to read


def box(re_lo, re_hi, im_lo, im_hi):
    return [str(n) for n in (re_lo, re_hi, im_lo, im_hi)]


def files(verdict="ACCEPTED", drop_antipode=False):
    """The four sources, keyed by path, for bulbs 1/2 and 1/3."""
    centres = [{"p": 1, "q": 2, "prec": PREC, "box_numerators": box(-17, -15, -1, 1), "verdict": "ACCEPTED"},
               {"p": 1, "q": 3, "prec": PREC, "box_numerators": box(-3, -1, 11, 13), "verdict": verdict}]
    antipodes = [{"p": 1, "q": 2, "prec": PREC, "c_box_numerators": box(-21, -19, -1, 1), "verdict": "ACCEPTED",
                  "G_ant_bounds": ["999999999999999/1000000000000000", "1000000000000001/1000000000000000"]},
                 {"p": 1, "q": 3, "prec": PREC, "c_box_numerators": box(-3, -1, 13, 15), "verdict": "ACCEPTED",
                  "G_ant_bounds": ["1/3", "2/3"]}]
    return {
        "experiments/data/center_certificates.json": {"schema": SCHEMAS["experiments/data/center_certificates.json"],
                                                      "certificates": centres},
        "experiments/data/antipode_certificates.json": {
            "schema": SCHEMAS["experiments/data/antipode_certificates.json"],
            "certificates": antipodes[:1] if drop_antipode else antipodes},
        "experiments/data/kappa_q1009.json": [{"p": 1, "q": 1009, "xt": 0.00099108, "G": 1.02637753,
                                               "kappa": [0.0238262652, -0.0524611]}],
        "conformance/cyclotomic_germ_v1.json": {"schema": SCHEMAS["conformance/cyclotomic_germ_v1.json"],
                                                "vectors": [{"p": 1, "q": 2, "reciprocal_coefficient": ["1/8"]}]},
    }


@pytest.fixture
def estate(tmp_path):
    def make(sources=None):
        sources = files() if sources is None else sources
        for repo, path in PAGE.files():
            target = tmp_path / "estate" / repo.split("/")[-1] / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if path in sources:
                content = sources[path]
                target.write_bytes(content if isinstance(content, bytes) else json.dumps(content).encode())
        return tmp_path / "estate"
    return make


def data_of(html: str) -> dict:
    return json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])


def test_the_template_takes_each_placeholder_once():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert all(text.count(mark) == 1 for mark in ("__DATA__", "__SOURCES__", "__CAVEAT__"))


def test_every_field_is_transcribed_and_no_verdict_is_decided_here():
    f = files(verdict="INCONCLUSIVE")
    data = transcribe(*(f[path] for _, path in PAGE.files()))
    half, third = data["bulbs"]
    assert half == {"p": 1, "q": 2, "cen": [-1.0, 0.0], "ant": [-1.25, 0.0], "Glo": "0.999999999999999",
                    "Ghi": "1.000000000000001", "Gw": float(Fraction(2, 10 ** 15)),
                    "verdictC": "ACCEPTED", "verdictA": "ACCEPTED"}
    assert third["verdictC"] == "INCONCLUSIVE"  # copied as written, never re-judged
    assert data["iota"] == {"1/2": ["1/8"]}
    assert data["dense"] == [[1, 0.000991, 1.026378, 0.02383, -0.05246]]


def test_a_bracket_is_rounded_outward_never_inward():
    third = transcribe(*(files()[path] for _, path in PAGE.files()))["bulbs"][1]
    assert Fraction(third["Glo"]) <= Fraction(1, 3) and Fraction(third["Ghi"]) >= Fraction(2, 3)
    assert (third["Glo"], third["Ghi"]) == ("0.333333333333333", "0.666666666666667")


def test_the_page_carries_every_source_stamp_and_the_caveat(estate, tmp_path):
    out = tmp_path / "out.html"
    assert isinstance(build(PAGE, estate(), out=out), Rendered)
    html = out.read_text(encoding="utf-8")
    assert all(f"{repo}/{path} @ sha256:" in html for repo, path in PAGE.files())
    assert CAVEAT in html
    assert data_of(html)["germ"].startswith("larsbx/finite-math-kernels/conformance/cyclotomic_germ_v1.json @ sha256:")


def test_a_missing_file_is_refused_by_name(estate, tmp_path):
    f = files()
    del f["conformance/cyclotomic_germ_v1.json"]
    outcome = build(PAGE, estate(f), out=tmp_path / "out.html")
    assert isinstance(outcome, Refused) and "cyclotomic_germ_v1.json" in outcome.reason
    assert not (tmp_path / "out.html").exists()


def test_another_schema_is_refused(estate):
    f = files()
    f["experiments/data/antipode_certificates.json"]["schema"] = "bulbford-antipode-certificates/v2"
    outcome = build(PAGE, estate(f))
    assert isinstance(outcome, Refused) and "v2" in outcome.reason


def test_a_bulb_with_a_centre_but_no_antipode_is_refused():
    with pytest.raises(SourceError, match="disagree about which bulbs exist: 1/3"):
        transcribe(*(files(drop_antipode=True)[path] for _, path in PAGE.files()))


@pytest.mark.parametrize("path, content", [
    ("experiments/data/kappa_q1009.json", b"{not json"),
    ("experiments/data/kappa_q1009.json", [{"p": 1, "xt": 0.1}]),
])
def test_a_file_that_no_longer_reads_is_refused(estate, path, content):
    f = files()
    f[path] = content
    assert isinstance(build(PAGE, estate(f)), Refused)


def test_a_dataset_is_refused_rather_than_ignored(estate, tmp_path):
    assert isinstance(build(PAGE, estate(), dataset=tmp_path / "d.json"), Refused)


def test_the_cli_builds_it(estate, tmp_path):
    assert main(["page", PAGE.id, "--sources", str(estate()), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / f"{PAGE.id}.html").is_file()
