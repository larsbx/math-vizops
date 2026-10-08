"""The PSC Rauzy representability page: the upstream HTML copied byte for byte
with one stamp added, and every way of not having that page refused.

The fixture is a minimal page in the upstream shape; the real file is read in
`test_estate.py`.
"""

import hashlib

import pytest

from vizops.__main__ import main
from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.rauzy import MARKERS, build
from vizops.sources import pages

PAGE = next(p for p in pages() if p.id == "psc-rauzy-representability")
GOOD = ('<!doctype html>\n<html><head><title>PSC Rauzy Coverage</title></head><body>'
        '<tbody id="rows"></tbody><figure data-fig="embed"><canvas></canvas></figure>'
        '</body></html>\n')


@pytest.fixture
def estate(tmp_path):
    def make(content=GOOD):
        target = tmp_path / "estate" / PAGE.checkout / PAGE.path
        target.parent.mkdir(parents=True, exist_ok=True)
        if content is not None:
            target.write_bytes(content.encode() if isinstance(content, str) else content)
        return tmp_path / "estate"
    return make


def test_the_page_is_copied_unchanged_apart_from_the_stamp(estate, tmp_path):
    out = tmp_path / "out" / "page.html"
    outcome = build(PAGE, estate(), out=out)
    assert isinstance(outcome, Rendered)
    html = out.read_text(encoding="utf-8")
    head, rest = html.split("<aside data-vizops-stamp", 1)
    stamp, tail = rest.split("</aside>\n", 1)
    assert head + tail == GOOD
    digest = hashlib.sha256(GOOD.encode()).hexdigest()
    assert f"{PAGE.repo}/{PAGE.path} @ sha256:{digest[:12]}" in stamp
    assert CAVEAT in stamp
    assert outcome.digest == hashlib.sha256(out.read_bytes()).hexdigest()


@pytest.mark.parametrize("content, reason", [
    (None, "no artifact"),
    (b"", "is empty"),
    (b"\xff\xfe not text", "not UTF-8"),
    (GOOD.replace("<!doctype html>", ""), "not an HTML document"),
    (GOOD.replace('id="rows"', ""), "no claim table"),
    (GOOD.replace("data-fig=", "data-x="), "no figure gallery"),
])
def test_a_page_of_another_shape_is_refused_and_nothing_is_written(estate, tmp_path, content, reason):
    out = tmp_path / "out" / "page.html"
    outcome = build(PAGE, estate(content), out=out)
    assert isinstance(outcome, Refused) and reason in outcome.reason
    assert not out.exists()


def test_a_dataset_is_refused(estate, tmp_path):
    outcome = build(PAGE, estate(), dataset=tmp_path / "d.json", out=tmp_path / "page.html")
    assert isinstance(outcome, Refused) and "dataset" in outcome.reason


def test_every_marker_names_a_reason():
    assert all(MARKERS.values())


def test_the_cli_builds_it(estate, tmp_path):
    assert main(["page", "psc-rauzy-representability", "--sources", str(estate()), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "psc-rauzy-representability.html").is_file()
