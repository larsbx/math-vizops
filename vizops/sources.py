"""The registry of artifacts, and the fail-closed read of one.

`sources.toml` is the only place a scene's source is named. The README's table
is generated from it (`python -m vizops --write`) and CI fails if the two have
drifted, so there is one answer to "where does this figure come from".

A source is either a sibling checkout, read as it is today, or -- when its
entry names `vendored` -- a package copied byte-for-byte under `vendor/` and
pinned in `vendored.toml`. `vendored_package` is the only way vizops reaches
such a package: it imports it, checks every pinned file where the import found
it, and refuses on any drift. Such an entry names the upstream repository and
package directory it was copied from, so the frame is still attributed
upstream, and its digest covers the package's whole pinned file set.

Reading is fail-closed in one direction only: a missing or unreadable artifact
is a refusal, never an empty figure and never a placeholder. A frame that
silently depicts nothing is worse than no frame, because it still looks like
evidence.
"""

from __future__ import annotations

import hashlib
import importlib
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
#: The vendoring manifest. In the source tree it is the repository root's
#: `vendored.toml`, the single copy. An installed wheel has no repository root,
#: so the build copies that file to `vizops/vendored.toml` (`setup.py`,
#: `build_py`); the source tree never holds that second copy.
_PACKAGED = Path(__file__).resolve().parent / "vendored.toml"
VENDORED = _PACKAGED if _PACKAGED.is_file() else Path(__file__).resolve().parents[1] / "vendored.toml"


class SourceError(ValueError):
    """The manifest is malformed, or an artifact is not where it says it is."""


@dataclass(frozen=True, slots=True)
class Pin:
    """One `vendored.toml` entry: the upstream commit and every pinned file."""

    name: str
    repository: str
    commit: str
    #: (path relative to the directory holding the package, sha256), sorted.
    files: tuple[tuple[str, str], ...]


def pin(name: str, manifest: Path | None = None) -> Pin:
    """The pins `vendored.toml` records for package `name`, or a refusal."""
    manifest = manifest or VENDORED
    try:
        entries = tomllib.loads(manifest.read_text(encoding="utf-8")).get("package", [])
    except (OSError, tomllib.TOMLDecodeError) as err:
        raise SourceError(f"{manifest.name} could not be read: {err}") from err
    entry = next((e for e in entries if isinstance(e, dict) and e.get("name") == name), None)
    if entry is None:
        raise SourceError(f"{manifest.name} vendors no package {name!r}")
    files = entry.get("files") or {}
    if not files or not entry.get("repository") or not entry.get("commit"):
        raise SourceError(f"{manifest.name}: {name} lacks a repository, a commit or pinned files")
    return Pin(name, entry["repository"], entry["commit"], tuple(sorted(files.items())))


@dataclass(frozen=True, slots=True)
class Vendored:
    """A vendored package, imported, with every pinned file checked where it was imported from."""

    pin: Pin
    module: ModuleType

    @property
    def listing(self) -> bytes:
        """The verified file set, in `sha256sum` form: the bytes `digest` is over."""
        return "".join(f"{digest}  {rel}\n" for rel, digest in self.pin.files).encode("utf-8")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.listing).hexdigest()


