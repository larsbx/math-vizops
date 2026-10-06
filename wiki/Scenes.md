# Scenes

Each scene is one entry in [`vizops/sources.toml`](https://github.com/larsbx/math-vizops/blob/main/vizops/sources.toml)
— the only place a source is named — and one `Scene` subclass in
`vizops/scenes.py` that knows its id and nothing else.

<!-- BEGIN generated scene table (python -m vizops --write); do not edit between the markers -->
<!-- Rendered by vizops/surfaces.py from vizops/sources.toml. -->

| Scene | Draws | Source surface | manim scene |
| --- | --- | --- | --- |
| `c1-claim-graph` | C1 claim relationship graph | [`docs/C1_claim_relationship_graph.json`](https://github.com/larsbx/finite-mandelbrot-research/blob/main/docs/C1_claim_relationship_graph.json) in `larsbx/finite-mandelbrot-research` | `ClaimGraph` |
| `psc-object-catalogue` | PSC mathematical-object catalogue | [`catalogues/mathematical_objects.toml`](https://github.com/larsbx/pisot-substitution-conjecture-research/blob/main/catalogues/mathematical_objects.toml) in `larsbx/pisot-substitution-conjecture-research` | `ObjectCatalogue` |
| `wake-cycle-3-7` | 3/7 wake cycle to Mandelbrot bulb root | [`oracles/rational_dynamics_py`](https://github.com/larsbx/finite-math-kernels/tree/65038cf1b6e8b038f1efc85e802d08b8c22fe4e1/oracles/rational_dynamics_py) in `larsbx/finite-math-kernels` (vendored at `65038cf1b6e8`) | `WakeCycleToMandelbrot` |

<!-- END generated scene table -->

## Gallery

Stills are produced locally (`python -m vizops still <id>`) and committed to
`wiki/images/`; CI cannot render them, for the reasons in
[[Rendering and viewing]].

<!-- BEGIN generated gallery (python -m vizops --write); do not edit between the markers -->
<!-- Rendered by vizops/surfaces.py from vizops/sources.toml and the stills in wiki/images/. -->

### C1 claim relationship graph

`ClaimGraph` — drawn from [`docs/C1_claim_relationship_graph.json`](https://github.com/larsbx/finite-mandelbrot-research/blob/main/docs/C1_claim_relationship_graph.json) in `larsbx/finite-mandelbrot-research`.

_No still published yet._ Run `python -m vizops still c1-claim-graph` and commit `wiki/images/c1-claim-graph.png`.

> Generated from ledger.json by proof_records/generate_ledgers.py; the status label and the provenance class are that generator's, not this one's.

### PSC mathematical-object catalogue

`ObjectCatalogue` — drawn from [`catalogues/mathematical_objects.toml`](https://github.com/larsbx/pisot-substitution-conjecture-research/blob/main/catalogues/mathematical_objects.toml) in `larsbx/pisot-substitution-conjecture-research`.

_No still published yet._ Run `python -m vizops still psc-object-catalogue` and commit `wiki/images/psc-object-catalogue.png`.

> The single machine-readable source of docs/mathematical-object-catalogue.md.

### 3/7 wake cycle to Mandelbrot bulb root

`WakeCycleToMandelbrot` — drawn from [`oracles/rational_dynamics_py`](https://github.com/larsbx/finite-math-kernels/tree/65038cf1b6e8b038f1efc85e802d08b8c22fe4e1/oracles/rational_dynamics_py) in `larsbx/finite-math-kernels` (vendored at `65038cf1b6e8`).

_No still published yet._ Run `python -m vizops still wake-cycle-3-7` and commit `wiki/images/wake-cycle-3-7.png`.

> Exact cycle data for p/q = 3/7 are the vendored rational_dynamics_py's (ported from the bulbs repository's kernel/bulbford/wake.py); the root coordinate is a numerical display aid and the rational parameter-ray landing relation is the imported [DH/Mil00].

<!-- END generated gallery -->

## What makes an artifact drawable

* It is an **owned source surface** its repository checks: normally a machine-readable artifact, or an exact module interface when VizOps calls that module rather than reimplementing it.
* It **declares its own vocabulary** — the classes nodes can be in, and the
  kinds edges can be. vizops colours and columns by that declaration.
* Its nodes carry an id and a label; its edges name two node ids.

An artifact that meets those is a few lines of adapter away
([[Adding a scene]]). One that does not is usually better fixed upstream: the
declaration a figure needs is the same declaration a reader of the artifact
needs.
