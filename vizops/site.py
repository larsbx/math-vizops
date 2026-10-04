"""Build a generated-only site; publication depicts bytes and authorizes nothing."""
from __future__ import annotations

import hashlib
import html
import importlib.metadata
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from . import bridge, media
from .figure import CAVEAT
from .outcome import Inconclusive, Rendered, Refused, worst
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


def frozen_digest(checkout: Path, filenames: tuple[str, ...] | None = None) -> str:
    names = filenames if filenames is not None else tuple(
        p.relative_to(checkout).as_posix() for p in checkout.rglob('*') if p.is_file() or p.is_symlink())
    files = {}
    for name in names:
        path = checkout / name
        if path.is_symlink() or not path.is_file():
            raise SourceError('missing file or symlink in frozen inputs')
        files[name] = digest(path)
    return hashlib.sha256(canonical(files)).hexdigest()


def freeze(checkout: Path, destination: Path, expected: dict) -> tuple[str, ...]:
    """Export the bound commit, refusing archive transformations or unsafe members."""
    archive = subprocess.check_output([
        'git', '-C', str(checkout), 'archive', '--format=tar', expected['revision'],
    ])
    destination.mkdir(parents=True)
    filenames = []
    with tarfile.open(fileobj=io.BytesIO(archive)) as entries:
        for member in entries:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise SourceError(f'unsafe source archive member: {member.name}')
            output = destination / path
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                stream = entries.extractfile(member)
                if stream is None:
                    raise SourceError(f'unreadable source archive member: {member.name}')
                with stream, output.open('wb') as into:
                    shutil.copyfileobj(stream, into)
                output.chmod(member.mode & 0o777)
                filenames.append(member.name)
    if frozen_digest(destination) != expected['tree_sha256']:
        raise SourceError('exported source bytes disagree with the bound input tree')
    return tuple(filenames)


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
    try:
        renderer_version = importlib.metadata.version('manimgl')
    except importlib.metadata.PackageNotFoundError:
        renderer_version = 'unavailable'
    manifest['build'] = {'renderer': 'manimgl', 'renderer_version': renderer_version, 'quality': quality}
    outcomes, fragments = [], [f"<!doctype html><html lang='en'><meta charset='utf-8'><title>Math vizops</title><h1>Math vizops</h1><p>{html.escape(CAVEAT)}</p>"]
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="vizops-site-") as directory:
        scratch = Path(directory)
        frozen = scratch / 'sources'
        frozen_files = {repo: freeze(checkout, frozen / repo.split('/')[-1], bound[repo])
                        for repo, checkout in checkouts.items()}
        for kind, target in targets:
            fragments.append(f"<section><h2>{html.escape(target.title)}</h2><p>{html.escape(target.note)}</p>")
            for repo, path in (target.files() if kind == 'page' else ((target.repo, target.path),)):
                fragments.append(f"<p>{html.escape(repo)} @ {bound[repo]['revision']} · {html.escape(path)} · sha256:{digest(frozen / repo.split('/')[-1] / path)}</p>")
            for mode in (("page",) if kind == 'page' else ("still", "video")):
                work = scratch / target.id / mode
                work.mkdir(parents=True)
                outcome = (build_page(target, frozen, dataset=None, out=work) if mode == 'page'
                           else bridge.render(target, frozen, out=work, quality=quality, still=mode == 'still'))
                if isinstance(outcome, Rendered):
                    try:
                        artifact = checked_output(outcome, work)
                        if artifact.suffix.lower() not in ({'.html'} if mode == 'page' else bridge.WANTED[mode == 'still']):
                            raise SourceError("unexpected output format")
                        extra = {}
                        if mode == 'video':
                            normalized = work / 'browser'
                            normalized.mkdir()
                            video, poster = normalized / 'video.mp4', normalized / 'poster.png'
                            playback = media.prepare(artifact, video, poster)
                            if digest(artifact) != outcome.digest:
                                raise SourceError('rendered input changed during media verification')
                            artifact = checked_output(Rendered(target.id, str(video), digest(video)), work)
                            checked_output(Rendered(target.id, str(poster), digest(poster)), work)
                            extra = {'render_sha256': outcome.digest, 'media': playback,
                                     'poster': target.id + '-poster.png', 'poster_sha256': digest(poster)}
                        filename = target.id + ('-' + mode if mode != 'page' else '') + artifact.suffix.lower()
                        expected_digest = digest(artifact) if mode == 'video' else outcome.digest
                        shutil.copyfile(artifact, out / filename)
                        if digest(out / filename) != expected_digest:
                            (out / filename).unlink()
                            raise SourceError("artifact changed while copying to publication")
                        if mode == 'video':
                            shutil.copyfile(poster, out / extra['poster'])
                            if digest(out / extra['poster']) != extra['poster_sha256']:
                                (out / filename).unlink()
                                (out / extra['poster']).unlink()
                                raise SourceError('poster changed while copying to publication')
                            manifest['files'][extra['poster']] = extra['poster_sha256']
                        manifest['files'][filename] = expected_digest
                        if mode == 'page':
                            fragments.append(f"<a href='{filename}'>Interactive page</a>")
                        elif mode == 'still':
                            fragments.append(f"<img src='{filename}' alt='{html.escape(target.title, quote=True)}' style='max-width:100%'>")
                        else:
                            fragments.append(f"<video controls playsinline preload='metadata' poster='{extra['poster']}' src='{filename}' style='max-width:100%'></video><a href='{filename}' download>Download MP4</a>")
                        record = {"id": target.id, "mode": mode, "verdict": outcome.verdict, "output": filename, "sha256": expected_digest, **extra}
                        outcome = Rendered(target.id, str(out / filename), expected_digest)
                    except (media.MediaUnavailable, subprocess.TimeoutExpired) as error:
                        outcome = Inconclusive(target.id, str(error))
                    except (SourceError, OSError, subprocess.CalledProcessError, ValueError) as error:
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
        for repo in repos:
            if frozen_digest(frozen / repo.split('/')[-1], frozen_files[repo]) != bound[repo]['tree_sha256']:
                raise SourceError('frozen inputs changed during site build; publication refused')
    (out / 'index.html').write_text('\n'.join(fragments) + '</html>\n', encoding='utf-8')
    manifest['files']['index.html'] = digest(out / 'index.html')
    manifest['exit_code'] = worst(tuple(outcomes))
    (out / 'manifest.json').write_bytes(canonical(manifest))
    (out / 'manifest.sha256').write_text(digest(out / 'manifest.json') + '  manifest.json\n')
    return manifest['exit_code']
