"""The Rauzy torus page: the bundle's records transcribed, never recomputed.

    python -m vizops page psc-rauzy-torus

pisot-substitution-conjecture-research's `kernel/psc/rauzy_torus.mojo` emits,
per unimodular substitution, certified scaled frequencies, integer enclosures
of the discrepancy vectors `D_n = p_n - n f` and the lift profile of a grid on
`T^2 = H / H_Z`; its independent oracle replays every record. Two files of one
dated bundle feed the page: the named specimens, with their points, and the
corpus summaries. Transcription is the whole job: every field the page shows is
copied as written, and a record is checked only against what the bundle says
about itself -- its schema, its lengths, and a lift histogram that agrees with
its own cells and occupancy.

What the page does with the numbers is display, and it says so: coordinates
are scaled by `2^-coord_bits`, folded mod `Z^2`, laid on a torus surface, and
the rotation `-(f_0, f_1) mod Z^2` is drawn from the certified floors. None of
that is a claim, and a lift profile certifies no covering degree upstream
either.

A file that is missing, empty, not JSON lines, of another schema, or whose
records disagree with themselves is a refusal, and nothing is written.
"""

from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path
from typing import Any

from ..figure import CAVEAT, Provenance
from ..outcome import Outcome, Refused, Rendered
from ..sources import Page, SourceError, read_artifact

TEMPLATE = Path(__file__).resolve().parent / "templates" / "page.html"
SCHEMA = "psc-rauzy-torus/v1"
LETTERS = frozenset("012")
#: The fields a diagnostic profile carries upstream, copied as they are.
PROFILE = ("regime", "freq_floor", "scale_bits", "grid", "points", "undecided", "occupied", "lift_keys", "lift_counts")
#: The fields a named record adds: the sampled points and the per-cell lifts.
POINTS = ("coord_bits", "x", "y", "letter", "lifts")


def _int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _ints(record: dict, key: str, *, length: int | None = None, lo: int | None = None, hi: int | None = None) -> list[int]:
    value = record.get(key)
    if (not isinstance(value, list) or not all(map(_int, value))
            or (length is not None and len(value) != length)
            or (lo is not None and any(v < lo for v in value))
            or (hi is not None and any(v >= hi for v in value))):
        raise SourceError(f"{key} is not a list of {length if length is not None else 'any number of'} integers"
                          f"{f' >= {lo}' if lo is not None else ''}{f' < {hi}' if hi is not None else ''}")
    return value


def _count(record: dict, key: str, lo: int = 0) -> int:
    value = record.get(key)
    if not _int(value) or value < lo:
        raise SourceError(f"{key} is not an integer >= {lo}")
    return value


def _profile(record: dict, cells: list[int] | None) -> None:
    """The lift histogram agrees with the occupancy, the grid and, where given, the cells."""
    grid = _count(record, "grid", 1)
    keys = _ints(record, "lift_keys", lo=1)
    counts = _ints(record, "lift_counts", length=len(keys), lo=1)
    if any(a >= b for a, b in zip(keys, keys[1:])):
        raise SourceError("lift_keys are not strictly increasing")
    occupied = _count(record, "occupied")
    if occupied != sum(counts) or occupied > grid * grid:
        raise SourceError(f"occupied {occupied} disagrees with lift_counts summing to {sum(counts)} on a {grid}x{grid} grid")
    if cells is not None:
        seen = {k: cells.count(k) for k in sorted(set(cells) - {0})}
        if occupied != len(cells) - cells.count(0) or seen != dict(zip(keys, counts)):
            raise SourceError("lifts disagree with occupied, lift_keys and lift_counts")


