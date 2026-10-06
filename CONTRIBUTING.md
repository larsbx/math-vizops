<!--
Derived from templates/docs/CONTRIBUTING.md in larsbx/agent-icm @ sha256:88bf9172c22bc8da
Edit the canonical template or estate.toml in larsbx/agent-icm, then re-render there: make estate
Hand-edits here are drift, and agent-icm's `make estate-check` fails on them.
-->

# Contributing to math-vizops

Animated surfaces and pages for the estate's research artifacts, drawn with
3b1b/manim: each reads a surface another repository owns and checks, draws
what it says, and authorizes nothing.

**Language / toolchain:** Python 3.11 (no runtime dependencies; `manimgl` 1.7.2 is an optional render
  extra), pytest
**CI:** GitHub Actions: `ci.yml` (`unit`: vendored digests, generated-block drift,
  pytest; `estate`, outside pull requests: every scene against the real
  sibling checkouts), `static.yml` (build and deploy the generated Pages) and
  `wiki.yml` (mirror `wiki/` to the GitHub wiki)

Read these first — they are normative, not background:

- `README.md`
- `vizops/sources.toml`
- `wiki/`
- `vendored.toml`

---

## The gates

Run these before you open a pull request. Paste what they said into the PR's
evidence table.

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

A check you did not run is not evidence. Say which ones you skipped and why;
the pull request template has a place for exactly that.

## What counts as evidence here

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

These are not style preferences. Each one is settled somewhere in the documents
above; changing one is a decision record, not a pull request comment.

## Working shape

1. **Branch** from the default branch.
2. **Make the failing case first** where this repository's discipline requires
   it, and in every case make sure the new test fails without your change.
3. **Run the gates.** All of them, or name the ones you did not.
4. **Update the surfaces.** Documentation, status tables, ledgers and generated
   artifacts that name the behaviour you changed are part of the change, not a
   follow-up. Regenerate generated files with their tooling; never hand-edit one.
5. **Open the pull request** using the template. Fill in *What this does not
   establish* — it is required, and it is the section reviewers read first.

## Claim discipline

State exactly what your change establishes and no more.

- A search that stopped at a limit reports where it stopped.
- A bounded failure is not an absence.
- A refusal is not a clean answer.
- A translation preserves or lowers authority; it never raises it.
- "Verified" unqualified is not a claim. Say verified *by what*.

## Commits

Imperative, present tense, describing the difference: `Add the M-adic ball
carrier`, `Reject a singular M before the zeroth power`. The body carries the
reasoning when the subject cannot.
