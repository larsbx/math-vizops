"""Publication is atomic, provenance-backed, playable, and refuses stale outputs."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import artifacts
from vizops import gallery
from vizops.outcome import Inconclusive, Rendered
from vizops.sources import load


def test_snapshot_uses_committed_bytes_and_preserves_revision(tmp_path):
    sources = tmp_path / "sources"
    checkout = sources / "repo"
    checkout.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    (checkout / "data").write_text("committed")
    subprocess.run(["git", "-C", str(checkout), "add", "data"], check=True)
    subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Test", "-c", "user.email=test@example.test",
                    "commit", "-qm", "fixture"], check=True)
    (checkout / "data").write_text("modified working tree")
    from vizops.sources import Scene
    scene = Scene("test", "Test", "owner/repo", "data", "typed_graph", "ClaimGraph")
    target = tmp_path / "snapshot"
    revisions = gallery.snapshot([scene], sources, target)
    assert (target / "repo" / "data").read_text() == "committed"
    assert len(revisions["owner/repo"]) == 40


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    sources = artifacts.estate(tmp_path / "estate")
    monkeypatch.setattr(gallery, "snapshot", lambda scenes, source, dest: (
        shutil.copytree(source, dest), {scene.repo: "a" * 40 for scene in scenes})[1])
    def renderer(scene, sources, **kwargs):
        output = kwargs["out"] / "movie.mp4"
        output.parent.mkdir(parents=True)
        output.write_bytes(b"rendered-video")
        return Rendered(scene.id, str(output), hashlib.sha256(output.read_bytes()).hexdigest())
    def media(movie, video, poster):
        video.write_bytes(movie.read_bytes())
        poster.write_bytes(b"poster")
        return {"duration_seconds": 1, "width": 640, "height": 360}
    monkeypatch.setattr(gallery, "render", renderer)
    monkeypatch.setattr(gallery, "media", media)
    return sources, tmp_path / "site", tmp_path / "report.json"


def test_complete_gallery_embeds_only_verified_media_with_digests(pipeline):
    sources, out, report = pipeline
    assert gallery.build(load()[:1], sources, out=out, report=report) == 0
    manifest = json.loads((out / "manifest.json").read_text())
    record = manifest["scenes"][0]
    assert record["source"]["revision"] == "a" * 40
    assert record["video_sha256"] == gallery.digest(out / record["video"])
    assert '<video controls playsinline' in (out / "index.html").read_text()
    assert json.loads(report.read_text())["published"] is True
    assert not (out / "sources").exists()


def test_inconclusive_blocks_entire_publication(pipeline, monkeypatch):
    sources, out, report = pipeline
    monkeypatch.setattr(gallery, "render", lambda scene, *args, **kwargs: Inconclusive(scene.id, "no GL"))
    assert gallery.build(load()[:1], sources, out=out, report=report) == 2
    assert not out.exists()
    assert json.loads(report.read_text())["published"] is False


def test_invalid_media_blocks_publication(pipeline, monkeypatch):
    sources, out, report = pipeline
    monkeypatch.setattr(gallery, "media", lambda *args: (_ for _ in ()).throw(ValueError("invalid movie")))
    assert gallery.build(load()[:1], sources, out=out, report=report) == 1
    assert not out.exists()


def test_existing_publication_is_not_reused_or_overwritten(pipeline):
    sources, out, report = pipeline
    out.mkdir()
    (out / "keep").write_text("previous publication")
    assert gallery.build(load()[:1], sources, out=out, report=report) == 1
    assert (out / "keep").read_text() == "previous publication"
    assert json.loads(report.read_text())["published"] is False


def test_gallery_escapes_source_and_title_text():
    record = {"title": '<script>alert(1)</script>', "poster": 'a".png', "video": "a.mp4",
              "video_sha256": "a" * 64, "source": {"repository": "owner/repo", "revision": "b" * 40,
              "path": '<danger>', "sha256": "c" * 64}}
    page = gallery.page([record])
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="media tools absent")
def test_real_ffmpeg_produces_browser_compatible_video_and_poster(tmp_path):
    movie = tmp_path / "input.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=blue:s=160x90:d=0.2", "-c:v", "libx264", str(movie)], check=True)
    metadata = gallery.media(movie, tmp_path / "browser.mp4", tmp_path / "poster.png")
    assert metadata["codec"] == "h264"
    assert metadata["duration_seconds"] > 0
    assert (tmp_path / "poster.png").stat().st_size > 0
