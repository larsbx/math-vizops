"""The Rauzy representability page: the upstream HTML verbatim, plus its stamp.

    python -m vizops page psc-rauzy-representability

pisot-substitution-conjecture-research commits the page as a self-contained
HTML document. Its classification of the closed claims, and the figures it
draws at load, belong to that repository, which owns both the claim ledger the
page reads and the review of the page. Transcription is the whole job here: the
bytes are copied unchanged and one block is added before ``</body>`` with the
source stamp and the caveat every vizops surface carries.

A file that is missing, empty, not an HTML document, or no longer carries the
claim table and the figure gallery this page is registered for is a refusal,
and nothing is written.
"""

from __future__ import annotations

import hashlib
from html import escape
from pathlib import Path

from ..figure import CAVEAT, Provenance
from ..outcome import Outcome, Refused, Rendered
from ..sources import Page, SourceError, read_artifact

#: What the registered page carries, each with the reason a page without it is refused.
MARKERS = {
    "<!doctype html": "not an HTML document",
    "</body>": "not an HTML document",
    'id="rows"': "no claim table",
    "data-fig=": "no figure gallery",
}


def read(root: Path, page: Page) -> tuple[str, Provenance]:
    """The upstream page as text, with the provenance of its exact bytes."""
    raw, digest = read_artifact(page.id, page.repo, page.path, Path(root) / page.checkout)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as err:
        raise SourceError(f"{page.repo}/{page.path} is not UTF-8: {err}") from None
    lowered = text.lower()
    missing = sorted({why for marker, why in MARKERS.items() if marker not in lowered})
    if missing:
        raise SourceError(f"{page.repo}/{page.path}: {', '.join(missing)}")
    return text, Provenance(page.repo, page.path, digest)


def stamp(provenance: Provenance) -> str:
    """The block a vizops surface adds: where the bytes came from, and what they are not."""
    return ('<aside data-vizops-stamp style="max-width:1060px;margin:0 auto;padding:0 20px 40px;'
            'font:0.8rem/1.5 ui-monospace,Menlo,monospace;color:var(--muted,#666)">'
            f"<div>source: <code>{escape(provenance.stamp)}</code></div>"
            f"<div>{escape(CAVEAT)}</div></aside>\n")


def build(page: Page, sources: Path, *, dataset: Path | None = None,
          out: Path = Path("psc-rauzy-representability.html")) -> Outcome:
    """Read the page, stamp it, and write it -- or say why not."""
    if dataset is not None:
        return Refused(page.id, "this page reads a committed file, not a dataset; drop --dataset")
    try:
        text, provenance = read(sources, page)
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    at = text.lower().rindex("</body>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text[:at] + stamp(provenance) + text[at:], encoding="utf-8")
    return Rendered(page.id, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
