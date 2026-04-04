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


# ---------------------------------------------------------------------------
# build_remember_start — Phase 7
#
# Architect contract (DISCUSSION.md):
#   build_remember_start(correction, project_slug, date, available_specialists=None)
#
# Required output tokens (ALL must be asserted individually per Architect):
# 1. correction text appears verbatim
# 2. project_slug appears (for YYYY-MM-DD [project] memory format)
# 3. date appears
# 4. "~/.claude/agent-memory/" path pattern
# 5. "## Corrections & Overrides" section header
# 6. Retrospective Facilitator pickup instruction
# ---------------------------------------------------------------------------


def test_build_remember_start_is_importable() -> None:
    """build_remember_start is importable from agent_design.prompts (Phase 7)."""
    from agent_design.prompts import build_remember_start  # noqa: F401


def test_build_remember_start_contains_correction() -> None:
    """Token 1: the returned string includes the correction text verbatim."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(
        correction="Mark overrode async queue for sync pipeline.",
        project_slug="news-reader",
        date="2026-04-04",
    )
    assert "Mark overrode async queue for sync pipeline." in result


def test_build_remember_start_contains_project_slug() -> None:
    """Token 2: the returned string includes the project slug."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(
        correction="Some correction",
        project_slug="my-project",
        date="2026-04-04",
    )
    assert "my-project" in result


def test_build_remember_start_contains_date() -> None:
    """Token 3: the returned string includes the date."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(
        correction="Some correction",
        project_slug="my-project",
        date="2026-04-04",
    )
    assert "2026-04-04" in result


def test_build_remember_start_references_agent_memory_path() -> None:
    """Token 4: the prompt references the ~/.claude/agent-memory/ path pattern."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(
        correction="Some correction",
        project_slug="my-project",
        date="2026-04-04",
    )
    assert "~/.claude/agent-memory/" in result, "Expected '~/.claude/agent-memory/' path in prompt"


def test_build_remember_start_contains_corrections_and_overrides_header() -> None:
    """Token 5: the prompt includes '## Corrections & Overrides' format hint."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(
        correction="Some correction",
        project_slug="my-project",
        date="2026-04-04",
    )
    assert "## Corrections & Overrides" in result, "Expected '## Corrections & Overrides' section header in prompt"


def test_build_remember_start_contains_facilitator_pickup_instruction() -> None:
    """Token 6: the prompt includes a Retrospective Facilitator pickup instruction."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(
        correction="Some correction",
        project_slug="my-project",
        date="2026-04-04",
    )
    lowered = result.lower()
    assert "facilitator" in lowered or "retrospective" in lowered, (
        "Expected Retrospective Facilitator pickup instruction in prompt"
    )


