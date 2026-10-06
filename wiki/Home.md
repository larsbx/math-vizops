# math-vizops

Animated surfaces for this estate's research artifacts, drawn with
[3b1b/manim](https://github.com/3b1b/manim) (`manimgl`).

A scene here reads **one source surface that another repository owns and
checks** — normally a machine-readable artifact, and for the wake specimen the
owning exact module itself — and draws what it says. It computes no status, closes
no dependency graph, classifies no object, and translates no vocabulary. Every
one of those questions is already answered where it was built; a second answer
in a repository that draws pictures could only disagree with the first.

```sh
pip install -e '.[test]'
python -m vizops                      # what each scene would draw, or why not
python -m vizops render c1-claim-graph
```

## What it draws

<!-- BEGIN generated scene table (python -m vizops --write); do not edit between the markers -->
<!-- Rendered by vizops/surfaces.py from vizops/sources.toml. -->

| Scene | Draws | Source surface | manim scene |
| --- | --- | --- | --- |
| `c1-claim-graph` | C1 claim relationship graph | [`docs/C1_claim_relationship_graph.json`](https://github.com/larsbx/finite-mandelbrot-research/blob/main/docs/C1_claim_relationship_graph.json) in `larsbx/finite-mandelbrot-research` | `ClaimGraph` |
| `psc-object-catalogue` | PSC mathematical-object catalogue | [`docs/catalogues/mathematical_objects.toml`](https://github.com/larsbx/pisot-substitution-conjecture-research/blob/main/docs/catalogues/mathematical_objects.toml) in `larsbx/pisot-substitution-conjecture-research` | `ObjectCatalogue` |
| `wake-cycle-3-7` | 3/7 wake cycle to Mandelbrot bulb root | [`oracles/rational_dynamics_py`](https://github.com/larsbx/finite-math-kernels/tree/d61bcf82d621b192a918ae90a031413bb2d30875/oracles/rational_dynamics_py) in `larsbx/finite-math-kernels` (vendored at `d61bcf82d621`) | `WakeCycleToMandelbrot` |

<!-- END generated scene table -->

## Where to go next

| Page | Answers |
| --- | --- |
| **[[Reading a frame]]** | What every mark on a rendered frame means, including the digest in the corner. |
| **[[Scenes]]** | The scenes, with stills, and what each one's artifact is. |
| **[[Pages]]** | The HTML pages — atlas, wake explorer, Bulbs & Ford Circles — with stills and published copies. |
| **[[Rendering and viewing]]** | Installing `manimgl`, rendering, producing a still, why CI renders nothing. |
| **[[Outcomes]]** | `rendered`, `refused`, `inconclusive` — and why the third one exists. |
| **[[Why it refuses]]** | Every refusal, the message it prints, and the fix. |
| **[[Adding a scene]]** | Pointing a new scene at a new artifact. |
| **[[Design notes]]** | The rulings this repository is built to keep, and the module map. |

## The one rule

> Draw the artifact. Never the mathematics.

Adapters transcribe fields. The classes on a frame are the classes the
artifact itself declares, in the order it declares them. A node in a class its
own file never declared is refused, rather than coloured grey and drawn
anyway. When a figure needs a fact no artifact carries, the fix is upstream in
the generator that writes the artifact — not here.
