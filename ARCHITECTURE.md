# Repository architecture

Animated surfaces and pages for the estate's research artifacts, drawn with 3b1b/manim. Each scene reads a surface another repository owns and checks, and draws what it says.

The machine-readable source of repository structure and authority is
[`ESTATE.toml`](ESTATE.toml), validated by the estate audit pinned there
(`larsbx/estate-governance`, contract `estate-repository-v2`). The layout is
`transitional`: planes name their target directory and the paths that
currently fill them.

| Plane | Target | Current | Content |
| --- | --- | --- | --- |
| policy | `policy/` | `ESTATE.toml`, `AGENTS.md`, `CONTRIBUTING.md` | estate manifest; agent and contribution policy |
| kernel | `kernel/` | `vizops` | the importable `vizops` package: source readers, layout, scenes |
| conformance | `tests/` | `tests` | unit tests and real-artifact estate checks |
| vendor | `vendor/` | `vendor`, `vendored.toml` | packages vendored from finite-math-kernels, hash-pinned |
| docs | `docs/` | `wiki`, `README.md`, `ARCHITECTURE.md` | GitHub wiki source and README |

## Authority boundary

Python is the canonical language and holds acceptance authority over one
boundary: **source acceptance for rendering**. `vizops/sources.py` is its
single implementation: it accepts a scene's upstream artifact or vendored
package only when the manifest, location and sha256 pins all agree, and
otherwise refuses (`SourceError`), never drawing a placeholder.

That acceptance concerns drawing inputs only. A rendered frame remains a
derived surface that depicts one revision and authorizes nothing about the
mathematics it shows; claim status stays with the repository that owns the
artifact.

## Migration

Boundary first, no mass move. Pending steps:

1. Move wiki/ to docs/wiki/ together with the wiki.yml mirror source path.
2. Decide whether the kernel target is the `vizops` package path or a kernel/ wrapper before declaring the layout canonical.
