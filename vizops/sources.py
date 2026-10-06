"""The registry of artifacts, and the fail-closed read of one.

`sources.toml` is the only place a scene's source is named. The README's table
is generated from it (`python -m vizops --write`) and CI fails if the two have
drifted, so there is one answer to "where does this figure come from".

A source is either a sibling checkout, read as it is today, or -- when its
entry names `vendored` -- a package copied byte-for-byte under `vendor/` and
pinned in `vendored.toml`, read from that copy and refused if the copy no
longer has its pinned digest. The second kind names the upstream repository
and path it was copied from, so the frame is still attributed upstream.

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
#: The vendoring manifest; package roots in it are relative to its directory.
VENDORED = Path(__file__).resolve().parents[1] / "vendored.toml"


class SourceError(ValueError):
    """The manifest is malformed, or an artifact is not where it says it is."""


@dataclass(frozen=True, slots=True)
class Copy:
    """One vendored file: where the copy is, what it was copied from, and its pin."""

    package: str
    repository: str
    commit: str
    local: Path
    digest: str


def pinned_copy(package: str, repo: str, path: str, manifest: Path | None = None) -> Copy:
    """The vendored copy of `repo`'s `path`, as `vendored.toml` pins it -- or a refusal.

    The upstream path is mapped to the copy at the package directory: the
    segment of `path` named `package` is where the copy's root begins, so
    `oracles/rational_dynamics_py/doubling.py` is `<root>/rational_dynamics_py/doubling.py`.
    """
    manifest = manifest or VENDORED
    try:
        entries = tomllib.loads(manifest.read_text(encoding="utf-8")).get("package", [])
    except (OSError, tomllib.TOMLDecodeError) as err:
        raise SourceError(f"{manifest.name} could not be read: {err}") from err
    entry = next((e for e in entries if isinstance(e, dict) and e.get("name") == package), None)
    if entry is None:
        raise SourceError(f"{manifest.name} vendors no package {package!r}")
    if entry.get("repository") != repo:
        raise SourceError(f"{manifest.name}: {package} is vendored from {entry.get('repository')}, not {repo}")
    parts = Path(path).parts
    if package not in parts:
        raise SourceError(f"{path} is not inside the vendored package {package}")
    rel = Path(*parts[parts.index(package):]).as_posix()
    digest = entry.get("files", {}).get(rel)
    if not digest:
        raise SourceError(f"{manifest.name}: {package} pins no {rel}")
    return Copy(package, repo, entry.get("commit", ""), manifest.parent / entry.get("root", ".") / rel, digest)


@dataclass(frozen=True, slots=True)
class Scene:
    id: str
    title: str
    repo: str
    path: str
    adapter: str
    scene: str
    note: str = ""
    #: The `vendored.toml` package the artifact is read from, instead of a checkout.
    vendored: str = ""

    @property
    def checkout(self) -> str:
        """The directory name a sibling checkout is expected to have."""
        return self.repo.split("/")[-1]

    def copy(self) -> Copy | None:
        """The pinned vendored copy this scene reads, or None for a checkout."""
        return pinned_copy(self.vendored, self.repo, self.path) if self.vendored else None

    def artifact(self, root: Path) -> Path:
        copy = self.copy()
        return copy.local if copy else Path(root) / self.checkout / self.path

    def read(self, root: Path) -> tuple[bytes, str]:
        """The artifact's bytes and their sha256, or a refusal that names the
        path that was looked for."""
        return read_artifact(self.id, self.repo, self.path, self.copy(), Path(root) / self.checkout)


def read_artifact(owner: str, repo: str, path: str, copy: Copy | None, checkout: Path) -> tuple[bytes, str]:
    """A checkout's file as it is, or a vendored copy that still has its pin."""
    where = copy.local if copy else checkout / path
    if not where.is_file():
        if copy:
            raise SourceError(f"{owner}: no vendored copy at {where}; it is pinned in {VENDORED.name}")
        raise SourceError(
            f"{owner}: no artifact at {where}. Expected a checkout of {repo} "
            f"at {checkout}; pass --sources to say where the estate is."
        )
    raw = where.read_bytes()
    if not raw:
        raise SourceError(f"{owner}: {where} is empty")
    digest = hashlib.sha256(raw).hexdigest()
    if copy and digest != copy.digest:
        raise SourceError(
            f"{owner}: {where} differs from {repo}@{copy.commit[:12]} as pinned in {VENDORED.name}; "
            "re-vendor it, never patch it"
        )
    return raw, digest


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
        scene = Scene(**entry)
        if scene.vendored:
            try:
                scene.copy()
            except SourceError as err:
                problems.append(f"scene {scene.id}: {err}")
                continue
        scenes.append(scene)
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
    #: Further files the page reads, as "owner/repo:path".
    also: tuple[str, ...] = ()
    #: Where a published copy of the page can be viewed, if anywhere.
    artifact: str = ""
    #: The `vendored.toml` package the page's own `path` is read from, instead
    #: of a checkout. `also` files are always read from checkouts.
    vendored: str = ""

    @property
    def checkout(self) -> str:
        return self.repo.split("/")[-1]

    def copy(self) -> Copy | None:
        """The pinned vendored copy the page's own path names, or None for a checkout."""
        return pinned_copy(self.vendored, self.repo, self.path) if self.vendored else None

    def read(self, root: Path) -> tuple[bytes, str]:
        """The page's own source, by the same rules as `Scene.read`."""
        return read_artifact(self.id, self.repo, self.path, self.copy(), Path(root) / self.checkout)

    def files(self) -> tuple[tuple[str, str], ...]:
        """Every (repo, path) the page reads, its own first."""
        return ((self.repo, self.path), *(tuple(entry.split(":", 1)) for entry in self.also))


