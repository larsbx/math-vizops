# Scenes

Each scene is one entry in [`vizops/sources.toml`](https://github.com/larsbx/math-vizops/blob/main/vizops/sources.toml)
— the only place a source is named — and one `Scene` subclass in
`vizops/scenes.py` that knows its id and nothing else.

<!-- BEGIN generated scene table (python -m vizops --write); do not edit between the markers -->
<!-- Rendered by vizops/surfaces.py from vizops/sources.toml. -->

| Scene | Draws | Source artifact | manim scene |
| --- | --- | --- | --- |
| `c1-claim-graph` | C1 claim relationship graph | [`docs/C1_claim_relationship_graph.json`](https://github.com/larsbx/finite-mandelbrot-research/blob/main/docs/C1_claim_relationship_graph.json) in `larsbx/finite-mandelbrot-research` | `ClaimGraph` |
| `psc-object-catalogue` | PSC mathematical-object catalogue | [`catalogues/mathematical_objects.toml`](https://github.com/larsbx/pisot-substitution-conjecture-research/blob/main/catalogues/mathematical_objects.toml) in `larsbx/pisot-substitution-conjecture-research` | `ObjectCatalogue` |

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

<!-- END generated gallery -->

## What makes an artifact drawable

* It is **machine-readable** and its own repository generates and checks it.
* It **declares its own vocabulary** — the classes nodes can be in, and the
  kinds edges can be. vizops colours and columns by that declaration.
* Its nodes carry an id and a label; its edges name two node ids.

An artifact that meets those is a few lines of adapter away
([[Adding a scene]]). One that does not is usually better fixed upstream: the
declaration a figure needs is the same declaration a reader of the artifact
needs.
