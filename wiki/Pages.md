# Pages

Three surfaces are self-contained HTML pages rather than manim scenes: an
atlas, an interactive wake explorer, and a six-scene tour of the satellite
bulbs. Each is a `[[page]]` entry in
[`vizops/sources.toml`](https://github.com/larsbx/math-vizops/blob/main/vizops/sources.toml),
built into `out/<id>.html` by `python -m vizops page <id>`, and never
committed. Open the file in a browser; [[Rendering and viewing]] covers the
command and its outcomes.

Every page is stamped with the digest of each file it read and carries the
same line a frame does: it depicts its sources at those digests and
authorizes nothing. A published copy is a snapshot of one build; rebuild and
republish it when its sources move.

<!-- BEGIN generated page gallery (python -m vizops --write); do not edit between the markers -->
<!-- Rendered by vizops/surfaces.py from the [[page]] entries in vizops/sources.toml and the stills in wiki/images/. -->

### Ray address atlas

`python -m vizops page mandelbrot-atlas` — reads [`kernel/mojo/entrypoints/atlas_dataset.mojo`](https://github.com/larsbx/finite-mandelbrot-research/blob/main/kernel/mojo/entrypoints/atlas_dataset.mojo) in `larsbx/finite-mandelbrot-research`.

**View it:** [Ray address atlas](https://claude.ai/artifact/9LDj75kM1AFBjZLmDxuFgA) — a published build, private to its owner until shared.

![Ray address atlas](images/mandelbrot-atlas.png)

> The exact sections are that emitter's, checked against the Python oracles by tests/test_atlas_dataset.py; the positions are traced by vizops/atlas/trace.py and are a placement, not a claim.

### Wake cycle to Mandelbrot bulb root

`python -m vizops page wake-to-mandelbrot` — reads [`oracles/rational_dynamics_py`](https://github.com/larsbx/finite-math-kernels/tree/65038cf1b6e8b038f1efc85e802d08b8c22fe4e1/oracles/rational_dynamics_py) in `larsbx/finite-math-kernels` (vendored at `65038cf1b6e8`).

![Wake cycle to Mandelbrot bulb root](images/wake-to-mandelbrot.png)

> Rotation words, doubling cycles and characteristic pairs are the vendored rational_dynamics_py's (ported from the bulbs repository's kernel/bulbford/wake.py); the raster, the root coordinate and the dashed rays are display aids. The landing relation is the imported [DH/Mil00].

### Bulbs & Ford Circles

`python -m vizops page bulbs-and-ford-circles` — reads [`experiments/data/center_certificates.json`](https://github.com/larsbx/mandelbrot-bulbs-and-ford-circles-research/blob/main/experiments/data/center_certificates.json) in `larsbx/mandelbrot-bulbs-and-ford-circles-research`, [`experiments/data/antipode_certificates.json`](https://github.com/larsbx/mandelbrot-bulbs-and-ford-circles-research/blob/main/experiments/data/antipode_certificates.json) in `larsbx/mandelbrot-bulbs-and-ford-circles-research`, [`experiments/data/kappa_q1009.json`](https://github.com/larsbx/mandelbrot-bulbs-and-ford-circles-research/blob/main/experiments/data/kappa_q1009.json) in `larsbx/mandelbrot-bulbs-and-ford-circles-research`, [`conformance/cyclotomic_germ_v1.json`](https://github.com/larsbx/finite-math-kernels/blob/main/conformance/cyclotomic_germ_v1.json) in `larsbx/finite-math-kernels`.

**View it:** [Bulbs & Ford Circles](https://claude.ai/artifact/X6cYWjyUe8VZLRL75dorKh) — a published build, private to its owner until shared.

![Bulbs & Ford Circles](images/bulbs-and-ford-circles.png)

> Certified centre and antipode boxes, G brackets and the q = 1009 sweep are that repository's; the exact indices are finite-math-kernels' cyclotomic germ vectors. The page transcribes them; every certificate it shows was issued upstream.

<!-- END generated page gallery -->
