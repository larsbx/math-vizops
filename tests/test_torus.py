"""The PSC Rauzy torus page: an evidence bundle transcribed field for field,
held to the bundle's own SHA256SUMS, and every way of not having it refused.

The fixtures are a two-specimen bundle in the upstream shape; the real bundle
is read in `test_estate.py`.
"""

import hashlib
import json

import pytest

from vizops.__main__ import main
from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.sources import SourceError, pages
from vizops.torus import SCHEMA, TEMPLATE, build, records, transcribe

PAGE = next(p for p in pages() if p.id == "psc-rauzy-torus")
NAMED, CORPUS, SUMS = (path for _, path in PAGE.files())
REASON = "the torus picture needs a unimodular incidence matrix (|det M| = 1)"


def specimen(**changes):
    """A named diagnostic record: four points on a 2 x 2 grid."""
    return {"schema": SCHEMA, "kind": "named", "name": "tribonacci", "sigma": ["01", "02", "0"],
            "regime": "unimodular-complex", "status": "diagnostic", "scale_bits": 40,
            "freq_floor": [597792391348, 325013155047, 176706081379], "points": 4,
            "sup_bound": 920370025771, "coord_bits": 16, "x": [0, 29904, -5727, 70000],
            "y": [0, -19373, 26791, 1], "letter": [0, 1, 0, 2], "grid": 2, "undecided": 0,
            "occupied": 3, "lift_keys": [1, 2], "lift_counts": [2, 1], "lifts": [1, 0, 2, 1], **changes}


def control():
    return {"schema": SCHEMA, "kind": "named", "name": "nonunit_control", "sigma": ["011", "20", "0"],
            "regime": "nonunimodular", "status": "refused", "reason": REASON}


def summary(index, **changes):
    return {"schema": SCHEMA, "kind": "corpus", "index": index, "i": 1, "j": 2, "k": 4 + index,
            "sigma": ["1", "2", "01"], "regime": "unimodular-real", "status": "diagnostic", "scale_bits": 40,
            "freq_floor": [269514856189, 472965601848, 357031169738], "points": 4096,
            "sup_bound": 1543830283676, "grid": 32, "undecided": 0, "occupied": 1024,
            "lift_keys": [1, 2, 3, 4], "lift_counts": [104, 532, 372, 16], **changes}


def lines(*recs) -> bytes:
    return "".join(json.dumps(r) + "\n" for r in recs).encode()


def bundle(named=None, corpus=None, sums=None):
    """The three files, keyed by path; SHA256SUMS agrees unless given."""
    named = lines(specimen(), control()) if named is None else named
    corpus = lines(summary(0), summary(1, status="refused", regime="nonunimodular", reason=REASON)) \
        if corpus is None else corpus
    if sums is None:
        sums = "".join(f"{hashlib.sha256(raw).hexdigest()}  {path.rsplit('/', 1)[1]}\n"
                       for path, raw in ((NAMED, named), (CORPUS, corpus))).encode()
    return {NAMED: named, CORPUS: corpus, SUMS: sums}


@pytest.fixture
def estate(tmp_path):
    def make(files=None):
        for path, raw in (bundle() if files is None else files).items():
            target = tmp_path / "estate" / PAGE.checkout / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        return tmp_path / "estate"
    return make


def data_of(html: str) -> dict:
    return json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])


def test_the_template_takes_each_placeholder_once():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert all(text.count(mark) == 1 for mark in ("__DATA__", "__SOURCES__", "__CAVEAT__"))


def test_every_field_is_transcribed_and_no_status_is_decided_here():
    f = bundle()
    data = transcribe(records(f[NAMED], NAMED), records(f[CORPUS], CORPUS))
    one, = data["specimens"]
    assert one == {"name": "tribonacci", "sigma": "01/02/0", "regime": "unimodular-complex",
                   "status": "diagnostic", "freq_floor": [597792391348, 325013155047, 176706081379],
                   "points": 4, "sup_bound": 920370025771, "coord_bits": 16, "grid": 2, "undecided": 0,
                   "occupied": 3, "profile": [[1, 2], [2, 1]], "x": [0, 29904, -5727, 70000],
                   "y": [0, -19373, 26791, 1], "letter": [0, 1, 0, 2], "lifts": [1, 0, 2, 1]}
    assert data["controls"] == [{"name": "nonunit_control", "sigma": "011/20/0",
                                 "regime": "nonunimodular", "reason": REASON}]
    assert data["scale_bits"] == 40
    assert data["corpus"] == {
        "rows": [[0, "1/2/01", "unimodular-real", 269514856189, 472965601848, [[1, 104], [2, 532], [3, 372], [4, 16]]]],
        "regimes": ["unimodular-real"],
        "refused": {"count": 1, "regimes": {"nonunimodular": 1}, "reasons": [REASON]},
    }


