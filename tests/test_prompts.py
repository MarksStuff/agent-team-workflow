"""Tests for prompt-building helpers and dynamic specialist discovery."""

from pathlib import Path

from agent_design.prompts import (
    _parse_frontmatter_name,
    build_feedback_start,
    build_impl_start,
    build_review_start,
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


def test_build_review_start_includes_specialists() -> None:
    result = build_review_start("Build a login system", available_specialists="architect, developer")
    assert "Available specialists: architect, developer" in result
    assert "Build a login system" in result


def test_build_impl_start_includes_specialists() -> None:
    result = build_impl_start("Add caching layer", available_specialists="architect, developer, qa_engineer")
    assert "Available specialists: architect, developer, qa_engineer" in result
    assert "Add caching layer" in result


def test_build_impl_start_resume_includes_specialists() -> None:
    result = build_impl_start("Add caching layer", is_resume=True, available_specialists="architect")
    assert "Available specialists: architect" in result
    assert "resume" in result.lower()


def test_build_feedback_start_includes_specialists() -> None:
    result = build_feedback_start(2, feature_request="Add caching", available_specialists="architect, developer")
    assert "Available specialists: architect, developer" in result
    assert "round 2" in result.lower()
    assert "Add caching" in result


def test_build_feedback_start_includes_feature_request() -> None:
    result = build_feedback_start(1, feature_request="My feature", available_specialists="architect")
    assert "My feature" in result


def test_build_review_start_empty_specialists_allowed() -> None:
    """build_review_start accepts an empty specialists string without error."""
    result = build_review_start("Build something", available_specialists="")
    assert isinstance(result, str)
    assert "Build something" in result
    assert "Available specialists:" in result
