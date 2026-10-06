# math-vizops

Animated surfaces for this estate's research artifacts, drawn with
[3b1b/manim](https://github.com/3b1b/manim) (`manimgl`).

A scene here reads one source surface that another repository owns and checks —
normally a machine-readable artifact, and for the wake specimen the owning
exact module itself — and draws what it says. It does not compute a status, close a dependency graph, classify
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
<!-- Rendered by vizops/surfaces.py from vizops/sources.toml. -->

| Scene | Draws | Source surface | manim scene |
| --- | --- | --- | --- |
| `c1-claim-graph` | C1 claim relationship graph | [`docs/C1_claim_relationship_graph.json`](https://github.com/larsbx/finite-mandelbrot-research/blob/main/docs/C1_claim_relationship_graph.json) in `larsbx/finite-mandelbrot-research` | `ClaimGraph` |
| `psc-object-catalogue` | PSC mathematical-object catalogue | [`catalogues/mathematical_objects.toml`](https://github.com/larsbx/pisot-substitution-conjecture-research/blob/main/catalogues/mathematical_objects.toml) in `larsbx/pisot-substitution-conjecture-research` | `ObjectCatalogue` |
| `wake-cycle-3-7` | 3/7 wake cycle to Mandelbrot bulb root | [`oracles/rational_dynamics_py`](https://github.com/larsbx/finite-math-kernels/tree/3fd22c1ec0c356b1415639dcc712967c583cb7b8/oracles/rational_dynamics_py) in `larsbx/finite-math-kernels` (vendored at `3fd22c1ec0c3`) | `WakeCycleToMandelbrot` |

<!-- END generated scene table -->

Sibling checkouts are looked for beside this repository — `../<repo-name>` —
or wherever `--sources` / `$VIZOPS_SOURCES` points.

## Pages

Three surfaces are not manim scenes but self-contained HTML pages, each declared
as a `[[page]]` in `sources.toml` and built into `out/<id>.html`, never
committed:

```sh
python -m vizops page                                     # every page
python -m vizops page mandelbrot-atlas --dataset d.json   # the atlas from saved emitter output
python -m vizops page wake-to-mandelbrot
python -m vizops page bulbs-and-ford-circles
```

* **`mandelbrot-atlas`** — the ray address atlas for
  `finite-mandelbrot-research`: the parameter plane, the circle of addresses
  and the incidence package. Its exact sections are that repository's
  `pixi run atlas-dataset` output (run in the sibling checkout, or read with
  `--dataset`), refused if a section is missing or a float has leaked in. Its
  positions are traced here by `vizops/atlas/trace.py` — floating point, the
  analytic machinery that repository's kernel refuses, and a placement rather
  than a claim. The exclusion-box verdicts are upstream's oracle, loaded from
  the checkout and never copied.
* **`wake-to-mandelbrot`** — for any reduced `p/q` with `q ≤ 12`, the rotation
  word, the doubling cycle and the characteristic pair `θ₋, θ₊` that select
  the `p/q` bulb root. Every exact number is `finite-math-kernels`'
  `rational_dynamics_py` — a port of `mandelbrot-bulbs-and-ford-circles-research`'s
  `kernel/bulbford/wake.py`, vendored under `vendor/python/` (see
  [Vendored code](#vendored-code)) — and embedded; the raster, the root
  coordinate and the dashed rays are display aids. Its 3/7 still,
  `wiki/images/wake-cycle-3-7.svg`, is drawn by hand and held to the package
  by `tests/test_wake.py`.
* **`bulbs-and-ford-circles`** — six scenes on the satellite bulbs: the
  critical orbit, Ford circles against bulb sizes, wakes, the parabolic flower
  and its index, how a Krawczyk box certifies a centre, and G against the
  modular inverse at q = 1009. It transcribes four committed files — the
  centre and antipode certificates and the q = 1009 sweep from
  `mandelbrot-bulbs-and-ford-circles-research`, and `finite-math-kernels`'
  cyclotomic germ vectors — field for field: boxes drawn at their midpoints,
  G brackets rounded outward, verdicts copied as written. A missing file,
  another schema, or centre and antipode certificates that disagree about
  which bulbs exist is refused.

A page carries each source's stamp and the same caveat as a frame.

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

No checkout is pinned by digest. vizops draws whatever the checkout says today
and stamps that digest on the frame, so the frame is a statement about one
revision rather than a claim that the revision is current. Code vizops
*executes* is the exception, below.

### Vendored code

Exact arithmetic vizops calls rather than reads is vendored, not re-derived and
not executed out of a sibling checkout. `vendor/python/` holds byte-for-byte
copies of `finite-math-kernels`' `oracles/rational_dynamics_py` (the doubling
map: exact type, rotation cycles, wakes) and `tools/vendoring` (the checker),
each pinned in `vendored.toml` to one upstream commit and the SHA-256 of every
file. `pyproject.toml` installs `rational_dynamics_py` under its own name from
there; nothing edits `sys.path`.

vizops reaches the package only through `vizops.sources.vendored_package`. It
imports the package, resolves every file `vendored.toml` pins for it against
the directory Python actually imported it from (`vendor/python/` here,
`site-packages/` in a wheel), checks each SHA-256, refuses a missing file, a
drifted one or an unpinned module beside them, and returns the verified module
with a digest over the whole pinned file set. The wake scene and page reach it
through a `vendored = "rational_dynamics_py"` entry in `sources.toml` and stamp
that digest; the atlas chooses root rays with its `exact_type` and stamps it
too.

An installed wheel needs the pins as well. The root `vendored.toml` stays the
only copy in the repository: `setup.py` hooks `build_py` to copy it into the
build tree as `vizops/vendored.toml`, which is where an installed vizops reads
it, and `tests/test_packaging.py` builds a wheel, checks that copy is
byte-identical to the root file, and runs the installed CLI from outside the
source tree.

To update: copy the package directories from upstream at the new commit
(`git archive <sha> oracles/rational_dynamics_py tools/vendoring`), then

```sh
python vendor/python/vendoring/check_vendored_sync.py pin rational_dynamics_py <sha>
python vendor/python/vendoring/check_vendored_sync.py pin vendoring <sha>
python vendor/python/vendoring/check_vendored_sync.py     # what CI runs
```

Never patch a vendored file; a fix goes upstream and is re-vendored.

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

<!-- BEGIN generated outcome table (python -m vizops --write); do not edit between the markers -->
<!-- Rendered by vizops/surfaces.py from EXIT_CODES and MEANING in vizops/outcome.py. -->

| Outcome | Exit | When |
| --- | ---: | --- |
| `rendered` | 0 | A file exists, and the outcome carries its digest. |
| `refused` | 1 | The source is missing, empty, of an unknown format, or describes a figure the type refuses -- or the renderer died. Nothing was drawn, on purpose. |
| `inconclusive` | 2 | No verdict was reached: no `manimgl` on PATH (or, for a page, no `pixi`), no GL context, a timeout, or a clean exit that wrote no file. |

<!-- END generated outcome table -->

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
| `vizops/atlas/build.py` | The atlas page: exact sections from finite-mandelbrot-research, positions traced here. |
| `vizops/atlas/trace.py` | Where the catalogued objects sit in the parameter plane. |
| `vizops/wake/build.py` | The wake page: exact angle data from the vendored `rational_dynamics_py`, drawn here. |
| `vizops/wake/scene.py` | The canonical 3/7 wake as a typed Manim payload. |
| `vizops/bulbs/build.py` | The Bulbs & Ford Circles page: certificates transcribed, never reissued. |

<!-- END generated module table -->

`vizops/sources.toml` is the only place a source is named — scenes as
`[[scene]]`, pages as `[[page]]`; the tables above,
in this file and in the wiki, are rendered from it and from the modules' own
docstrings by `vizops/surfaces.py`.

## Docs

The explainers live in the [wiki](https://github.com/larsbx/math-vizops/wiki)
— what every mark on a frame means, the scenes with their stills, every
refusal and its fix, how to add a scene. Its pages are written in `wiki/` in
this repository and mirrored outward:

```sh
python -m vizops --check              # README and wiki pages match their sources
python -m vizops still c1-claim-graph # a frame for the gallery, into wiki/images/
python -m vizops wiki --publish       # mirror wiki/ to the GitHub wiki
```

The wiki is a derived surface: an edit made in the browser is overwritten by
the next publish, which is what keeps one page from existing in two editable
copies.

## Rendering

`manimgl` is an optional extra because everything up to the last step runs
without it:

```sh
pip install -e '.[render]'            # 3b1b/manim
python -m vizops render psc-object-catalogue --quality high --out out/
manimgl vizops/scenes.py ClaimGraph -w   # the same scene, driven directly
```

It needs a system Pango and FFmpeg (`apt install libpango1.0-dev ffmpeg`, or
`brew install pango ffmpeg`) and a working GL context. The Pages workflow provisions these dependencies and attempts rendering with
Xvfb and Mesa. An absent renderer remains `inconclusive`, and blocks deployment.

## What CI checks

* every artifact in `sources.toml` loads, transcribes, lays out and colours —
  against the real sibling checkouts, with `VIZOPS_REQUIRE_SOURCES=1` so that
  a missing checkout fails instead of quietly skipping;
* the README's scene table has not drifted from `sources.toml`;
* every vendored file under `vendor/python/` still has the digest
  `vendored.toml` pins, and no unpinned source file sits beside them;
* the unit suite, whose negative controls are inputs each refusal is known to
  reject: an artifact of the wrong declared format, a node in an undeclared
  class, an edge to a node that is not there, a renderer that exits clean
  without writing, one that dies, one that never finishes;
* the scenes themselves, against a stand-in `manimlib` that offers exactly the
  names manimgl 1.7.2 exports and raises on anything else
  (`tests/manimlib_stub.py`). That says the scene's lookups and arithmetic
  hold — one box per node, one wire per edge, the stamp on the frame. It says
  nothing about how the frame looks, which is what `render` is for;
* the wiki publisher, against a local bare repository: the mirror is exact, a
  deleted page is deleted, a second publish is a no-op.

On a push to `main`, CI also mirrors `wiki/` to the GitHub wiki. That needs a
`WIKI_TOKEN_AND_AGENT_ASSISTANTS` secret — `GITHUB_TOKEN` cannot push to a
wiki — and a wiki that has been enabled and had its first page created;
without either, the job says so and publishing stays a local command.

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

## Generated-site deployment

`python -m vizops site --sources .. --out out/site --quality low` builds every
registered HTML page (including the atlas through its upstream Pixi emitter),
and a canonical still and video for every registered scene. Use a fresh output
directory. Inputs must be clean Git checkouts; upstream builders and renderers
read isolated exports of those committed bytes. Movies are converted to
H.264/yuv420p MP4, checked with FFprobe for a positive finite duration and valid
dimensions, and paired with first-frame PNG posters. Missing FFmpeg/FFprobe or
a timeout is inconclusive; invalid media or a failed conversion refuses. The
index embeds verified media, links the interactive pages, and repeats the source notes and non-authorizing
caveat. No source checkout, hand-drawn substitute, or partial renderer output
is published.

`manifest.json` records each input revision and a SHA-256 digest of its tracked
file/digest map, the registry digest, renderer version and quality, each build
verdict, and each generated file digest. Video records retain the raw-render
digest, playback metadata, and video/poster digests. `manifest.sha256` binds the
deterministic JSON bytes. Timestamps and temporary paths are omitted; video
bytes can still vary between renderer versions. Original inputs and exported
source files are checked again after building, so a changed checkout blocks
publication. Digests attest bytes, never mathematical correctness.

Pages now builds under Xvfb with Mesa software GL, Pango, FFmpeg, TeX, ManimGL
and Pixi. A private sibling needs `ESTATE_TOKEN` read access; absent sources
refuse. Exit 1 (`refused`) or 2 (`inconclusive`) blocks the Pages upload and
deployment. Build evidence is retained separately for diagnosis. PRs run the
unit and surface gates, followed by real software-GL still/video/poster checks
through the site builder against an explicit scene-only test registry. The
reviewable fixture artifact is labeled as validation, without sibling secrets
or deployment permissions. Complete upstream rendering runs on main or manual dispatch. Wiki mirroring remains
in `wiki.yml`.
