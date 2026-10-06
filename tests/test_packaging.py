"""An installed wheel carries the vendoring pins and checks its own vendored package.

`vendored.toml` at the repository root is the only copy in the source tree;
`setup.py` copies it into the build as `vizops/vendored.toml`. This builds a
real wheel, checks that copy, installs the wheel into a directory, and runs the
installed vizops from outside the source tree in a fresh interpreter that
cannot see the editable install.
"""

import importlib.util
import json
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("pip") is None or importlib.util.find_spec("setuptools") is None,
    reason="building a wheel needs pip and setuptools in the test interpreter",
)


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    work = tmp_path_factory.mktemp("wheel")
    subprocess.run([sys.executable, "-m", "pip", "wheel", "-q", "--no-deps", "--no-build-isolation",
                    "-w", str(work / "dist"), str(ROOT)], check=True, capture_output=True)
    (wheel,) = (work / "dist").glob("vizops-*.whl")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "--target",
                    str(work / "site"), str(wheel)], check=True, capture_output=True)
    venv.EnvBuilder(with_pip=False).create(work / "env")
    python = work / "env" / "bin" / "python"
    return wheel, work, python


def run(installed, *argv):
    _, work, python = installed
    outside = work / "cwd"
    outside.mkdir(exist_ok=True)
    return subprocess.run([str(python), *argv], cwd=outside, env={"PYTHONPATH": str(work / "site")},
                          capture_output=True, text=True)


def test_the_wheel_ships_the_root_pins_byte_for_byte(installed):
    wheel, _, _ = installed
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        assert archive.read("vizops/vendored.toml") == (ROOT / "vendored.toml").read_bytes()
    assert {"rational_dynamics_py/__init__.py", "rational_dynamics_py/doubling.py"} <= names
    assert not (ROOT / "vizops" / "vendored.toml").exists()  # the build wrote the copy, not the source tree


def test_the_installed_vizops_loads_its_registry_and_verifies_the_installed_package(installed):
    _, work, _ = installed
    done = run(installed, "-c", """
import json
from pathlib import Path
from vizops import sources
package = sources.vendored_package("rational_dynamics_py")
print(json.dumps({"pages": [p.id for p in sources.pages()], "scenes": [s.id for s in sources.load()],
                  "manifest": str(sources.VENDORED), "package": str(Path(package.module.__file__).parent),
                  "digest": package.digest}))
""")
    assert done.returncode == 0, done.stderr
    found = json.loads(done.stdout)
    site = work / "site"
    assert "wake-to-mandelbrot" in found["pages"] and "wake-cycle-3-7" in found["scenes"]
    assert Path(found["manifest"]) == site / "vizops" / "vendored.toml"
    assert Path(found["package"]) == site / "rational_dynamics_py"
    from vizops.sources import vendored_package
    assert found["digest"] == vendored_package("rational_dynamics_py").digest


def test_the_installed_cli_builds_the_same_wake_page(installed, tmp_path):
    from vizops.sources import pages
    from vizops.wake import build

    done = run(installed, "-m", "vizops", "page", "wake-to-mandelbrot", "--out", str(tmp_path / "installed"))
    assert done.returncode == 0, done.stdout + done.stderr
    page = next(p for p in pages() if p.id == "wake-to-mandelbrot")
    build(page, tmp_path, out=tmp_path / "source" / "wake-to-mandelbrot.html")
    assert ((tmp_path / "installed" / "wake-to-mandelbrot.html").read_bytes()
            == (tmp_path / "source" / "wake-to-mandelbrot.html").read_bytes())


def test_the_installed_cli_refuses_a_drifted_installed_package(installed, tmp_path):
    _, work, _ = installed
    init = work / "site" / "rational_dynamics_py" / "__init__.py"
    original = init.read_bytes()
    init.write_bytes(original + b"\n# a local patch\n")
    try:
        done = run(installed, "-m", "vizops", "page", "wake-to-mandelbrot", "--out", str(tmp_path))
    finally:
        init.write_bytes(original)
    assert done.returncode == 1
    assert "rational_dynamics_py/__init__.py" in done.stdout and "differs from" in done.stdout
