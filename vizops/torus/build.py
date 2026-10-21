"""The Rauzy torus page: an exact evidence bundle transcribed, never recomputed.

    python -m vizops page psc-rauzy-torus

pisot-substitution-conjecture-research's `evidence/rauzy-torus-2026-10-21/`
feeds it, three files named in `sources.toml`:

* `named.jsonl` -- per named substitution, the fixed-point prefix projected to
  `H = {sum x = 0}` as floored integer coordinates, each point's subtile letter,
  the certified frequency floors and the lift profile on a G x G grid of T^2;
* `corpus.jsonl` -- the same summary, without points, for every standing
  specimen;
* `SHA256SUMS` -- the bundle's own digests. Bytes it does not vouch for are
  refused, so the page draws what upstream's oracle replayed.

Transcription is the whole job. A record's status is copied as written, and a
status other than `diagnostic` or `refused` is not this page's to show. Folding
a point onto the torus, embedding the torus in space and placing a specimen in
the frequency triangle are the page's own display arithmetic and it says so;
the lift counts it colours by are the bundle's, cell for cell.

A file that is missing, of another schema, inconsistent with itself, or not the
bytes its SHA256SUMS names is a refusal, and nothing is written.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any, Iterable

from .. import palette
from ..figure import CAVEAT, Provenance
from ..outcome import Outcome, Refused, Rendered
from ..sources import Page, SourceError, read_artifact

TEMPLATE = Path(__file__).resolve().parent / "templates" / "page.html"
SCHEMA = "psc-rauzy-torus/v1"
#: The statuses the bundle may carry; anything else is a bundle this page was not registered for.
STATUSES = ("diagnostic", "refused")
ALPHABET = (0, 1, 2)
NAMED = ("name", "sigma", "regime", "freq_floor", "points", "sup_bound", "coord_bits", "grid",
         "undecided", "occupied", "lift_keys", "lift_counts", "x", "y", "letter", "lifts")
SUMMARY = ("index", "sigma", "regime", "freq_floor", "points", "grid", "lift_keys", "lift_counts")
DIGEST_LINE = re.compile(r"([0-9a-f]{64}) [ *](\S+)")


def records(raw: bytes, where: str) -> list[dict[str, Any]]:
    """Every line of a JSONL file, each of this schema and a known status."""
    out = []
    for n, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as err:
            raise SourceError(f"{where} line {n} is not JSON: {err}") from None
        if not isinstance(record, dict) or record.get("schema") != SCHEMA:
            declared = record.get("schema") if isinstance(record, dict) else None
            raise SourceError(f"{where} line {n}: schema {declared!r}, expected {SCHEMA!r}")
        if record.get("status") not in STATUSES:
            raise SourceError(f"{where} line {n}: status {record.get('status')!r}; this page draws a "
                              f"bundle whose records are {' or '.join(STATUSES)}, and nothing else")
        out.append(record)
    return out


def vouched(sums: bytes, files: Iterable[tuple[str, bytes]]) -> None:
    """Refuse any file whose bytes the bundle's SHA256SUMS does not name."""
    listed = {}
    for line in sums.decode("utf-8").splitlines():
        match = DIGEST_LINE.fullmatch(line.strip())
        if not match:
            raise SourceError(f"not a SHA256SUMS line: {line!r}")
        listed[match[2]] = match[1]
    for path, raw in files:
        name = path.rsplit("/", 1)[-1]
        if name not in listed:
            raise SourceError(f"{name} is not listed in the bundle's SHA256SUMS")
        if listed[name] != hashlib.sha256(raw).hexdigest():
            raise SourceError(f"{name} disagrees with the bundle's SHA256SUMS")


