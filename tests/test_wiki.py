"""Publishing `wiki/` to a wiki repository, against a local bare repository
rather than GitHub: the mirror is exact, a second publish is a no-op, and a
wiki that does not exist yet is a message that says how to make one."""

import subprocess

import pytest

from vizops import wiki


@pytest.fixture
def remote(tmp_path):
    bare = tmp_path / "math-vizops.wiki.git"
    subprocess.run(["git", "init", "--quiet", "--bare", str(bare)], check=True)
    return str(bare)


@pytest.fixture
def pages(tmp_path):
    source = tmp_path / "wiki"
    (source / "images").mkdir(parents=True)
    (source / "Home.md").write_text("# Home\n", encoding="utf-8")
    (source / "Outcomes.md").write_text("# Outcomes\n", encoding="utf-8")
    (source / "images" / "scene.png").write_bytes(b"pixels")
    return source


def published(tmp_path, remote):
    """What the remote actually holds, as a fresh checkout."""
    out = tmp_path / f"verify-{len(list(tmp_path.iterdir()))}"
    subprocess.run(["git", "clone", "--quiet", remote, str(out)], check=True)
    return {str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and ".git" not in p.parts}


def test_pages_and_images_reach_the_wiki(tmp_path, remote, pages):
    done = wiki.publish(remote, source=pages, workdir=tmp_path / "checkout")
    assert done.committed and done.pages == ("Home.md", "Outcomes.md")
    assert published(tmp_path, remote) == {"Home.md", "Outcomes.md", "images/scene.png"}


def test_a_page_deleted_from_the_repository_is_deleted_from_the_wiki(tmp_path, remote, pages):
    wiki.publish(remote, source=pages, workdir=tmp_path / "checkout")
    (pages / "Outcomes.md").unlink()
    wiki.publish(remote, source=pages, workdir=tmp_path / "checkout")
    assert "Outcomes.md" not in published(tmp_path, remote)


def test_publishing_twice_changes_nothing_the_second_time(tmp_path, remote, pages):
    wiki.publish(remote, source=pages, workdir=tmp_path / "checkout")
    again = wiki.publish(remote, source=pages, workdir=tmp_path / "checkout")
    assert not again.committed
    assert "already current" in str(again)


def test_a_dry_run_pushes_nothing(tmp_path, remote, pages):
    done = wiki.publish(remote, source=pages, workdir=tmp_path / "checkout", dry_run=True)
    assert not done.committed and done.pages
    assert published(tmp_path, remote) == set()


def test_a_wiki_that_does_not_exist_yet_says_how_to_make_one(tmp_path, pages):
    with pytest.raises(wiki.PublishError, match="its first page has been created"):
        wiki.publish(str(tmp_path / "absent.wiki.git"), source=pages, workdir=tmp_path / "checkout")


def test_publishing_nothing_is_refused(tmp_path, remote):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(wiki.PublishError, match="holds no pages"):
        wiki.publish(remote, source=empty, workdir=tmp_path / "checkout")