def vendored_package(name: str, manifest: Path | None = None) -> Vendored:
    """Import vendored package `name` and verify all of it against its pins -- or refuse.

    Each pinned path is resolved against the directory that holds the package
    Python actually imported (`vendor/python/` in the source tree,
    `site-packages/` in a wheel), so what is checked is what runs, wherever it
    was installed and whatever else is on the path. A missing file, a digest
    that is not the pinned one, or an unpinned source file inside the package
    is a refusal.
    """
    pinned = pin(name, manifest)
    try:
        loaded = importlib.import_module(name)
    except ImportError as err:
        raise SourceError(f"vendored package {name} could not be imported: {err}") from err
    if not getattr(loaded, "__file__", None):
        raise SourceError(f"vendored package {name} has no location to check")
    package_dir = Path(loaded.__file__).resolve().parent
    base = package_dir.parent
    problems: list[str] = []
    for rel, want in pinned.files:
        path = base / rel
        if not path.is_file():
            problems.append(f"{rel} is missing at {path}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != want:
            problems.append(f"{rel} at {path} differs from {pinned.repository}@{pinned.commit[:12]}")
    listed = {rel for rel, _ in pinned.files}
    problems += [f"{p.relative_to(base).as_posix()} is not pinned" for p in sorted(package_dir.rglob("*.py"))
                 if p.relative_to(base).as_posix() not in listed]
    if problems:
        raise SourceError("\n  ".join((f"vendored package {name} refused (pinned in {VENDORED.name}; "
                                        "re-vendor it, never patch it):", *problems)))
    return Vendored(pinned, loaded)


def _entry_pin(owner: str, vendored: str, repo: str, path: str) -> Pin:
    """The pin a `vendored = ...` entry names, checked against its repo and path."""
    found = pin(vendored)
    if found.repository != repo:
        raise SourceError(f"{owner}: {vendored} is vendored from {found.repository}, not {repo}")
    if Path(path).name != vendored:
        raise SourceError(f"{owner}: path {path} must name the vendored package directory {vendored}")
    return found


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

    def pin(self) -> Pin | None:
        """The `vendored.toml` pin this scene names, or None for a checkout."""
        return _entry_pin(self.id, self.vendored, self.repo, self.path) if self.vendored else None

    def package(self) -> Vendored:
        """The verified vendored package this scene reads, or a refusal."""
        if not self.vendored:
            raise SourceError(f"{self.id}: reads a checkout, not a vendored package")
        self.pin()
        try:
            return vendored_package(self.vendored)
        except SourceError as err:
            raise SourceError(f"{self.id}: {err}") from err

    def artifact(self, root: Path) -> Path:
        """The checkout file this scene reads; a vendored scene reads no checkout."""
        if self.vendored:
            raise SourceError(f"{self.id}: reads the vendored {self.vendored}, not a file in a checkout")
        return Path(root) / self.checkout / self.path

    def read(self, root: Path) -> tuple[bytes, str]:
        """The artifact's bytes and their sha256, or a refusal that names the
        path that was looked for. A vendored scene's bytes are its verified
        file listing."""
        if self.vendored:
            package = self.package()
            return package.listing, package.digest
        return read_artifact(self.id, self.repo, self.path, Path(root) / self.checkout)


def read_artifact(owner: str, repo: str, path: str, checkout: Path) -> tuple[bytes, str]:
    """A checkout's file as it is."""
    where = checkout / path
    if not where.is_file():
        raise SourceError(
            f"{owner}: no artifact at {where}. Expected a checkout of {repo} "
            f"at {checkout}; pass --sources to say where the estate is."
        )
    raw = where.read_bytes()
    if not raw:
        raise SourceError(f"{owner}: {where} is empty")
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
        scene = Scene(**entry)
        if scene.vendored:
            try:
                scene.pin()
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
    #: The `vendored.toml` package the page's own `path` names, instead of a
    #: checkout. `also` files are always read from checkouts.
    vendored: str = ""

    @property
    def checkout(self) -> str:
        return self.repo.split("/")[-1]

    def pin(self) -> Pin | None:
        """The `vendored.toml` pin the page's own path names, or None for a checkout."""
        return _entry_pin(self.id, self.vendored, self.repo, self.path) if self.vendored else None

    def package(self) -> Vendored:
        """The verified vendored package the page reads, or a refusal."""
        if not self.vendored:
            raise SourceError(f"{self.id}: reads a checkout, not a vendored package")
        self.pin()
        try:
            return vendored_package(self.vendored)
        except SourceError as err:
            raise SourceError(f"{self.id}: {err}") from err

    def read(self, root: Path) -> tuple[bytes, str]:
        """The page's own source, by the same rules as `Scene.read`."""
        if self.vendored:
            package = self.package()
            return package.listing, package.digest
        return read_artifact(self.id, self.repo, self.path, Path(root) / self.checkout)

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
                page.pin()
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
