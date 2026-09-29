"""Wake cycle to Mandelbrot bulb root: one interactive page for mandelbrot-bulbs-and-ford-circles-research.

The exact angle data is that repository's `kernel/bulbford/wake.py`, embedded at
build time; the raster and the root coordinate are drawn in the browser.
"""

from .build import QMAX, STILL, TEMPLATE, build, rows, still_claims

__all__ = ["QMAX", "STILL", "TEMPLATE", "build", "rows", "still_claims"]
