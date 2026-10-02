"""Render revision snapshots into a verified, embeddable publication directory."""
from __future__ import annotations

import hashlib
import html
import io
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Sequence

from .bridge import REFUSALS, figure, render, root
from .outcome import Inconclusive, Refused, Rendered, worst
from .sources import Scene, SourceError


def snapshot(scenes: Sequence[Scene], sources: Path, destination: Path) -> dict[str, str]:
    """Copy committed upstream bytes, never a mutable working tree, into isolation."""
    revisions = {}
    for repo in sorted({scene.repo for scene in scenes}):
        name = repo.split("/")[-1]
        checkout = sources / name
        try:
            revision = subprocess.check_output(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                raise SourceError(f"{repo}: invalid checkout revision")
            archive = subprocess.check_output(
                ["git", "-C", str(checkout), "archive", "--format=tar", revision])
        except subprocess.CalledProcessError as err:
            raise SourceError(f"{repo}: cannot snapshot committed source") from err
        target = destination / name
        target.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar:
                path = Path(member.name)
                if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                    raise SourceError(f"{repo}: unsafe archive member {member.name}")
                output = target / path
                if member.isdir():
                    output.mkdir(parents=True, exist_ok=True)
                else:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise SourceError(f"{repo}: unreadable archive member {member.name}")
                    with stream, output.open("wb") as into:
                        shutil.copyfileobj(stream, into)
        revisions[repo] = revision
    return revisions


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def media(movie: Path, target: Path, poster: Path) -> dict:
    """Transcode the finished render to browser-safe H.264 and verify playback data."""
    subprocess.run([
        "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(movie),
        "-map", "0:v:0", "-an", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)
    ], check=True, capture_output=True, timeout=900)
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
        "-show_format", "-of", "json", str(target)
    ], timeout=60))
    streams = info.get("streams", [])
    duration = float(info.get("format", {}).get("duration", 0))
    if (len(streams) != 1 or streams[0].get("codec_name") != "h264"
            or streams[0].get("pix_fmt") != "yuv420p" or not math.isfinite(duration)
            or duration <= 0 or streams[0].get("width", 0) <= 0 or streams[0].get("height", 0) <= 0):
        raise SourceError("rendered media is not a playable H.264 video")
    subprocess.run([
        "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(target),
        "-frames:v", "1", str(poster)
    ], check=True, capture_output=True, timeout=60)
    if not poster.is_file() or not poster.stat().st_size:
        raise SourceError("poster was not produced")
    return {"codec": "h264", "pixel_format": "yuv420p", "duration_seconds": duration,
            "width": streams[0]["width"], "height": streams[0]["height"]}


