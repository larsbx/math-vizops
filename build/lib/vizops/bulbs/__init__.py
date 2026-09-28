"""Bulbs & Ford Circles: six scenes for mandelbrot-bulbs-and-ford-circles-research.

Every number is transcribed from the certificates, sweeps and germ vectors the
research repositories commit; nothing is certified or recomputed here.
"""

from .build import SCHEMAS, TEMPLATE, build, read, transcribe

__all__ = ["SCHEMAS", "TEMPLATE", "build", "read", "transcribe"]
