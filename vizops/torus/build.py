"""The Rauzy torus page: PSC's exact fractal records, transcribed onto T².

    python -m vizops page psc-rauzy-torus

pisot-substitution-conjecture-research's kernel `psc/rauzy_torus.mojo` emits two
`psc-rauzy-torus/v1` JSONL files: named substitutions, each with its fractal points
in the coordinates of `H = {Σx = 0}` and a lift profile on a grid over `T² = H/H_Z`,
and one summary line per corpus specimen. Transcription is the whole job. An
integer coordinate over `2^coord_bits` becomes a float, a frequency floor over
`2^40` becomes a float, and the lift histogram is copied as it is. The page folds
points mod 1 and wraps them onto a torus surface, and that is drawing, not
derivation. Nothing here recomputes a frequency, a point or a lift count, and the
diagnostic status is shown as the file states it.

A file that is missing, not JSONL, of another schema, or whose records no longer
have the fields and lengths this page reads is a refusal, and nothing is written.
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
SCALE = 2 ** 40
STATUSES = {"diagnostic", "refused"}


def read(root: Path, page: Page, repo: str, path: str) -> tuple[list[dict], Provenance]:
    """One JSONL file as its records, each of the declared schema and a known status."""
    raw, digest = read_artifact(page.id, repo, path, Path(root) / repo.split("/")[-1])
    try:
        records = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    except (UnicodeDecodeError, ValueError) as err:
        raise SourceError(f"{repo}/{path} is not JSONL: {err}") from None
    for n, record in enumerate(records, 1):
        if not isinstance(record, dict) or record.get("schema") != SCHEMA:
            raise SourceError(f"{repo}/{path} line {n} does not declare schema {SCHEMA!r}")
        if record.get("status") not in STATUSES:
            raise SourceError(f"{repo}/{path} line {n} has status {record.get('status')!r}")
    return records, Provenance(repo, path, digest)


def _named(r: dict) -> dict[str, Any]:
    head = {"name": r["name"], "sigma": r["sigma"], "regime": r["regime"], "status": r["status"]}
    if r["status"] == "refused":
        return {**head, "reason": r["reason"]}
    n, grid = r["points"], r["grid"]
    if not (len(r["x"]) == len(r["y"]) == len(r["letter"]) == n) or len(r["lifts"]) != grid * grid:
        raise SourceError(f"named record {r['name']!r}: point or lift arrays disagree with points/grid")
    return {**head, "points": n, "grid": grid, "bits": r["coord_bits"], "x": r["x"], "y": r["y"],
            "letter": r["letter"], "lifts": r["lifts"], "undecided": r["undecided"],
            "hist": dict(zip(r["lift_keys"], r["lift_counts"], strict=True)),
            "freq": [f / SCALE for f in r["freq_floor"]], "sup": r["sup_bound"] / SCALE}


def _corpus(r: dict) -> list[Any]:
    """`[index, sigma, regime, f0, f1, one-lift cells, occupied, max lift]`."""
    if r["status"] == "refused":
        return [r["index"], " ".join(r["sigma"]), r["regime"]]
    hist = dict(zip(r["lift_keys"], r["lift_counts"], strict=True))
    f = r["freq_floor"]
    return [r["index"], " ".join(r["sigma"]), r["regime"], round(f[0] / SCALE, 6), round(f[1] / SCALE, 6),
            hist.get(1, 0), r["occupied"], max(hist, default=0)]


def transcribe(named: list[dict], corpus: list[dict]) -> dict[str, Any]:
    """The page's data, field for field from the two files."""
    if not any(r["status"] == "diagnostic" for r in named):
        raise SourceError("the named file has no diagnostic record to draw")
    rows = [_corpus(r) for r in corpus]
    return {"named": [_named(r) for r in named], "corpus": rows,
            "corpusGrid": corpus[0]["grid"] if corpus and "grid" in corpus[0] else None,
            "corpusPoints": next((r["points"] for r in corpus if "points" in r), None)}


def build(page: Page, sources: Path, *, dataset: Path | None = None,
          out: Path = Path("psc-rauzy-torus.html")) -> Outcome:
    """Read both files, transcribe, and write the page -- or say why not."""
    if dataset is not None:
        return Refused(page.id, "this page reads committed files, not a dataset; drop --dataset")
    try:
        loaded = [read(sources, page, repo, path) for repo, path in page.files()]
        (named, _), (corpus, _) = loaded
        data = transcribe(named, corpus)
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    except (KeyError, TypeError, ValueError) as err:
        return Refused(page.id, f"a source no longer reads as this page reads it: {err!r}")
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__SOURCES__", "".join(f"<li><code>{escape(p.stamp)}</code></li>" for _, p in loaded))
            .replace("__CAVEAT__", escape(CAVEAT))
            .replace("__DATA__", json.dumps(data, separators=(",", ":"))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return Rendered(page.id, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
