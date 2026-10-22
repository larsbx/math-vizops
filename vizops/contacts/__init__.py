"""PSC Rauzy contacts: exact tile contacts and box verdicts, drawn.

The verdicts, contacts, lattice neighbours and points are
pisot-substitution-conjecture-research's; nothing is certified or computed here.
"""

from .build import SCHEMA, TEMPLATE, build, transcribe

__all__ = ["SCHEMA", "TEMPLATE", "build", "transcribe"]
