# math-vizops

Animated surfaces for this estate's research artifacts, drawn with
[3b1b/manim](https://github.com/3b1b/manim) (`manimgl`).

A scene here reads one machine-readable artifact that another repository
generates and checks — a typed claim graph, an object catalogue — and draws
what it says. It does not compute a status, close a dependency graph, classify
an object, or translate one repository's vocabulary into another's. Every one
of those questions already has an answer where it was built, and a second
answer here could only ever disagree with it.

```sh
pip install -e '.[test]'
python -m vizops                      # what each scene would draw, or why not
python -m vizops --check              # the README's table has not drifted
python -m vizops render c1-claim-graph
pytest -q
```

`python -m vizops` needs no renderer and no GPU: it reads every artifact,
refuses every malformed one, and names what it found. That is the part worth
running in CI. Rendering is the last step and the least interesting one.

## What it draws

<!-- BEGIN generated scene table (python -m vizops --write); do not edit between the markers -->
<!-- Generated from sources.toml by `python -m vizops --write`. -->

| Scene | Draws | Source artifact | manim scene |
| --- | --- | --- | --- |
| `c1-claim-graph` | C1 claim relationship graph | [`docs/C1_claim_relationship_graph.json`](https://github.com/larsbx/finite-mandelbrot-research/blob/main/docs/C1_claim_relationship_graph.json) in `larsbx/finite-mandelbrot-research` | `ClaimGraph` |
| `psc-object-catalogue` | PSC mathematical-object catalogue | [`catalogues/mathematical_objects.toml`](https://github.com/larsbx/pisot-substitution-conjecture-research/blob/main/catalogues/mathematical_objects.toml) in `larsbx/pisot-substitution-conjecture-research` | `ObjectCatalogue` |

<!-- END generated scene table -->

Sibling checkouts are looked for beside this repository — `../<repo-name>` —
or wherever `--sources` / `$VIZOPS_SOURCES` points.

## Draw the artifact, never the mathematics

Each adapter in `vizops/adapters.py` transcribes fields. The classes on a
frame are the classes the artifact itself declares (`provenance_classes` and
`edge_types` in the typed graph; `[[taxonomy]]` in the catalogue), in the order
it declares them, and a node in a class its own file never declared is
refused rather than coloured grey and drawn anyway.

The consequence is deliberate: when a figure needs a fact no artifact carries,
the fix is upstream in the generator, not here. A status label in
`finite-mandelbrot-research` is derived from a record's kind, its override tag
and the completeness of its closure by `proof_records/generate_ledgers.py`;
vizops reads the label that generator wrote. Re-deriving it here would put a
second implementation of an estate rule inside a repository that draws
pictures.

Nothing is pinned by digest. vizops draws whatever the checkout says today and
stamps that digest on the frame, so the frame is a statement about one revision
rather than a claim that the revision is current.

## Every frame carries its provenance, and authorizes nothing

`Figure` cannot be constructed without a `Provenance` — repository, path, and
the sha256 of the exact bytes the figure was built from — and every scene
stamps it, beside this line:

> derived surface — depicts the source at this digest; authorizes nothing

A rendered animation is evidence of what one artifact said at one digest. It
is not evidence that the claim is true, that the census ran, or that anything
was accepted. Promotion from evidence to finding happens in the repositories
that own the claims, in `proof_records` and `claim_governance`, by an
attributable act. A video cannot participate in that, and this repository is
built so that it cannot look as though it did.

## Three outcomes, and fail-closed has a direction

A render run reports `rendered`, `refused`, or `inconclusive`, and the set is
closed — a fourth outcome has to be declared in `vizops/outcome.py` beside the
exit codes, where CI can be taught what it means. The two failure directions
are not the same direction:

| Outcome | Exit | When |
| --- | ---: | --- |
| `rendered` | 0 | A file exists, and the outcome carries its digest. |
| `refused` | 1 | The source is missing, empty, of an unknown format, or describes a figure the type refuses — or the renderer died. Nothing was drawn, on purpose. |
| `inconclusive` | 2 | No verdict was reached: no `manimgl` on PATH, no GL context, a timeout, or a clean exit that wrote no file. |

A machine with no renderer has not shown that a scene is broken and has not
shown that it works. Scoring that as a pass would be a verdict the run did not
reach; scoring it as a failure would be a different one.

## Colour is the third encoding, never the carrier

Hues are the eight categorical slots of the reference palette, stepped for the
`#1a1a19` surface the scenes use and validated as a set — lightness band,
chroma floor, CVD separation (worst adjacent pair ΔE 8.4), normal-vision floor
(19.3) and contrast all pass for the seven slots the estate's artifacts
currently need. A node graph is a harder case than that pairlist, because it
puts every pair of colours on screen at once, so colour is made redundant:
each class gets its own column, every node is directly labelled, and each
column is headed by the source's own word for the class. Take the colour away
and the frame still reads.

A ninth class is not a generated hue — `palette.assign` refuses, and the fix is
to fold the tail at the source or to facet the figure.

## The files

| File | Holds |
| --- | --- |
| `vizops/sources.toml` | Every artifact vizops draws, and nothing else. The README table above is generated from it. |
| `vizops/sources.py` | The manifest loader, and the fail-closed read of one artifact. |
| `vizops/adapters.py` | One transcriber per artifact format. No computation. |
| `vizops/figure.py` | `Figure` and its refusals — the whole interface between artifacts and animation. |
| `vizops/palette.py`, `vizops/layout.py` | Colour and geometry: pure, deterministic, tested without a renderer. |
| `vizops/outcome.py` | The three outcomes and their exit codes. |
| `vizops/bridge.py` | Artifact → figure, and figure → file via a `manimgl` subprocess. |
| `vizops/scenes.py` | The only file that imports `manimlib`. |

## Rendering

`manimgl` is an optional extra because everything up to the last step runs
without it:

```sh
pip install -e '.[render]'            # 3b1b/manim
python -m vizops render psc-object-catalogue --quality high --out out/
manimgl vizops/scenes.py ClaimGraph -w   # the same scene, driven directly
```

It needs a system Pango and FFmpeg (`apt install libpango1.0-dev ffmpeg`, or
`brew install pango ffmpeg`) and a working GL context. A headless runner
usually has neither, which is why CI renders nothing and why an absent
renderer is `inconclusive` rather than red.

## What CI checks

* every artifact in `sources.toml` loads, transcribes, lays out and colours —
  against the real sibling checkouts, with `VIZOPS_REQUIRE_SOURCES=1` so that
  a missing checkout fails instead of quietly skipping;
* the README's scene table has not drifted from `sources.toml`;
* the unit suite, whose negative controls are inputs each refusal is known to
  reject: an artifact of the wrong declared format, a node in an undeclared
  class, an edge to a node that is not there, a renderer that exits clean
  without writing, one that dies, one that never finishes;
* the scenes themselves, against a stand-in `manimlib` that offers exactly the
  names manimgl 1.7.2 exports and raises on anything else
  (`tests/manimlib_stub.py`). That says the scene's lookups and arithmetic
  hold — one box per node, one wire per edge, the stamp on the frame. It says
  nothing about how the frame looks, which is what `render` is for.

## Rulings

The estate's shared rulings are recorded in
[`larsbx/cross-pollinated`](https://github.com/larsbx/cross-pollinated); that
package records only that a repository *states* a ruling, and the evidence for
keeping one belongs in the repository that claims it. What this one is built
to keep:

* **P1 — derive from the source, never re-derive.** Adapters transcribe; the
  vocabulary on a frame is the source's own; the README table is generated
  from `sources.toml` and `--check` runs in CI.
* **P3 — inconclusive is a third outcome.** `vizops/outcome.py`, with its own
  exit code, reached by an absent renderer, a timeout, or an empty write.
* **P4 — a derived artifact never authorizes.** Provenance is a required field
  of `Figure`; the caveat is on every frame; no adapter promotes anything.
* **P5 — make the illegal state unrepresentable.** A figure with no
  provenance, an undeclared class, a dangling edge or a fourth outcome cannot
  be built, rather than being detected later.
* **P6 — fail-closed has a direction.** A missing source refuses; a missing
  renderer does not. The table above is the whole of it.
