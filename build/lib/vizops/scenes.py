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

from manimlib import (
    DL,
    DOWN,
    DR,
    LEFT,
    UL,
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

BOX = (2.8, 0.62)  # the most a node box is allowed to take; it shrinks to fit
BADGE_FITS = 0.44  # below this box height the badge is dropped rather than overlapped
TITLE, HEADER, LABEL, SMALL = 30, 20, 16, 13


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
