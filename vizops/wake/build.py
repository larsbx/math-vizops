"""The wake page: exact angle data from the vendored `rational_dynamics_py`, drawn here.

    python -m vizops page wake-to-mandelbrot

For every reduced p/q with q <= `QMAX`, the page shows the rotation word, the
doubling cycle over 2^q - 1 and the characteristic pair (theta-, theta+). All of
it is computed by finite-math-kernels' `rational_dynamics_py` (`mechanical_word`,
`rotation_cycle`, `wake`), vendored byte-for-byte under vendor/python/ and
pinned in vendored.toml, and embedded in the page as integers over 2^q - 1; the
page's script only looks it up. That package's rotation functions are a port of
mandelbrot-bulbs-and-ford-circles-research's `kernel/bulbford/wake.py`, which
this page used to execute from the sibling checkout; the tabulated rows are
byte-identical. The Mandelbrot raster, the cardioid-root coordinate and the
dashed rays are floating point or schematic, and the page says so.

The page is stamped with the digest of the vendored `doubling.py`, which is
refused if it no longer has its pinned digest. It is a picture of finite
arithmetic and an imported landing theorem, and it authorizes nothing.

`STILL` is the committed 3/7 still for the wiki. It is drawn by hand, so
`still_claims` reads the exact numbers it prints back out of it, for the estate
test to hold against the module.
"""

from __future__ import annotations

import hashlib
import json
import re
from math import gcd
from pathlib import Path
from typing import Any

import rational_dynamics_py as rd
import rational_dynamics_py.doubling

from ..figure import CAVEAT, Provenance
from ..outcome import Outcome, Refused, Rendered
from ..sources import Copy, Page, SourceError

TEMPLATE = Path(__file__).resolve().parent / "templates" / "page.html"
STILL = Path(__file__).resolve().parents[2] / "wiki" / "images" / "wake-cycle-3-7.svg"
#: The largest denominator on the page's slider. 2^q - 1 stays an exact JS integer far beyond it.
QMAX = 12


def rows(qmax: int = QMAX) -> list[dict[str, Any]]:
    """Every reduced p/q up to `qmax`, as the vendored package answers it."""
    def row(p: int, q: int) -> dict[str, Any]:
        den = 2 ** q - 1
        lo, hi = rd.wake(p, q)
        return {"p": p, "q": q, "den": den, "word": rd.mechanical_word(p, q, 0),
                "cycle": [int(x * den) for x in rd.rotation_cycle(p, q)],
                "lo": int(lo * den), "hi": int(hi * den)}
    return [row(p, q) for q in range(2, qmax + 1) for p in range(1, q) if gcd(p, q) == 1]


def executed(copy: Copy | None, owner: str) -> Copy:
    """The pinned copy, checked to be the very file Python imported.

    The stamp names the bytes `read` checked against the pin; this is what
    makes those the bytes that ran, and not some other `rational_dynamics_py`
    on the path.
    """
    if copy is None:
        raise SourceError(f"{owner}: the wake data is the vendored rational_dynamics_py's; "
                          "its sources.toml entry must say vendored = \"rational_dynamics_py\"")
    imported = Path(rational_dynamics_py.doubling.__file__).resolve()
    if imported != copy.local.resolve():
        raise SourceError(f"{owner}: rational_dynamics_py was imported from {imported}, "
                          f"not the vendored copy at {copy.local}")
    return copy


def still_claims(svg: str) -> dict[str, Any]:
    """The exact numbers the 3/7 still prints: angular order, theta-, theta+."""
    order = re.search(r"Angular order:</tspan>\s*([\d, ]+)<", svg)
    pair = re.search(r"θ₋ = (\d+)/(\d+),\s*θ₊ = (\d+)/(\d+)", svg)
    if not order or not pair:
        raise SourceError(f"{STILL.name}: no angular order or characteristic pair found")
    return {"cycle": [int(n) for n in order.group(1).split(",")],
            "lo": int(pair.group(1)), "hi": int(pair.group(3)), "den": int(pair.group(2))}


def build(page: Page, sources: Path, *, dataset: Path | None = None,
          out: Path = Path("wake-to-mandelbrot.html")) -> Outcome:
    """Check the vendored copy, tabulate, and write the page -- or say why not.

    `sources` is not read: the module is vendored, not a sibling checkout.
    """
    if dataset is not None:
        return Refused(page.id, "this page reads a module, not a dataset; drop --dataset")
    try:
        _, digest = page.read(Path(sources))
        executed(page.copy(), page.id)
        table = rows()
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    except (AttributeError, TypeError, ValueError) as err:
        return Refused(page.id, f"{page.path} no longer answers as this page reads it: {err}")
    provenance = Provenance(page.repo, page.path, digest, page.note)
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__STAMP__", f"{provenance.stamp} · {CAVEAT}")
            .replace("__QMAX__", str(QMAX))
            .replace("__DATA__", json.dumps(table, separators=(",", ":"))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return Rendered(page.id, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
