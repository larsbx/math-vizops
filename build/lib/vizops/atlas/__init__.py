"""The ray address atlas: one self-contained HTML page for finite-mandelbrot-research.

The exact sections come from that repository's own emitter; the positions are
traced here, in `trace.py`, because no module in its kernel may produce one.
"""

from .build import SECTIONS, TEMPLATES, assemble, build, exact

__all__ = ["SECTIONS", "TEMPLATES", "assemble", "build", "exact"]
