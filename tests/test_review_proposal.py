"""Tests for the `agent-design review-proposal` CLI command.

Derivation:
- Takes a positional argument `agent_name` (e.g. "crypto_expert")
- Optional --repo-path (default: current dir)
- Reads proposal file from <repo_path>/.agent-design/proposals/<agent_name>.md
- Outputs the file content to stdout
- Outputs a hint about apply-proposal
- No subprocess is called
- Proposal file does not exist → abort with message mentioning the missing path

No subprocess patching needed — this is a pure file read + console output command.
"""

from pathlib import Path

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_PROPOSAL_CONTENT = """\
# Agent Proposal: myagent

**Proposed by:** Architect
**Session:** feat/some-feature — 2026-04-05
**Gap identified:** Domain expertise needed

**Proposed location:** `~/.claude/agents/myagent.md`
**Rationale:** Specialised knowledge required.

**Agent type:** Domain expert

---

## Agent Definition (written verbatim if approved)

---
name: myagent
description: >
  A domain expert agent.
model: claude-sonnet-4-6
tools: Read
---

You are a domain expert.
"""


def _write_proposal(tmp_path: Path, agent_name: str, content: str = SAMPLE_PROPOSAL_CONTENT) -> Path:
    """Write a proposal file under <tmp_path>/.agent-design/proposals/ and return its path."""
    proposals_dir = tmp_path / ".agent-design" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    proposal_file = proposals_dir / f"{agent_name}.md"
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
# Happy path
# ---------------------------------------------------------------------------


class TestReviewProposalHappyPath:
    """review-proposal outputs proposal content and a hint about apply-proposal."""

    def test_exits_zero_with_valid_proposal(self, tmp_path: Path) -> None:
        """Command exits 0 when proposal file exists."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "myagent")

        runner = CliRunner()
        result = runner.invoke(cmd, ["myagent", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0

    def test_outputs_proposal_file_content(self, tmp_path: Path) -> None:
        """Command outputs the raw content of the proposal file."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        custom_content = "# Agent Proposal: myagent\n\nUnique marker: XYZ987\n"
        _write_proposal(tmp_path, "myagent", custom_content)

        runner = CliRunner()
        result = runner.invoke(cmd, ["myagent", "--repo-path", str(tmp_path)])

        assert "XYZ987" in result.output

    def test_output_contains_agent_name(self, tmp_path: Path) -> None:
        """Command output includes the agent name."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "myagent")

        runner = CliRunner()
        result = runner.invoke(cmd, ["myagent", "--repo-path", str(tmp_path)])

        assert "myagent" in result.output

    def test_output_contains_apply_proposal_hint(self, tmp_path: Path) -> None:
        """Command output includes a hint about the apply-proposal command."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "myagent")

        runner = CliRunner()
        result = runner.invoke(cmd, ["myagent", "--repo-path", str(tmp_path)])

        assert "apply-proposal" in result.output

    def test_no_subprocess_invoked(self, tmp_path: Path) -> None:
        """review-proposal does not invoke any subprocess (pure file read)."""
        from unittest.mock import patch

        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "myagent")

        runner = CliRunner()
        with patch("subprocess.run") as mock_subprocess:
            result = runner.invoke(cmd, ["myagent", "--repo-path", str(tmp_path)])

        mock_subprocess.assert_not_called()
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestReviewProposalErrorPaths:
    """review-proposal handles error conditions correctly."""

    def test_missing_proposal_exits_nonzero(self, tmp_path: Path) -> None:
        """Command exits non-zero when proposal file does not exist."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent", "--repo-path", str(tmp_path)])

        assert result.exit_code != 0

    def test_missing_proposal_shows_file_path_in_error(self, tmp_path: Path) -> None:
        """Command shows a message mentioning the missing file path."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent", "--repo-path", str(tmp_path)])

        output = (result.output or "").lower()
        has_message = any(w in output for w in ("nonexistent", "not found", "proposal", "missing", "no such"))
        assert has_message, f"Expected error message mentioning missing file. Output: {result.output!r}"

    def test_missing_positional_arg_exits_nonzero(self) -> None:
        """Command exits non-zero when agent_name positional argument is missing."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])

        assert result.exit_code != 0
