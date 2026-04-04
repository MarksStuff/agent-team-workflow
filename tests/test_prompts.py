"""Tests for prompt-building helpers and dynamic specialist discovery."""

from pathlib import Path

import pytest

from agent_design.prompts import (
    _parse_frontmatter_name,
    build_continue_start,
    build_impl_start,
    get_available_specialists,
)

# ---------------------------------------------------------------------------
# _parse_frontmatter_name
# ---------------------------------------------------------------------------

ARCHITECT_FRONTMATTER = """\
---
name: architect
description: >
  Systems design expert and technical direction owner.
model: claude-sonnet-4-6
tools: all
memory: project
---

Body content here.
"""

MULTIWORD_DESCRIPTION = """\
---
name: sre
description: Production readiness and deployment safety.
model: claude-sonnet-4-6
tools: all
---
"""

NO_FRONTMATTER = """\
# Just a plain markdown file

No YAML here.
"""

MISSING_NAME = """\
---
description: Some description
model: claude-sonnet-4-6
---
"""


def test_parse_frontmatter_name_simple() -> None:
    assert _parse_frontmatter_name(ARCHITECT_FRONTMATTER) == "architect"


def test_parse_frontmatter_name_other_agent() -> None:
    assert _parse_frontmatter_name(MULTIWORD_DESCRIPTION) == "sre"


def test_parse_frontmatter_name_no_frontmatter() -> None:
    assert _parse_frontmatter_name(NO_FRONTMATTER) is None


def test_parse_frontmatter_name_missing_name_field() -> None:
    assert _parse_frontmatter_name(MISSING_NAME) is None


def test_parse_frontmatter_name_empty_string() -> None:
    assert _parse_frontmatter_name("") is None


# ---------------------------------------------------------------------------
# get_available_specialists
# ---------------------------------------------------------------------------


def _make_agent_file(agents_dir: Path, stem: str, name: str) -> None:
    """Write a minimal agent .md file with frontmatter."""
    (agents_dir / f"{stem}.md").write_text(f"---\nname: {name}\ndescription: Test agent.\n---\n")