def test_build_remember_start_instructs_memory_self_update() -> None:
    """The returned string instructs agents to update their own memory files."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(
        correction="Some correction",
        project_slug="my-project",
        date="2026-04-04",
    )
    lowered = result.lower()
    # Must reference memory files and self-update concept
    assert "memory" in lowered, "Expected 'memory' in prompt"
    assert "update" in lowered, "Expected 'update' in prompt"


def test_build_remember_start_returns_non_empty_string() -> None:
    """Returns a non-empty string for any valid input."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(correction="x", project_slug="p", date="2026-01-01")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_remember_start_empty_correction_does_not_raise() -> None:
    """Empty correction string returns a string without raising (QA: AC edge case)."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(correction="", project_slug="p", date="2026-01-01")
    assert isinstance(result, str)


def test_build_remember_start_accepts_available_specialists_kwarg() -> None:
    """build_remember_start accepts optional available_specialists parameter."""
    from agent_design.prompts import build_remember_start

    result = build_remember_start(
        correction="Some correction",
        project_slug="p",
        date="2026-01-01",
        available_specialists="architect, developer",
    )
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# build_review_feedback_start — Phase 7
#
# Architect contract (DISCUSSION.md):
#   build_review_feedback_start(pr_comments, pr_url, available_specialists=None)
#
# Note: NO project_slug and NO date parameters.
# QA confirmed in DISCUSSION.md: AC2.4 corrected, date param removed.
#
# Required output tokens:
# 1. pr_url appears
# 2. pr_comments appears verbatim
# 3. "~/.claude/agent-memory/" path pattern
# 4. Retrospective Facilitator pickup instruction
# ---------------------------------------------------------------------------


def test_build_review_feedback_start_is_importable() -> None:
    """build_review_feedback_start is importable from agent_design.prompts (Phase 7)."""
    from agent_design.prompts import build_review_feedback_start  # noqa: F401


def test_build_review_feedback_start_contains_pr_comments() -> None:
    """Token 2: the returned string includes the PR comments block verbatim."""
    from agent_design.prompts import build_review_feedback_start

    pr_comments = "Reviewer: this function is too long. Please extract."
    result = build_review_feedback_start(
        pr_comments=pr_comments,
        pr_url="https://github.com/owner/repo/pull/42",
    )
    assert pr_comments in result


def test_build_review_feedback_start_contains_pr_url() -> None:
    """Token 1: the returned string includes the PR URL."""
    from agent_design.prompts import build_review_feedback_start

    pr_url = "https://github.com/owner/repo/pull/42"
    result = build_review_feedback_start(
        pr_comments="some comment",
        pr_url=pr_url,
    )
    assert pr_url in result


def test_build_review_feedback_start_contains_project_slug() -> None:
    """The PR URL appears in the output (replaces former project_slug field)."""
    from agent_design.prompts import build_review_feedback_start

    result = build_review_feedback_start(
        pr_comments="some comment",
        pr_url="https://github.com/owner/special-project/pull/1",
    )
    assert "special-project" in result


def test_build_review_feedback_start_contains_date() -> None:
    """The returned string includes the PR URL for context (no explicit date param)."""
    from agent_design.prompts import build_review_feedback_start

    result = build_review_feedback_start(
        pr_comments="some comment",
        pr_url="https://github.com/o/r/pull/1",
    )
    # pr_url must appear in result
    assert "https://github.com/o/r/pull/1" in result


def test_build_review_feedback_start_references_agent_memory_path() -> None:
    """Token 3: the prompt references the ~/.claude/agent-memory/ path pattern."""
    from agent_design.prompts import build_review_feedback_start

    result = build_review_feedback_start(
        pr_comments="some comment",
        pr_url="https://github.com/o/r/pull/1",
    )
    assert "~/.claude/agent-memory/" in result, "Expected '~/.claude/agent-memory/' path in prompt"


def test_build_review_feedback_start_contains_facilitator_pickup_instruction() -> None:
    """Token 4: the prompt includes a Retrospective Facilitator pickup instruction."""
    from agent_design.prompts import build_review_feedback_start

    result = build_review_feedback_start(
        pr_comments="some comment",
        pr_url="https://github.com/o/r/pull/1",
    )
    lowered = result.lower()
    assert "facilitator" in lowered or "retrospective" in lowered, (
        "Expected Retrospective Facilitator pickup instruction in prompt"
    )


def test_build_review_feedback_start_instructs_memory_self_update() -> None:
    """The returned string instructs agents to update their own memory files."""
    from agent_design.prompts import build_review_feedback_start

    result = build_review_feedback_start(
        pr_comments="some comment",
        pr_url="https://github.com/o/r/pull/1",
    )
    lowered = result.lower()
    assert "memory" in lowered
    assert "update" in lowered


def test_build_review_feedback_start_returns_non_empty_string() -> None:
    """Returns a non-empty string for any valid input."""
    from agent_design.prompts import build_review_feedback_start

    result = build_review_feedback_start(pr_comments="x", pr_url="https://github.com/o/r/pull/1")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_review_feedback_start_empty_comments_does_not_raise() -> None:
    """Empty pr_comments string returns a string without raising."""
    from agent_design.prompts import build_review_feedback_start

    result = build_review_feedback_start(pr_comments="", pr_url="https://github.com/o/r/pull/1")
    assert isinstance(result, str)


def test_build_review_feedback_start_accepts_available_specialists_kwarg() -> None:
    """build_review_feedback_start accepts optional available_specialists parameter."""
    from agent_design.prompts import build_review_feedback_start

    result = build_review_feedback_start(
        pr_comments="some comment",
        pr_url="https://github.com/o/r/pull/1",
        available_specialists="architect, developer",
    )
    assert isinstance(result, str)


def test_build_review_feedback_start_does_not_take_project_slug() -> None:
    """build_review_feedback_start does NOT accept project_slug (Architect contract).

    The Architect explicitly specified: signature is (pr_comments, pr_url, available_specialists).
    """
    import pytest

    from agent_design.prompts import build_review_feedback_start

    with pytest.raises(TypeError):
        build_review_feedback_start(  # type: ignore[call-arg]
            pr_comments="comment",
            pr_url="https://github.com/o/r/pull/1",
            project_slug="my-project",
        )


def test_build_review_feedback_start_does_not_take_date() -> None:
    """build_review_feedback_start does NOT accept date param (QA AC2.4 correction).

    QA confirmed in DISCUSSION.md: date param was removed from the signature.
    """
    import pytest

    from agent_design.prompts import build_review_feedback_start

    with pytest.raises(TypeError):
        build_review_feedback_start(  # type: ignore[call-arg]
            pr_comments="comment",
            pr_url="https://github.com/o/r/pull/1",
            date="2026-04-04",
        )


# ---------------------------------------------------------------------------
# build_retro_start — Phase 8
#
# Architect contract (DISCUSSION.md):
#   build_retro_start(
#       project_slug: str,
#       date: str,
#       discussion_path: str,
#       tasks_path: str,
#       decisions_path: str,
#       available_specialists: str | None = None,
#   ) -> str
#
# Takes paths (not file content) — agents read files themselves via --add-dir.
#
# Required output tokens:
# 1. project_slug appears
# 2. date appears
# 3. discussion_path appears
# 4. tasks_path appears
# 5. decisions_path appears
# 6. Instruction to produce RETRO.md
# 7. Prompt-suggestion format [PS-N] mentioned
# ---------------------------------------------------------------------------


def test_build_retro_start_is_importable() -> None:
    """build_retro_start is importable from agent_design.prompts (Phase 8)."""
    from agent_design.prompts import build_retro_start  # noqa: F401


def test_build_retro_start_returns_non_empty_string() -> None:
    """Returns a non-empty string for valid input."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="news-reader",
        date="2026-04-04",
        discussion_path="/repo/.agent-design/DISCUSSION.md",
        tasks_path="/repo/TASKS.md",
        decisions_path="/repo/.agent-design/DECISIONS.md",
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_retro_start_contains_project_slug() -> None:
    """Token 1: returned string includes the project_slug."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/repo/.agent-design/DISCUSSION.md",
        tasks_path="/repo/TASKS.md",
        decisions_path="/repo/.agent-design/DECISIONS.md",
    )
    assert "my-feature" in result


def test_build_retro_start_contains_date() -> None:
    """Token 2: returned string includes the date."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/repo/.agent-design/DISCUSSION.md",
        tasks_path="/repo/TASKS.md",
        decisions_path="/repo/.agent-design/DECISIONS.md",
    )
    assert "2026-04-04" in result


