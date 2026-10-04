"""Real GL smoke of all registered scene classes, using explicit test artifacts.

This is a scene-only fixture registry, not a complete upstream site or a Pages
publication. The real site builder still freezes commits, renders stills/videos,
normalizes playback, extracts posters, and binds every generated digest.
Run after the stand-in suite and after installing vizops[render], under Xvfb.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import artifacts
from vizops import site
from vizops.sources import MANIFEST, load


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='vizops-render-fixture-') as directory:
        work = Path(directory)
        sources = artifacts.estate(work / 'sources')
        for checkout in sources.iterdir():
            subprocess.run(['git', 'init', '-q', str(checkout)], check=True)
            subprocess.run(['git', '-C', str(checkout), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(checkout), '-c', 'user.name=Rendering Fixture',
                            '-c', 'user.email=fixture@example.test', 'commit', '-qm',
                            'Deterministic rendering fixture, no upstream claim evidence'], check=True)
        registry = work / 'fixture-sources.toml'
        registry.write_text(MANIFEST.read_text().split('[[page]]', 1)[0])
        scenes = load(registry)
        assert {s.id for s in scenes} == {s.id for s in load()}
        # Explicitly select the fixture's scene-only registry. Upstream HTML
        # emitters and private-source validation remain trusted-build checks.
        site.MANIFEST = registry
        site.load = lambda: scenes
        site.pages = lambda: ()
        code = site.build(sources, args.out, quality='low')
        if code:
            return code
        manifest = json.loads((args.out / 'manifest.json').read_text())
        assert len(manifest['outcomes']) == 2 * len(scenes)
        assert all(r['verdict'] == 'rendered' for r in manifest['outcomes'])
        assert sum(r['mode'] == 'video' and r['media']['codec'] == 'h264'
                   and r['media']['pixel_format'] == 'yuv420p' for r in manifest['outcomes']) == len(scenes)
        assert all(site.digest(args.out / name) == value for name, value in manifest['files'].items())
        (args.out / 'VALIDATION-SCOPE.txt').write_text(
            'Real software-GL rendering of all registered scene classes from deterministic test artifacts.\n'
            'This scene-only fixture site is not upstream research evidence or a complete deployable Pages build.\n')
        print(f'{len(scenes)} scene classes: real GL stills, H.264 videos, posters and digests verified')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
