"""The outcome set is closed, every non-render says why, and the three
verdicts are distinguishable by exit code."""

import pytest

from vizops.outcome import EXIT_CODES, Inconclusive, Outcome, Refused, Rendered, worst

DIGEST = "a" * 64


def test_a_fourth_outcome_cannot_be_declared_elsewhere():
    with pytest.raises(TypeError, match="the outcome set is closed"):
        type("Maybe", (Outcome,), {})


def test_every_verdict_has_its_own_exit_code():
    assert sorted(EXIT_CODES.values()) == [0, 1, 2]
    assert Rendered("s", "out.mp4", DIGEST).exit_code == 0
    assert Refused("s", "why").exit_code == 1
    assert Inconclusive("s", "no renderer").exit_code == 2


@pytest.mark.parametrize("outcome", [Refused, Inconclusive])
@pytest.mark.parametrize("reason", ["", "   "])
def test_a_non_render_must_say_why(outcome, reason):
    with pytest.raises(ValueError, match="must say why"):
        outcome("s", reason)


@pytest.mark.parametrize("digest", ["", "abc", "A" * 64, "g" * 64])
def test_a_render_carries_a_real_digest(digest):
    with pytest.raises(ValueError, match="sha256"):
        Rendered("s", "out.mp4", digest)


def test_an_empty_run_is_inconclusive_rather_than_clean():
    assert worst(()) == EXIT_CODES["inconclusive"]


def test_the_loudest_outcome_scores_the_run():
    assert worst((Rendered("a", "f", DIGEST), Inconclusive("b", "no renderer"))) == 2
    assert worst((Rendered("a", "f", DIGEST), Refused("b", "malformed"), Inconclusive("c", "none"))) == 2
    assert worst((Rendered("a", "f", DIGEST), Refused("b", "malformed"))) == 1
    assert worst((Rendered("a", "f", DIGEST),)) == 0


def test_outcomes_are_immutable():
    with pytest.raises(AttributeError):
        Refused("s", "why").reason = "other"
