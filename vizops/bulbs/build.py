"""The Bulbs & Ford Circles page: certificates transcribed, never reissued.

    python -m vizops page bulbs-and-ford-circles

Four committed files feed it, all named in `sources.toml`:

* the centre and antipode certificates of every satellite bulb with q <= 16 --
  exact dyadic boxes over 2^prec, their verdicts, and the exact G bracket;
* the q = 1009 sweep of G against the modular inverse, floating point upstream;
* finite-math-kernels' cyclotomic germ vectors, the exact index iota in Q(zeta_q).

Transcription is the whole job: a box is drawn at its midpoint, a G bracket is
printed to 15 decimals rounded outward, a verdict is copied as written. Nothing
here re-runs a Krawczyk test or decides a verdict, so a certificate that says
INCONCLUSIVE is shown saying so. Scene 5's moving boxes are the page's own
floating-point illustration and it says as much on the page.

A file that is missing, of another schema, or that disagrees with its partner
about which bulbs exist is a refusal, and nothing is written.
"""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from html import escape
from pathlib import Path
from typing import Any

from ..figure import CAVEAT, Provenance
from ..outcome import Outcome, Refused, Rendered
from ..sources import Page, SourceError

TEMPLATE = Path(__file__).resolve().parent / "templates" / "page.html"
#: The schema each file declares, by path. The sweep is a bare list and declares none.
SCHEMAS = {
    "experiments/data/center_certificates.json": "bulbford-center-certificates/v1",
    "experiments/data/antipode_certificates.json": "bulbford-antipode-certificates/v1",
    "conformance/cyclotomic_germ_v1.json": "cyclotomic-germ/v1",
}


def _midpoint(numerators: list[str], prec: int) -> list[float]:
    re_lo, re_hi, im_lo, im_hi = (int(n) for n in numerators)
    return [float(Fraction(re_lo + re_hi, 2 ** (prec + 1))), float(Fraction(im_lo + im_hi, 2 ** (prec + 1)))]


def _decimal(x: Fraction, up: bool, places: int = 15) -> str:
    """`x` to `places` decimals, rounded away from the bracket's inside."""
    scaled = (math.ceil if up else math.floor)(x * 10 ** places)
    whole, frac = divmod(scaled, 10 ** places)
    return f"{whole}.{frac:0{places}d}"


def transcribe(centres: dict, antipodes: dict, sweep: list, germ: dict) -> dict[str, Any]:
    """The page's data, field for field from the four files."""
    cen = {(c["p"], c["q"]): c for c in centres["certificates"]}
    ant = {(a["p"], a["q"]): a for a in antipodes["certificates"]}
    if set(cen) != set(ant):
        lonely = sorted(set(cen) ^ set(ant), key=lambda k: (k[1], k[0]))
        raise SourceError("centre and antipode certificates disagree about which bulbs exist: "
                          + ", ".join(f"{p}/{q}" for p, q in lonely[:6]))

    def bulb(p: int, q: int) -> dict[str, Any]:
        c, a = cen[p, q], ant[p, q]
        lo, hi = (Fraction(x) for x in a["G_ant_bounds"])
        return {"p": p, "q": q, "cen": _midpoint(c["box_numerators"], c["prec"]),
                "ant": _midpoint(a["c_box_numerators"], a["prec"]),
                "Glo": _decimal(lo, up=False), "Ghi": _decimal(hi, up=True), "Gw": float(hi - lo),
                "verdictC": c["verdict"], "verdictA": a["verdict"]}

    return {
        "bulbs": [bulb(p, q) for p, q in sorted(cen, key=lambda k: (k[1], k[0]))],
        "iota": {f"{v['p']}/{v['q']}": v["reciprocal_coefficient"] for v in germ["vectors"]},
        "dense": [[r["p"], round(r["xt"], 6), round(r["G"], 6), round(r["kappa"][0], 5), round(r["kappa"][1], 5)]
                  for r in sweep],
    }


def read(root: Path, repo: str, path: str) -> tuple[Any, Provenance]:
    source = Path(root) / repo.split("/")[-1] / path
    if not source.is_file():
        raise SourceError(f"no {path} in a checkout of {repo} at {source.parent}")
    raw = source.read_bytes()
    try:
        data = json.loads(raw)
    except ValueError as err:
        raise SourceError(f"{repo}/{path} is not JSON: {err}") from None
    declared = data.get("schema") if isinstance(data, dict) else None
    if path in SCHEMAS and declared != SCHEMAS[path]:
        raise SourceError(f"{repo}/{path} declares schema {declared!r}, expected {SCHEMAS[path]!r}")
    return data, Provenance(repo, path, hashlib.sha256(raw).hexdigest())


def build(page: Page, sources: Path, *, dataset: Path | None = None,
          out: Path = Path("bulbs-and-ford-circles.html")) -> Outcome:
    """Read the four files, transcribe, and write the page -- or say why not."""
    if dataset is not None:
        return Refused(page.id, "this page reads committed files, not a dataset; drop --dataset")
    try:
        loaded = [read(sources, repo, path) for repo, path in page.files()]
        (centres, _), (antipodes, _), (sweep, _), (germ, germ_at) = loaded
        data = transcribe(centres, antipodes, sweep, germ)
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    except (KeyError, TypeError, ValueError) as err:
        return Refused(page.id, f"a source no longer reads as this page reads it: {err!r}")
    stamps = [provenance.stamp for _, provenance in loaded]
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__SOURCES__", "".join(f"<li><code>{escape(s)}</code></li>" for s in stamps))
            .replace("__CAVEAT__", escape(CAVEAT))
            .replace("__DATA__", json.dumps({**data, "germ": germ_at.stamp}, separators=(",", ":"))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return Rendered(page.id, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
