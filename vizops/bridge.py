"""Artifact to figure, and figure to file.

The first half needs no renderer: `figure` reads an artifact, refuses a
malformed one and hands back the laid-out content. That is what CI runs, and
it is where every interesting failure lives.

The second half shells out to `manimgl` (3b1b/manim). It is a subprocess and
not an import on purpose -- the renderer owns a window, a GL context and its
own CLI, and a machine without one is a machine that reaches no verdict rather
than one that fails.

Fail-closed has a direction here, and the two directions are different:

*   A source that is missing, empty, in an unknown format, or that describes a
    figure the type refuses is a **refusal** (exit 1). Nothing is drawn.
*   A renderer that is absent, that times out, or that exits clean without
    writing a file is **inconclusive** (exit 2). Nothing was shown either way.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from .adapters import ADAPTERS, AdapterError
from .figure import Figure, FigureError, Provenance
from .outcome import Inconclusive, Outcome, Refused, Rendered
from .palette import PaletteError, assign
from .sources import DEFAULT_ROOT, Scene, SourceError, by_id, load

SCENES = Path(__file__).resolve().parent / "scenes.py"
ENV_ROOT = "VIZOPS_SOURCES"
DEFAULT_OUT = Path("out")
QUALITIES = {"low": "-l", "medium": "-m", "high": "--hd", "uhd": "--uhd"}
#: Anything vizops raises when it declines to draw.
REFUSALS = (SourceError, AdapterError, FigureError, PaletteError)


def root(explicit: Path | None = None) -> Path:
    """Where the sibling checkouts are: the flag, then `VIZOPS_SOURCES`, then
    the directory this repository sits in."""
    return Path(explicit or os.environ.get(ENV_ROOT) or DEFAULT_ROOT)


def figure(scene: Scene, sources: Path | None = None) -> Figure:
    """Read the artifact, transcribe it, and check it can be drawn -- or raise
    one of `REFUSALS`."""
    adapter = ADAPTERS.get(scene.adapter)
    if adapter is None:
        raise SourceError(f"{scene.id}: no adapter named {scene.adapter!r}; have {', '.join(sorted(ADAPTERS))}")
    raw, digest = scene.read(root(sources))
    drawn = adapter(raw, Provenance(scene.repo, scene.path, digest, scene.note), scene.title)
    assign(tuple(t.id for t in drawn.terms))  # a figure with more classes than hues is refused here,
    return drawn                              # where the message is readable, not inside the renderer


def figure_for(source_id: str, sources: Path | None = None) -> Figure:
    """The figure a `scenes.py` class draws. Kept here so the scene file holds
    no policy: a scene knows its id and nothing else about where data lives."""
    scenes = by_id(load())
    if source_id not in scenes:
        raise SourceError(f"no scene {source_id!r} in sources.toml; have {', '.join(scenes)}")
    return figure(scenes[source_id], sources)


def renderer() -> str | None:
    """The `manimgl` executable, or None on a machine that has none."""
    from shutil import which

    return which("manimgl")


def render(
    scene: Scene,
    sources: Path | None = None,
    *,
    out: Path = DEFAULT_OUT,
    quality: str = "medium",
    timeout: float = 900.0,
) -> Outcome:
    try:
        figure(scene, sources)  # refuse before starting a renderer, not after
    except REFUSALS as refusal:
        return Refused(scene.id, str(refusal))
    if quality not in QUALITIES:
        return Refused(scene.id, f"quality {quality!r} is not one of {', '.join(QUALITIES)}")
    exe = renderer()
    if exe is None:
        return Inconclusive(scene.id, "no manimgl on PATH; `pip install 'vizops[render]'` and run again")
    out.mkdir(parents=True, exist_ok=True)
    before = {p: p.stat().st_mtime for p in out.rglob("*") if p.is_file()}
    argv = [exe, str(SCENES), scene.scene, "-w", QUALITIES[quality], "--video_dir", str(out)]
    env = {**os.environ, ENV_ROOT: str(root(sources))}
    try:
        done = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Inconclusive(scene.id, f"manimgl did not finish within {timeout:g}s; no frame was produced or refused")
    if done.returncode != 0:
        return Refused(scene.id, f"manimgl exited {done.returncode}: {_tail(done.stderr)}")
    written = [p for p in out.rglob("*") if p.is_file() and before.get(p) != p.stat().st_mtime]
    if not written:
        return Inconclusive(scene.id, f"manimgl exited 0 and wrote nothing under {out}")
    newest = max(written, key=lambda p: p.stat().st_mtime)
    return Rendered(scene.id, str(newest), hashlib.sha256(newest.read_bytes()).hexdigest())


def _tail(text: str, lines: int = 3) -> str:
    kept = [line for line in text.strip().splitlines() if line.strip()][-lines:]
    return " / ".join(kept) or "no output on stderr"
