"""The atlas page: exact sections from finite-mandelbrot-research, positions traced here.

    python -m vizops page mandelbrot-atlas [--dataset dataset.json]

The split is that repository's policy, and vizops keeps it.

Exact objects -- the catalogue and its counts, kneading sequences and internal
addresses, tuned angles, the obstruction extractions with their pairs, the
decided measures, the incidence packages -- come from one run of its
`pixi run atlas-dataset`, the canonical implementation, which its
`tests/test_atlas_dataset.py` checks against the Python oracles. vizops reads
that output and refuses it if a section is missing or a float has leaked in.

Positions cannot come from there: they are floating point, and no module under
its `kernel/` may produce one. They come from `trace.py` beside this file, and
the page says so where it shows them.

The exclusion boxes are the exception that proves the split. Their verdicts
are exact and are the upstream oracle's -- `interval_exclusion_reference.py`,
loaded from the checkout, never copied here -- and only the choice of box about
a traced position, and its placement on a canvas, is made here. Exclusion is
not existence: a root in the box is a separate witness and the page claims none.

Fail-closed has the direction it has everywhere in vizops: a missing checkout,
an emitter that fails, a malformed dataset or a traced position that disagrees
with its exact type is a refusal and writes nothing; a machine with no `pixi`
reaches no verdict.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from types import ModuleType
from typing import Any

from ..figure import CAVEAT, Provenance
from ..outcome import Inconclusive, Outcome, Refused, Rendered
from ..sources import Page, SourceError, module, vendored_package
from . import trace as tp

TEMPLATES = Path(__file__).resolve().parent / "templates"
#: The sections the emitter prints, and all of them: a dataset with one more or
#: one fewer is a different emitter, and the page would silently misdraw it.
SECTIONS = frozenset({"counts", "catalogues", "kneading", "tunings", "graphs", "density", "incidence"})
ORACLE = "reference/python/interval/interval_exclusion_reference.py"
MAX_COMPONENT_PERIOD = 5
NAMED_ROOT_RAY = {
    (1, 3): "doubling", (2, 3): "doubling", (1, 7): "rabbit", (2, 7): "rabbit",
    (3, 7): "airplane", (4, 7): "airplane", (7, 15): "primitive period 4",
    (8, 15): "primitive period 4", (2, 5): "satellite period 4", (3, 5): "satellite period 4",
}


def exact(raw: bytes) -> dict[str, Any]:
    """The emitter's output, or a refusal naming what is wrong with it."""
    try:
        data = json.loads(raw)
    except ValueError as err:
        raise SourceError(f"the dataset is not JSON: {err}") from None
    if not isinstance(data, dict) or set(data) != SECTIONS:
        got = sorted(data) if isinstance(data, dict) else type(data).__name__
        raise SourceError(f"the dataset's sections are {got}, expected {sorted(SECTIONS)}")
    leaks = list(_floats(data, "dataset"))
    if leaks:
        raise SourceError("a float reached the exact sections at " + ", ".join(leaks[:5]))
    return data


