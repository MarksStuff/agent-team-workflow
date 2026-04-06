"""Tests for RoundState serialization and phase management."""

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from agent_design.state import RoundState, generate_slug, load_round_state, save_round_state


def test_round_state_defaults() -> None:
    state = RoundState(
        feature_slug="test-feature",
        feature_request="Build something cool",
        target_repo="/some/repo",
    )
    assert state.discussion_turns == 0
    assert state.completed == []
    assert state.pr_url is None
    assert state.checkpoint_tag is None
    assert state.baseline_commit is None


def test_round_state_core_fields() -> None:
    """RoundState stores and retrieves its core non-phase fields correctly."""
    state = RoundState(
        feature_slug="news-admin-cli",
        feature_request="Build an admin CLI",
        target_repo="/Users/mark/news_reader",
        discussion_turns=3,
        completed=["baseline", "initial_draft"],
    )
    assert state.feature_slug == "news-admin-cli"
    assert state.discussion_turns == 3
    assert state.completed == ["baseline", "initial_draft"]


def test_round_state_roundtrip_json() -> None:
    """RoundState survives JSON serialization round-trip via asdict."""
    from dataclasses import asdict

    original = RoundState(
        feature_slug="test-slug",
        feature_request="A feature request",
        target_repo="/tmp/repo",
        discussion_turns=5,
        completed=["baseline", "initial_draft", "open_discussion"],
        pr_url="https://github.com/MarksStuff/repo/pull/42",
        checkpoint_tag="chk-phase-2",
        baseline_commit="abc123",
    )
    data = asdict(original)
    restored = RoundState(**data)

    assert restored.feature_slug == original.feature_slug
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
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        save_round_state(path, state)

        assert (path / "ROUND_STATE.json").exists()
        loaded = load_round_state(path)

        assert loaded.feature_slug == state.feature_slug
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


# ---------------------------------------------------------------------------
# Phase 5: RoundState without `phase` field
# (AC2 in DESIGN.md Phase 5 acceptance criteria)
# These tests are RED until the `phase` field is removed from RoundState.
# ---------------------------------------------------------------------------


def test_round_state_has_no_phase_attribute() -> None:
    """After Phase 5: RoundState must not have a `phase` attribute (AC2).

    This test is RED while `phase` still exists on the dataclass.
    """
    state = RoundState(
        feature_slug="test-feature",
        feature_request="Build something",
        target_repo="/some/repo",
    )
    assert not hasattr(state, "phase"), "RoundState still has a `phase` attribute — it must be removed in Phase 5"


def test_phase_type_not_importable_from_state() -> None:
    """After Phase 5: PhaseType must not be importable from agent_design.state (AC2)."""
    import agent_design.state as state_module

    assert not hasattr(state_module, "PhaseType"), "PhaseType still exists in state.py — it must be removed in Phase 5"


def test_round_state_constructor_rejects_phase_kwarg() -> None:
    """After Phase 5: passing `phase` as a kwarg to RoundState must raise TypeError (AC2)."""
    import pytest  # noqa: PLC0415

    with pytest.raises(TypeError):
        RoundState(  # type: ignore[call-arg]
            feature_slug="test",
            feature_request="request",
            target_repo="/repo",
            phase="open_discussion",
        )


def test_load_round_state_ignores_phase_key_in_old_json(tmp_path: Path) -> None:
    """load_round_state() on old JSON with a 'phase' key must not raise TypeError (AC2).

    Old ROUND_STATE.json files on disk will have "phase": "awaiting_human".
    After Phase 5 removes the field from the dataclass, RoundState(**data) would
    raise TypeError unless load_round_state strips unknown keys first.
    """
    old_state_data = {
        "feature_slug": "old-feature",
        "feature_request": "An old feature",
        "target_repo": "/old/repo",
        "phase": "awaiting_human",  # legacy field
        "discussion_turns": 2,
        "baseline_commit": None,
        "completed": ["baseline", "initial_draft"],
        "pr_url": None,
        "checkpoint_tag": None,
    }
    state_file = tmp_path / "ROUND_STATE.json"
    state_file.write_text(json.dumps(old_state_data))

    # Must not raise TypeError despite 'phase' being present in JSON
    loaded = load_round_state(tmp_path)

    # All valid fields must be preserved
    assert loaded.feature_slug == "old-feature"
    assert loaded.feature_request == "An old feature"
    assert loaded.target_repo == "/old/repo"
    assert loaded.discussion_turns == 2
    assert loaded.completed == ["baseline", "initial_draft"]


