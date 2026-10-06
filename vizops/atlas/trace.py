"""Where the catalogued objects sit in the parameter plane.

This is a picture, not a certificate. It is floating point and it uses the
analytic machinery finite-mandelbrot-research's executable core refuses: a
parameter ray is traced by Newton down a decreasing potential, then finished on
the equation the point satisfies. That is why it lives in vizops and not in
that repository at all, and why the audits that police its core need no
exception for it.

What it computes is a placement. Associating a ray address with a parameter is
the imported landing theorem; finite-mandelbrot-research neither computes that
association nor claims it, and a position drawn from this file proves nothing
about the address it is drawn for.
"""

from __future__ import annotations

import cmath
from fractions import Fraction

R0 = 64.0        # the potential the ray is picked up at
SHARP = 12       # Newton steps per doubling of the potential


def trace_ray(theta: Fraction, depth: int = 20) -> complex | None:
    """Follow the parameter ray at angle `theta` inward from potential `R0`.

    The ray is the preimage of a radial line under the Boettcher coordinate,
    and `Phi_M(c) = Phi_c(c)`, so the target at step `m` is written with the
    exponent `2^(n-1)`: the critical value is the first iterate, not the zeroth.
    """
    c = R0 * cmath.exp(2j * cmath.pi * float(theta))
    for m in range(1, depth * SHARP + 1):
        n = m // SHARP + 1
        e = n - 1
        target = (R0 ** (2.0 ** (e - m / SHARP))) * cmath.exp(
            2j * cmath.pi * float(theta * (2 ** e) % 1))
        for _ in range(64):
            z, dz = 0j, 0j
            for _ in range(n):
                dz, z = 2 * z * dz + 1, z * z + c
            if dz == 0 or not abs(z) < 1e300:
                break
            step = (z - target) / dz
            c -= step
            if abs(step) < 1e-15 * max(1.0, abs(c)):
                break
        if not abs(c) < 1e4:
            return None
    return c


def newton_center(c0: complex, n: int) -> complex | None:
    """Newton on `f_c^n(0) = 0` from a traced landing point.

    A periodic angle lands at a parabolic root, which the ray approaches
    tangentially, so the trace stops short. The centre of the component the
    root bounds is the nearby solution of the defining equation, and naming the
    component that way is stabler than trying to resolve the root itself.
    """
    c = c0
    for _ in range(200):
        z, dz = 0j, 0j
        for _ in range(n):
            dz, z = 2 * z * dz + 1, z * z + c
        if dz == 0:
            return None
        step = z / dz
        c -= step
        if abs(step) < 1e-15:
            break
    return c


def polish_misiurewicz(c0: complex, preperiod: int, period: int, steps: int = 80) -> complex | None:
    """Newton on `f^(l+k)(c) = f^(l)(c)`, from the traced landing point.

    Same two stages as a periodic angle: trace to find which point, then solve
    to place it. The orbit is counted from the critical value `c`, not from
    zero, which is what makes the preperiod here the angle's own.
    """
    c = complex(c0)
    for _ in range(steps):
        z, dz = complex(c), complex(1)
        zl = dzl = None
        for i in range(preperiod + period):
            if i == preperiod:
                zl, dzl = z, dz
            dz = 2 * z * dz + 1
            z = z * z + c
        if preperiod == 0:
            zl, dzl = complex(c), complex(1)
        if zl is None:
            zl, dzl = z, dz
        num, den = z - zl, dz - dzl
        if den == 0 or not abs(c) < 1e4:
            return None
        step = num / den
        c -= step
        if abs(step) < 1e-15 * max(1.0, abs(c)):
            break
    return c if abs(c) < 1e4 else None


def satisfies_type(c: complex, preperiod: int, period: int, tol: float = 1e-6) -> bool:
    """Whether the critical-value orbit at `c` closes up as type `(l, k)`.

    The defining equation is tested directly, in `l + k` steps. Searching for
    the cycle instead would run the orbit far longer, and these orbits are
    repelling, so the error is amplified until the iterate escapes: the direct
    test is the reliable one.
    """
    z = complex(c)
    orbit = [z]
    for _ in range(preperiod + period):
        z = z * z + c
        orbit.append(z)
    return abs(orbit[preperiod + period] - orbit[preperiod]) < tol * max(1.0, abs(orbit[preperiod]))

