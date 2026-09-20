"""`python -m vizops` -- report on every scene, check the README, or render.

    python -m vizops                    what each scene would draw, or why not
    python -m vizops --check            the README's table has not drifted
    python -m vizops --write            regenerate it from sources.toml
    python -m vizops render [ID ...]    render with manimgl

The report needs no renderer, which is the point: it reads every artifact,
refuses every malformed one and names what it found, on a machine with no GL
context. Its exit code is 1 if any scene was refused and 0 otherwise -- the
renderer's absence is reported, not scored, because the report did not try to
render anything.

`render` scores what it did try: 0 all rendered, 1 something was refused,
2 nothing reached a verdict.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .outcome import worst
from .bridge import QUALITIES, REFUSALS, DEFAULT_OUT, figure, render, renderer, root
from .sources import MANIFEST, Scene, load

README = Path(__file__).resolve().parents[1] / "README.md"
BEGIN = "<!-- BEGIN generated scene table (python -m vizops --write); do not edit between the markers -->"
END = "<!-- END generated scene table -->"


def table(scenes: Sequence[Scene]) -> str:
    rows = [
        BEGIN,
        f"<!-- Generated from {MANIFEST.name} by `python -m vizops --write`. -->",
        "",
        "| Scene | Draws | Source artifact | manim scene |",
        "| --- | --- | --- | --- |",
        *(f"| `{s.id}` | {s.title} | [`{s.path}`](https://github.com/{s.repo}/blob/main/{s.path}) "
          f"in `{s.repo}` | `{s.scene}` |" for s in scenes),
        "",
        END,
    ]
    return "\n".join(rows)


def splice(text: str, fragment: str) -> str:
    start, stop = text.find(BEGIN), text.find(END)
    if start < 0 or stop < 0:
        raise SystemExit(f"{README}: the generated scene table's markers are missing")
    return text[:start] + fragment + text[stop + len(END):]


def report(scenes: Sequence[Scene], sources: Path | None) -> int:
    print(f"sources: {root(sources)}\n")
    refused = 0
    for scene in scenes:
        try:
            drawn = figure(scene, sources)
        except REFUSALS as refusal:
            refused += 1
            print(f"refused   {scene.id}\n  {refusal}\n")
            continue
        classes = ", ".join(f"{t.name} ({len(drawn.members()[t.id])})" for t in drawn.populated())
        print(f"ready     {scene.id}: {drawn.title}")
        print(f"          {drawn.provenance.stamp}")
        print(f"          {len(drawn.nodes)} nodes, {len(drawn.edges)} edges · {classes}\n")
    exe = renderer()
    print(f"renderer: {exe or 'absent — `render` would report inconclusive, not failure'}")
    return 1 if refused else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vizops", description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="report", choices=("report", "render"))
    parser.add_argument("ids", nargs="*", help="scene ids; all of them by default")
    parser.add_argument("--sources", type=Path, default=None, help="directory holding the sibling checkouts")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where manimgl writes")
    parser.add_argument("--quality", default="medium", choices=tuple(QUALITIES))
    parser.add_argument("--check", action="store_true", help="the README table matches sources.toml")
    parser.add_argument("--write", action="store_true", help="regenerate the README table")
    args = parser.parse_args(argv)

    scenes = load()
    if args.check or args.write:
        wanted = splice(README.read_text(encoding="utf-8"), table(scenes))
        if args.write:
            README.write_text(wanted, encoding="utf-8")
            print(f"wrote {README}")
            return 0
        if README.read_text(encoding="utf-8") != wanted:
            print(f"{README}: the scene table has drifted from {MANIFEST.name}; run `python -m vizops --write`")
            return 1
        print(f"{README}: scene table matches {MANIFEST.name}")
        return 0

    chosen = [s for s in scenes if not args.ids or s.id in args.ids]
    unknown = set(args.ids) - {s.id for s in scenes}
    if unknown:
        print(f"no such scene: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1
    if args.command == "report":
        return report(chosen, args.sources)
    outcomes = tuple(render(s, args.sources, out=args.out, quality=args.quality) for s in chosen)
    for outcome in outcomes:
        print(outcome)
    return worst(outcomes)


if __name__ == "__main__":
    raise SystemExit(main())
