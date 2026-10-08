"""Every surface that is generated rather than written, and the check that
says none of them has drifted.

The README and the wiki say some of the same things -- which scenes exist,
what the three outcomes mean, what each module is for. Two hand-maintained
copies of one fact is the drift this estate's first ruling is about, so those
passages are not written twice: each is rendered here from the one place that
holds it (`sources.toml`, `outcome.MEANING`, the modules' own docstrings) and
spliced into both surfaces between markers.

`python -m vizops --check` fails if a surface no longer matches what this
module renders; `--write` regenerates them. Editing between the markers by
hand is a change CI reverts, because the fact lives upstream of the prose.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .outcome import EXIT_CODES, MEANING
from .sources import Scene, load, pages

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WIKI = ROOT / "wiki"
IMAGES = "images"
#: Modules in reading order, for the map both surfaces show.
MODULES = (
    "sources.py", "adapters.py", "figure.py", "layout.py",
    "palette.py", "outcome.py", "bridge.py", "scenes.py", "surfaces.py", "wiki.py",
    "atlas/build.py", "atlas/trace.py", "wake/build.py", "wake/scene.py", "bulbs/build.py",
    "rauzy/build.py",
)


class DriftError(ValueError):
    """A surface lacks the markers a generated block needs."""


@dataclass(frozen=True, slots=True)
class Block:
    """One generated passage, named by the marker pair that delimits it."""

    name: str
    source: str
    render: Callable[[Sequence[Scene]], str]

    @property
    def begin(self) -> str:
        return f"<!-- BEGIN generated {self.name} (python -m vizops --write); do not edit between the markers -->"

    @property
    def end(self) -> str:
        return f"<!-- END generated {self.name} -->"

    def fragment(self, scenes: Sequence[Scene]) -> str:
        return "\n".join((self.begin, f"<!-- Rendered by vizops/surfaces.py from {self.source}. -->",
                          "", self.render(scenes), "", self.end))

    def splice(self, text: str, scenes: Sequence[Scene]) -> str:
        start, stop = text.find(self.begin), text.find(self.end)
        if start < 0 or stop < 0:
            raise DriftError(f"the {self.name} block's markers are missing")
        return text[:start] + self.fragment(scenes) + text[stop + len(self.end):]

    def present_in(self, text: str) -> bool:
        return self.begin in text


def source_link(repo: str, path: str, pinned=None) -> str:
    """A link to what is read: a file on `main` for a checkout, the package
    directory at its pinned commit for a vendored package, which is what was
    drawn whatever `main` says today."""
    if pinned:
        return (f"[`{path}`](https://github.com/{repo}/tree/{pinned.commit}/{path}) in `{repo}` "
                f"(vendored at `{pinned.commit[:12]}`)")
    return f"[`{path}`](https://github.com/{repo}/blob/main/{path}) in `{repo}`"


def scene_table(scenes: Sequence[Scene]) -> str:
    rows = [
        "| Scene | Draws | Source surface | manim scene |",
        "| --- | --- | --- | --- |",
        *(f"| `{s.id}` | {s.title} | {source_link(s.repo, s.path, s.pin())} | `{s.scene}` |" for s in scenes),
    ]
    return "\n".join(rows)


def outcome_table(_: Sequence[Scene] = ()) -> str:
    rows = ["| Outcome | Exit | When |", "| --- | ---: | --- |"]
    rows += [f"| `{verdict}` | {code} | {MEANING[verdict]} |" for verdict, code in sorted(EXIT_CODES.items(), key=lambda kv: kv[1])]
    return "\n".join(rows)


def module_table(_: Sequence[Scene] = ()) -> str:
    """Each module's own opening line, so the map cannot describe a module
    as something other than what the module says it is."""
    rows = ["| Module | Holds |", "| --- | --- |"]
    for name in MODULES:
        rows.append(f"| `vizops/{name}` | {_summary(Path(__file__).parent / name)} |")
    return "\n".join(rows)


def gallery(scenes: Sequence[Scene]) -> str:
    """One section per scene, with its still if one has been published.

    A still is a file in the repository, so what this renders is a fact about
    the checkout and `--check` can hold it. An unrendered scene says so in
    words rather than showing a broken image.
    """
    out: list[str] = []
    for scene in scenes:
        still = WIKI / IMAGES / f"{scene.id}.png"
        out += [f"### {scene.title}", "",
                f"`{scene.scene}` — drawn from {source_link(scene.repo, scene.path, scene.pin())}.", ""]
        out += ([f"![{scene.title}]({IMAGES}/{scene.id}.png)"] if still.is_file() else
                [f"_No still published yet._ Run `python -m vizops still {scene.id}` "
                 f"and commit `wiki/{IMAGES}/{scene.id}.png`."])
        out += [""]
        if scene.note:
            out += [f"> {scene.note}", ""]
    return "\n".join(out).rstrip()


def page_gallery(_: Sequence[Scene] = ()) -> str:
    """One section per page: how to build it, what it reads, where a published
    copy lives, and its still if one has been committed."""
    out: list[str] = []
    for page in pages():
        still = WIKI / IMAGES / f"{page.id}.png"
        read = ", ".join(source_link(repo, path, page.pin() if i == 0 else None)
                         for i, (repo, path) in enumerate(page.files()))
        out += [f"### {page.title}", "", f"`python -m vizops page {page.id}` — reads {read}.", ""]
        if page.artifact:
            out += [f"**View it:** [{page.title}]({page.artifact}) — a published build, private to its owner "
                    "until shared.", ""]
        out += ([f"![{page.title}]({IMAGES}/{page.id}.png)"] if still.is_file() else
                [f"_No still published yet._ Build the page, capture it, and commit `wiki/{IMAGES}/{page.id}.png`."])
        out += [""]
        if page.note:
            out += [f"> {page.note}", ""]
    return "\n".join(out).rstrip()


BLOCKS = (
    Block("scene table", "vizops/sources.toml", scene_table),
    Block("outcome table", "EXIT_CODES and MEANING in vizops/outcome.py", outcome_table),
    Block("module table", "each module's own docstring", module_table),
    Block("gallery", "vizops/sources.toml and the stills in wiki/images/", gallery),
    Block("page gallery", "the [[page]] entries in vizops/sources.toml and the stills in wiki/images/", page_gallery),
)


def surfaces() -> tuple[Path, ...]:
    """The README and every wiki page, in a stable order."""
    return (README, *sorted(WIKI.glob("*.md"))) if WIKI.is_dir() else (README,)


def rendered(path: Path, scenes: Sequence[Scene] | None = None) -> str:
    """What `path` should contain: its own prose, with every block it carries
    regenerated. A surface that carries no block is returned unchanged."""
    scenes = load() if scenes is None else scenes
    text = path.read_text(encoding="utf-8")
    for block in BLOCKS:
        if block.present_in(text):
            text = block.splice(text, scenes)
    return text


def drifted(scenes: Sequence[Scene] | None = None) -> tuple[Path, ...]:
    scenes = load() if scenes is None else scenes
    return tuple(p for p in surfaces() if p.read_text(encoding="utf-8") != rendered(p, scenes))


def write(scenes: Sequence[Scene] | None = None) -> tuple[Path, ...]:
    scenes = load() if scenes is None else scenes
    written = drifted(scenes)
    for path in written:
        path.write_text(rendered(path, scenes), encoding="utf-8")
    return written


def _summary(path: Path) -> str:
    """The opening paragraph of a module's docstring, read rather than
    imported -- so the map renders on a machine with no manimlib."""
    if not path.is_file():
        return "—"
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    return " ".join(doc.split("\n\n")[0].split()) or "—"

