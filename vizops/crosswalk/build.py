"""The Mandelbrot Names Atlas page: the structure crosswalk, transcribed.

    python -m vizops page mandelbrot-names-atlas

One committed file feeds it: `docs/structure_crosswalk.json` in
finite-mandelbrot-research, format `structure crosswalk 1`. It joins the names
atlas (every named structure with its exact key) to the places across the
estate whose code or data hold the same datum, and carries the atlas's own
relations as edges. Upstream checks every datum against the atlas and every
anchor against its file; this page copies what the file says.

The file declares its own classes and relations, and a node or edge outside
that vocabulary is refused rather than drawn. So is a float anywhere: the
surface is exact by contract, and the only floating point on the page is the
display position of an exact angle on the circle.
"""

from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path
from typing import Any

from ..figure import CAVEAT, Provenance
from ..outcome import Outcome, Refused, Rendered
from ..sources import Page, SourceError

TEMPLATE = Path(__file__).resolve().parent / "templates" / "page.html"
FORMAT = "structure crosswalk 1"
ATLAS = "atlas/"
#: Fields an occurrence node carries over to the page as written.
OCCURRENCE_FIELDS = ("label", "relation", "repo", "path", "anchor", "json_row", "exactness", "emits", "datum", "note")


def _refuse_float(text: str) -> None:
    raise SourceError(f"the surface carries a float ({text}); it is exact by contract")


def transcribe(surface: dict) -> dict[str, Any]:
    """The page's data, field for field, after the vocabulary checks."""
    if surface.get("format") != FORMAT:
        raise SourceError(f"format is {surface.get('format')!r}, expected {FORMAT!r}")
    classes = {c["id"]: c["name"] for c in surface["classes"]}
    relations = {r["id"]: r["name"] for r in surface["relations"]}
    nodes, edges = surface["nodes"], surface["edges"]
    ids = [n["id"] for n in nodes]
    twice = sorted({i for i in ids if ids.count(i) > 1})
    problems = [f"node id {i} appears twice" for i in twice]
    problems += [f"node {n['id']}: class {n['class']!r} is not declared" for n in nodes if n["class"] not in classes]
    known = set(ids)
    for e in edges:
        where = f"edge {e['source']} -{e['relation']}-> {e['target']}"
        problems += [f"{where}: relation {e['relation']!r} is not declared"] if e["relation"] not in relations else []
        problems += [f"{where}: {end} {e[end]!r} is not a node" for end in ("source", "target") if e[end] not in known]
    if problems:
        raise SourceError("; ".join(problems))

    atlas_ids = {n["id"] for n in nodes if n["class"].startswith(ATLAS)}
    structures = [
        {"id": n["id"], "kind": n["class"][len(ATLAS):], "label": n["label"], "names": n.get("names", [n["label"]]),
         "status": n.get("name_status", ""), "key": n.get("key", {})}
        for n in nodes if n["id"] in atlas_ids
    ]
    occurrences = [
        {"id": n["id"], "plane": n["class"], **{f: n[f] for f in OCCURRENCE_FIELDS if f in n},
         "atlas": [e["target"] for e in edges if e["source"] == n["id"]]}
        for n in nodes if n["id"] not in atlas_ids
    ]
    links = [[e["source"], e["relation"], e["target"]] for e in edges
             if e["source"] in atlas_ids and e["target"] in atlas_ids]
    return {
        "repository": surface.get("repository", ""),
        "caveat": surface.get("caveat", ""),
        "classes": classes,
        "relations": relations,
        "structures": structures,
        "occurrences": occurrences,
        "links": links,
    }


def read(root: Path, page: Page) -> tuple[dict, Provenance]:
    source = Path(root) / page.checkout / page.path
    if not source.is_file():
        raise SourceError(f"no {page.path} in a checkout of {page.repo} at {source.parent}")
    raw = source.read_bytes()
    try:
        data = json.loads(raw, parse_float=_refuse_float)
    except ValueError as err:
        raise SourceError(f"{page.repo}/{page.path} is not JSON: {err}") from None
    return data, Provenance(page.repo, page.path, hashlib.sha256(raw).hexdigest())


def build(page: Page, sources: Path, *, dataset: Path | None = None,
          out: Path = Path("mandelbrot-names-atlas.html")) -> Outcome:
    """Read the surface, transcribe it, and write the page -- or say why not."""
    if dataset is not None:
        return Refused(page.id, "this page reads a committed file, not a dataset; drop --dataset")
    try:
        surface, provenance = read(sources, page)
        data = transcribe(surface)
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    except (KeyError, TypeError, AttributeError) as err:
        return Refused(page.id, f"the surface no longer reads as this page reads it: {err!r}")
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__SOURCES__", f"<code>{escape(provenance.stamp)}</code>")
            .replace("__CAVEAT__", escape(CAVEAT))
            .replace("__DATA__", json.dumps({**data, "stamp": provenance.stamp}, separators=(",", ":"))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return Rendered(page.id, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
