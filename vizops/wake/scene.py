"""The canonical 3/7 wake as a typed Manim payload.

The interactive wake page can explore every reduced p/q with q <= 12.  A
Manim scene has a different job: tell one stable story well.  This module
therefore asks the *upstream* wake module for the 3/7 specimen and packages
its answers for the renderer.

No exact wake arithmetic is reimplemented here.  `rows` calls the upstream
`mechanical`, `rotation_cycle` and `wake` functions, and the orbit order
below advances with the upstream `double` function.  The only calculation
owned here is the floating-point main-cardioid root coordinate used as a
display aid; it is carried separately from the exact integers.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from math import cos, pi, sin
from pathlib import Path

from ..figure import CAVEAT, FigureError, Provenance
from ..sources import Scene, SourceError, module
from .build import rows

P, Q = 3, 7


@dataclass(frozen=True, slots=True)
class WakeCycleFigure:
    """Exact upstream wake data plus one explicitly numerical placement."""

    title: str
    provenance: Provenance
    p: int
    q: int
    denominator: int
    word: int
    orbit: tuple[int, ...]
    angular: tuple[int, ...]
    theta_minus: int
    theta_plus: int
    root_re: float
    root_im: float

    def __post_init__(self) -> None:
        problems: list[str] = []
        if not self.title.strip():
            problems.append("wake figure: no title")
        if self.q < 2 or not (0 < self.p < self.q):
            problems.append(f"wake figure: invalid internal angle {self.p}/{self.q}")
        if len(self.orbit) != self.q or len(set(self.orbit)) != self.q:
            problems.append("wake figure: orbit is not one q-cycle")
        if tuple(sorted(self.orbit)) != self.angular:
            problems.append("wake figure: angular order is not the sorted orbit")
        if self.theta_plus - self.theta_minus != 1:
            problems.append("wake figure: characteristic pair is not adjacent")
        if self.denominator <= 0:
            problems.append("wake figure: nonpositive denominator")
        if problems:
            raise FigureError("\n  ".join(("wake figure refused:", *problems)))

    @property
    def caveat(self) -> str:
        return CAVEAT

    @property
    def characteristic(self) -> tuple[int, int]:
        return self.theta_minus, self.theta_plus


def figure(scene: Scene, sources: Path, p: int = P, q: int = Q) -> WakeCycleFigure:
    """Load the owning module and package its 3/7 answers, or refuse."""

    raw, digest = scene.read(sources)
    checkout = Path(sources) / scene.checkout
    try:
        wake = module(checkout, scene.path)
        table = rows(wake, qmax=q)
        row = next(r for r in table if (r["p"], r["q"]) == (p, q))

        den = row["den"]
        x = Fraction(row["word"], den)
        orbit: list[int] = []
        for _ in range(q):
            orbit.append(int(x * den))
            x = wake.double(x)
    except StopIteration as err:
        raise SourceError(f"{scene.id}: upstream wake module has no {p}/{q} row") from err
    except SourceError:
        raise
    except (AttributeError, TypeError, ValueError) as err:
        raise SourceError(f"{scene.id}: {scene.path} no longer answers as the Manim scene reads it: {err}") from err

    # Numerical placement only: the boundary of the main cardioid is
    # c(lambda) = lambda/2 - lambda^2/4 for lambda = exp(2*pi*i*p/q).
    t = 2 * pi * p / q
    root_re = cos(t) / 2 - cos(2 * t) / 4
    root_im = sin(t) / 2 - sin(2 * t) / 4

    # Re-hash the bytes here only as a consistency assertion: Scene.read is
    # the authority for the digest placed in Provenance.
    if digest != hashlib.sha256(raw).hexdigest():
        raise FigureError("wake figure: source digest changed while being read")

    return WakeCycleFigure(
        title=scene.title,
        provenance=Provenance(scene.repo, scene.path, digest, scene.note),
        p=p,
        q=q,
        denominator=row["den"],
        word=row["word"],
        orbit=tuple(orbit),
        angular=tuple(row["cycle"]),
        theta_minus=row["lo"],
        theta_plus=row["hi"],
        root_re=root_re,
        root_im=root_im,
    )