def _record(record: object, kind: str) -> dict[str, Any]:
    """One record, checked against its own schema, as the page shows it."""
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise SourceError(f"schema is not {SCHEMA!r}")
    if record.get("kind") != kind:
        raise SourceError(f"kind is {record.get('kind')!r}, expected {kind!r}")
    sigma = record.get("sigma")
    if not (isinstance(sigma, list) and len(sigma) == 3
            and all(isinstance(w, str) and w and set(w) <= LETTERS for w in sigma)):
        raise SourceError(f"sigma {sigma!r} is not three nonempty words on 0, 1, 2")
    if not isinstance(record.get("regime"), str):
        raise SourceError("regime is not a string")
    if kind == "named" and not (isinstance(record.get("name"), str) and record["name"]):
        raise SourceError("a named record has no name")
    head = {"name": record.get("name")} if kind == "named" else {"index": record.get("index")}
    head |= {"sigma": sigma, "regime": record["regime"]}
    status = record.get("status")
    if status == "refused":
        if not isinstance(record.get("reason"), str) or not record["reason"]:
            raise SourceError("a refused record gives no reason")
        return {**head, "status": status, "reason": record["reason"]}
    if status != "diagnostic":
        raise SourceError(f"status {status!r} is neither 'diagnostic' nor 'refused'")
    scale = _count(record, "scale_bits", 1)
    _ints(record, "freq_floor", length=3, lo=0, hi=1 << scale)
    _count(record, "points", 1)
    _count(record, "undecided")
    cells = None
    if kind == "named":
        _count(record, "coord_bits", 1)
        for key in ("x", "y"):
            _ints(record, key, length=record["points"])
        _ints(record, "letter", length=record["points"], lo=0, hi=3)
        cells = _ints(record, "lifts", length=_count(record, "grid", 1) ** 2, lo=0)
    _profile(record, cells)
    return {**head, "status": status, **{k: record[k] for k in PROFILE + (POINTS if kind == "named" else ())}}


def _records(text: str, kind: str) -> list[dict[str, Any]]:
    records = []
    for number, line in enumerate(text.splitlines(), 1):
        try:
            records.append(_record(json.loads(line), kind))
        except (ValueError, SourceError) as err:
            raise SourceError(f"{kind} line {number}: {err}") from None
    return records


def transcribe(named_text: str, corpus_text: str) -> dict[str, Any]:
    """The page's data: the named records whole, the corpus split by status."""
    named = _records(named_text, "named")
    if not any(r["status"] == "diagnostic" for r in named):
        raise SourceError("no diagnostic named record to draw")
    corpus = _records(corpus_text, "corpus")
    for position, record in enumerate(corpus):
        if record["index"] != position:
            raise SourceError(f"corpus line {position + 1}: index {record['index']!r}, expected {position}")
    return {"named": named,
            "corpus": [{k: v for k, v in r.items() if k != "status"} for r in corpus if r["status"] == "diagnostic"],
            "refused": [{k: v for k, v in r.items() if k != "status"} for r in corpus if r["status"] == "refused"]}


def read(root: Path, page: Page) -> tuple[list[str], list[Provenance]]:
    """Both files as text, each with the provenance of its exact bytes."""
    texts, stamps = [], []
    for repo, path in page.files():
        raw, digest = read_artifact(page.id, repo, path, Path(root) / repo.split("/")[-1])
        try:
            texts.append(raw.decode("utf-8"))
        except UnicodeDecodeError as err:
            raise SourceError(f"{repo}/{path} is not UTF-8: {err}") from None
        stamps.append(Provenance(repo, path, digest))
    return texts, stamps


def build(page: Page, sources: Path, *, dataset: Path | None = None,
          out: Path = Path("psc-rauzy-torus.html")) -> Outcome:
    """Read the bundle, transcribe it, and write the page -- or say why not."""
    if dataset is not None:
        return Refused(page.id, "this page reads committed files, not a dataset; drop --dataset")
    try:
        texts, stamps = read(sources, page)
        data = transcribe(*texts)
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__SOURCES__", "".join(f"<li><code>{escape(s.stamp)}</code></li>" for s in stamps))
            .replace("__CAVEAT__", escape(CAVEAT))
            .replace("__DATA__", json.dumps(data, separators=(",", ":"))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return Rendered(page.id, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
