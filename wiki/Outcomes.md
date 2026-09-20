# Outcomes

A render run reports one of three things, and the set is closed — a fourth
outcome has to be declared in `vizops/outcome.py` beside the exit codes, where
CI can be taught what it means, rather than invented at a call site.

<!-- BEGIN generated outcome table (python -m vizops --write); do not edit between the markers -->
<!-- Rendered by vizops/surfaces.py from EXIT_CODES and MEANING in vizops/outcome.py. -->

| Outcome | Exit | When |
| --- | ---: | --- |
| `rendered` | 0 | A file exists, and the outcome carries its digest. |
| `refused` | 1 | The source is missing, empty, of an unknown format, or describes a figure the type refuses -- or the renderer died. Nothing was drawn, on purpose. |
| `inconclusive` | 2 | No verdict was reached: no `manimgl` on PATH, no GL context, a timeout, or a clean exit that wrote no file. |

<!-- END generated outcome table -->

## Why the third one exists

A machine with no `manimgl`, no GL context, or a renderer that hung has not
shown that a scene is broken and has not shown that it works. Scoring that
`rendered` is a verdict the run did not reach; scoring it `refused` is a
different verdict it did not reach either. So it has its own name and its own
exit code, and a CI job can tell "this scene is wrong" from "this machine
cannot answer".

This is the estate's P3 — *inconclusive is a third outcome* — in the one place
in this repository where a run can fail to reach a verdict at all.

## Fail-closed has a direction

The two non-zero codes are not the same direction:

* **Refused (1)** — vizops declined to draw. A missing artifact, an empty one,
  an unknown declared format, a node in an undeclared class, an edge to a node
  that is not there, more classes than the palette has hues. Nothing is drawn,
  and nothing that looks like evidence is produced. See [[Why it refuses]].
* **Inconclusive (2)** — nothing was shown either way. No renderer, a timeout,
  or a clean exit that wrote no file.

`python -m vizops` — the report — scores only what it tried: it reads every
artifact and exits 1 if any was refused, 0 otherwise. The renderer's absence
is *reported* there, not scored, because the report never tried to render.

## What a run of scenes scores

The worst outcome wins, and a run with nothing in it is inconclusive rather
than clean — an empty pass is the failure mode this whole file exists to
avoid.
