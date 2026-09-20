# Why it refuses

vizops declines to draw rather than drawing something misleading. Each
refusal below is a case the test suite feeds a known-bad input to, so the
check is known to fire rather than assumed to.

One refusal names **every** problem it found, so a malformed artifact takes
one run to diagnose rather than one run per defect.

## Reading the artifact

| Message | What happened | Fix |
| --- | --- | --- |
| `no artifact at …` | The checkout is not where vizops looked. | Clone the sibling beside this repository, or pass `--sources` / set `$VIZOPS_SOURCES`. |
| `… is empty` | The file is there and has no bytes. | Regenerate it upstream. An empty frame is worse than no frame. |
| `format is 'x', expected 'y'` | The artifact's declared format is not the one this adapter reads. | Update the adapter deliberately, or point the scene at the right artifact. A file that changed shape is not a file to guess at. |
| `lacks provenance_classes, edge_types` | The artifact does not declare its own vocabulary. | Declare it upstream. vizops will not invent a class list. |

## Building the figure

| Message | What happened | Fix |
| --- | --- | --- |
| `term 'x' is not one the source declares` | A node is in a class its own file never declared. | Declare the class upstream, or fix the node. |
| `'X' is not a node in this figure` | An edge points at something that is not there. | A dangling reference in the artifact — fix it upstream; it is a defect in the data, not in the picture. |
| `kind 'x' is not one the source declares` | An edge type outside the declared `edge_types`. | Same: declare it or fix it. |
| `an edge from a node to itself` | A self-loop. | Usually a `related` entry naming its own object. |
| `declared twice` | Two terms, nodes or edge kinds share an id. | Upstream duplicate. |
| `no nodes` / `no terms` | The artifact parsed and describes nothing. | An empty frame is not a render. |

## Drawing it

| Message | What happened | Fix |
| --- | --- | --- |
| `N classes and 8 hues: a ninth hue is not generated` | More declared classes than the palette has slots. | Fold the tail into one class at the source, or split the figure. Generating a ninth hue would put two classes a reader cannot separate on one frame. |
| `no members for x` | A column was requested for a class with nothing in it. | Internal: `Figure.populated()` decides what is on the frame. |
| `manimgl exited N: …` | The renderer started and died; its last lines are quoted. | Usually a missing GL context or Pango — see [[Rendering and viewing]]. |

## Not refusals

`no manimgl on PATH`, a timeout, and a clean exit that wrote no file are
**inconclusive**, not refused. Nothing was shown either way. See [[Outcomes]].
