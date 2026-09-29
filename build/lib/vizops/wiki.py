"""Publishing `wiki/` to the repository's GitHub wiki.

A GitHub wiki is an ordinary git repository (`<repo>.wiki.git`) whose files
are its pages. That makes it editable in two places, and two editable copies
of one page is the drift this repository refuses everywhere else -- so the
pages here are written in `wiki/`, checked by `python -m vizops --check`, and
mirrored outward by `publish`. The wiki is a **derived surface**: an edit made
in the browser is overwritten by the next publish, which is why every page
says so in its footer.

Mirroring is exact. A page deleted from `wiki/` is deleted from the wiki, so
the published set is the set in the repository rather than that set plus
whatever was ever published. `.git` is the only thing left alone.

The wiki repository has to exist before anything can be pushed to it: the
feature must be enabled for the repository (Settings -> Features -> Wikis;
on a private repository that needs a plan that includes wikis) and its first
page created once, after which `<repo>.wiki.git` is clonable. `publish`
reports that case rather than guessing at it.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .surfaces import ROOT, WIKI

REMOTE = "https://github.com/larsbx/math-vizops.wiki.git"
MESSAGE = "Publish wiki from {sha}"


class PublishError(RuntimeError):
    """The wiki could not be published, and the message says what to do."""


@dataclass(frozen=True, slots=True)
class Published:
    remote: str
    pages: tuple[str, ...]
    committed: bool

    def __str__(self) -> str:
        what = f"{len(self.pages)} page(s)" if self.pages else "nothing"
        return f"{'published' if self.committed else 'already current'}: {what} at {self.remote}"


def publish(remote: str = REMOTE, *, source: Path = WIKI, workdir: Path | None = None, dry_run: bool = False) -> Published:
    """Mirror `source` into the wiki repository and push it."""
    if not source.is_dir() or not any(source.glob("*.md")):
        raise PublishError(f"{source} holds no pages to publish")
    workdir = workdir or ROOT / ".wiki-checkout"
    clone(remote, workdir)
    pages = mirror(source, workdir)
    if not _dirty(workdir):
        return Published(remote, (), committed=False)
    if dry_run:
        return Published(remote, pages, committed=False)
    _git(workdir, "add", "-A")
    _git(workdir, *_identity(workdir), "commit", "-m", MESSAGE.format(sha=_sha(ROOT)))
    _git(workdir, "push", "origin", "HEAD")
    return Published(remote, pages, committed=True)


def clone(remote: str, into: Path) -> None:
    """A fresh checkout every time. A wiki is small, and a reused checkout is
    a third copy of the pages to keep in step with the other two."""
    shutil.rmtree(into, ignore_errors=True)
    done = subprocess.run(["git", "clone", remote, str(into)], capture_output=True, text=True)
    if done.returncode != 0:
        raise PublishError(
            f"could not clone {remote}: {done.stderr.strip().splitlines()[-1] if done.stderr.strip() else 'no output'}\n"
            "A wiki exists only once it is enabled for the repository and its first page has been "
            "created; until then there is no wiki repository to clone."
        )


def mirror(source: Path, into: Path) -> tuple[str, ...]:
    """Make `into` hold exactly `source`, `.git` aside. Returns the page set."""
    for existing in into.rglob("*"):
        if ".git" in existing.parts:
            continue
        if existing.is_file():
            existing.unlink()
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        target = into / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return tuple(sorted(p.name for p in source.glob("*.md")))


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise PublishError(f"git {' '.join(args)}: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def _identity(repo: Path) -> tuple[str, ...]:
    """Commit as whoever git is configured to be, and as vizops where it is
    not configured at all -- a publish that dies on an unset identity helps
    nobody."""
    configured = subprocess.run(["git", "config", "user.email"], cwd=repo, capture_output=True, text=True)
    return () if configured.returncode == 0 else ("-c", "user.name=vizops", "-c", "user.email=vizops@localhost")


def _dirty(repo: Path) -> bool:
    return bool(_git(repo, "status", "--porcelain").strip())


def _sha(repo: Path) -> str:
    return _git(repo, "rev-parse", "--short", "HEAD").strip()
