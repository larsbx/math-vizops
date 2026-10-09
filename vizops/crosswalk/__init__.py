"""Mandelbrot Names Atlas: the structure crosswalk of finite-mandelbrot-research.

Every name, exact key, relation and code occurrence is transcribed from the
crosswalk surface that repository generates and checks; nothing is decided here.
"""

from .build import FORMAT, TEMPLATE, build, read, transcribe

__all__ = ["FORMAT", "TEMPLATE", "build", "read", "transcribe"]
