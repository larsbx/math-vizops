"""The manim scenes. This file is the only place that imports manimlib.

Rendered with 3b1b/manim (`manimgl`):

    manimgl vizops/scenes.py ClaimGraph -w

or, with the refusal check and the outcome codes around it:

    python -m vizops render c1-claim-graph

A scene knows its id in `sources.toml` and nothing else. It does not know
where the estate is checked out, what format its artifact has, or what the
classes on the frame mean -- it asks `vizops.bridge.figure_for` for a figure
and draws it. That is what keeps the mathematics upstream: there is no field
here for a scene to compute, only fields to draw.

Every frame carries the source's digest and the caveat. A video of an artifact
is a derived surface; it shows what one revision said and authorizes nothing.
"""

from __future__ import annotations

from math import cos, pi, sin

from manimlib import (
    DL,
    DOWN,
    DR,
    LEFT,
    UL,
    UR,
    UP,
    DashedLine,
    FadeIn,
    FullScreenRectangle,
    Line,
    RoundedRectangle,
    Scene,
    ShowCreation,
    Text,
    VGroup,
)

from vizops import layout, palette
from vizops.bridge import figure_for
from vizops.figure import Figure, Node
from vizops.wake.scene import WakeCycleFigure

BOX = (2.8, 0.62)  # the most a node box is allowed to take; it shrinks to fit
BADGE_FITS = 0.44  # below this box height the badge is dropped rather than overlapped
TITLE, HEADER, LABEL, SMALL = 30, 20, 16, 13
WAKE_FOOTER_CEILING = -3.10  # reserve the bottom band for provenance + caveat
WAKE_LANDING_NOTE_Y = -2.68
WAKE_COORDINATE_Y = -2.94


class FigureScene(Scene):
    """One column per class the source declares, in the source's order."""

    source_id = ""

    def construct(self) -> None:
        figure = figure_for(self.source_id)
        terms = figure.populated()
        hues = palette.assign(tuple(t.id for t in figure.terms))
        members = figure.members()
        frame = layout.Frame()
        points = layout.columns(tuple(t.id for t in terms), members, frame)
        width = min(BOX[0], 0.82 * layout.column_spacing(len(terms), frame))
        height = min(BOX[1], 0.78 * layout.pitch(members, frame))

        self.add(FullScreenRectangle().set_fill(palette.SURFACE, 1).set_stroke(width=0))
        self.add(chrome(figure))

        headers = VGroup(*(
            Text(term.name, font_size=HEADER)
            .set_color(hues[term.id])
            .set_max_width(width + 0.4)
            .move_to([points[members[term.id][0]][0], frame.height / 2 + 0.6, 0])
            for term in terms
        ))
        self.play(FadeIn(headers, lag_ratio=0.15), run_time=1.2)

        boxes = {
            node.id: node_box(node, hues[node.term], width, height).move_to([*points[node.id], 0])
            for node in figure.nodes
        }
        for term in terms:
            column = VGroup(*(boxes[i] for i in members[term.id]))
            self.play(FadeIn(column, shift=0.2 * UP, lag_ratio=0.12), run_time=1.0)

        styles = palette.edge_styles(figure.used_kinds())
        wires = VGroup(*(
            wire(boxes[e.source], boxes[e.target], styles[e.kind])
            for e in figure.edges
        ))
        if figure.edges:
            self.play(ShowCreation(wires, lag_ratio=0.03), run_time=2.0)
            self.bring_to_front(*boxes.values())
        self.wait(2)


class ClaimGraph(FigureScene):
    source_id = "c1-claim-graph"


class ObjectCatalogue(FigureScene):
    source_id = "psc-object-catalogue"


