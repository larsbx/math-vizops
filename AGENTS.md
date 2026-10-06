<!--
Derived from templates/docs/AGENTS.md in larsbx/agent-icm @ sha256:e0ea75600e3d136a
Edit the canonical template or estate.toml in larsbx/agent-icm, then re-render there: make estate
Hand-edits here are drift, and agent-icm's `make estate-check` fails on them.
-->

# Agent policy — math-vizops

Animated surfaces and pages for the estate's research artifacts, drawn with
3b1b/manim: each reads a surface another repository owns and checks, draws
what it says, and authorizes nothing.

**Language / toolchain:** Python 3.11 (no runtime dependencies; `manimgl` 1.7.2 is an optional render
  extra), pytest
**CI:** GitHub Actions: `ci.yml` (`unit`: vendored digests, generated-block drift,
  pytest; `estate`, outside pull requests: every scene against the real
  sibling checkouts), `static.yml` (build and deploy the generated Pages) and
  `wiki.yml` (mirror `wiki/` to the GitHub wiki)

This file is for whoever is working here next, human or otherwise. It states
what is settled, so that it does not get re-litigated by someone reading only
the code.

## Read first

- `README.md`
- `vizops/sources.toml`
- `wiki/`
- `vendored.toml`

## Gates

Before proposing a change as finished, run:

1. every vendored file matches its pin in vendored.toml —

   ```sh
   python vendor/python/vendoring/check_vendored_sync.py
   ```

2. no generated block in the README or the wiki has drifted (after `pip
   install -e '.[test]'`) —

   ```sh
   python -m vizops --check
   ```

3. unit suite —

   ```sh
   pytest -q
   ```

4. every scene reads, transcribes and lays out its real artifact (`estate`
   job; needs the sibling checkouts) —

   ```sh
   python -m vizops
   ```

5. the scenes against the real sibling artifacts (`estate` job) —

   ```sh
   pytest tests/test_estate.py -q
   ```

Report honestly which ran. A partial environment that reports a skip is worth
more than one that passes vacuously.

## What this repository treats as evidence

- Every frame carries a `Provenance` (repository, path, and the sha256 of the
  exact bytes it was built from) and the line "derived surface — depicts the
  source at this digest; authorizes nothing". A rendering is evidence of what
  one artifact said at one digest, not that the claim is true.
- A render run reports `rendered`, `refused` or `inconclusive`, and the set is
  closed. A machine with no renderer is `inconclusive`, neither a pass nor a
  failure.
- The suite's negative controls are inputs each refusal is known to reject: a
  wrong declared format, a node in an undeclared class, a dangling edge, a
  renderer that exits clean without writing, one that dies, one that never
  finishes.
- Code vizops executes is vendored and pinned per file in `vendored.toml`;
  `vizops.sources.vendored_package` checks every pinned digest against the
  directory Python imported the package from.

## Standing prohibitions

- Never patch a vendored file; a fix goes upstream and is re-vendored (README,
  Vendored code).
- Never compute a status, close a dependency graph, classify an object or
  translate one repository's vocabulary here. When a figure needs a fact no
  artifact carries, the fix is upstream in the generator (README).
- Never draw a node in a class its own artifact did not declare; it is
  refused, not coloured grey and drawn anyway (README, Draw the artifact,
  never the mathematics).
- Never edit between the generated-block markers in the README or the wiki;
  edit `vizops/sources.toml` or the module docstrings and run `python -m
  vizops --write`.
- Never edit the GitHub wiki in the browser: `wiki/` in this repository is the
  source, and the next publish overwrites a browser edit (README, Docs).
- Never score an absent renderer as a pass: it is `inconclusive`, and it
  blocks deployment (README, Rendering).

## Scope discipline

- Make the change that was asked for. If the surrounding code is wrong in a way
  the task did not name, say so — do not widen the diff to fix it.
- If something is blocked, finish everything that is not, and say precisely what
  was left and why.
- Where a decision is already recorded, follow it or reopen it explicitly. Do
  not route around it in code.