def page(records: list[dict]) -> str:
    cards = []
    for record in records:
        source = record["source"]
        url = f'https://github.com/{source["repository"]}/blob/{source["revision"]}/{source["path"]}'
        escape = lambda value: html.escape(str(value), quote=True)
        cards.append(f'''<article><h2>{escape(record['title'])}</h2>
<video controls playsinline preload="metadata" poster="{escape(record['poster'])}">
<source src="{escape(record['video'])}" type="video/mp4">
<a href="{escape(record['video'])}">Download animation</a></video>
<p><a href="{escape(record['video'])}" download>Download MP4</a> ·
<a href="{escape(url)}">Source revision</a></p>
<p class="provenance">{escape(source['repository'])} · {escape(source['path'])}<br>
revision {escape(source['revision'])}<br>source SHA-256 {escape(source['sha256'])}<br>
video SHA-256 {escape(record['video_sha256'])}</p>
<p>Derived surface — depicts the source at this digest; authorizes nothing.</p></article>''')
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Research animations · math-vizops</title><style>
body{margin:0;background:#1a1a19;color:#eee;font:17px system-ui;line-height:1.5}
main{max-width:1100px;margin:auto;padding:24px}article{margin:32px 0;padding:20px;border:1px solid #555;border-radius:12px}
video{display:block;width:100%;background:#000}a{color:#a6d8ff}.provenance{font:12px monospace;overflow-wrap:anywhere}
</style><main><h1>Research animations</h1><p>Playable scenes drawn from immutable source snapshots.
Numerical placements and schematic rays are display aids.</p>''' + "\n".join(cards) + \
        '<p><a href="manifest.json">Publication manifest and media digests</a></p></main></html>'


def build(scenes: Sequence[Scene], sources: Path | None, *, out: Path,
          report: Path, quality: str = "medium") -> int:
    """Publish only a complete verified gallery; any other outcome blocks deployment."""
    outcomes = []
    records = []
    try:
        if not scenes:
            raise SourceError("no scenes selected")
        if out.exists():
            raise SourceError(f"publication destination already exists: {out}")
        if any(not re.fullmatch(r"[a-z0-9][a-z0-9-]*", scene.id) for scene in scenes):
            raise SourceError("unsafe scene ID")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            outcomes.append(Inconclusive("gallery", "ffmpeg/ffprobe are required to verify browser media"))
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({"format": "vizops publication report 1", "published": False,
                "outcomes": [{"scene": "gallery", "verdict": "inconclusive", "reason": outcomes[0].reason}]}))
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="vizops-gallery-", dir=out.parent) as temporary:
            workspace = Path(temporary)
            snapshots = workspace / "sources"
            revisions = snapshot(scenes, root(sources), snapshots)
            public = workspace / "public"
            (public / "media").mkdir(parents=True)
            for scene in scenes:
                try:
                    drawn = figure(scene, snapshots)
                    outcome = render(scene, snapshots, out=workspace / "renders" / scene.id, quality=quality)
                    if not isinstance(outcome, Rendered):
                        outcomes.append(outcome)
                        continue
                    video = public / "media" / f"{scene.id}.mp4"
                    poster = public / "media" / f"{scene.id}.png"
                    metadata = media(Path(outcome.output), video, poster)
                    provenance = drawn.provenance
                    records.append({"scene": scene.id, "title": scene.title,
                        "source": {"repository": provenance.repo, "path": provenance.path,
                                   "revision": revisions[scene.repo], "sha256": provenance.digest},
                        "video": f"media/{video.name}", "poster": f"media/{poster.name}",
                        "video_sha256": digest(video), "poster_sha256": digest(poster), "media": metadata})
                    outcomes.append(Rendered(scene.id, f"media/{video.name}", digest(video)))
                except (REFUSALS + (subprocess.CalledProcessError, ValueError, OSError)) as err:
                    outcomes.append(Refused(scene.id, str(err)))
                except subprocess.TimeoutExpired as err:
                    outcomes.append(Inconclusive(scene.id, str(err)))
            if len(records) == len(scenes) and worst(tuple(outcomes)) == 0:
                try:
                    renderer_version = importlib.metadata.version("manimgl")
                except importlib.metadata.PackageNotFoundError:
                    renderer_version = "unavailable"
                manifest = {"format": "vizops gallery 1", "scenes": records,
                            "build": {"revision": os.environ.get("GITHUB_SHA", "local-checkout"),
                                      "renderer": "manimgl", "renderer_version": renderer_version,
                                      "quality": quality}}
                (public / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                (public / "index.html").write_text(page(records), encoding="utf-8")
                (public / ".nojekyll").touch()
                os.replace(public, out)
    except (SourceError, OSError, subprocess.CalledProcessError) as err:
        outcomes.append(Refused("gallery", str(err)))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"format": "vizops publication report 1", "published": out.exists() and bool(records)
        and len(records) == len(scenes) and worst(tuple(outcomes)) == 0,
        "outcomes": [{"scene": o.scene, "verdict": o.verdict,
                      "reason": getattr(o, "reason", ""), "digest": getattr(o, "digest", "")} for o in outcomes]}, indent=2) + "\n")
    print("\n".join(map(str, outcomes)))
    print(f"publication report: {report}")
    return worst(tuple(outcomes))