class WakeCycleToMandelbrot(Scene):
    """Three beats: exact orbit, characteristic pair, imported landing."""

    source_id = "wake-cycle-3-7"

    def construct(self) -> None:
        figure = figure_for(self.source_id)
        if not isinstance(figure, WakeCycleFigure):
            raise TypeError(f"{self.source_id}: expected WakeCycleFigure, got {type(figure).__name__}")

        self.add(FullScreenRectangle().set_fill(palette.SURFACE, 1).set_stroke(width=0))
        self.add(wake_chrome(figure))

        exact, characteristic, imported = palette.RING[0], palette.RING[3], palette.RING[6]

        orbit_title = Text(
            f"exact doubling orbit · p/q = {figure.p}/{figure.q}",
            font_size=HEADER,
        ).set_color(palette.INK).move_to([0, 2.75, 0])
        orbit_positions = [
            [3.0 * cos(pi / 2 - 2 * pi * i / figure.q),
             1.15 * sin(pi / 2 - 2 * pi * i / figure.q) + 0.9, 0]
            for i in range(figure.q)
        ]
        orbit_boxes = [
            wake_box(str(n), point, exact)
            for n, point in zip(figure.orbit, orbit_positions)
        ]
        self.play(FadeIn(VGroup(orbit_title, *orbit_boxes), lag_ratio=0.08), run_time=1.6)
        orbit_wires = VGroup(*(
            Line(orbit_boxes[i].get_center(), orbit_boxes[(i + 1) % figure.q].get_center())
            .set_stroke(palette.RULE, 1.5, opacity=0.85)
            for i in range(figure.q)
        ))
        self.play(ShowCreation(orbit_wires, lag_ratio=0.08), run_time=1.8)
        self.bring_to_front(*orbit_boxes)
        self.add(
            Text(f"×2 mod {figure.denominator}", font_size=SMALL)
            .set_color(palette.MUTED).move_to([0, 0.9, 0])
        )

        angular_title = Text(
            "angular order · shortest adjacent pair is characteristic",
            font_size=LABEL,
        ).set_color(palette.MUTED).move_to([0, -0.72, 0])
        step = 0.92
        start = -step * (figure.q - 1) / 2
        angular_boxes = [
            wake_box(
                str(n),
                [start + i * step, -1.2, 0],
                characteristic if n in figure.characteristic else exact,
                width=0.72,
                height=0.42,
            )
            for i, n in enumerate(figure.angular)
        ]
        pair = Text(
            f"θ₋ = {figure.theta_minus}/{figure.denominator}    "
            f"θ₊ = {figure.theta_plus}/{figure.denominator}    "
            f"width = 1/{figure.denominator}",
            font_size=LABEL,
        ).set_color(characteristic).move_to([0, -1.72, 0])
        self.play(FadeIn(VGroup(angular_title, *angular_boxes, pair), lag_ratio=0.06), run_time=1.5)

        left = wake_box(f"θ₋  {figure.theta_minus}/{figure.denominator}", [-2.8, -2.12, 0], characteristic)
        right = wake_box(f"θ₊  {figure.theta_plus}/{figure.denominator}", [2.8, -2.12, 0], characteristic)
        root = wake_box(f"{figure.p}/{figure.q} bulb root", [0, -2.32, 0], imported, width=1.65)
        rays = VGroup(
            DashedLine(left.get_center(), root.get_center()).set_stroke(characteristic, 1.8),
            DashedLine(right.get_center(), root.get_center()).set_stroke(characteristic, 1.8),
        )
        landing = Text(
            "[DH/Mil00] imported landing · ray paths schematic",
            font_size=SMALL,
        ).set_color(imported).move_to([0, WAKE_LANDING_NOTE_Y, 0])
        coordinate = Text(
            f"display aid: c ≈ {figure.root_re:+.6f}{figure.root_im:+.6f}i",
            font_size=SMALL,
        ).set_color(palette.MUTED).move_to([0, WAKE_COORDINATE_Y, 0])
        self.play(FadeIn(VGroup(left, right, root), lag_ratio=0.12), run_time=1.0)
        self.play(ShowCreation(rays, lag_ratio=0.15), run_time=1.2)
        self.bring_to_front(left, right, root)
        self.play(FadeIn(VGroup(landing, coordinate), lag_ratio=0.1), run_time=0.8)
        self.wait(2)


def wake_chrome(figure: WakeCycleFigure) -> VGroup:
    """Title, provenance and the exact/imported/display distinction."""
    title = Text(figure.title, font_size=TITLE).set_color(palette.INK).to_corner(UL, buff=0.35)
    footer = VGroup(*(
        Text(line, font_size=SMALL).set_color(palette.MUTED)
        for line in (figure.provenance.stamp, figure.caveat)
    )).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(DL, buff=0.3)
    key = Text(
        "blue: exact upstream · yellow: characteristic · violet: imported landing",
        font_size=SMALL,
    ).set_color(palette.MUTED).to_corner(UR, buff=0.3)
    return VGroup(title, footer, key)


def wake_box(label: str, point, hue: str, *, width: float = 1.05, height: float = 0.5) -> VGroup:
    """One directly labelled mark; colour is redundant, as in every scene."""
    box = (
        RoundedRectangle(width=width, height=height, corner_radius=0.1)
        .set_fill(palette.SURFACE, 1)
        .set_stroke(hue, 2)
    )
    text = Text(label, font_size=SMALL).set_color(palette.INK)
    text.set_max_width(width - 0.16).set_max_height(height - 0.1).move_to(box)
    return VGroup(box, text).move_to(point)


def chrome(figure: Figure) -> VGroup:
    """Title, provenance stamp, caveat, edge key. Present on every frame."""
    title = Text(figure.title, font_size=TITLE).set_color(palette.INK).to_corner(UL, buff=0.35)
    footer = VGroup(*(
        Text(line, font_size=SMALL).set_color(palette.MUTED)
        for line in (figure.provenance.stamp, figure.caveat)
    )).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(DL, buff=0.3)
    key = Text(palette.edge_key(figure.used_kinds()), font_size=SMALL).set_color(palette.MUTED).to_corner(DR, buff=0.3)
    return VGroup(title, footer, key)


def node_box(node: Node, hue: str, width: float, height: float) -> VGroup:
    """An opaque box so the wires pass behind it, outlined in its class's hue.

    The label is always drawn; the badge -- the source's own status word --
    only where there is room for it to be legible. A box that does not fit its
    own text is a node the frame claims to show and does not.
    """
    box = (
        RoundedRectangle(width=width, height=height, corner_radius=min(0.12, height / 4))
        .set_fill(palette.SURFACE, 1)
        .set_stroke(hue, 2)
    )
    label = Text(node.label, font_size=LABEL).set_color(palette.INK)
    if not node.badge or height < BADGE_FITS:
        return VGroup(box, label.set_max_width(width - 0.24).set_max_height(height - 0.12).move_to(box))
    badge = Text(node.badge, font_size=SMALL).set_color(hue)
    label.set_max_width(width - 0.24).set_max_height(height * 0.46)
    badge.set_max_width(width - 0.3).set_max_height(height * 0.3)
    return VGroup(box, VGroup(label, badge).arrange(DOWN, buff=0.04).move_to(box))


def wire(start: VGroup, end: VGroup, style: str) -> Line:
    line = DashedLine if style == "dashed" else Line
    return line(start.get_center(), end.get_center()).set_stroke(palette.RULE, 1.6, opacity=0.9)
