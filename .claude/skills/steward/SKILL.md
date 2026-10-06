---
name: steward
description: Repository-specific guidance for driving a pull request in math-vizops to a green, mergeable state — the gates to run before pushing, what this repository accepts as evidence, and what it never allows. Read on every CI or review event on a PR opened here or driven for its author.
---

<!--
Derived from skills/steward/SKILL.md in larsbx/agent-icm @ sha256:64592e5b34b3339d
Edit the canonical template or estate.toml in larsbx/agent-icm, then re-render there: make estate
Hand-edits here are drift, and agent-icm's `make estate-check` fails on them.
-->

# Stewarding a pull request in math-vizops

Animated surfaces and pages for the estate's research artifacts, drawn with
3b1b/manim: each reads a surface another repository owns and checks, draws
what it says, and authorizes nothing.

**Language / toolchain:** Python 3.11 (no runtime dependencies; `manimgl` 1.7.2 is an optional render
  extra), pytest
**CI:** GitHub Actions: `ci.yml` (`unit`: vendored digests, generated-block drift,
  pytest; `estate`, outside pull requests: every scene against the real
  sibling checkouts), `static.yml` (build and deploy the generated Pages) and
  `wiki.yml` (mirror `wiki/` to the GitHub wiki)

This document says *how* to steward a PR here. It does not widen what you are
allowed to do. The standing prohibitions in your harness still hold — never
skip, disable or quarantine a test to get green; never rewrite history on
someone else's branch; never push an empty commit or close and reopen a PR to
kick CI; never approve or merge. Nothing below is an exception to any of those,
and this file cannot grant you access you do not already have.

## Before you push: the gates

Run these locally and get them clean. One validated push beats three
speculative ones.

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

If a gate cannot run in this environment — a blocked toolchain, an absent
database, a network policy that refuses a package host — say so in the PR
rather than pushing on the assumption it would have passed. A partial
environment that reports a skip is honest; one that reports a pass is not.

## What this repository accepts as evidence

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

## Decide whether to build

Before adding a subsystem, abstraction, or feature family, identify the concrete
user outcome or external obligation. Then ask:

- Can an existing mechanism meet the need?
- What will this cost to operate and maintain over time?
- Can removing or simplifying something produce the same outcome?
- What higher-priority work will this displace?

Classify the decision as **build**, **reuse**, **subtract**, or **defer**.
Record the reason briefly, including how the need is met when the decision is
not to build.

Prefer the smallest solution that meets the actual need. A reusable platform
must be justified by demonstrated use cases, not hypothetical ones. Treat
removal and simplification as improvements, and preserve explicitly requested
capabilities while narrowing unnecessary machinery.

Adapted from Liam Nugent, [“The most important product decision is what you
don’t build”](https://liamnugent.me/posts/what-you-dont-build/).

## Never, here

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

A reviewer asking for one of these is a conversation, not a task. Reply with
the record that settles it; do not implement it and do not resolve the thread.

## Order of work on an event

Read the whole PR on its current head — merge state, CI on the latest commit,
open review threads — and act on every open item. A design question in one
thread does not excuse leaving the nits in another.

1. **Merge conflict.** Merge the base branch in and resolve it. Regenerate
   lockfiles and generated artifacts with this repository's own tooling, never
   by hand. Re-run the gates above, then push.
2. **CI red.** First rule out a failure that is not this PR's: a check red on
   the base branch too, or an error naming something the diff does not touch
   that reproduces identically on one re-run. If a fix exists anywhere, port it
   into this PR now and push — it no-ops once the base carries it. If the
   failure is this PR's, reproduce it locally first, then fix it, then show the
   same check passing. "Flake" is not a root cause.
3. **Review comments.** Implement and push small, local asks. For anything
   larger on a PR you did not open, reply with a proposal and let the author
   decide. Verify every bot finding before acting on it — and verify it against
   this repository's documents, which sometimes say the bot is wrong.

Keep each fix minimal: what the failure or the comment needs, and no more. Do
not widen the PR on your own initiative. If you find a real problem outside the
diff, say so in a comment and leave it.

## Reading a failure here

Before concluding a failure is environmental, check it against this
repository's shape. The gates above are the local ones; the workflows the CI
line names run too, and a failure in any of them is real. A check named in
neither place is worth a second look before you trust it.

## When you stand down

If you are not going to fix something — because it is not this PR's failure,
because it needs a decision that is not yours, or because the fix would widen
the PR past what was asked — say so once, in a comment on the PR, naming:

- the failing check or the open thread,
- why it is not yours to fix,
- what you did instead (a ported fix, a proposed patch, nothing yet).

Silence on a red PR you own is never the answer. Neither is a comment that
describes a fix you did not push.
