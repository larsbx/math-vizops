"""Wake cycle to Mandelbrot bulb root: one interactive page for mandelbrot-bulbs-and-ford-circles-research.

The exact angle data is finite-math-kernels' `rational_dynamics_py` -- a port of
that repository's `kernel/bulbford/wake.py`, vendored under vendor/python/ and
pinned in vendored.toml -- embedded at build time; the raster and the root
coordinate are drawn in the browser.
"""

from .build import QMAX, STILL, TEMPLATE, build, rows, still_claims
from .scene import WakeCycleFigure, figure as scene_figure

__all__ = [
    "QMAX", "STILL", "TEMPLATE", "build", "rows", "still_claims",
    "WakeCycleFigure", "scene_figure",
]
