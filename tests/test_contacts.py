"""The PSC Rauzy contacts page: an exact contacts bundle transcribed field for
field, and every way of not having it in the registered shape refused.

The fixtures are one named and two corpus records in the upstream shape; the
real bundle is read in `test_estate.py`.
"""

import hashlib
import json

import pytest

from vizops.contacts import SCHEMA, build, transcribe
from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.sources import SourceError, pages

PAGE = next(p for p in pages() if p.id == "psc-rauzy-contacts")
NAMED_PATH, CORPUS_PATH, SUMS_PATH = (path for _, path in PAGE.files())
CONSEQUENCE = "PDS by BoxAutomatonPDSCertificate; covering degree 1 by the cited equivalence"
# Two contacts and their reversals: one lattice contact (|w|_1 = 0), one not.
CONTACTS = [[0, 1, 1, 0, -1, 1 << 16, 0], [1, 0, -1, 0, 1, -(1 << 16), 0],
            [0, 2, 1, 0, 0, 30000, -20000], [2, 0, -1, 0, 0, -30000, 20000]]


def verdict(**over):
    return {"box_productive": True, "box_states": 743, "box_recurrent": 14, "box_coincidence_depth": 8,
            "contacts": 4, "lattice_contacts": 2,
            "lattice_neighbours": [[1, 0], [-1, 0]], "consequence": CONSEQUENCE, **over}


def named(**over):
    return {"schema": SCHEMA, "kind": "named", "name": "tribonacci", "sigma": ["01", "02", "0"],
            "regime": "unimodular-complex", "status": "exact", "coord_bits": 16, "freq_floor": [5, 3, 1],
            **verdict(), "contact_list": CONTACTS, "points": 3, "x": [0, 1, 2], "y": [0, -1, 2],
            "letter": [0, 1, 2], **over}


def refused(**over):
    return {"schema": SCHEMA, "kind": "named", "name": "nonunit_control", "sigma": ["011", "20", "0"],
            "regime": "nonunimodular", "status": "refused", "reason": "needs |det M| = 1", **over}


def corpus():
    return [{"schema": SCHEMA, "kind": "corpus", "index": 0, "i": 0, "j": 3, "k": 1, "sigma": ["0", "01", "2"],
             "regime": "unimodular-real", "status": "exact", "freq_floor": [5, 3, 1], **verdict()},
            {"schema": SCHEMA, "kind": "corpus", "index": 1, "i": 0, "j": 3, "k": 2, "sigma": ["0", "01", "22"],
             "regime": "nonunimodular", "status": "refused", "reason": "needs |det M| = 1"}]


def jsonl(records):
    return "".join(json.dumps(r) + "\n" for r in records).encode()


@pytest.fixture
def estate(tmp_path):
    def make(named_records=None, corpus_records=None, sums=None):
        files = {NAMED_PATH: jsonl(named_records if named_records is not None else [named(), refused()]),
                 CORPUS_PATH: jsonl(corpus_records if corpus_records is not None else corpus())}
        files[SUMS_PATH] = sums if sums is not None else "".join(
            f"{hashlib.sha256(raw).hexdigest()}  {path.rsplit('/', 1)[-1]}\n" for path, raw in files.items()).encode()
        for repo, path in PAGE.files():
            target = tmp_path / "estate" / repo.split("/")[-1] / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(files[path])
        return tmp_path / "estate"
    return make


def test_records_are_transcribed_not_recomputed():
    data = transcribe([named(), refused()], corpus())
    s, = data["specimens"]
    assert s["contacts"] == CONTACTS and s["verdict"]["neighbours"] == [[1, 0], [-1, 0]]
    # The page's drawing loops run over `points`; without it every canvas is empty.
    assert s["points"] == 3 and s["x"] == [0, 1, 2] and s["letter"] == [0, 1, 2]
    assert s["verdict"]["productive"] is True and s["verdict"]["consequence"] == CONSEQUENCE
    assert data["controls"] == [{"name": "nonunit_control", "sigma": "011/20/0", "reason": "needs |det M| = 1"}]
    assert data["corpus"] == {"rows": [[0, "0/01/2", "unimodular-real", True, 4, 2, 8]], "refused": 1,
                              "refusedRegimes": {"nonunimodular": 1}}


def test_the_page_carries_data_stamps_and_caveat(estate, tmp_path):
    out = tmp_path / "out" / "page.html"
    outcome = build(PAGE, estate(), out=out)
    assert isinstance(outcome, Rendered)
    html = out.read_text(encoding="utf-8")
    assert "__DATA__" not in html and "__SOURCES__" not in html and CAVEAT in html
    for path in (NAMED_PATH, CORPUS_PATH, SUMS_PATH):
        assert f"{PAGE.repo}/{path} @ sha256:" in html
    assert CONSEQUENCE in html


ASYMMETRIC = [c for c in CONTACTS if c[:2] != [1, 0]]


@pytest.mark.parametrize("named_records, corpus_records, sums, reason", [
    ([named(schema="psc-rauzy-torus/v1")], None, None, "expected 'psc-rauzy-contacts/v1'"),
    ([named(status="diagnostic")], None, None, "status 'diagnostic'"),
    ([refused()], None, None, "no exact specimen"),
    ([named(contact_list=ASYMMETRIC, contacts=3)], None, None, "not closed under reversal"),
    ([named(contacts=5)], None, None, "disagrees with contacts"),
    ([named(lattice_neighbours=[[1, 0]])], None, None, "not closed under negation"),
    ([named(lattice_neighbours=[[0, 1], [0, -1]])], None, None, "disagree with contact_list"),
    ([named(contact_list=[c[:6] for c in CONTACTS])], None, None, "not [top, bottom"),
    ([named(x=[0, 1])], None, None, "disagree with points"),
    ([{k: v for k, v in named().items() if k != "consequence"}], None, None, "lacks consequence"),
    (None, corpus() + corpus()[:1], None, "gives index 0 twice"),
    (None, None, b"0" * 64 + b"  contacts-named.jsonl\n", "disagrees with the bundle's SHA256SUMS"),
])
def test_a_bundle_of_another_shape_is_refused_and_nothing_is_written(
        estate, tmp_path, named_records, corpus_records, sums, reason):
    out = tmp_path / "out" / "page.html"
    outcome = build(PAGE, estate(named_records, corpus_records, sums), out=out)
    assert isinstance(outcome, Refused) and reason in outcome.reason, outcome
    assert not out.exists()


def test_a_dataset_is_refused(estate, tmp_path):
    outcome = build(PAGE, estate(), dataset=tmp_path / "x.json", out=tmp_path / "p.html")
    assert isinstance(outcome, Refused) and "drop --dataset" in outcome.reason


def test_transcribe_refuses_a_named_file_with_nothing_to_draw():
    with pytest.raises(SourceError):
        transcribe([refused()], corpus())
