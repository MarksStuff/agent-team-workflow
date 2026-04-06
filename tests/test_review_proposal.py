"""Tests for the `agent-design review-proposal` CLI command.

Derivation (DESIGN.md § "Escalation: proposing a new agent"):
- Takes a positional argument `name` (proposal name, e.g. "cryptography_expert")
- Optional --repo-path (default: current dir)
- Reads .agent-design/proposals/<name>.md (appends .md if not already present)
- Prints the proposal content to the console
- Missing proposal file → clear error message, non-zero exit
- No external process is launched; this is a pure file read + print

All external dependencies are patched where needed. File I/O uses tmp_path.
"""

from pathlib import Path

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Sample proposal content
# ---------------------------------------------------------------------------

SAMPLE_PROPOSAL = """\
# Agent Proposal: cryptography_expert

**Proposed by:** Eng Manager
**Session:** feat/add-user-auth — 2026-04-03
**Gap identified:** AES-256 key derivation and PBKDF2 iteration counts.

**Proposed location:** `~/.claude/agents/cryptography_expert.md`
**Rationale:** Cryptography concerns appear across projects.

**Agent type:** Domain expert (advises; does not write implementation code)

---

## Agent Definition (written verbatim if approved)

---
name: cryptography_expert
description: >
  Cryptography domain expert.
model: claude-sonnet-4-6
tools: WebSearch, WebFetch, Read
---

You are a cryptography domain expert on a collaborative engineering team.
"""


def _write_proposal(tmp_path: Path, name: str, content: str = SAMPLE_PROPOSAL) -> Path:
    """Write a proposal file under <tmp_path>/.agent-design/proposals/ and return its path."""
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


class TestReviewProposalCommandArguments:
    """The `review-proposal` command argument surface."""

    def test_name_is_required(self) -> None:
        """Calling review-proposal with no name argument must exit non-zero."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code != 0

    def test_name_accepted_as_positional(self, tmp_path: Path) -> None:
        """name is accepted as a positional argument without raising."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "cryptography_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["cryptography_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "cryptography_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["cryptography_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Happy path: proposal file exists → content printed
# ---------------------------------------------------------------------------


class TestReviewProposalHappyPath:
    """review-proposal prints proposal content when file exists."""

    def test_prints_proposal_content(self, tmp_path: Path) -> None:
        """Proposal file content appears in command output."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "cryptography_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["cryptography_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        assert "cryptography_expert" in result.output

    def test_prints_proposal_header(self, tmp_path: Path) -> None:
        """Proposal heading text appears in command output."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "cryptography_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["cryptography_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        # The proposal starts with "# Agent Proposal:"
        assert "Agent Proposal" in result.output

    def test_name_without_md_extension_works(self, tmp_path: Path) -> None:
        """Passing name without .md extension still resolves the file correctly."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "my_expert")
        runner = CliRunner()
        # Pass without .md
        result = runner.invoke(cmd, ["my_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        assert "my_expert" in result.output

    def test_name_with_md_extension_also_works(self, tmp_path: Path) -> None:
        """Passing name with .md extension works (command handles both forms)."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "my_expert")
        runner = CliRunner()
        # Pass with .md — command should strip or handle gracefully
        result = runner.invoke(cmd, ["my_expert.md", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_prints_agent_definition_section(self, tmp_path: Path) -> None:
        """The 'Agent Definition' section appears in the output."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "cryptography_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["cryptography_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        assert "Agent Definition" in result.output

    def test_exits_zero_on_success(self, tmp_path: Path) -> None:
        """Command exits 0 when proposal file exists."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        _write_proposal(tmp_path, "cryptography_expert")
        runner = CliRunner()
        result = runner.invoke(cmd, ["cryptography_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestReviewProposalErrorHandling:
    """review-proposal handles error conditions gracefully."""

    def test_missing_proposal_file_exits_nonzero(self, tmp_path: Path) -> None:
        """If proposal file does not exist, command exits non-zero."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        # No proposal file created
        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_missing_proposal_file_shows_error_message(self, tmp_path: Path) -> None:
        """If proposal file does not exist, command shows an informative error."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent_expert", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("not found", "missing", "error", "no such", "proposal", "nonexistent")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_missing_proposal_file_mentions_expected_path(self, tmp_path: Path) -> None:
        """Error message hints at where the file was expected."""
        from agent_design.cli.commands.review_proposal import review_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["missing_agent", "--repo-path", str(tmp_path)])
        output = result.output or ""
        # Should mention the proposals dir or the agent name
        has_path_hint = "proposals" in output.lower() or "missing_agent" in output.lower()
        assert has_path_hint, f"Error message lacks path hint. Output: {output!r}"
