import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


import hashlib
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _vendored_digests() -> dict[str, str]:
    manifest = tomllib.loads((ROOT / "vendored.toml").read_text(encoding="utf-8"))
    return {f"{pkg['root']}/{rel}": hashlib.sha256((ROOT / pkg["root"] / rel).read_bytes()).hexdigest()
            for pkg in manifest["package"] for rel in pkg["files"]}


@pytest.fixture(autouse=True)
def vendored_files_are_never_written():
    """A vendored scene's artifact() is the repository's own copy under vendor/,
    so a test that writes a fixture there would patch it. Fail that test."""
    before = _vendored_digests()
    yield
    assert _vendored_digests() == before, "a test wrote to a vendored file under vendor/"
