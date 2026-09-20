"""A stand-in for `manimlib`, so `vizops/scenes.py` can be exercised on a
machine with no renderer.

It offers exactly the names manimgl 1.7.2 exports and this repository uses --
checked against the wheel -- and raises `AttributeError` on anything else, so
a scene that reaches for a method manim does not have fails here instead of
inside a renderer nobody can run in CI. It is a stand-in for the API, not for
manim: it draws nothing, and a passing scene test says the scene's arithmetic
and lookups hold, not that the frame looks right.
"""

from __future__ import annotations

import sys
import types

#: Mobject methods this repository calls. Every one exists in manimgl 1.7.2.
METHODS = frozenset(
    {"set_color", "set_fill", "set_stroke", "set_max_width", "set_max_height",
     "move_to", "to_corner", "arrange", "next_to", "shift"}
)


class Vec(tuple):
    def __rmul__(self, k: float) -> "Vec":
        return Vec(k * c for c in self)

    __mul__ = __rmul__

    def __add__(self, other) -> "Vec":
        return Vec(a + b for a, b in zip(self, other))

    def __sub__(self, other) -> "Vec":
        return Vec(a - b for a, b in zip(self, other))


ORIGIN, UP, DOWN, LEFT, RIGHT = Vec((0, 0, 0)), Vec((0, 1, 0)), Vec((0, -1, 0)), Vec((-1, 0, 0)), Vec((1, 0, 0))
UL, UR, DL, DR = UP + LEFT, UP + RIGHT, DOWN + LEFT, DOWN + RIGHT


class Mobject:
    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs
        self.point = ORIGIN

    def __getattr__(self, name):
        if name not in METHODS:
            raise AttributeError(f"manimlib has no {type(self).__name__}.{name}")

        def call(*args, **kwargs):
            if name == "move_to":
                target = args[0]
                self.point = target.point if isinstance(target, Mobject) else Vec(target)
            return self

        return call

    def get_center(self) -> Vec:
        return self.point


class Text(Mobject):
    @property
    def text(self) -> str:
        return self.args[0]


class Line(Mobject):
    pass


class DashedLine(Line):
    pass


class RoundedRectangle(Mobject):
    pass


class FullScreenRectangle(Mobject):
    pass


class VGroup(Mobject):
    @property
    def children(self) -> tuple:
        return self.args


class Animation:
    def __init__(self, mobject, **kwargs):
        self.mobject, self.kwargs = mobject, kwargs


class FadeIn(Animation):
    pass


class ShowCreation(Animation):
    pass


class Scene:
    def __init__(self):
        self.added: list = []
        self.played: list = []
        self.waited: list = []

    def add(self, *mobjects):
        self.added.extend(mobjects)

    def bring_to_front(self, *mobjects):
        self.added.extend(mobjects)

    def play(self, *animations, **kwargs):
        # Playing an animation puts its mobject on the frame, as manim does.
        self.played.extend(animations)
        self.added.extend(a.mobject for a in animations)

    def wait(self, duration=1.0):
        self.waited.append(duration)


def install() -> bool:
    """Put the stand-in on `sys.modules` unless the real manimlib is there.

    Returns True if the stand-in was used, so a test can say which it ran
    against rather than implying it ran against manim.
    """
    try:
        import manimlib  # noqa: F401
    except ImportError:
        module = types.ModuleType("manimlib")
        module.__dict__.update({k: v for k, v in globals().items() if not k.startswith("_")})
        sys.modules["manimlib"] = module
        return True
    return False
