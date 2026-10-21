"""The PSC Rauzy torus page: two committed JSONL files transcribed field for field,
and every way of not having them in the registered shape refused.

The fixtures are one named and two corpus records in the upstream shape; the real
files are read in `test_estate.py`.
"""

import json

import pytest

from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.sources import SourceError, pages
from vizops.torus import SCHEMA, build, transcribe

PAGE = next(p for p in pages() if p.id == "psc-rauzy-torus")
NAMED_PATH, CORPUS_PATH = (path for _, path in PAGE.files())


def named(**over):
    record = {"schema": SCHEMA, "kind": "named", "name": "tribonacci", "sigma": ["01", "02", "0"],
              "regime": "unimodular-complex", "status": "diagnostic", "scale_bits": 40,
              "freq_floor": [2 ** 39, 2 ** 38, 2 ** 38 - 2], "points": 3, "sup_bound": 2 ** 39,
              "coord_bits": 16, "x": [0, -2 ** 15, 2 ** 16], "y": [0, 2 ** 14, -2 ** 16], "letter": [0, 1, 0],
              "grid": 2, "undecided": 0, "occupied": 3, "lift_keys": [1, 2], "lift_counts": [2, 1],
              "lifts": [1, 2, 0, 1]}
    return {**record, **over}


def refused(**over):
    return {"schema": SCHEMA, "kind": "named", "name": "nonunit_control", "sigma": ["011", "20", "0"],
            "regime": "nonunimodular", "status": "refused", "reason": "needs |det M| = 1", **over}


def corpus():
    return [{"schema": SCHEMA, "kind": "corpus", "index": 0, "i": 0, "j": 3, "k": 1, "sigma": ["0", "01", "2"],
             "regime": "unimodular-real", "status": "diagnostic", "scale_bits": 40,
             "freq_floor": [2 ** 39, 2 ** 38, 2 ** 38 - 1], "points": 4096, "sup_bound": 1, "grid": 32,
             "undecided": 0, "occupied": 10, "lift_keys": [1, 3], "lift_counts": [8, 2]},
            {"schema": SCHEMA, "kind": "corpus", "index": 1, "i": 0, "j": 3, "k": 2, "sigma": ["0", "01", "22"],
             "regime": "nonunimodular", "status": "refused", "reason": "needs |det M| = 1"}]


def jsonl(records):
    return "".join(json.dumps(r) + "\n" for r in records).encode()


@pytest.fixture
def estate(tmp_path):
    def make(named_records=None, corpus_records=None, raw=None):
        files = {NAMED_PATH: jsonl(named_records if named_records is not None else [named(), refused()]),
                 CORPUS_PATH: jsonl(corpus_records if corpus_records is not None else corpus())}
        files.update(raw or {})
        for repo, path in PAGE.files():
            target = tmp_path / "estate" / repo.split("/")[-1] / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if files[path] is not None:
                target.write_bytes(files[path])
        return tmp_path / "estate"
    return make


def test_records_are_transcribed_not_recomputed():
    data = transcribe([named(), refused()], corpus())
    tri, control = data["named"]
    assert tri["x"] == [0, -2 ** 15, 2 ** 16] and tri["bits"] == 16 and tri["lifts"] == [1, 2, 0, 1]
    assert tri["freq"][:2] == [0.5, 0.25] and tri["hist"] == {1: 2, 2: 1} and tri["sup"] == 0.5
    assert control == {"name": "nonunit_control", "sigma": ["011", "20", "0"], "regime": "nonunimodular",
                       "status": "refused", "reason": "needs |det M| = 1"}
    assert data["corpus"] == [[0, "0 01 2", "unimodular-real", 0.5, 0.25, 8, 10, 3],
                              [1, "0 01 22", "nonunimodular"]]
    assert data["corpusGrid"] == 32 and data["corpusPoints"] == 4096


def test_the_page_carries_data_stamps_and_caveat(estate, tmp_path):
    out = tmp_path / "out" / "page.html"
    outcome = build(PAGE, estate(), out=out)
    assert isinstance(outcome, Rendered)
    html = out.read_text(encoding="utf-8")
    assert "__DATA__" not in html and "__SOURCES__" not in html
    assert f"{PAGE.repo}/{NAMED_PATH} @ sha256:" in html and f"{PAGE.repo}/{CORPUS_PATH} @ sha256:" in html
    assert CAVEAT in html and '"name":"tribonacci"' in html


@pytest.mark.parametrize("named_records, corpus_records, raw, reason", [
    (None, None, {NAMED_PATH: None}, "no artifact"),
    (None, None, {CORPUS_PATH: b"not json\n"}, "not JSONL"),
    ([named(schema="psc-rauzy-torus/v0")], None, None, "does not declare schema"),
    ([named(status="certified")], None, None, "has status 'certified'"),
    ([refused()], None, None, "no diagnostic record"),
    ([named(x=[0, 1])], None, None, "arrays disagree"),
    ([named(lifts=[1, 2, 0])], None, None, "arrays disagree"),
    ([named(lift_counts=[2])], None, None, "no longer reads"),
])
def test_a_source_of_another_shape_is_refused_and_nothing_is_written(
        estate, tmp_path, named_records, corpus_records, raw, reason):
    out = tmp_path / "out" / "page.html"
    outcome = build(PAGE, estate(named_records, corpus_records, raw), out=out)
    assert isinstance(outcome, Refused) and reason in outcome.reason, outcome
    assert not out.exists()


def test_a_dataset_is_refused(estate, tmp_path):
    outcome = build(PAGE, estate(), dataset=tmp_path / "x.json", out=tmp_path / "p.html")
    assert isinstance(outcome, Refused) and "drop --dataset" in outcome.reason


def test_transcribe_refuses_a_named_file_with_nothing_to_draw():
    with pytest.raises(SourceError):
        transcribe([refused()], corpus())