def test_load_round_state_without_phase_key_succeeds(tmp_path: Path) -> None:
    """load_round_state() on new-format JSON (no 'phase' key) must succeed (AC2)."""
    new_state_data = {
        "feature_slug": "new-feature",
        "feature_request": "A new feature",
        "target_repo": "/new/repo",
        "discussion_turns": 0,
        "baseline_commit": None,
        "completed": [],
        "pr_url": None,
        "checkpoint_tag": None,
    }
    state_file = tmp_path / "ROUND_STATE.json"
    state_file.write_text(json.dumps(new_state_data))

    loaded = load_round_state(tmp_path)

    assert loaded.feature_slug == "new-feature"
    assert loaded.discussion_turns == 0
    assert loaded.completed == []


def test_round_state_roundtrip_without_phase(tmp_path: Path) -> None:
    """New-format RoundState round-trips through save/load without phase (AC2)."""
    original = RoundState(
        feature_slug="roundtrip-test",
        feature_request="Test round-trip",
        target_repo="/tmp/repo",
        discussion_turns=3,
        completed=["baseline", "initial_draft"],
        pr_url="https://github.com/owner/repo/pull/7",
        checkpoint_tag="chk-review",
        baseline_commit="deadbeef",
    )

    save_round_state(tmp_path, original)
    loaded = load_round_state(tmp_path)

    assert loaded.feature_slug == original.feature_slug
    assert loaded.feature_request == original.feature_request
    assert loaded.target_repo == original.target_repo
    assert loaded.discussion_turns == original.discussion_turns
    assert loaded.completed == original.completed
    assert loaded.pr_url == original.pr_url
    assert loaded.checkpoint_tag == original.checkpoint_tag
    assert loaded.baseline_commit == original.baseline_commit
    # Confirm no phase key in saved JSON
    saved_data = json.loads((tmp_path / "ROUND_STATE.json").read_text())
    assert "phase" not in saved_data


def test_load_round_state_missing_required_field_raises(tmp_path: Path) -> None:
    """load_round_state() on JSON missing required field raises descriptive error (EC2).

    Missing `feature_slug` must raise, not silently produce a broken object.
    """
    import pytest  # noqa: PLC0415

    incomplete_data = {
        # feature_slug intentionally missing
        "feature_request": "A feature",
        "target_repo": "/repo",
        "discussion_turns": 0,
        "completed": [],
    }
    (tmp_path / "ROUND_STATE.json").write_text(json.dumps(incomplete_data))

    with pytest.raises((TypeError, KeyError)):
        load_round_state(tmp_path)


def test_load_round_state_invalid_json_raises_value_error(tmp_path: Path) -> None:
    """load_round_state() on invalid JSON raises ValueError (EC3 — existing contract)."""
    import pytest  # noqa: PLC0415

    (tmp_path / "ROUND_STATE.json").write_text("{not valid json}")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_round_state(tmp_path)


def test_round_state_serialised_dict_has_no_phase_key() -> None:
    """asdict(RoundState(...)) must not include 'phase' key after Phase 5 (AC2)."""
    state = RoundState(
        feature_slug="serialise-test",
        feature_request="Test serialise",
        target_repo="/repo",
    )
    data = asdict(state)
    assert "phase" not in data, "phase key must not appear in serialised RoundState after Phase 5"
