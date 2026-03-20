"""Tests for RoundState serialization and phase management."""

import tempfile
from pathlib import Path

from agent_design.state import RoundState, generate_slug, load_round_state, save_round_state


def test_round_state_defaults() -> None:
    state = RoundState(
        feature_slug="test-feature",
        feature_request="Build something cool",
        target_repo="/some/repo",
    )
    assert state.phase == "baseline"
    assert state.discussion_turns == 0
    assert state.completed == []
    assert state.pr_url is None
    assert state.checkpoint_tag is None
    assert state.baseline_commit is None


def test_round_state_fields() -> None:
    state = RoundState(
        feature_slug="news-admin-cli",
        feature_request="Build an admin CLI",
        target_repo="/Users/mark/news_reader",
        phase="open_discussion",
        discussion_turns=3,
        completed=["baseline", "initial_draft"],
    )
    assert state.feature_slug == "news-admin-cli"
    assert state.phase == "open_discussion"
    assert state.discussion_turns == 3
    assert state.completed == ["baseline", "initial_draft"]


def test_round_state_roundtrip_json() -> None:
    """RoundState survives JSON serialization round-trip via asdict."""
    from dataclasses import asdict

    original = RoundState(
        feature_slug="test-slug",
        feature_request="A feature request",
        target_repo="/tmp/repo",
        phase="awaiting_human",
        discussion_turns=5,
        completed=["baseline", "initial_draft", "open_discussion"],
        pr_url="https://github.com/MarksStuff/repo/pull/42",
        checkpoint_tag="chk-phase-2",
        baseline_commit="abc123",
    )
    data = asdict(original)
    restored = RoundState(**data)

    assert restored.feature_slug == original.feature_slug
    assert restored.phase == original.phase
    assert restored.discussion_turns == original.discussion_turns
    assert restored.completed == original.completed
    assert restored.pr_url == original.pr_url
    assert restored.checkpoint_tag == original.checkpoint_tag
    assert restored.baseline_commit == original.baseline_commit


def test_save_and_load_state() -> None:
    state = RoundState(
        feature_slug="save-load-test",
        feature_request="Test save/load",
        target_repo="/tmp/repo",
        phase="initial_draft",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        save_round_state(path, state)

        assert (path / "ROUND_STATE.json").exists()
        loaded = load_round_state(path)

        assert loaded.feature_slug == state.feature_slug
        assert loaded.phase == state.phase
        assert loaded.feature_request == state.feature_request


def test_load_state_missing_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            load_round_state(Path(tmpdir))
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass


def test_generate_slug_basic() -> None:
    assert generate_slug("Build a news admin CLI tool") == "build-a-news-admin-cli-tool"


def test_generate_slug_special_chars() -> None:
    slug = generate_slug("Feature with special chars! @#$%")
    assert all(c.isalnum() or c == "-" for c in slug)
    assert not slug.startswith("-")
    assert not slug.endswith("-")


def test_generate_slug_max_length() -> None:
    long_slug = generate_slug("A very long feature request " * 10)
    assert len(long_slug) <= 40
