"""The registry of artifacts, and the fail-closed read of one.

`sources.toml` is the only place a scene's source is named. The README's table
is generated from it (`python -m vizops --write`) and CI fails if the two have
drifted, so there is one answer to "where does this figure come from".

Reading is fail-closed in one direction only: a missing or unreadable artifact
is a refusal, never an empty figure and never a placeholder. A frame that
silently depicts nothing is worse than no frame, because it still looks like
evidence.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Mapping

MANIFEST = Path(__file__).resolve().parent / "sources.toml"
FORMAT = "vizops sources 1"
#: Where sibling checkouts live, relative to this repository's own root.
DEFAULT_ROOT = Path(__file__).resolve().parents[2]


class SourceError(ValueError):
    """The manifest is malformed, or an artifact is not where it says it is."""


@dataclass(frozen=True, slots=True)
class Scene:
    id: str
    title: str
    repo: str
    path: str
    adapter: str
    scene: str
    note: str = ""

    @property
    def checkout(self) -> str:
        """The directory name a sibling checkout is expected to have."""
        return self.repo.split("/")[-1]

    def artifact(self, root: Path) -> Path:
        return Path(root) / self.checkout / self.path

    def read(self, root: Path) -> tuple[bytes, str]:
        """The artifact's bytes and their sha256, or a refusal that names the
        path that was looked for."""
        path = self.artifact(root)
        if not path.is_file():
            raise SourceError(
                f"{self.id}: no artifact at {path}. Expected a checkout of {self.repo} "
                f"at {Path(root) / self.checkout}; pass --sources to say where the estate is."
            )
        raw = path.read_bytes()
        if not raw:
            raise SourceError(f"{self.id}: {path} is empty")
        return raw, hashlib.sha256(raw).hexdigest()


def load(manifest: Path = MANIFEST) -> tuple[Scene, ...]:
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    if data.get("format") != FORMAT:
        raise SourceError(f"{manifest}: format is {data.get('format')!r}, expected {FORMAT!r}")
    entries = data.get("scene", [])
    problems: list[str] = []
    scenes: list[Scene] = []
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"scene {i}: not a table")
            continue
        missing = [f for f in ("id", "title", "repo", "path", "adapter", "scene") if not entry.get(f)]
        if missing:
            problems.append(f"scene {entry.get('id', i)}: lacks {', '.join(missing)}")
            continue
        unknown = set(entry) - {f.name for f in Scene.__dataclass_fields__.values()}
        if unknown:
            problems.append(f"scene {entry['id']}: unknown field(s) {', '.join(sorted(unknown))}")
            continue
        if entry["id"] in seen:
            problems.append(f"scene {entry['id']}: declared twice")
        seen.add(entry["id"])
        scenes.append(Scene(**entry))
    if not scenes and not problems:
        problems.append(f"{manifest}: no scenes")
    if problems:
        raise SourceError("\n  ".join((f"{manifest} refused:", *problems)))
    return tuple(scenes)


@dataclass(frozen=True, slots=True)
class Page:
    """A self-contained HTML surface, built by the named builder from code or
    output that its own repository owns -- never from a copy of either."""

    id: str
    title: str
    repo: str
    path: str
    builder: str
    task: str = ""
    note: str = ""

    @property
    def checkout(self) -> str:
        return self.repo.split("/")[-1]


def pages(manifest: Path = MANIFEST) -> tuple[Page, ...]:
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    fields = {f for f in Page.__dataclass_fields__}
    optional = {"task", "note"}
    problems = [
        f"page {entry.get('id', i)}: needs {', '.join(sorted(fields - optional))}, "
        f"may have {', '.join(sorted(optional))}, and nothing else"
        for i, entry in enumerate(data.get("page", []))
        if not isinstance(entry, dict) or not set(entry) <= fields
        or any(not entry.get(f) for f in fields - optional)
    ]
    if problems:
        raise SourceError("\n  ".join((f"{manifest} refused:", *problems)))
    return tuple(Page(**entry) for entry in data.get("page", []))


def module(checkout: Path, path: str) -> ModuleType:
    """A Python file from a sibling checkout, loaded where it lives.

    Borrowing upstream's own code is how a page answers an exact question
    without a second implementation here to disagree with it.
    """
    source = Path(checkout) / path
    if not source.is_file():
        raise SourceError(f"no {path} in {checkout}")
    spec = importlib.util.spec_from_file_location(f"vizops_upstream.{Path(checkout).name}.{source.stem}", source)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded  # dataclasses resolve their annotations through here
    spec.loader.exec_module(loaded)
    return loaded


def by_id(scenes: tuple[Scene, ...] = ()) -> Mapping[str, Scene]:
    return {s.id: s for s in (scenes or load())}
