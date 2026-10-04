"""Playback checks exercise real FFmpeg separately from explicit unit stand-ins."""
import json
import io
import shutil
import subprocess
import tarfile

import pytest

from vizops import media, site
from vizops.sources import SourceError


@pytest.fixture
def movie(tmp_path):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('FFmpeg/FFprobe are absent')
    path = tmp_path / 'raw.mov'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                    'testsrc=s=161x91:d=0.2', '-c:v', 'qtrle', str(path)], check=True)
    return path


def test_real_ffmpeg_normalizes_movie_and_extracts_poster(movie, tmp_path):
    target, poster = tmp_path / 'browser.mp4', tmp_path / 'poster.png'
    playback = media.prepare(movie, target, poster)
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(target)]))
    stream, = info['streams']
    assert (stream['codec_name'], stream['pix_fmt'], stream['width'], stream['height']) == ('h264', 'yuv420p', 160, 90)
    assert playback['duration_seconds'] > 0
    assert poster.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert site.digest(movie) != site.digest(target)


def test_corrupt_movie_cannot_reach_a_playback_verdict(movie, tmp_path):
    movie.write_bytes(b'not a movie')
    with pytest.raises(subprocess.CalledProcessError):
        media.prepare(movie, tmp_path / 'browser.mp4', tmp_path / 'poster.png')


def test_absent_media_tools_are_inconclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(media.shutil, 'which', lambda name: None if name == 'ffprobe' else name)
    with pytest.raises(media.MediaUnavailable, match='ffmpeg/ffprobe'):
        media.prepare(tmp_path / 'input', tmp_path / 'browser.mp4', tmp_path / 'poster.png')


@pytest.mark.parametrize('field,value', [('codec_name', 'vp9'), ('pix_fmt', 'yuv444p'),
                                      ('width', 0), ('height', -1), ('duration', 'nan'), ('duration', '0')])
def test_invalid_playback_metadata_is_refused(tmp_path, monkeypatch, field, value):
    stream = {'codec_name': 'h264', 'pix_fmt': 'yuv420p', 'width': 160, 'height': 90}
    info = {'streams': [stream], 'format': {'duration': '1'}}
    (info['format'] if field == 'duration' else stream)[field] = value
    monkeypatch.setattr(media.shutil, 'which', lambda name: name)
    monkeypatch.setattr(media.subprocess, 'run', lambda *a, **kw: None)
    monkeypatch.setattr(media.subprocess, 'check_output', lambda *a, **kw: json.dumps(info).encode())
    with pytest.raises(SourceError, match='playable'):
        media.prepare(tmp_path / 'input', tmp_path / 'browser.mp4', tmp_path / 'poster.png')


def test_missing_poster_is_refused(tmp_path, monkeypatch):
    info = {'streams': [{'codec_name': 'h264', 'pix_fmt': 'yuv420p', 'width': 160, 'height': 90}], 'format': {'duration': '1'}}
    monkeypatch.setattr(media.shutil, 'which', lambda name: name)
    monkeypatch.setattr(media.subprocess, 'run', lambda *a, **kw: None)
    monkeypatch.setattr(media.subprocess, 'check_output', lambda *a, **kw: json.dumps(info).encode())
    with pytest.raises(SourceError, match='poster'):
        media.prepare(tmp_path / 'input', tmp_path / 'browser.mp4', tmp_path / 'poster.png')


def test_exports_use_committed_bytes_and_track_only_exported_inputs(tmp_path):
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    subprocess.run(['git', 'init', '-q', str(checkout)], check=True)
    (checkout / 'input').write_text('committed')
    subprocess.run(['git', '-C', str(checkout), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(checkout), '-c', 'user.name=Test', '-c', 'user.email=test@example.org',
                    'commit', '-qm', 'fixture'], check=True)
    bound = site.snapshot(checkout)
    (checkout / 'input').write_text('transient live edit')
    exported = tmp_path / 'export'
    filenames = site.freeze(checkout, exported, bound)
    assert (exported / 'input').read_text() == 'committed'
    assert not (exported / '.git').exists()
    (exported / '__pycache__').mkdir()
    (exported / '__pycache__' / 'generated.pyc').write_bytes(b'cache')
    assert site.frozen_digest(exported, filenames) == bound['tree_sha256']
    (exported / 'input').write_text('changed exported input')
    assert site.frozen_digest(exported, filenames) != bound['tree_sha256']


@pytest.mark.parametrize('name,kind', [('../escape', tarfile.REGTYPE), ('link', tarfile.SYMTYPE)])
def test_unsafe_archive_members_are_refused(tmp_path, monkeypatch, name, kind):
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w') as entries:
        member = tarfile.TarInfo(name)
        member.type = kind
        member.linkname = '../escape' if kind == tarfile.SYMTYPE else ''
        entries.addfile(member)
    monkeypatch.setattr(site.subprocess, 'check_output', lambda *a, **kw: archive.getvalue())
    with pytest.raises(SourceError, match='unsafe'):
        site.freeze(tmp_path, tmp_path / 'export', {'revision': 'a' * 40, 'tree_sha256': 'b' * 64})
    assert not (tmp_path / 'escape').exists()