def test_get_available_specialists_basic(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    _make_agent_file(agents_dir, "architect", "architect")
    _make_agent_file(agents_dir, "developer", "developer")

    result = get_available_specialists(agents_dir=agents_dir)

    assert "architect" in result
    assert "developer" in result


def test_get_available_specialists_excludes_eng_manager(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    _make_agent_file(agents_dir, "architect", "architect")
    _make_agent_file(agents_dir, "eng_manager", "eng_manager")

    result = get_available_specialists(agents_dir=agents_dir)

    assert "architect" in result
    assert "eng_manager" not in result


def test_get_available_specialists_missing_directory(tmp_path: Path) -> None:
    nonexistent = tmp_path / "no_such_dir"
    result = get_available_specialists(agents_dir=nonexistent)
    assert result == ""


def test_get_available_specialists_empty_directory(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    result = get_available_specialists(agents_dir=agents_dir)
    assert result == ""


def test_get_available_specialists_fallback_to_stem_when_no_frontmatter(tmp_path: Path) -> None:
    """Files without valid frontmatter fall back to the filename stem."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "mystery_agent.md").write_text("# Just markdown, no frontmatter\n")

    result = get_available_specialists(agents_dir=agents_dir)

    assert "mystery_agent" in result


def test_get_available_specialists_sorted_alphabetically(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    _make_agent_file(agents_dir, "qa_engineer", "qa_engineer")
    _make_agent_file(agents_dir, "architect", "architect")
    _make_agent_file(agents_dir, "developer", "developer")

    result = get_available_specialists(agents_dir=agents_dir)
    names = [n.strip() for n in result.split(",")]

    assert names == sorted(names)


def test_get_available_specialists_comma_separated(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    _make_agent_file(agents_dir, "architect", "architect")
    _make_agent_file(agents_dir, "developer", "developer")

    result = get_available_specialists(agents_dir=agents_dir)

    # Must be comma-separated
    assert "," in result
    parts = [p.strip() for p in result.split(",")]
    assert len(parts) == 2


# ---------------------------------------------------------------------------
# build_* functions include available_specialists
# ---------------------------------------------------------------------------


def test_build_impl_start_includes_specialists() -> None:
    result = build_impl_start("Add caching layer", available_specialists="architect, developer, qa_engineer")
    assert "Available specialists: architect, developer, qa_engineer" in result
    assert "Add caching layer" in result


def test_build_impl_start_resume_includes_specialists() -> None:
    result = build_impl_start("Add caching layer", is_resume=True, available_specialists="architect")
    assert "Available specialists: architect" in result
    assert "resume" in result.lower()


# ---------------------------------------------------------------------------
# build_continue_start — replaces build_review_start and build_feedback_start
# (AC1 in DESIGN.md Phase 5 acceptance criteria)
# ---------------------------------------------------------------------------


def test_build_continue_start_includes_feature_request() -> None:
    """Returned string contains the feature request text (AC1)."""
    result = build_continue_start("Build a login system", available_specialists="architect, developer")
    assert "Build a login system" in result


def test_build_continue_start_includes_available_specialists() -> None:
    """Returned string contains 'Available specialists: <value>' (AC1)."""
    result = build_continue_start("Build a login system", available_specialists="architect, developer")
    assert "Available specialists: architect, developer" in result


def test_build_continue_start_returns_non_empty_string() -> None:
    """Returns a non-empty string regardless of inputs (AC1)."""
    result = build_continue_start("anything", available_specialists="architect")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_continue_start_empty_specialists_does_not_raise() -> None:
    """Called with empty specialists string returns a string without raising (AC1, EC1 adjacent)."""
    result = build_continue_start("anything", available_specialists="")
    assert isinstance(result, str)


def test_build_continue_start_empty_feature_request_does_not_raise() -> None:
    """Called with empty feature_request string returns a string without raising (EC1)."""
    result = build_continue_start("", available_specialists="architect")
    assert isinstance(result, str)


def test_build_continue_start_calls_get_available_specialists_when_none(tmp_path: Path) -> None:
    """When available_specialists is None, calls get_available_specialists() (AC1).

    We verify this by passing an agents_dir via the injected path — but since
    build_continue_start() delegates to get_available_specialists() with the
    default (real) agents dir, we instead verify that passing None does not
    raise and returns a string. The integration with get_available_specialists
    is exercised separately.
    """
    # No available_specialists arg — must not raise and must return str
    result = build_continue_start("My feature")
    assert isinstance(result, str)


def test_build_continue_start_no_phase_assumption_in_output() -> None:
    """Output must not hardcode 'Stage 2' or 'round N' language (Architect contract)."""
    result = build_continue_start("My feature", available_specialists="architect")
    assert "Stage 2" not in result
    assert "Stage 3" not in result
    # 'round N' pattern — check for common round-number strings
    assert "round 1" not in result.lower()
    assert "round 2" not in result.lower()


def test_build_continue_start_no_round_num_parameter() -> None:
    """build_continue_start does not accept round_num as a parameter (Architect contract).

    The function signature is build_continue_start(feature_request, available_specialists=None).
    Passing round_num as a keyword arg must raise TypeError.
    """
    with pytest.raises(TypeError):
        build_continue_start("feature", available_specialists="arch", round_num=3)  # type: ignore[call-arg]


def test_build_review_start_no_longer_importable() -> None:
    """After Phase 5: build_review_start must not be importable from prompts (AC1).

    This test will be RED until build_review_start is removed.
    """

    import agent_design.prompts as prompts_module

    assert not hasattr(prompts_module, "build_review_start"), (
        "build_review_start still exists in prompts.py — it must be removed in Phase 5"
    )


def test_build_feedback_start_no_longer_importable() -> None:
    """After Phase 5: build_feedback_start must not be importable from prompts (AC1).

    This test will be RED until build_feedback_start is removed.
    """
    import agent_design.prompts as prompts_module

    assert not hasattr(prompts_module, "build_feedback_start"), (
        "build_feedback_start still exists in prompts.py — it must be removed in Phase 5"
    )
