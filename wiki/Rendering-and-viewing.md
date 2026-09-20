# Rendering and viewing

Everything up to the last step — reading an artifact, refusing a malformed
one, laying it out, colouring it — runs with no renderer and no GPU. That is
the part CI runs. Rendering is the last step and the least interesting one.

## Install the renderer

```sh
pip install -e '.[render]'            # 3b1b/manim (manimgl)
```

`manimgl` needs a system Pango and FFmpeg, and a working GL context:

```sh
apt install libpango1.0-dev ffmpeg    # Debian/Ubuntu
brew install pango ffmpeg             # macOS
```

Without them the install fails at `manimpango`; without a GL context the
renderer starts and dies. Neither is a broken scene — see [[Outcomes]].

## Render

```sh
python -m vizops render c1-claim-graph                  # 720p, into out/
python -m vizops render --quality high --out out/       # every scene, 1080p
python -m vizops render psc-object-catalogue --quality uhd
```

`--quality` is `low` (480p), `medium` (720p), `high` (1080p) or `uhd` (4k).
The command refuses a scene before starting a renderer if its artifact is
missing or malformed, so a failure you can fix is a readable message rather
than a manim traceback.

The same scene, driven by manim directly — useful when you want manim's own
flags, its window, or `-p` presenter mode:

```sh
manimgl vizops/scenes.py ClaimGraph -w
```

## Stills, for the wiki

```sh
python -m vizops still c1-claim-graph                   # -> wiki/images/c1-claim-graph.png
```

This renders the last frame only (manim's `-s`) and writes it where the
[[Scenes]] gallery looks for it. Commit the PNG, then run
`python -m vizops --write` so the gallery embeds it, and publish:

```sh
python -m vizops wiki --publish
```

## Viewing

* **In the wiki** — stills, on [[Scenes]]. A wiki renders images from its own
  repository; it is not a video host.
* **Locally** — `out/<SceneName>.mp4`, or drop `-w` from the `manimgl` command
  and watch it in manim's own window, where you can scrub and re-run.
* **Sharing a video** — attach the MP4 to a release or a pull request rather
  than committing it to the wiki. A wiki that carries a 40 MB binary per
  revision is a wiki nobody can clone; a still plus the command that made it
  is reproducible and small.

## Why CI renders nothing

A headless runner has no GL context and usually no Pango. CI therefore runs
the report, the surface check and the test suite — including the scenes
themselves against a stand-in `manimlib` — and never calls the renderer. If it
did, it would report `inconclusive`, which is honest but not informative.