def _floats(node: Any, where: str):
    if isinstance(node, float):
        yield where
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _floats(value, f"{where}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _floats(value, f"{where}[{i}]")


def oracle(checkout: Path) -> ModuleType:
    """The upstream exclusion oracle, loaded from the checkout it lives in."""
    try:
        return module(checkout, ORACLE)
    except SourceError:
        raise SourceError(f"no exclusion oracle at {checkout / ORACLE}") from None


def traced_addresses(catalogues: list[dict]) -> list[dict]:
    """Each catalogue address traced to a position and finished on its equation."""
    out = []
    for row in catalogues:
        preperiod, period, den = row["l"], row["k"], row["den"]
        for num in row["addresses"]:
            landed = tp.trace_ray(Fraction(num, den), depth=22)
            if landed is None:
                continue
            polished = tp.polish_misiurewicz(landed, preperiod, period)
            moved = abs(polished - landed) if polished is not None else -1.0
            if polished is not None and tp.satisfies_type(polished, preperiod, period):
                landed = polished
            out.append({"num": num, "den": den, "l": preperiod, "k": period,
                        "re": round(landed.real, 12), "im": round(landed.imag, 12),
                        "agrees": tp.satisfies_type(landed, preperiod, period),
                        "moved": round(moved, 12)})
    return out


#: The vendored package root rays are chosen with (see `traced_components`).
EXACT = "rational_dynamics_py"


def traced_components(rd: ModuleType) -> list[dict]:
    """Root rays traced and met at one centre, which is what groups them.

    Which angles are root rays of period-k components is exact, and is the
    `exact_type` of the vendored `rational_dynamics_py` (finite-math-kernels),
    passed in as `rd` after `sources.vendored_package` has verified it: an angle
    over 2^k - 1 qualifies when its type is (preperiod 0, period k). That
    replaced a local `period_of`, which answered None both for a preperiodic
    angle and for a period past its search cap (cap=32, whose loop admitted
    33). `exact_type` is closed form with no cap, so "preperiodic" is
    `preperiod > 0` and "not found" no longer exists. On the angles asked
    about here -- odd denominators, k <= MAX_COMPONENT_PERIOD -- the two agree.
    """
    found: dict[tuple, dict] = {}
    for period in range(1, MAX_COMPONENT_PERIOD + 1):
        den = 2 ** period - 1
        for num in range(1, den):
            theta = Fraction(num, den)
            if rd.exact_type(theta) != (0, period):
                continue
            landed = tp.trace_ray(theta, depth=18)
            centre = tp.newton_center(landed, period) if landed is not None else None
            if centre is None:
                continue
            key = (period, round(centre.real, 6), round(centre.imag, 6))
            entry = found.setdefault(key, {"period": period, "re": round(centre.real, 12),
                                           "im": round(centre.imag, 12), "rays": [], "name": None})
            entry["rays"].append([num, den])
            if (num, den) in NAMED_ROOT_RAY:
                entry["name"] = NAMED_ROOT_RAY[(num, den)]
    found[(1, 0.0, 0.0)] = {"period": 1, "re": 0.0, "im": 0.0, "rays": [[0, 1]],
                            "name": "main cardioid"}
    return sorted(found.values(), key=lambda e: (e["period"], e["re"], e["im"]))


def placed_tunings(tunings: list[dict]) -> list[dict]:
    """A tuned angle is exact; the component it names still has to be found."""
    def place(row: dict) -> dict:
        if row["tuned"] is None or not row["period"]:
            return {**row, "re": None, "im": None}
        landed = tp.trace_ray(Fraction(*row["tuned"]), depth=18)
        centre = tp.newton_center(landed, row["period"]) if landed is not None else None
        return {**row, "re": round(centre.real, 12) if centre else None,
                "im": round(centre.imag, 12) if centre else None}
    return [place(row) for row in tunings]


def box_record(ie: ModuleType, name: str, box, preperiod: int, period: int, horizon: int,
               angles: list[Fraction], note: str) -> dict:
    excluded, forbidden, failures = ie.excluded_count(box, preperiod, period, horizon)
    return {"name": name, "l": preperiod, "k": period, "horizon": horizon,
            "re": [str(box.re.lo), str(box.re.hi)], "im": [str(box.im.lo), str(box.im.hi)],
            "re_f": [float(box.re.lo), float(box.re.hi)],
            "im_f": [float(box.im.lo), float(box.im.hi)],
            "excluded": excluded, "forbidden": forbidden,
            "failures": [list(f) for f in failures],
            "theta": [[a.numerator, a.denominator] for a in angles], "note": note}


def certificates(ie: ModuleType, addresses: list[dict]) -> list[dict]:
    """The two pinned boxes, a horizon control, and one box per further type."""
    rows = [
        box_record(ie, "c = -2", ie.c_minus_2_box(), 2, 1, 3, [Fraction(1, 2)],
                   "finite-mandelbrot-research's minimal smoke test: half-width 1/16 about -2"),
        box_record(ie, "c = -2, one step further", ie.c_minus_2_box(), 2, 1, 4, [Fraction(1, 2)],
                   "computed here: the same box at horizon 4. Exclusion is relative to a horizon, "
                   "and this box is too wide to decide the two collisions the extra step introduces"),
        box_record(ie, "M(4,1)", ie.m41_box(), 4, 1, 6,
                   [Fraction(9, 56), Fraction(11, 56), Fraction(15, 56)],
                   "finite-mandelbrot-research's stress test: half-width 2^-25, three rays landing together"),
    ]
    seen: set[tuple[int, int]] = set()
    for row in addresses:
        preperiod, period = row["l"], row["k"]
        if (preperiod, period) in seen or preperiod + period > 5 or not row["agrees"]:
            continue
        # The critical-orbit preperiod is one more than the angle's own.
        ell, horizon = preperiod + 1, preperiod + 1 + period + 1
        for half_exp in range(6, 34):
            centre_exp = half_exp + 4
            box = ie.dyadic_box(round(row["re"] * 2 ** centre_exp),
                                round(row["im"] * 2 ** centre_exp), centre_exp, half_exp)
            if not ie.excluded_count(box, ell, period, horizon)[2]:
                rows.append(box_record(
                    ie, f"({preperiod},{period}) at {row['num']}/{row['den']}", box, ell, period,
                    horizon, [Fraction(row["num"], row["den"])],
                    "computed here: the widest dyadic box about the traced position that "
                    "excludes every forbidden collision"))
                seen.add((preperiod, period))
                break
    return rows


def assemble(data: dict[str, Any], ie: ModuleType, provenances: tuple[Provenance, ...],
             rd: ModuleType) -> tuple[str, dict[str, Any]]:
    """The page, and the dataset it embeds: the exact sections untouched, the
    traced ones beside them."""
    misiurewicz = traced_addresses(data["catalogues"])
    full = {**data, "misiurewicz": misiurewicz, "components": traced_components(rd),
            "tunings": placed_tunings(data["tunings"]), "certificates": certificates(ie, misiurewicz)}
    head, body, script = ((TEMPLATES / f"{part}.html").read_text(encoding="utf-8")
                          for part in ("head", "body", "script"))
    stamp = f"{' · '.join(p.stamp for p in provenances)} · {CAVEAT}"
    page = head + body.replace("__STAMP__", stamp) + \
        script.replace("__DATA__", json.dumps(full, separators=(",", ":")))
    return page, full


def build(page: Page, sources: Path, *, dataset: Path | None = None, out: Path = Path("atlas.html"),
          timeout: float = 1800.0) -> Outcome:
    """Read or emit the dataset, trace, and write the page -- or say why not."""
    checkout = Path(sources) / page.checkout
    if not checkout.is_dir():
        return Refused(page.id, f"no checkout of {page.repo} at {checkout}; pass --sources to say where the estate is")
    try:
        ie = oracle(checkout)
    except SourceError as refusal:
        return Refused(page.id, str(refusal))

    if dataset is not None:
        if not dataset.is_file() or not dataset.stat().st_size:
            return Refused(page.id, f"no dataset at {dataset}")
        raw = dataset.read_bytes()
    else:
        pixi = shutil.which("pixi")
        if pixi is None:
            return Inconclusive(page.id, f"no pixi on PATH; run `pixi run {page.task} > dataset.json` "
                                         f"in {checkout} and pass --dataset")
        try:
            done = subprocess.run([pixi, "run", page.task], cwd=checkout, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return Inconclusive(page.id, f"`pixi run {page.task}` did not finish within {timeout:g}s")
        if done.returncode != 0:
            tail = " / ".join(done.stderr.decode(errors="replace").strip().splitlines()[-3:])
            return Refused(page.id, f"`pixi run {page.task}` exited {done.returncode}: {tail or 'no stderr'}")
        raw = done.stdout

    try:
        data = exact(raw)
        exact_types = vendored_package(EXACT)
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    emitter = checkout / page.path
    oracle_source = checkout / ORACLE
    if not emitter.is_file():
        return Refused(page.id, f"no emitter at {emitter}")
    provenances = (
        Provenance(page.repo, page.path, hashlib.sha256(emitter.read_bytes()).hexdigest(), page.note),
        Provenance(page.repo, ORACLE, hashlib.sha256(oracle_source.read_bytes()).hexdigest()),
        Provenance("dataset", dataset.name if dataset is not None else page.task,
                   hashlib.sha256(raw).hexdigest()),
        Provenance(exact_types.pin.repository, f"{EXACT} (vendored at {exact_types.pin.commit[:12]})",
                   exact_types.digest),
    )
    try:
        html, full = assemble(data, ie, provenances, exact_types.module)
    except SourceError as refusal:
        return Refused(page.id, str(refusal))
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, ZeroDivisionError) as err:
        return Refused(page.id, f"the dataset's nested records no longer match the atlas schema: {err!r}")
    disagreeing = [f"{r['num']}/{r['den']}" for r in full["misiurewicz"] if not r["agrees"]]
    if disagreeing:
        return Refused(page.id, f"{len(disagreeing)} traced position(s) disagree with their exact type: "
                                f"{', '.join(disagreeing[:5])}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return Rendered(page.id, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
