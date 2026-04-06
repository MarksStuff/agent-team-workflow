"""Tests for the `agent-design review-proposal` CLI command.

Derivation:
- Takes a positional argument `name` (required)
- Optional --repo-path (default: current dir)
- Reads .agent-design/proposals/<name>.md from repo_path
- Prints the proposal content to stdout (no Claude subprocess)
- Errors if proposal file not found
- Registered as 'review-proposal' in agent_design.cli.main.cli

All external dependencies are patched. No real subprocess or filesystem writes
are made beyond what the tests themselves set up.
"""

from pathlib import Path

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_PROPOSAL_CONTENT = """\
# Agent Proposal: sample_expert

**Proposed by:** Eng Manager
**Session:** feat/example — 2026-04-05
**Gap identified:** Sample expertise needed.

**Proposed location:** ~/.claude/agents/sample_expert.md
**Rationale:** Global expertise.

**Agent type:** Domain expert

---

## Agent Definition (written verbatim if approved)

---
name: sample_expert
description: >
  Sample domain expert.
model: claude-sonnet-4-6
tools: WebSearch, WebFetch, Read
---

You are a sample domain expert.
"""


def _write_proposal(tmp_path: Path, name: str, content: str = SAMPLE_PROPOSAL_CONTENT) -> Path:
    """Write a proposals/<name>.md under <tmp_path>/.agent-design/ and return its path."""
    proposals_dir = tmp_path / ".agent-design" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    proposal_file = proposals_dir / f"{name}.md"
    proposal_file.write_text(content)
    return proposal_file


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestReviewProposalCommandRegistered:
    """The `review-proposal` command is importable and registered in main CLI."""

    def test_review_proposal_module_importable(self) -> None:
        """agent_design.cli.commands.review_proposal is importable."""
        from agent_design.cli.commands import review_proposal  # noqa: F401

    def test_review_proposal_command_callable(self) -> None:
        """The review_proposal Click command object is callable."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        assert callable(cmd)

    def test_review_proposal_registered_in_main_cli(self) -> None:
        """The 'review-proposal' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "review-proposal" in cli.commands, "'review-proposal' not registered in main.py"

    def test_review_proposal_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestReviewProposalArguments:
    """The `review-proposal` command argument surface."""

    def test_name_is_required(self, tmp_path: Path) -> None:
        """Calling review-proposal with no name must exit non-zero."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code != 0

    def test_name_accepted_as_positional(self, tmp_path: Path) -> None:
        """name is accepted as a positional argument without raising."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "sample_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["sample_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "another_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["another_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Reading and displaying the proposal
# ---------------------------------------------------------------------------


class TestReviewProposalReadsFile:
    """review-proposal reads and displays the proposal file content."""

    def test_reads_proposal_file(self, tmp_path: Path) -> None:
        """Command exits 0 when proposal file exists."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "sample_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["sample_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_shows_proposal_content_in_output(self, tmp_path: Path) -> None:
        """Command prints the proposal file content to stdout."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "sample_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["sample_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        # The proposal content (or a key distinctive piece) should appear in output
        assert "sample_expert" in (result.output or "")

    def test_shows_proposed_location_in_output(self, tmp_path: Path) -> None:
        """Command output includes the proposed location from the proposal."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "sample_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["sample_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        # The proposed location line should appear in output
        assert "sample_expert.md" in (result.output or "")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestReviewProposalErrorHandling:
    """review-proposal handles missing proposal files gracefully."""

    def test_missing_proposal_exits_nonzero(self, tmp_path: Path) -> None:
        """If the proposal file does not exist, command exits non-zero."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent_proposal", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_missing_proposal_shows_error_message(self, tmp_path: Path) -> None:
        """If proposal file not found, command prints an informative error."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent_proposal", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("not found", "missing", "does not exist", "error", "nonexistent_proposal", "no such")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"
