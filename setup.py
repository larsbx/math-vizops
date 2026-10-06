"""Ship the vendoring pins with an installed vizops.

`vendored.toml` at the repository root is the single source of truth for what
is vendored under vendor/python/ and at which digests. vizops checks every
vendored package against it before calling it (`vizops.sources.vendored_package`),
so an installed wheel needs the pins too, but package data cannot reach a file
outside the package. This hook copies the root file into the *build* tree as
`vizops/vendored.toml` while building; the source tree never holds a second
copy, and `tests/test_packaging.py` checks the built wheel's copy is
byte-identical to the root file. Everything else is in pyproject.toml.
"""

from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

PINS = Path(__file__).resolve().parent / "vendored.toml"


class build_py_with_pins(build_py):
    def run(self):
        super().run()
        target = Path(self.build_lib) / "vizops" / "vendored.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.copy_file(str(PINS), str(target), preserve_mode=False)

    def get_outputs(self, include_bytecode=True):
        return [*super().get_outputs(include_bytecode), str(Path(self.build_lib) / "vizops" / "vendored.toml")]


setup(cmdclass={"build_py": build_py_with_pins})
