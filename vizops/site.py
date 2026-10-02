"""Build a generated-only site; publication depicts bytes and authorizes nothing."""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import bridge
from .figure import CAVEAT
from .outcome import Rendered, Refused, worst
from .sources import MANIFEST, load, pages, SourceError


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def snapshot(checkout: Path) -> dict:
    """Bind every tracked input, including imported helpers, to an immutable revision."""
    def git(*args):
        return subprocess.check_output(["git", "-C", str(checkout), *args])
    revision = git("rev-parse", "HEAD").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SourceError(f"invalid revision at {checkout}")
    if git("status", "--porcelain", "--untracked-files=normal").strip():
        raise SourceError(f"dirty checkout at {checkout}; publication needs a clean revision")
    files = {}
    for name in git("ls-files", "-z").decode().split("\0"):
        if not name:
            continue
        path = checkout / name
        if path.is_symlink() or not path.is_file():
            raise SourceError(f"unsupported tracked input: {path}")
        files[name] = digest(path)
    return {"revision": revision, "tree_sha256": hashlib.sha256(canonical(files)).hexdigest()}


def checked_output(outcome: Rendered, scratch: Path) -> Path:
    path = Path(outcome.output)
    if path.is_symlink() or not path.resolve().is_relative_to(scratch.resolve()):
        raise SourceError("builder output escaped the isolated build directory")
    if not path.is_file() or not path.stat().st_size or digest(path) != outcome.digest:
        raise SourceError("builder output is missing, empty, or disagrees with its digest")
    return path


def build(sources: Path, out: Path, *, quality: str = "low") -> int:
    """All declared pages and both canonical media for every scene; no partial deployment."""
    from .__main__ import build_page
    if out.exists():
        raise SourceError(f"{out} already exists; use a fresh output directory")
    scenes, declared_pages = load(), pages()
    targets = [*(('page', p) for p in declared_pages), *(('scene', s) for s in scenes)]
    ids = [p.id for _, p in targets]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[a-z0-9][a-z0-9-]*", i) for i in ids):
        raise SourceError("site identifiers must be unique safe filenames")
    repos = sorted({s.repo for s in scenes} | {r for p in declared_pages for r, _ in p.files()})
    checkouts = {r: sources / r.split('/')[-1] for r in repos}
    owner = Path(__file__).resolve().parents[1]
    bound = {"math-vizops": snapshot(owner), **{r: snapshot(c) for r, c in checkouts.items()}}
    manifest = {"format": "vizops site 1", "caveat": CAVEAT,
                "registry_sha256": digest(MANIFEST), "inputs": bound, "outcomes": [], "files": {}}
    outcomes, fragments = [], [f"<!doctype html><html lang='en'><meta charset='utf-8'><title>Math vizops</title><h1>Math vizops</h1><p>{html.escape(CAVEAT)}</p>"]
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="vizops-site-") as directory:
        scratch = Path(directory)
        for kind, target in targets:
            fragments.append(f"<section><h2>{html.escape(target.title)}</h2><p>{html.escape(target.note)}</p>")
            for repo, path in (target.files() if kind == 'page' else ((target.repo, target.path),)):
                fragments.append(f"<p>{html.escape(repo)} @ {bound[repo]['revision']} · {html.escape(path)} · sha256:{digest(checkouts[repo] / path)}</p>")
            for mode in (("page",) if kind == 'page' else ("still", "video")):
                work = scratch / target.id / mode
                work.mkdir(parents=True)
                outcome = (build_page(target, sources, dataset=None, out=work) if mode == 'page'
                           else bridge.render(target, sources, out=work, quality=quality, still=mode == 'still'))
                if isinstance(outcome, Rendered):
                    try:
                        artifact = checked_output(outcome, work)
                        if artifact.suffix.lower() not in ({'.html'} if mode == 'page' else bridge.WANTED[mode == 'still']):
                            raise SourceError("unexpected output format")
                        filename = target.id + ('-' + mode if mode != 'page' else '') + artifact.suffix.lower()
                        shutil.copyfile(artifact, out / filename)
                        if digest(out / filename) != outcome.digest:
                            (out / filename).unlink()
                            raise SourceError("artifact changed while copying to publication")
                        manifest['files'][filename] = outcome.digest
                        if mode == 'page':
                            fragments.append(f"<a href='{filename}'>Interactive page</a>")
                        elif mode == 'still' or artifact.suffix.lower() == '.gif':
                            fragments.append(f"<img src='{filename}' alt='{html.escape(target.title, quote=True)}' style='max-width:100%'>")
                        else:
                            fragments.append(f"<video controls preload='metadata' src='{filename}' style='max-width:100%'></video>")
                        record = {"id": target.id, "mode": mode, "verdict": outcome.verdict, "output": filename, "sha256": outcome.digest}
                    except SourceError as error:
                        outcome = Refused(target.id, str(error))
                if not isinstance(outcome, Rendered):
                    record = {"id": target.id, "mode": mode, "verdict": outcome.verdict, "reason": outcome.reason}
                    fragments.append(f"<p>{html.escape(mode + ': ' + outcome.verdict + ' — ' + outcome.reason)}</p>")
                manifest['outcomes'].append(record)
                outcomes.append(outcome)
                print(f"{mode}: {outcome}")
            fragments.append('</section>')
        after = {"math-vizops": snapshot(owner), **{r: snapshot(c) for r, c in checkouts.items()}}
        if bound != after:
            raise SourceError("inputs changed during site build; publication refused")
    (out / 'index.html').write_text('\n'.join(fragments) + '</html>\n', encoding='utf-8')
    manifest['files']['index.html'] = digest(out / 'index.html')
    manifest['exit_code'] = worst(tuple(outcomes))
    (out / 'manifest.json').write_bytes(canonical(manifest))
    (out / 'manifest.sha256').write_text(digest(out / 'manifest.json') + '  manifest.json\n')
    return manifest['exit_code']
