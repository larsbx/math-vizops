"""`python -m vizops` -- report on every scene, check the surfaces, render.

    python -m vizops                    what each scene would draw, or why not
    python -m vizops --check            README and wiki pages have not drifted
    python -m vizops --write            regenerate their generated blocks
    python -m vizops render [ID ...]    render with manimgl
    python -m vizops still [ID ...]     the last frame, into wiki/images/
    python -m vizops wiki --publish     mirror wiki/ to the GitHub wiki

The report needs no renderer, which is the point: it reads every artifact,
refuses every malformed one and names what it found, on a machine with no GL
context. Its exit code is 1 if any scene was refused and 0 otherwise -- the
renderer's absence is reported, not scored, because the report did not try to
render anything.

`render` and `still` score what they did try: 0 all produced, 1 something was
refused, 2 nothing reached a verdict.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import surfaces, wiki
from .bridge import DEFAULT_OUT, QUALITIES, REFUSALS, figure, render, renderer, root, still
from .outcome import worst
from .sources import MANIFEST, Scene, load

STILLS = surfaces.WIKI / surfaces.IMAGES


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


def check_surfaces(scenes: Sequence[Scene], write: bool) -> int:
    if write:
        written = surfaces.write(scenes)
        print("\n".join(f"wrote {p}" for p in written) or "nothing to write")
        return 0
    drift = surfaces.drifted(scenes)
    for path in drift:
        print(f"{path}: a generated block has drifted from its source; run `python -m vizops --write`")
    if not drift:
        print(f"{len(surfaces.surfaces())} surface(s) match {MANIFEST.name} and the modules they describe")
    return 1 if drift else 0


def publish(remote: str, dry_run: bool) -> int:
    try:
        print(wiki.publish(remote, dry_run=dry_run))
    except wiki.PublishError as refusal:
        print(refusal, file=sys.stderr)
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vizops", description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="report", choices=("report", "render", "still", "wiki"))
    parser.add_argument("ids", nargs="*", help="scene ids; all of them by default")
    parser.add_argument("--sources", type=Path, default=None, help="directory holding the sibling checkouts")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where manimgl writes")
    parser.add_argument("--into", type=Path, default=STILLS, help="where `still` files its images")
    parser.add_argument("--quality", default="medium", choices=tuple(QUALITIES))
    parser.add_argument("--check", action="store_true", help="every generated block matches its source")
    parser.add_argument("--write", action="store_true", help="regenerate every generated block")
    parser.add_argument("--remote", default=wiki.REMOTE, help="the wiki repository to publish to")
    parser.add_argument("--publish", action="store_true", help="with `wiki`: mirror wiki/ and push")
    parser.add_argument("--dry-run", action="store_true", help="with `wiki --publish`: stop before committing")
    args = parser.parse_args(argv)

    scenes = load()
    if args.check or args.write:
        return check_surfaces(scenes, args.write)
    if args.command == "wiki":
        if not args.publish:
            parser.error("`wiki` needs --publish (or use --check / --write for the pages themselves)")
        return publish(args.remote, args.dry_run)

    chosen = [s for s in scenes if not args.ids or s.id in args.ids]
    unknown = set(args.ids) - {s.id for s in scenes}
    if unknown:
        print(f"no such scene: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1
    if args.command == "report":
        return report(chosen, args.sources)
    if args.command == "still":
        outcomes = tuple(still(s, args.sources, into=args.into, quality=args.quality) for s in chosen)
        print("\n".join(map(str, outcomes)))
        print("\nCommit the images, then `python -m vizops --write` so the gallery embeds them.")
        return worst(outcomes)
    outcomes = tuple(render(s, args.sources, out=args.out, quality=args.quality) for s in chosen)
    print("\n".join(map(str, outcomes)))
    return worst(outcomes)


if __name__ == "__main__":
    raise SystemExit(main())