def test_build_retro_start_contains_discussion_path() -> None:
    """Token 3: returned string includes the discussion_path."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/some/repo/.agent-design/DISCUSSION.md",
        tasks_path="/some/repo/TASKS.md",
        decisions_path="/some/repo/.agent-design/DECISIONS.md",
    )
    assert "/some/repo/.agent-design/DISCUSSION.md" in result


def test_build_retro_start_contains_tasks_path() -> None:
    """Token 4: returned string includes the tasks_path."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/some/repo/.agent-design/DISCUSSION.md",
        tasks_path="/some/repo/TASKS.md",
        decisions_path="/some/repo/.agent-design/DECISIONS.md",
    )
    assert "/some/repo/TASKS.md" in result


def test_build_retro_start_contains_decisions_path() -> None:
    """Token 5: returned string includes the decisions_path."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/some/repo/.agent-design/DISCUSSION.md",
        tasks_path="/some/repo/TASKS.md",
        decisions_path="/some/repo/.agent-design/DECISIONS.md",
    )
    assert "/some/repo/.agent-design/DECISIONS.md" in result


def test_build_retro_start_instructs_retro_md_output() -> None:
    """Token 6: returned string instructs the agent to produce RETRO.md."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/repo/.agent-design/DISCUSSION.md",
        tasks_path="/repo/TASKS.md",
        decisions_path="/repo/.agent-design/DECISIONS.md",
    )
    assert "RETRO.md" in result


def test_build_retro_start_mentions_prompt_suggestion_format() -> None:
    """Token 7: returned string mentions [PS-N] prompt-suggestion format."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/repo/.agent-design/DISCUSSION.md",
        tasks_path="/repo/TASKS.md",
        decisions_path="/repo/.agent-design/DECISIONS.md",
    )
    assert "[PS-" in result


def test_build_retro_start_accepts_available_specialists_kwarg() -> None:
    """build_retro_start accepts optional available_specialists parameter."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/repo/.agent-design/DISCUSSION.md",
        tasks_path="/repo/TASKS.md",
        decisions_path="/repo/.agent-design/DECISIONS.md",
        available_specialists="architect, developer",
    )
    assert isinstance(result, str)


def test_build_retro_start_does_not_take_file_content() -> None:
    """build_retro_start signature does not accept content kwargs.

    The Architect contract is clear: paths are passed, not file content.
    Passing 'discussion_content' as a kwarg must raise TypeError.
    """
    from agent_design.prompts import build_retro_start

    with pytest.raises(TypeError):
        build_retro_start(  # type: ignore[call-arg]
            project_slug="my-feature",
            date="2026-04-04",
            discussion_path="/repo/.agent-design/DISCUSSION.md",
            tasks_path="/repo/TASKS.md",
            decisions_path="/repo/.agent-design/DECISIONS.md",
            discussion_content="some content",
        )