def _lacks(record: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [f for f in fields if f not in record]
    if missing:
        raise SourceError(f"{label}: lacks {', '.join(missing)}")


def _floors(record: dict, label: str) -> list[int]:
    if len(record["freq_floor"]) != len(ALPHABET):
        raise SourceError(f"{label}: {len(record['freq_floor'])} frequency floors, not {len(ALPHABET)} frequency floors")
    return record["freq_floor"]


def _profile(record: dict, label: str) -> list[list[int]]:
    keys, counts = record["lift_keys"], record["lift_counts"]
    if len(keys) != len(counts):
        raise SourceError(f"{label}: lift_keys and lift_counts differ in length")
    return [[k, c] for k, c in zip(keys, counts)]


def _specimen(r: dict) -> dict[str, Any]:
    label = f"named {r.get('name')!r}"
    _lacks(r, NAMED, label)
    points, grid, bits = r["points"], r["grid"], r["coord_bits"]
    if not len(r["x"]) == len(r["y"]) == len(r["letter"]) == points:
        raise SourceError(f"{label}: {len(r['x'])}/{len(r['y'])}/{len(r['letter'])} x/y/letter entries "
                          f"for {points} points")
    if not set(r["letter"]) <= set(ALPHABET):
        raise SourceError(f"{label}: a letter outside the alphabet {set(ALPHABET)}")
    if len(r["lifts"]) != grid * grid:
        raise SourceError(f"{label}: {len(r['lifts'])} lift counts for a {grid} x {grid} grid")
    if (1 << bits) % grid:
        raise SourceError(f"{label}: grid {grid} does not divide 2^{bits}, so a folded point has no cell")
    return {"name": r["name"], "sigma": "/".join(r["sigma"]), "regime": r["regime"], "status": r["status"],
            "freq_floor": _floors(r, label), "points": points, "sup_bound": r["sup_bound"], "coord_bits": bits,
            "grid": grid, "undecided": r["undecided"], "occupied": r["occupied"],
            "profile": _profile(r, label), "x": r["x"], "y": r["y"], "letter": r["letter"], "lifts": r["lifts"]}


def _summary(r: dict) -> list[Any]:
    label = f"corpus index {r.get('index')!r}"
    _lacks(r, SUMMARY, label)
    return [r["index"], "/".join(r["sigma"]), r["regime"], *_floors(r, label), _profile(r, label)]


def _tally(refused: list[dict]) -> dict[str, Any]:
    return {"count": len(refused), "regimes": dict(sorted(Counter(r["regime"] for r in refused).items())),
            "reasons": sorted({r["reason"] for r in refused})}


def transcribe(named: list[dict], corpus: list[dict]) -> dict[str, Any]:
    """The page's data, field for field from the two record files."""
    indices = Counter(r.get("index") for r in corpus)
    twice = sorted(i for i, n in indices.items() if n > 1)
    if twice:
        raise SourceError(f"corpus.jsonl gives index {twice[0]} twice")
    scale = {r["scale_bits"] for r in (*named, *corpus) if r["status"] == "diagnostic"}
    if len(scale) > 1:
        raise SourceError(f"records disagree about scale_bits: {sorted(scale)}")
    rows = [_summary(r) for r in corpus if r["status"] == "diagnostic"]
    return {
        "scale_bits": scale.pop() if scale else None,
        "specimens": [_specimen(r) for r in named if r["status"] == "diagnostic"],
        "controls": [{"name": r["name"], "sigma": "/".join(r["sigma"]), "regime": r["regime"], "reason": r["reason"]}
                     for r in named if r["status"] == "refused"],
        "corpus": {"rows": rows, "regimes": sorted({row[2] for row in rows}),
                   "refused": _tally([r for r in corpus if r["status"] == "refused"])},
    }


def read(root: Path, page: Page) -> list[tuple[bytes, Provenance]]:
    """Each file the page reads, as bytes with the provenance of those bytes."""
    out = []
    for repo, path in page.files():
        raw, digest = read_artifact(page.id, repo, path, Path(root) / repo.split("/")[-1])
        out.append((raw, Provenance(repo, path, digest)))
    return out


def build(page: Page, sources: Path, *, dataset: Path | None = None,
          out: Path = Path("psc-rauzy-torus.html")) -> Outcome:
    """Read the bundle, check it vouches for itself, transcribe, and write the page -- or say why not."""
    if dataset is not None:
        return Refused(page.id, "this page reads a committed bundle, not a dataset; drop --dataset")
    try:
        loaded = read(sources, page)
        (named, named_at), (corpus, corpus_at), (sums, _) = loaded
        vouched(sums, ((named_at.path, named), (corpus_at.path, corpus)))
        data = transcribe(records(named, named_at.path), records(corpus, corpus_at.path))
        hues = {"letters": list(palette.assign(tuple(map(str, ALPHABET))).values()),
                "regimes": dict(palette.assign(tuple(data["corpus"]["regimes"])))}
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    except (KeyError, TypeError, ValueError) as err:
        return Refused(page.id, f"the bundle no longer reads as this page reads it: {err!r}")
    stamps = [provenance.stamp for _, provenance in loaded]
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__SOURCES__", "".join(f"<li><code>{escape(s)}</code></li>" for s in stamps))
            .replace("__CAVEAT__", escape(CAVEAT))
            .replace("__DATA__", json.dumps({**data, "hues": hues}, separators=(",", ":"))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return Rendered(page.id, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
