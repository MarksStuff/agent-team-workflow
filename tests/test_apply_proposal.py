"""Tests for the `agent-design apply-proposal` CLI command.

Derivation:
- Takes a positional argument `name` (required)
- Optional --repo-path (default: current dir)
- Reads .agent-design/proposals/<name>.md from repo_path
- Parses '**Proposed location:** <path>' line to find target path
- Extracts agent definition: find '## Agent Definition' section, extract from
  first '---' delimiter onwards to end of file
- Expands ~ in proposed location, creates parent dirs
- Writes extracted content to proposed location
- Prints confirmation showing where file was written
- Errors if proposal not found
- Errors if '**Proposed location:**' line is missing from proposal
- Registered as 'apply-proposal' in agent_design.cli.main.cli

All external dependencies are patched. No real subprocess or filesystem writes
to ~/.claude/agents/ are made — tests use tmp_path for all file I/O.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_sample_proposal(proposed_location: str) -> str:
    """Return a well-formed proposal with the given proposed_location."""
    return f"""\
# Agent Proposal: test_expert

**Proposed by:** Eng Manager
**Session:** feat/example — 2026-04-05
**Gap identified:** Testing expertise needed.

**Proposed location:** {proposed_location}
**Rationale:** Global expertise.

**Agent type:** Domain expert

---

## Agent Definition (written verbatim if approved)

---
name: test_expert
description: >
  Test domain expert.
model: claude-sonnet-4-6
tools: WebSearch, WebFetch, Read
---

You are a test domain expert.
"""


PROPOSAL_WITHOUT_LOCATION = """\
# Agent Proposal: no_location_expert

**Proposed by:** Eng Manager

**Agent type:** Domain expert

---

## Agent Definition (written verbatim if approved)

---
name: no_location_expert
---

You are an expert.
"""


def _write_proposal(tmp_path: Path, name: str, content: str) -> Path:
    """Write a proposals/<name>.md under <tmp_path>/.agent-design/ and return its path."""
    proposals_dir = tmp_path / ".agent-design" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    proposal_file = proposals_dir / f"{name}.md"
    proposal_file.write_text(content)
    return proposal_file


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestApplyProposalCommandRegistered:
    """The `apply-proposal` command is importable and registered in main CLI."""

    def test_apply_proposal_module_importable(self) -> None:
        """agent_design.cli.commands.apply_proposal is importable."""
        from agent_design.cli.commands import apply_proposal  # noqa: F401

    def test_apply_proposal_command_callable(self) -> None:
        """The apply_proposal Click command object is callable."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        assert callable(cmd)

    def test_apply_proposal_registered_in_main_cli(self) -> None:
        """The 'apply-proposal' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "apply-proposal" in cli.commands, "'apply-proposal' not registered in main.py"

    def test_apply_proposal_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestApplyProposalArguments:
    """The `apply-proposal` command argument surface."""

    def test_name_is_required(self) -> None:
        """Calling apply-proposal with no name must exit non-zero."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code != 0

    def test_name_accepted_as_positional(self, tmp_path: Path) -> None:
        """name is accepted as a positional argument without raising."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        target_file = tmp_path / "output" / "test_expert.md"
        _write_proposal(tmp_path, "test_expert", _make_sample_proposal(str(target_file)))
        runner = CliRunner()
        result = runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        target_file = tmp_path / "output" / "test_expert.md"
        _write_proposal(tmp_path, "test_expert", _make_sample_proposal(str(target_file)))
        runner = CliRunner()
        result = runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestApplyProposalParsing:
    """apply-proposal parses the proposal file correctly."""

    def test_parses_proposed_location(self, tmp_path: Path) -> None:
        """Command reads the **Proposed location:** line and writes to the given path."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        target_file = tmp_path / "agents" / "test_expert.md"
        _write_proposal(tmp_path, "test_expert", _make_sample_proposal(str(target_file)))
        runner = CliRunner()
        result = runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        assert target_file.exists(), "Expected output file was not created"

    def test_extracts_agent_definition_correctly(self, tmp_path: Path) -> None:
        """Extracted content starts from the first --- delimiter after ## Agent Definition."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        target_file = tmp_path / "agents" / "test_expert.md"
        _write_proposal(tmp_path, "test_expert", _make_sample_proposal(str(target_file)))
        runner = CliRunner()
        result = runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        written = target_file.read_text()
        # Should contain the YAML frontmatter
        assert "name: test_expert" in written
        # Should contain the body
        assert "You are a test domain expert." in written

    def test_does_not_include_proposal_preamble_in_output(self, tmp_path: Path) -> None:
        """Written file does not include the proposal header (Proposed by, Gap identified, etc.)."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        target_file = tmp_path / "agents" / "test_expert.md"
        _write_proposal(tmp_path, "test_expert", _make_sample_proposal(str(target_file)))
        runner = CliRunner()
        runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        if target_file.exists():
            written = target_file.read_text()
            assert "Proposed by" not in written
            assert "Gap identified" not in written


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------


class TestApplyProposalWritesFile:
    """apply-proposal writes the extracted content to the proposed location."""

    def test_writes_extracted_content_to_proposed_location(self, tmp_path: Path) -> None:
        """The file at the proposed location contains the extracted agent definition."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        target_file = tmp_path / "custom" / "dir" / "test_expert.md"
        _write_proposal(tmp_path, "test_expert", _make_sample_proposal(str(target_file)))
        runner = CliRunner()
        result = runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        assert target_file.exists()
        written = target_file.read_text()
        assert "test_expert" in written

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Parent directories are created if they do not exist."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        target_file = tmp_path / "deep" / "nested" / "path" / "test_expert.md"
        assert not target_file.parent.exists()
        _write_proposal(tmp_path, "test_expert", _make_sample_proposal(str(target_file)))
        runner = CliRunner()
        result = runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        assert target_file.parent.exists()
        assert target_file.exists()

    def test_prints_confirmation_with_written_path(self, tmp_path: Path) -> None:
        """Command prints a confirmation message that includes the written file path."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        target_file = tmp_path / "output" / "test_expert.md"
        _write_proposal(tmp_path, "test_expert", _make_sample_proposal(str(target_file)))
        runner = CliRunner()
        result = runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        # Output should contain some indication of where the file was written
        output = result.output or ""
        has_path_info = "test_expert" in output or str(target_file) in output
        assert has_path_info, f"No path confirmation in output. Output: {output!r}"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestApplyProposalErrorHandling:
    """apply-proposal handles missing proposals and malformed content."""

    def test_missing_proposal_exits_nonzero(self, tmp_path: Path) -> None:
        """If the proposal file does not exist, command exits non-zero."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_missing_proposal_shows_error_message(self, tmp_path: Path) -> None:
        """If proposal file not found, command prints an informative error."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("not found", "missing", "does not exist", "error", "nonexistent", "no such")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_missing_proposed_location_line_exits_nonzero(self, tmp_path: Path) -> None:
        """If **Proposed location:** line is absent, command exits non-zero."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "no_location_expert", PROPOSAL_WITHOUT_LOCATION)
        runner = CliRunner()
        result = runner.invoke(cmd, ["no_location_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_missing_proposed_location_line_shows_error_message(self, tmp_path: Path) -> None:
        """If **Proposed location:** line is absent, command prints an informative error."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "no_location_expert", PROPOSAL_WITHOUT_LOCATION)
        runner = CliRunner()
        result = runner.invoke(cmd, ["no_location_expert", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("proposed location", "location", "missing", "not found", "error", "parse")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"