def pages(manifest: Path = MANIFEST) -> tuple[Page, ...]:
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    fields = {f for f in Page.__dataclass_fields__}
    optional = {"task", "note", "also", "artifact", "vendored"}
    problems = [
        f"page {entry.get('id', i)}: needs {', '.join(sorted(fields - optional))}, "
        f"may have {', '.join(sorted(optional))}, and nothing else"
        for i, entry in enumerate(data.get("page", []))
        if not isinstance(entry, dict) or not set(entry) <= fields
        or any(not entry.get(f) for f in fields - optional)
        or any(":" not in e or "/" not in e.split(":", 1)[0] for e in entry.get("also", []))
    ]
    found = () if problems else tuple(
        Page(**{**entry, "also": tuple(entry.get("also", ()))}) for entry in data.get("page", []))
    for page in found:
        if page.vendored:
            try:
                page.copy()
            except SourceError as err:
                problems.append(f"page {page.id}: {err}")
    if problems:
        raise SourceError("\n  ".join((f"{manifest} refused:", *problems)))
    return found


def module(checkout: Path, path: str, *, raw: bytes | None = None) -> ModuleType:
    """A Python file from a sibling checkout, loaded where it lives.

    When raw is supplied, those exact bytes are compiled and executed. This
    lets a caller stamp the digest of the bytes that actually supplied its
    data, instead of reading once for provenance and reopening the path for
    execution. Module-execution failures are refusals; process-control
    exceptions such as KeyboardInterrupt and SystemExit still pass through.
    """
    source = Path(checkout) / path
    if raw is None:
        if not source.is_file():
            raise SourceError(f"no {path} in {checkout}")
        raw = source.read_bytes()
    if not raw:
        raise SourceError(f"{path} in {checkout} is empty")

    name = f"vizops_upstream.{Path(checkout).name}.{source.stem}"
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None:
        raise SourceError(f"could not create a module spec for {source}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded  # dataclasses resolve their annotations through here
    try:
        code = compile(raw, str(source), "exec", dont_inherit=True)
        exec(code, loaded.__dict__)
    except Exception as err:
        sys.modules.pop(name, None)
        raise SourceError(
            f"{path} in {checkout} could not be loaded: {type(err).__name__}: {err}"
        ) from err
    return loaded


def by_id(scenes: tuple[Scene, ...] = ()) -> Mapping[str, Scene]:
    return {s.id: s for s in (scenes or load())}
