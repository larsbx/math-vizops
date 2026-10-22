"""The Rauzy contacts page: PSC's exact tile contacts and box verdicts, transcribed.

    python -m vizops page psc-rauzy-contacts

pisot-substitution-conjecture-research's `evidence/rauzy-contacts-2026-10-22/`
feeds it, three files named in `sources.toml`:

* `contacts-named.jsonl` -- per named substitution, the box automaton's verdict,
  every exact contact `R(top) + P(w) ∩ R(bottom) ≠ ∅` as `[top, bottom, w0, w1,
  w2, x, y]` (x, y floored over 2^coord_bits), the lattice neighbours,
  and the fractal points the contacts are drawn against;
* `contacts-corpus.jsonl` -- the verdict, the contact counts and the lattice
  neighbours of every standing specimen;
* `SHA256SUMS` -- the bundle's digests; bytes it does not vouch for are refused.

Transcription is the whole job. The verdict and the `consequence` string are
copied as written. Covering degree 1 is upstream's cited consequence of a
productive box, so the page quotes it and never states it as its own. Drawing a
subtile translated by a contact's `(x, y)` is display arithmetic.

A file that is missing, of another schema or status, inconsistent with itself,
or not the bytes its SHA256SUMS names is a refusal, and nothing is written.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

from .. import palette
from ..figure import CAVEAT
from ..outcome import Outcome, Refused, Rendered
from ..sources import Page, SourceError
from ..torus.build import ALPHABET, read, records, vouched

TEMPLATE = Path(__file__).resolve().parent / "templates" / "page.html"
SCHEMA = "psc-rauzy-contacts/v1"
STATUSES = ("exact", "refused")
VERDICT = ("box_productive", "box_states", "box_recurrent", "box_coincidence_depth", "contacts",
           "lattice_contacts", "lattice_neighbours", "consequence")
NAMED = ("name", "sigma", "regime", "coord_bits", "freq_floor", "contact_list", "points", "x", "y", "letter",
         *VERDICT)
SUMMARY = ("index", "sigma", "regime", "freq_floor", *VERDICT)


def _lacks(record: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [f for f in fields if f not in record]
    if missing:
        raise SourceError(f"{label}: lacks {', '.join(missing)}")


def _neighbours(r: dict, label: str) -> list[list[int]]:
    """The lattice neighbours, checked against the contact counts they summarise."""
    nb = r["lattice_neighbours"]
    if any(len(v) != 2 for v in nb) or len({tuple(v) for v in nb}) != len(nb):
        raise SourceError(f"{label}: lattice_neighbours are not distinct pairs")
    if {tuple(v) for v in nb} != {(-a, -b) for a, b in nb}:
        raise SourceError(f"{label}: lattice_neighbours are not closed under negation")
    if not 0 <= r["lattice_contacts"] <= r["contacts"]:
        raise SourceError(f"{label}: lattice contacts exceed the contacts")
    return nb


def _verdict(r: dict, label: str) -> dict[str, Any]:
    return {"productive": r["box_productive"], "states": r["box_states"], "recurrent": r["box_recurrent"],
            "depth": r["box_coincidence_depth"], "contacts": r["contacts"],
            "lattice": r["lattice_contacts"], "neighbours": _neighbours(r, label),
            "consequence": r["consequence"]}


def _specimen(r: dict) -> dict[str, Any]:
    label = f"named {r.get('name')!r}"
    _lacks(r, NAMED, label)
    if not len(r["x"]) == len(r["y"]) == len(r["letter"]) == r["points"]:
        raise SourceError(f"{label}: x/y/letter entries disagree with points")
    if not set(r["letter"]) <= set(ALPHABET):
        raise SourceError(f"{label}: a letter outside the alphabet {set(ALPHABET)}")
    rows = r["contact_list"]
    if any(len(c) != 7 or c[0] not in ALPHABET or c[1] not in ALPHABET for c in rows):
        raise SourceError(f"{label}: a contact that is not [top, bottom, w0, w1, w2, x, y]")
    keys = {tuple(c[:5]) for c in rows}
    # The summary fields and the list describe the same contacts; the page shows both.
    if len(keys) != len(rows) or len(rows) != r["contacts"]:
        raise SourceError(f"{label}: contact_list disagrees with contacts")
    if keys != {(j, i, -a, -b, -c) for i, j, a, b, c in keys}:
        raise SourceError(f"{label}: contact_list is not closed under reversal")
    lattice = {(c[2], c[3]) for c in rows if c[2] + c[3] + c[4] == 0 and (c[2], c[3]) != (0, 0)}
    verdict = _verdict(r, label)
    if lattice != {tuple(v) for v in verdict["neighbours"]}:
        raise SourceError(f"{label}: lattice_neighbours disagree with contact_list")
    return {"name": r["name"], "sigma": "/".join(r["sigma"]), "regime": r["regime"], "bits": r["coord_bits"],
            "verdict": verdict, "contacts": rows, "points": r["points"], "x": r["x"], "y": r["y"],
            "letter": r["letter"]}


def _summary(r: dict) -> dict[str, Any]:
    label = f"corpus index {r.get('index')!r}"
    _lacks(r, SUMMARY, label)
    v = _verdict(r, label)
    return {"index": r["index"], "sigma": "/".join(r["sigma"]), "regime": r["regime"], "productive": v["productive"],
            "contacts": v["contacts"], "neighbours": len(v["neighbours"]), "depth": v["depth"]}


def transcribe(named: list[dict], corpus: list[dict]) -> dict[str, Any]:
    """The page's data, field for field from the two record files."""
    twice = sorted(i for i, n in Counter(r.get("index") for r in corpus).items() if n > 1)
    if twice:
        raise SourceError(f"contacts-corpus.jsonl gives index {twice[0]} twice")
    specimens = [_specimen(r) for r in named if r["status"] == "exact"]
    if not specimens:
        raise SourceError("contacts-named.jsonl holds no exact specimen, so there is nothing to draw")
    rows = [_summary(r) for r in corpus if r["status"] == "exact"]
    refused = [r for r in corpus if r["status"] == "refused"]
    return {
        "specimens": specimens,
        "controls": [{"name": r["name"], "sigma": "/".join(r["sigma"]), "reason": r["reason"]}
                     for r in named if r["status"] == "refused"],
        "corpus": {"rows": rows, "refused": len(refused),
                   "refusedRegimes": dict(sorted(Counter(r["regime"] for r in refused).items()))},
    }


def build(page: Page, sources: Path, *, dataset: Path | None = None,
          out: Path = Path("psc-rauzy-contacts.html")) -> Outcome:
    """Read the bundle, check it vouches for itself, transcribe, and write the page -- or say why not."""
    if dataset is not None:
        return Refused(page.id, "this page reads a committed bundle, not a dataset; drop --dataset")
    try:
        loaded = read(sources, page)
        (named, named_at), (corpus, corpus_at), (sums, _) = loaded
        vouched(sums, ((named_at.path, named), (corpus_at.path, corpus)))
        data = transcribe(records(named, named_at.path, SCHEMA, STATUSES),
                          records(corpus, corpus_at.path, SCHEMA, STATUSES))
        hues = {"letters": list(palette.assign(tuple(map(str, ALPHABET))).values())}
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
