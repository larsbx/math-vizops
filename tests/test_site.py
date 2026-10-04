"""Publication controls use explicit stand-ins, never evidence of actual GL rendering."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from vizops import media, site
from vizops.media import prepare as prepare_browser_media
from vizops.outcome import Inconclusive, Refused, Rendered
from vizops.sources import Page, Scene, SourceError


def test_snapshot_binds_revision_and_rejects_dirty_inputs(tmp_path):
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    (tmp_path / 'input').write_text('exact')
    subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-m', 'input'], check=True, capture_output=True)
    before = site.snapshot(tmp_path)
    assert before == site.snapshot(tmp_path)
    (tmp_path / 'input').write_text('changed')
    with pytest.raises(SourceError, match='dirty'):
        site.snapshot(tmp_path)


@pytest.fixture
def builders(tmp_path, monkeypatch):
    source = tmp_path / 'sources' / 'sibling'
    source.mkdir(parents=True)
    (source / 'input').write_text('exact')
    monkeypatch.setattr(site, 'snapshot', lambda p: {'revision': 'a' * 40, 'tree_sha256': site.frozen_digest(source)})
    def freeze(checkout, destination, expected):
        shutil.copytree(checkout, destination)
        return ('input',)
    monkeypatch.setattr(site, 'freeze', freeze)
    monkeypatch.setattr(site, 'load', lambda: (Scene('scene', 'Scene <test>', 'owner/sibling', 'input', 'adapter', 'Scene'),))
    monkeypatch.setattr(site, 'pages', lambda: (Page('page', 'Page', 'owner/sibling', 'input', 'wake'),))
    def emit(target, sources, *, out, **kwargs):
        out.mkdir(parents=True, exist_ok=True)
        output = out / ('result.html' if isinstance(target, Page) else 'frame.png' if kwargs.get('still') else 'video.mp4')
        output.write_bytes(b'generated fixture')
        return Rendered(target.id, str(output), site.digest(output))
    monkeypatch.setattr('vizops.__main__.build_page', emit)
    monkeypatch.setattr(site.bridge, 'render', emit)
    def prepare(movie, video, poster):
        video.write_bytes(b'normalized fixture')
        poster.write_bytes(b'poster fixture')
        return {'codec': 'h264', 'pixel_format': 'yuv420p', 'duration_seconds': 1.0, 'width': 160, 'height': 90}
    monkeypatch.setattr(site.media, 'prepare', prepare)
    return tmp_path / 'sources'


def test_only_generated_files_embedded_and_manifest_is_deterministic(builders, tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    assert site.build(builders, a) == site.build(builders, b) == 0
    assert (a / 'manifest.json').read_bytes() == (b / 'manifest.json').read_bytes()
    manifest = json.loads((a / 'manifest.json').read_text())
    assert set(p.name for p in a.iterdir()) == {'index.html', 'page.html', 'scene-still.png', 'scene-video.mp4', 'scene-poster.png', 'manifest.json', 'manifest.sha256'}
    for name, expected in manifest['files'].items():
        assert site.digest(a / name) == expected
    index = (a / 'index.html').read_text()
    assert 'Scene &lt;test&gt;' in index and '<video controls' in index and '<img src=' in index
    assert 'authorizes nothing' in index
    assert "playsinline" in index and "poster='scene-poster.png'" in index and 'Download MP4' in index
    video, = [r for r in manifest['outcomes'] if r['mode'] == 'video']
    assert video['render_sha256'] != video['sha256'] == site.digest(a / video['output'])
    assert video['poster_sha256'] == site.digest(a / video['poster'])
    assert video['media']['codec'] == 'h264'
    assert manifest['build']['quality'] == 'low'
    assert (a / 'manifest.sha256').read_text().startswith(site.digest(a / 'manifest.json'))


@pytest.mark.parametrize('outcome,code', [(Inconclusive('scene', 'no GL context'), 2), (Refused('scene', 'renderer died'), 1)])
def test_non_render_verdict_blocks_publication_without_fake_media(builders, tmp_path, monkeypatch, outcome, code):
    monkeypatch.setattr(site.bridge, 'render', lambda *a, **kw: outcome)
    out = tmp_path / 'site'
    assert site.build(builders, out) == code
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['exit_code'] == code
    assert not list(out.glob('*.mp4')) and not list(out.glob('*.png'))
    assert outcome.verdict in (out / 'index.html').read_text()


def test_wrong_output_digest_is_refused(builders, tmp_path, monkeypatch):
    def forged(target, sources, *, out, **kwargs):
        p = out / 'frame.png'
        p.write_bytes(b'changed after rendering')
        return Rendered(target.id, str(p), '0' * 64)
    monkeypatch.setattr(site.bridge, 'render', forged)
    assert site.build(builders, tmp_path / 'site') == 1
    assert not list((tmp_path / 'site').glob('*.png'))


def test_changed_input_blocks_build(builders, tmp_path, monkeypatch):
    calls = 0
    def snapshot(p):
        nonlocal calls
        calls += 1
        return {'revision': 'a' * 40, 'tree_sha256': str(calls // 3)}
    monkeypatch.setattr(site, 'snapshot', snapshot)
    with pytest.raises(SourceError, match='changed'):
        site.build(builders, tmp_path / 'site')


def test_existing_output_cannot_supply_stale_success(builders, tmp_path):
    with pytest.raises(SourceError, match='already exists'):
        site.build(builders, tmp_path)


def test_output_cannot_escape_scratch(tmp_path):
    p = tmp_path / 'old.mp4'
    p.write_bytes(b'stale')
    with pytest.raises(SourceError, match='escaped'):
        site.checked_output(Rendered('scene', str(p), site.digest(p)), tmp_path / 'scratch')


def test_pages_workflow_uploads_generated_bundle_and_gates_deployment():
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/static.yml').read_text()
    assert 'xvfb-run -a python -m vizops site' in workflow
    assert 'LIBGL_ALWAYS_SOFTWARE' in workflow
    assert 'path: math-vizops/out/site' in workflow
    assert "path: '.'" not in workflow
    assert 'needs: build' in workflow
    assert "if: success() && github.event_name != 'pull_request'" in workflow
    assert 'continue-on-error' not in workflow
    assert 'persist-credentials: true' not in workflow


def test_pages_artifacts_are_attempt_scoped_and_deploy_uses_producing_attempt():
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/static.yml').read_text()
    build, deploy = workflow.split('\n  deploy:', 1)
    assert 'name: site-build-evidence-${{ github.run_attempt }}' in build
    assert 'name=github-pages-${{ github.run_attempt }}' in build
    assert 'pages_artifact: ${{ steps.pages-artifact.outputs.name }}' in build
    upload = build.split('uses: actions/upload-pages-artifact@v3', 1)[1]
    assert 'name: ${{ steps.pages-artifact.outputs.name }}' in upload
    assert 'artifact_name: ${{ needs.build.outputs.pages_artifact }}' in deploy
    # A deploy-only retry must still select the earlier successful build's artifact.
    assert 'github.run_attempt' not in deploy
    assert 'name: site-build-evidence\n' not in workflow


@pytest.mark.parametrize('error,code', [
    (media.MediaUnavailable('no ffprobe'), 2),
    (subprocess.TimeoutExpired('ffmpeg', 900), 2),
    (subprocess.CalledProcessError(1, 'ffmpeg'), 1),
    (SourceError('invalid playback metadata'), 1),
])
def test_unverified_video_blocks_site_publication(builders, tmp_path, monkeypatch, error, code):
    def unavailable(*args):
        raise error
    monkeypatch.setattr(site.media, 'prepare', unavailable)
    out = tmp_path / 'site'
    assert site.build(builders, out) == code
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['exit_code'] == code
    assert not list(out.glob('*.mp4')) and not list(out.glob('*-poster.png'))
    assert all(not name.endswith('.mp4') for name in manifest['files'])


def test_renderers_read_frozen_bytes_even_if_live_checkout_changes(builders, tmp_path, monkeypatch):
    render = site.bridge.render
    seen = []
    live = builders / 'sibling' / 'input'
    def changing_live(target, frozen, **kwargs):
        live.write_text('transient mutation')
        try:
            seen.append((frozen / 'sibling' / 'input').read_text())
            assert frozen != builders and not (frozen / 'sibling' / '.git').exists()
            return render(target, frozen, **kwargs)
        finally:
            live.write_text('exact')
    monkeypatch.setattr(site.bridge, 'render', changing_live)
    assert site.build(builders, tmp_path / 'site') == 0
    assert seen == ['exact', 'exact']


def test_changed_frozen_input_blocks_site_build(builders, tmp_path, monkeypatch):
    render = site.bridge.render
    def modifying_export(target, frozen, **kwargs):
        (frozen / 'sibling' / 'input').write_text('modified export')
        return render(target, frozen, **kwargs)
    monkeypatch.setattr(site.bridge, 'render', modifying_export)
    with pytest.raises(SourceError, match='frozen inputs changed'):
        site.build(builders, tmp_path / 'site')


def test_source_required_checks_and_stand_in_suite_precede_renderer_installation():
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/static.yml').read_text()
    assert workflow.index('repository: larsbx/finite-math-kernels') < workflow.index('name: Check real upstream artifacts')
    assert workflow.index('pytest -q') < workflow.index('name: Install headless renderer')
    assert workflow.index('pytest tests/test_estate.py -q') < workflow.index('name: Install headless renderer')
    assert workflow.index('name: Install browser-media verification tools') < workflow.index('pytest -q')
    assert 'vizops gallery' not in workflow
    smoke = workflow.split('name: Render fixture scenes through the site builder', 1)[1]
    assert "if: github.event_name == 'pull_request'" in smoke
    assert 'python tests/smoke_site_render.py' in smoke
    assert 'name: fixture-rendering-${{ github.run_attempt }}' in smoke


def test_real_media_conversion_is_bound_into_site_manifest(builders, tmp_path, monkeypatch):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('FFmpeg/FFprobe are absent')
    render = site.bridge.render
    def movie(target, sources, *, out, **kwargs):
        if kwargs.get('still'):
            return render(target, sources, out=out, **kwargs)
        output = out / 'raw.mov'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc=s=161x91:d=0.2', '-c:v', 'qtrle', str(output)], check=True)
        return Rendered(target.id, str(output), site.digest(output))
    monkeypatch.setattr(site.bridge, 'render', movie)
    monkeypatch.setattr(site.media, 'prepare', prepare_browser_media)
    out = tmp_path / 'site'
    assert site.build(builders, out) == 0
    manifest = json.loads((out / 'manifest.json').read_text())
    video, = [r for r in manifest['outcomes'] if r['mode'] == 'video']
    assert video['output'] == 'scene-video.mp4' and video['media']['pixel_format'] == 'yuv420p'
    assert video['media']['width'] == 160 and video['media']['height'] == 90
    assert video['sha256'] == manifest['files'][video['output']] == site.digest(out / video['output'])
    assert video['poster_sha256'] == manifest['files'][video['poster']] == site.digest(out / video['poster'])
    assert not list(out.glob('*.mov')) and not (out / 'sources').exists()


def test_conformance_workflow_uses_available_step_context_and_trusted_estate_gate():
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_text()
    estate = workflow.split('\n  estate:', 1)[1]
    assert "if: github.event_name != 'pull_request'" in estate
    assert "VIZOPS_HAVE_ESTATE_TOKEN: ${{ secrets.ESTATE_TOKEN != '' }}" in estate
    assert estate.count("if: env.VIZOPS_HAVE_ESTATE_TOKEN == 'true'") == 2
    assert 'if: ${{ secrets.' not in workflow
