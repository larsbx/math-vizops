"""`python -m vizops` -- report on every scene, check the surfaces, render.

    python -m vizops                    what each scene would draw, or why not
    python -m vizops --check            README and wiki pages have not drifted
    python -m vizops --write            regenerate their generated blocks
    python -m vizops render [ID ...]    render with manimgl
    python -m vizops still [ID ...]     the last frame, into wiki/images/
    python -m vizops page [ID ...]      self-contained HTML pages, into out/
    python -m vizops site              complete generated-only deployment bundle
    python -m vizops wiki --publish     mirror wiki/ to the GitHub wiki

The report needs no renderer, which is the point: it reads every artifact,
refuses every malformed one and names what it found, on a machine with no GL
context. Its exit code is 1 if any scene was refused and 0 otherwise -- the
renderer's absence is reported, not scored, because the report did not try to
render anything.

`render`, `still` and `page` score what they did try: 0 all produced, 1 something was
refused, 2 nothing reached a verdict.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import subprocess
from pathlib import Path
from typing import Sequence

from . import surfaces, wiki
from .bridge import DEFAULT_OUT, QUALITIES, REFUSALS, figure, render, renderer, root, still
from .outcome import Outcome, Refused, worst
from .sources import MANIFEST, Page, Scene, SourceError, load, pages
from .wake.scene import WakeCycleFigure

STILLS = surfaces.WIKI / surfaces.IMAGES
#: The packages a `[[page]]` may name as its builder, each exporting `build`.
BUILDERS = ("atlas", "wake", "bulbs", "rauzy")


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
        print(f"ready     {scene.id}: {drawn.title}")
        print(f"          {drawn.provenance.stamp}")
        if isinstance(drawn, WakeCycleFigure):
            print(
                f"          {drawn.q}-cycle · θ₋={drawn.theta_minus}/{drawn.denominator} · "
                f"θ₊={drawn.theta_plus}/{drawn.denominator}\n"
            )
        else:
            classes = ", ".join(f"{t.name} ({len(drawn.members()[t.id])})" for t in drawn.populated())
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


def build_page(page: Page, sources: Path, *, dataset: Path | None, out: Path) -> Outcome:
    if page.builder not in BUILDERS:
        return Refused(page.id, f"no builder named {page.builder!r}; have {', '.join(BUILDERS)}")
    # A builder is imported only when asked for, so a scene run never loads a tracer.
    build = importlib.import_module(f".{page.builder}", __package__).build
    return build(page, sources, dataset=dataset, out=out / f"{page.id}.html")


def publish(remote: str, dry_run: bool) -> int:
    try:
        print(wiki.publish(remote, dry_run=dry_run))
    except wiki.PublishError as refusal:
        print(refusal, file=sys.stderr)
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vizops", description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="report", choices=("report", "render", "still", "page", "site", "wiki"))
    parser.add_argument("ids", nargs="*", help="scene or page ids; all of them by default")
    parser.add_argument("--sources", type=Path, default=None, help="directory holding the sibling checkouts")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where manimgl and `page` write")
    parser.add_argument("--into", type=Path, default=STILLS, help="where `still` files its images")
    parser.add_argument("--dataset", type=Path, default=None,
                        help="with `page mandelbrot-atlas`: the emitter's JSON, instead of running it with pixi")
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

    if args.command == "site":
        from .site import build
        if args.ids or args.dataset:
            parser.error("site builds the complete registry from upstream emitters")
        try:
            return build(root(args.sources), args.out, quality=args.quality)
        except (SourceError, OSError, subprocess.CalledProcessError) as error:
            print(f"refused site: {error}", file=sys.stderr)
            return 1

    targets = pages() if args.command == "page" else scenes
    chosen = [t for t in targets if not args.ids or t.id in args.ids]
    unknown = set(args.ids) - {t.id for t in targets}
    if unknown:
        print(f"no such {'page' if args.command == 'page' else 'scene'}: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1
    if args.command == "page":
        outcomes = tuple(build_page(p, root(args.sources), dataset=args.dataset, out=args.out) for p in chosen)
        print("\n".join(map(str, outcomes)))
        return worst(outcomes)
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
