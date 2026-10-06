<!--
Derived from templates/github/PULL_REQUEST_TEMPLATE.md in larsbx/agent-icm @ sha256:1e174a33ab48cac7
Edit the canonical template or estate.toml in larsbx/agent-icm, then re-render there: make estate
Hand-edits here are drift, and agent-icm's `make estate-check` fails on them.
-->

## What changed

<!-- The behaviour change, in one or two sentences. Not the effort — the difference. -->

## Why

<!-- The problem, and why this is the shape of the fix. Link the issue, spec item, decision record or task id. -->

## Evidence

<!--
Paste what you ran and what it said. A check you did not run is not evidence;
say so plainly rather than leaving the line blank.
-->

| Check                                                                                                     | Command                                                 | Result  |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ------- |
| every vendored file matches its pin in vendored.toml                                                      | `python vendor/python/vendoring/check_vendored_sync.py` | not run |
| no generated block in the README or the wiki has drifted (after `pip install -e '.[test]'`)               | `python -m vizops --check`                              | not run |
| unit suite                                                                                                | `pytest -q`                                             | not run |
| every scene reads, transcribes and lays out its real artifact (`estate` job; needs the sibling checkouts) | `python -m vizops`                                      | not run |
| the scenes against the real sibling artifacts (`estate` job)                                              | `pytest tests/test_estate.py -q`                        | not run |

## What this does *not* establish

<!--
Required. Name the bound.
 - A search that stopped at a limit says where it stopped.
 - A refusal is not a clean answer.
 - A test that could not run is not a test that passed.
 - Claim exactly what the run, the proof or the certificate establishes — no more.
Write "nothing outstanding" only if that is true.
-->

## Risk and reversibility

<!-- What breaks if this is wrong, and how it is backed out. -->

## Checklist

- [ ] The gates above were run, and the table says honestly which were not.
- [ ] New behaviour is covered by a test that fails without this change.
- [ ] Generated artifacts were regenerated with their tooling, never hand-edited.
- [ ] Documentation and status surfaces that name this behaviour were updated in this PR.
- [ ] No secret, token or credential is in the diff.
- [ ] The repository's standing prohibitions (see `AGENTS.md` / `CONTRIBUTING.md`) still hold.
