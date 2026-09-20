# Reading a frame

Every scene draws the same anatomy, so a frame from a new scene is readable
without learning a new convention.

```
 Title of the figure
                        Class A          Class B          Class C     <- column headers,
                                                                         the source's own words
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │ node label   │  │ node label   │  │ node label   │            <- one box per node
      │ BADGE        │  │ BADGE        │  │ BADGE        │            <- the source's own status word
      └──────────────┘  └──────────────┘  └──────────────┘
              ╲               │
               ╲──────────────┤                                       <- wires: solid and dashed
                              │                                          per the edge key

 repo/path @ sha256:0123abcd…                       solid: implicative · dashed: part-whole
 derived surface — depicts the source at this digest; authorizes nothing
```

## The column is the class

One column per class the source declares, left to right in the order the file
declares them. Class membership is carried by **position first**, then by the
column header, then by colour. Take the colour away and the frame still reads
— that is deliberate, and it is why colour is never asked to mean anything on
its own. See [[Design notes]].

A declared class with no members keeps its colour and leaves the frame, so a
class losing its last member never repaints the classes that stayed.

## The badge is the source's word

The smaller line inside a box is a field of the artifact, printed verbatim:
`SCAFFOLDED`, `open-boundary`, `definition`. vizops does not interpret it,
rank it, or map it onto another repository's vocabulary. Where a column is too
dense for a second line to be legible, the badge is dropped rather than
overlapped — an unreadable label is a node the frame claims to show and does
not.

## The wires

Edges are drawn once per pair, in the kinds the source declares. The key in
the bottom-right names which line style is which; only the kinds actually on
the frame appear in it, because a key listing seven unused edge types tells a
reader nothing.

## The stamp, and what it does not claim

The bottom-left carries the repository, the path, and the **sha256 of the
exact bytes the figure was built from**, followed by:

> derived surface — depicts the source at this digest; authorizes nothing

A rendered animation is evidence of what one artifact said at one digest. It
is not evidence that a claim is true, that a census ran, or that anything was
accepted. Promotion from evidence to finding happens in the repositories that
own the claims — `proof_records` and `claim_governance` — by an attributable
act. A video cannot take part in that, and this repository is shaped so that
it cannot look as though it did.

Nothing is pinned. vizops draws whatever the checkout says today; the digest
is what makes the frame a statement about one revision rather than a claim
that the revision is current.