def test_the_page_carries_every_source_stamp_the_caveat_and_the_status(estate, tmp_path):
    out = tmp_path / "out.html"
    outcome = build(PAGE, estate(), out=out)
    assert isinstance(outcome, Rendered)
    html = out.read_text(encoding="utf-8")
    assert all(f"{repo}/{path} @ sha256:" in html for repo, path in PAGE.files())
    assert CAVEAT in html and "certifies no covering degree" in html
    assert data_of(html)["specimens"][0]["status"] == "diagnostic"
    assert outcome.digest == hashlib.sha256(out.read_bytes()).hexdigest()


def test_a_missing_file_is_refused_by_name_and_nothing_is_written(estate, tmp_path):
    files = bundle()
    del files[CORPUS]
    outcome = build(PAGE, estate(files), out=tmp_path / "out.html")
    assert isinstance(outcome, Refused) and "corpus.jsonl" in outcome.reason
    assert not (tmp_path / "out.html").exists()


@pytest.mark.parametrize("sums, reason", [
    (b"0" * 64 + b"  named.jsonl\n", "disagrees with the bundle's SHA256SUMS"),
    (b"", "is empty"),
    (b"not a digest line\n", "not a SHA256SUMS line"),
])
def test_bytes_the_bundle_does_not_vouch_for_are_refused(estate, tmp_path, sums, reason):
    files = bundle()
    files[SUMS] = sums
    outcome = build(PAGE, estate(files), out=tmp_path / "out.html")
    assert isinstance(outcome, Refused) and reason in outcome.reason
    assert not (tmp_path / "out.html").exists()


def test_a_file_edited_after_its_digest_was_taken_is_refused(estate):
    files = bundle()
    files[NAMED] = lines(specimen(name="renamed"), control())
    outcome = build(PAGE, estate(files))
    assert isinstance(outcome, Refused) and "named.jsonl" in outcome.reason


@pytest.mark.parametrize("record, reason", [
    (specimen(schema="psc-rauzy-torus/v2"), "psc-rauzy-torus/v2"),
    (specimen(status="certified"), "status 'certified'"),
    (specimen(x=[0, 1, 2]), "4 points"),
    (specimen(letter=[0, 1, 0, 3]), "letter"),
    (specimen(lifts=[1, 0, 2]), "2 x 2 grid"),
    (specimen(grid=3, lifts=[0] * 9), "does not divide"),
    (specimen(lift_counts=[2]), "lift_keys"),
    ({k: v for k, v in specimen().items() if k != "lifts"}, "lifts"),
])
def test_a_record_of_another_shape_is_refused(record, reason):
    with pytest.raises(SourceError) as refusal:
        transcribe(records(lines(record), NAMED), [])
    assert reason in str(refusal.value)


def test_a_corpus_index_given_twice_is_refused():
    with pytest.raises(SourceError, match="index 0 twice"):
        transcribe([], records(lines(summary(0), summary(0)), CORPUS))


def test_a_line_that_is_not_json_is_refused_by_number():
    with pytest.raises(SourceError, match=r"named.jsonl line 2"):
        records(lines(specimen()) + b"{not json\n", NAMED)


def test_a_dataset_is_refused_rather_than_ignored(estate, tmp_path):
    assert isinstance(build(PAGE, estate(), dataset=tmp_path / "d.json"), Refused)


def test_the_cli_builds_it(estate, tmp_path):
    assert main(["page", PAGE.id, "--sources", str(estate()), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / f"{PAGE.id}.html").is_file()
