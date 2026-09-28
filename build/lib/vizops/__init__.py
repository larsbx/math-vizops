"""Animated surfaces for this estate's research artifacts.

    from vizops import figure_for
    figure_for("c1-claim-graph")          # what a scene draws, no renderer needed

Everything here reads an artifact that another repository generates and checks.
Nothing here derives a mathematical fact, and a rendered frame authorizes
nothing: see the README.
"""

from .figure import CAVEAT, Edge, Figure, FigureError, Node, Provenance, Term
from .outcome import EXIT_CODES, Inconclusive, Outcome, Refused, Rendered, worst
from .bridge import figure_for, render, renderer
from .sources import Scene, SourceError, load

__all__ = [
    "CAVEAT", "EXIT_CODES", "Edge", "Figure", "FigureError", "Inconclusive", "Node", "Outcome",
    "Provenance", "Refused", "Rendered", "Scene", "SourceError", "Term", "figure_for",
    "load", "render", "renderer", "worst",
]
