# Design notes

The estate's shared rulings are recorded in
[`larsbx/cross-pollinated`](https://github.com/larsbx/cross-pollinated). That
package records only that a repository **states** a ruling; the evidence for
keeping one belongs in the repository that claims it. What this one is built
to keep, and where:

## P1 — derive from the source, never re-derive

Adapters transcribe. The vocabulary on a frame is the artifact's own. The
status label a frame shows is the label `proof_records/generate_ledgers.py`
wrote — derived upstream from a record's kind, its override tag and the
completeness of its closure — not a second derivation here.

The same rule inside this repository: the scene table, the outcome table, the
module map and the gallery are **rendered** into the README and these wiki
pages by `vizops/surfaces.py`, from `sources.toml`, `outcome.MEANING` and the
modules' own docstrings. `python -m vizops --check` runs in CI.

## P3 — inconclusive is a third outcome

`vizops/outcome.py`. A sealed set of three, with three exit codes. See
[[Outcomes]].

## P4 — a derived or machine-produced artifact never authorizes

`Figure` cannot be constructed without a `Provenance`; every frame carries the
digest and the caveat. No adapter promotes anything, and no scene states a
finding. See [[Reading a frame]].

## P5 — make the illegal state unrepresentable

A figure with no provenance, a node in an undeclared class, a dangling edge,
an edge of an undeclared kind, a self-loop, an outcome with no reason, a
fourth outcome — none of these can be constructed. They are refused at
construction rather than detected later. See [[Why it refuses]].

## P6 — fail-closed has a direction

A missing or malformed source refuses; a missing renderer does not. The table
in [[Outcomes]] is the whole of it.

## Colour

Hues are the eight categorical slots of the reference palette, stepped for the
`#1a1a19` surface these scenes use and validated as a set — lightness band,
chroma floor, CVD separation (worst adjacent pair ΔE 8.4), normal-vision floor
(19.3) and contrast all pass for the seven slots the estate's artifacts
currently need.

A node graph is a harder case than that pairlist, because it puts every pair
of colours on screen at once. So colour is made **redundant**: the class is
carried by the column, then by the column header, then by the hue. A ninth
class is refused rather than given a generated hue.

## The modules

<!-- BEGIN generated module table (python -m vizops --write); do not edit between the markers -->
<!-- Rendered by vizops/surfaces.py from each module's own docstring. -->

| Module | Holds |
| --- | --- |
| `vizops/sources.py` | The registry of artifacts, and the fail-closed read of one. |
| `vizops/adapters.py` | Artifact bytes in, `Figure` out. One adapter per artifact format. |
| `vizops/figure.py` | The thing a scene draws, and every reason it can be refused. |
| `vizops/layout.py` | Where the nodes go. Pure, deterministic, and testable without a renderer. |
| `vizops/palette.py` | Colour, assigned in a fixed order and carrying no meaning on its own. |
| `vizops/outcome.py` | What a render run reports. Three inhabitants, and the third has a name. |
| `vizops/bridge.py` | Artifact to figure, and figure to file. |
| `vizops/scenes.py` | The manim scenes. This file is the only place that imports manimlib. |
| `vizops/surfaces.py` | Every surface that is generated rather than written, and the check that says none of them has drifted. |
| `vizops/wiki.py` | Publishing `wiki/` to the repository's GitHub wiki. |

<!-- END generated module table -->

## This wiki

These pages live in `wiki/` in the repository and are mirrored outward by
`python -m vizops wiki --publish`. The wiki is a derived surface: an edit made
in the browser is overwritten by the next publish. Edit `wiki/*.md`, run
`python -m vizops --check`, and publish.
