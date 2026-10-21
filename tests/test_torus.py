"""The PSC Rauzy torus page: the bundle's records transcribed field for field,
and every record that does not read as the bundle says it reads refused.

The fixtures are minimal records in the upstream shape; the real bundle is read
in `test_estate.py`.
"""

import hashlib
import json

import pytest

from vizops.__main__ import main
from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.sources import SourceError, pages
from vizops.torus import build, transcribe

PAGE = next(p for p in pages() if p.id == "psc-rauzy-torus")
REASON = "the torus picture needs a unimodular incidence matrix (|det M| = 1)"


def named(**changes):
    record = {"schema": "psc-rauzy-torus/v1", "kind": "named", "name": "toy", "sigma": ["01", "02", "0"],
              "regime": "unimodular-complex", "status": "diagnostic", "scale_bits": 40,
              "freq_floor": [597792391348, 325013155047, 176706081379], "points": 3, "sup_bound": 9,
              "coord_bits": 16, "x": [0, 29904, -5727], "y": [0, -19373, 7000], "letter": [0, 1, 2],
              "grid": 2, "undecided": 0, "occupied": 3, "lift_keys": [1, 2], "lift_counts": [2, 1],
              "lifts": [1, 0, 2, 1]}
    return {**record, **changes}


def corpus(**changes):
    record = {"schema": "psc-rauzy-torus/v1", "kind": "corpus", "index": 0, "i": 1, "j": 2, "k": 4,
              "sigma": ["1", "2", "01"], "regime": "unimodular-complex", "status": "diagnostic", "scale_bits": 40,
              "freq_floor": [269514856189, 472965601848, 357031169738], "points": 4096, "sup_bound": 9,
              "grid": 2, "undecided": 0, "occupied": 4, "lift_keys": [1, 2], "lift_counts": [3, 1]}
    return {**record, **changes}


def refused(kind, **changes):
    base = named() if kind == "named" else corpus()
    keep = {"schema", "kind", "sigma", "name", "index", "i", "j", "k"}
    return {**{k: v for k, v in base.items() if k in keep},
            "regime": "nonunimodular", "status": "refused", "reason": REASON, **changes}


def jsonl(*records):
    return "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records).encode()


GOOD = (jsonl(named(), refused("named", name="control")),
        jsonl(corpus(), refused("corpus", index=1)))


@pytest.fixture
def estate(tmp_path):
    def make(files=GOOD):
        for (repo, path), content in zip(PAGE.files(), files):
            target = tmp_path / "estate" / repo.split("/")[-1] / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if content is not None:
                target.write_bytes(content)
        return tmp_path / "estate"
    return make


def test_it_reads_the_named_records_and_the_corpus_of_one_bundle():
    (_, own), (_, corpus_path) = PAGE.files()
    assert own.endswith("/named.jsonl") and corpus_path.endswith("/corpus.jsonl")
    assert own.rsplit("/", 1)[0] == corpus_path.rsplit("/", 1)[0]


def test_records_are_transcribed_field_for_field():
    data = transcribe(*(GOOD[0].decode(), GOOD[1].decode()))
    toy, control = data["named"]
    assert toy["x"] == [0, 29904, -5727] and toy["letter"] == [0, 1, 2] and toy["lifts"] == [1, 0, 2, 1]
    assert toy["freq_floor"] == [597792391348, 325013155047, 176706081379]
    assert (toy["lift_keys"], toy["lift_counts"]) == ([1, 2], [2, 1])
    assert control == {"name": "control", "sigma": ["01", "02", "0"], "regime": "nonunimodular",
                       "status": "refused", "reason": REASON}
    row, = data["corpus"]
    assert row == {"index": 0, "sigma": ["1", "2", "01"], "regime": "unimodular-complex",
                   "freq_floor": [269514856189, 472965601848, 357031169738], "scale_bits": 40,
                   "grid": 2, "points": 4096, "undecided": 0, "occupied": 4,
                   "lift_keys": [1, 2], "lift_counts": [3, 1]}
    assert data["refused"] == [{"index": 1, "sigma": ["1", "2", "01"], "regime": "nonunimodular", "reason": REASON}]


