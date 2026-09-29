"""The wake page: exact rows are the upstream module's, the page embeds them,
and every way of not having that module is a refusal.

The module is upstream's and is not copied here, so these tests hand `build` a
stand-in with the same three names; the real one, and the committed still, are
held to each other in `test_estate.py`.
"""

import json

import pytest

from vizops.__main__ import main
from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered
from vizops.sources import SourceError, pages
from vizops.wake import QMAX, STILL, TEMPLATE, build, still_claims

PAGE = next(p for p in pages() if p.id == "wake-to-mandelbrot")
#: A faithful stand-in: the same construction, so the rows it yields are right.
STUB = '''
from fractions import Fraction


def mechanical(p, q, r):
    return int("".join("1" if (r + k * p) % q >= q - p else "0" for k in range(q)), 2)


def rotation_cycle(p, q):
    x, out = Fraction(mechanical(p, q, 0), 2 ** q - 1), []
    for _ in range(q):
        out.append(x)
        x = 2 * x % 1
    return tuple(sorted(out))


def wake(p, q):
    c = rotation_cycle(p, q)
    return min(zip(c, c[1:]), key=lambda pair: pair[1] - pair[0])
'''


def estate(tmp_path, source=STUB):
    path = tmp_path / "estate" / PAGE.checkout / PAGE.path
    path.parent.mkdir(parents=True)
    path.write_text(source, encoding="utf-8")
    return tmp_path / "estate"


def embedded(html: str) -> list[dict]:
    return json.loads(html.split("var DATA=", 1)[1].split(";\n", 1)[0])


def test_the_template_takes_each_placeholder_once_and_computes_no_angle():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert all(text.count(mark) == 1 for mark in ("__DATA__", "__STAMP__", "__QMAX__"))
    assert "mechanical" not in text and "cycleNums" not in text  # the page looks up; it does not derive


def test_the_page_embeds_every_reduced_angle_with_its_stamp(tmp_path):
    out = tmp_path / "out" / "wake.html"
    assert isinstance(build(PAGE, estate(tmp_path), out=out), Rendered)
    html = out.read_text(encoding="utf-8")
    assert CAVEAT in html and f"{PAGE.repo}/{PAGE.path} @ sha256:" in html
    assert f'max="{QMAX}"' in html
    rows = embedded(html)
    assert {(r["p"], r["q"]) for r in rows} == {(p, q) for q in range(2, QMAX + 1) for p in range(1, q)
                                                if all(p % d or q % d for d in range(2, q + 1))}
    (row,) = [r for r in rows if (r["p"], r["q"]) == (3, 7)]
    assert row == {"p": 3, "q": 7, "den": 127, "word": 21,
                   "cycle": [21, 37, 41, 42, 74, 82, 84], "lo": 41, "hi": 42}


def test_a_missing_checkout_is_refused(tmp_path):
    assert isinstance(build(PAGE, tmp_path / "nothing"), Refused)


def test_a_checkout_without_the_module_is_refused(tmp_path):
    (tmp_path / PAGE.checkout).mkdir()
    outcome = build(PAGE, tmp_path)
    assert isinstance(outcome, Refused) and PAGE.path in outcome.reason


def test_a_module_that_no_longer_answers_is_refused_and_nothing_is_written(tmp_path):
    out = tmp_path / "wake.html"
    outcome = build(PAGE, estate(tmp_path, "def wake(p, q):\n    raise ValueError('renamed')\n"), out=out)
    assert isinstance(outcome, Refused) and "no longer answers" in outcome.reason
    assert not out.exists()


def test_a_dataset_is_refused_rather_than_ignored(tmp_path):
    outcome = build(PAGE, estate(tmp_path), dataset=tmp_path / "dataset.json")
    assert isinstance(outcome, Refused) and "--dataset" in outcome.reason


def test_the_committed_still_prints_the_3_7_pair():
    assert still_claims(STILL.read_text(encoding="utf-8")) == {
        "cycle": [21, 37, 41, 42, 74, 82, 84], "lo": 41, "hi": 42, "den": 127}


def test_a_still_that_prints_no_pair_is_refused():
    with pytest.raises(SourceError, match="no angular order"):
        still_claims("<svg><text>3/7</text></svg>")


def test_the_cli_builds_one_page_by_id(tmp_path, capsys):
    assert main(["page", PAGE.id, "--sources", str(estate(tmp_path)), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / f"{PAGE.id}.html").is_file()
    assert main(["page", "no-such-page"]) == 1
    assert "no such page" in capsys.readouterr().err