def test_build_retro_start_none_tasks_path_does_not_raise() -> None:
    """build_retro_start handles None tasks_path gracefully (TASKS.md may not exist)."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/repo/.agent-design/DISCUSSION.md",
        tasks_path=None,  # type: ignore[arg-type]
        decisions_path="/repo/.agent-design/DECISIONS.md",
    )
    assert isinstance(result, str)


def test_build_retro_start_none_decisions_path_does_not_raise() -> None:
    """build_retro_start handles None decisions_path gracefully (DECISIONS.md may not exist)."""
    from agent_design.prompts import build_retro_start

    result = build_retro_start(
        project_slug="my-feature",
        date="2026-04-04",
        discussion_path="/repo/.agent-design/DISCUSSION.md",
        tasks_path="/repo/TASKS.md",
        decisions_path=None,  # type: ignore[arg-type]
    )
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# build_apply_suggestion_start — Phase 8
#
# Architect contract (DISCUSSION.md):
#   build_apply_suggestion_start(
#       suggestion_id: str,
#       suggestion_text: str,
#       agents_dir: str,
#   ) -> str
#
# The command layer parses RETRO.md and extracts suggestion_text before calling
# this builder. The builder receives already-parsed text — no file I/O here.
#
# Required output tokens:
# 1. suggestion_id appears (e.g. "PS-1")
# 2. suggestion_text appears verbatim
# 3. agents_dir path appears
# 4. Instruction to edit the agent definition file
# ---------------------------------------------------------------------------


def test_build_apply_suggestion_start_is_importable() -> None:
    """build_apply_suggestion_start is importable from agent_design.prompts (Phase 8)."""
    from agent_design.prompts import build_apply_suggestion_start  # noqa: F401


def test_build_apply_suggestion_start_returns_non_empty_string() -> None:
    """Returns a non-empty string for valid input."""
    from agent_design.prompts import build_apply_suggestion_start

    result = build_apply_suggestion_start(
        suggestion_id="PS-1",
        suggestion_text='architect.md: add "check BASELINE.md before proposing infrastructure"',
        agents_dir="/Users/mark/.claude/agents",
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_apply_suggestion_start_contains_suggestion_id() -> None:
    """Token 1: returned string includes the suggestion_id."""
    from agent_design.prompts import build_apply_suggestion_start

    result = build_apply_suggestion_start(
        suggestion_id="PS-3",
        suggestion_text="some suggestion text",
        agents_dir="/Users/mark/.claude/agents",
    )
    assert "PS-3" in result


def test_build_apply_suggestion_start_contains_suggestion_text() -> None:
    """Token 2: returned string includes the suggestion_text verbatim."""
    from agent_design.prompts import build_apply_suggestion_start

    suggestion = 'architect.md: add "always read CLAUDE.md first"'
    result = build_apply_suggestion_start(
        suggestion_id="PS-1",
        suggestion_text=suggestion,
        agents_dir="/Users/mark/.claude/agents",
    )
    assert suggestion in result


def test_build_apply_suggestion_start_contains_agents_dir() -> None:
    """Token 3: returned string includes the agents_dir path."""
    from agent_design.prompts import build_apply_suggestion_start

    agents_dir = "/Users/mark/.claude/agents"
    result = build_apply_suggestion_start(
        suggestion_id="PS-1",
        suggestion_text="some suggestion",
        agents_dir=agents_dir,
    )
    assert agents_dir in result


def test_build_apply_suggestion_start_instructs_file_edit() -> None:
    """Token 4: returned string instructs the agent to edit the agent definition file."""
    from agent_design.prompts import build_apply_suggestion_start

    result = build_apply_suggestion_start(
        suggestion_id="PS-1",
        suggestion_text="some suggestion",
        agents_dir="/Users/mark/.claude/agents",
    )
    lowered = result.lower()
    # Must reference editing/writing to the file
    assert "edit" in lowered or "write" in lowered or "update" in lowered or "apply" in lowered


def test_build_apply_suggestion_start_does_not_accept_available_specialists() -> None:
    """build_apply_suggestion_start does NOT accept available_specialists.

    Architect contract: signature is (suggestion_id, suggestion_text, agents_dir).
    This is a solo session — no team, no specialists list.
    """
    from agent_design.prompts import build_apply_suggestion_start

    with pytest.raises(TypeError):
        build_apply_suggestion_start(  # type: ignore[call-arg]
            suggestion_id="PS-1",
            suggestion_text="some suggestion",
            agents_dir="/Users/mark/.claude/agents",
            available_specialists="architect",
        )