def test_the_page_embeds_the_records_and_stamps_both_files(estate, tmp_path):
    out = tmp_path / "out" / "page.html"
    outcome = build(PAGE, estate(), out=out)
    assert isinstance(outcome, Rendered)
    html = out.read_text(encoding="utf-8")
    for (repo, path), content in zip(PAGE.files(), GOOD):
        assert f"{repo}/{path} @ sha256:{hashlib.sha256(content).hexdigest()[:12]}" in html
    assert CAVEAT in html and "certifies no covering degree" in html
    assert "__DATA__" not in html and '"x":[0,29904,-5727]' in html
    assert outcome.digest == hashlib.sha256(out.read_bytes()).hexdigest()


@pytest.mark.parametrize("record, reason", [
    (named(schema="psc-rauzy-torus/v2"), "schema"),
    (named(kind="corpus"), "kind"),
    (named(status="certified"), "status"),
    (named(sigma=["01", "03", "0"]), "sigma"),
    (named(x=[0, 1]), "x"),
    (named(letter=[0, 1, 3]), "letter"),
    (named(y=[0, 1.5, 2]), "y"),
    (named(x=[0, True, 2]), "x"),
    (named(lifts=[1, 0, 2]), "lifts"),
    (named(lifts=[1, -1, 2, 1]), "lifts"),
    (named(occupied=4), "occupied"),
    (named(lift_counts=[1, 2]), "lift_counts"),
    (named(lift_keys=[2, 1]), "lift_keys"),
    (named(freq_floor=[1, 2]), "freq_floor"),
    (named(freq_floor=[1 << 40, 2, 3]), "freq_floor"),
    (named(undecided=-1), "undecided"),
    (refused("named", reason=""), "reason"),
    ({k: v for k, v in named().items() if k != "grid"}, "grid"),
])
def test_a_named_record_of_another_shape_is_refused(record, reason):
    with pytest.raises(SourceError, match=reason):
        transcribe(jsonl(record).decode(), GOOD[1].decode())


@pytest.mark.parametrize("record, reason", [
    (corpus(index=3), "index"),
    (corpus(occupied=5), "occupied"),
    (corpus(occupied=5, lift_counts=[4, 1]), "occupied"),
    (corpus(lift_counts=[4, 0], occupied=4), "lift_counts"),
    (corpus(kind="named"), "kind"),
])
def test_a_corpus_record_of_another_shape_is_refused(record, reason):
    with pytest.raises(SourceError, match=reason):
        transcribe(GOOD[0].decode(), jsonl(record).decode())


@pytest.mark.parametrize("files, reason", [
    ((None, GOOD[1]), "no artifact"),
    ((GOOD[0], None), "no artifact"),
    ((b"", GOOD[1]), "is empty"),
    ((b"{not json\n", GOOD[1]), "line 1"),
    ((b"\xff\xfe", GOOD[1]), "UTF-8"),
    ((jsonl(refused("named")), GOOD[1]), "no diagnostic"),
])
def test_a_bundle_that_cannot_be_read_is_refused_and_nothing_is_written(estate, tmp_path, files, reason):
    out = tmp_path / "out" / "page.html"
    outcome = build(PAGE, estate(files), out=out)
    assert isinstance(outcome, Refused) and reason in outcome.reason
    assert not out.exists()


def test_a_dataset_is_refused(estate, tmp_path):
    outcome = build(PAGE, estate(), dataset=tmp_path / "d.json", out=tmp_path / "page.html")
    assert isinstance(outcome, Refused) and "dataset" in outcome.reason


def test_the_cli_builds_it(estate, tmp_path):
    assert main(["page", "psc-rauzy-torus", "--sources", str(estate()), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "psc-rauzy-torus.html").is_file()
