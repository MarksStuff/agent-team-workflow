"""Tests for the `agent-design apply-proposal` CLI command.

Derivation:
- Takes a positional argument `agent_name` (e.g. "crypto_expert")
- Optional --repo-path (default: current dir)
- Reads proposal file from <repo_path>/.agent-design/proposals/<agent_name>.md
- Parses "Proposed location:" line to determine where to write the agent file
- Parses "## Agent Definition" section to extract the content to write
- Writes the agent definition to the proposed location (expanding ~)
- Output message mentions the path where the file was written
- No subprocess is called
- Error if proposal file does not exist
- Error if "Proposed location:" line is missing
- Error if "## Agent Definition" section is missing

No subprocess patching needed — this is a pure file read + write command.
"""

from pathlib import Path

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_PROPOSAL = """\
# Agent Proposal: crypto_expert

**Proposed by:** Eng Manager
**Session:** feat/add-auth — 2026-04-03
**Gap identified:** Key derivation evaluation

**Proposed location:** `~/.claude/agents/crypto_expert.md`
**Rationale:** Global expertise.

**Agent type:** Domain expert

---

## Agent Definition (written verbatim if approved)

---
name: crypto_expert
description: >
  Cryptography domain expert.
model: claude-sonnet-4-6
tools: WebSearch, WebFetch, Read
---

You are a cryptography domain expert.
"""

PROPOSAL_WITHOUT_LOCATION = """\
# Agent Proposal: crypto_expert

**Proposed by:** Eng Manager

## Agent Definition (written verbatim if approved)

---
name: crypto_expert
---
"""

PROPOSAL_WITHOUT_DEFINITION = """\
# Agent Proposal: crypto_expert

**Proposed location:** `~/.claude/agents/crypto_expert.md`

No agent definition section here.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_proposal(tmp_path: Path, agent_name: str, content: str = SAMPLE_PROPOSAL) -> Path:
    """Write a proposal file under <tmp_path>/.agent-design/proposals/ and return its path."""
    proposals_dir = tmp_path / ".agent-design" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    proposal_file = proposals_dir / f"{agent_name}.md"
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
# Happy path
# ---------------------------------------------------------------------------


class TestApplyProposalHappyPath:
    """apply-proposal writes the agent definition to the proposed location."""

    def test_exits_zero_with_valid_proposal(self, tmp_path: Path, monkeypatch: object) -> None:
        """Command exits 0 when proposal is valid and file can be written."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert")
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0, f"Unexpected exit code. Output: {result.output}"

    def test_writes_agent_definition_to_proposed_location(self, tmp_path: Path, monkeypatch: object) -> None:
        """Agent definition file is created at the proposed location."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert")
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

        runner = CliRunner()
        runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        expected_path = home_dir / ".claude" / "agents" / "crypto_expert.md"
        assert expected_path.exists(), f"Agent file not written to {expected_path}"

    def test_written_file_starts_with_yaml_frontmatter(self, tmp_path: Path, monkeypatch: object) -> None:
        """The written agent definition file starts with '---' (YAML frontmatter)."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert")
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

        runner = CliRunner()
        runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        expected_path = home_dir / ".claude" / "agents" / "crypto_expert.md"
        content = expected_path.read_text()
        assert content.startswith("---"), f"File should start with '---'. Got: {content[:50]!r}"

    def test_written_file_contains_agent_name(self, tmp_path: Path, monkeypatch: object) -> None:
        """The written agent definition file contains 'name: crypto_expert'."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert")
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

        runner = CliRunner()
        runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        expected_path = home_dir / ".claude" / "agents" / "crypto_expert.md"
        content = expected_path.read_text()
        assert "name: crypto_expert" in content, f"'name: crypto_expert' not found in file. Content: {content!r}"

    def test_output_mentions_written_path(self, tmp_path: Path, monkeypatch: object) -> None:
        """Command output mentions the path where the agent file was written."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert")
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert "crypto_expert" in result.output

    def test_no_subprocess_invoked(self, tmp_path: Path, monkeypatch: object) -> None:
        """apply-proposal does not invoke any subprocess (pure file read + write)."""
        from unittest.mock import patch

        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert")
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

        runner = CliRunner()
        with patch("subprocess.run") as mock_subprocess:
            runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        mock_subprocess.assert_not_called()


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestApplyProposalErrorPaths:
    """apply-proposal handles error conditions correctly."""

    def test_missing_proposal_file_aborts(self, tmp_path: Path) -> None:
        """Command exits non-zero when proposal file does not exist."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent", "--repo-path", str(tmp_path)])

        assert result.exit_code != 0

    def test_missing_proposal_file_shows_error_message(self, tmp_path: Path) -> None:
        """Command shows an error message when proposal file does not exist."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent", "--repo-path", str(tmp_path)])

        output = (result.output or "").lower()
        has_message = any(w in output for w in ("nonexistent", "not found", "proposal", "missing", "no such"))
        assert has_message, f"Expected error message. Output: {result.output!r}"

    def test_proposal_without_location_line_aborts(self, tmp_path: Path) -> None:
        """Command exits non-zero when proposal has no 'Proposed location:' line."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert", PROPOSAL_WITHOUT_LOCATION)

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code != 0

    def test_proposal_without_location_line_shows_error(self, tmp_path: Path) -> None:
        """Command shows an error when 'Proposed location:' is missing."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert", PROPOSAL_WITHOUT_LOCATION)

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        output = (result.output or "").lower()
        has_message = any(w in output for w in ("location", "proposed location", "missing", "not found", "error"))
        assert has_message, f"Expected error about missing location. Output: {result.output!r}"

    def test_proposal_without_definition_section_aborts(self, tmp_path: Path) -> None:
        """Command exits non-zero when proposal has no 'Agent Definition' section."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert", PROPOSAL_WITHOUT_DEFINITION)

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code != 0

    def test_proposal_without_definition_section_shows_error(self, tmp_path: Path) -> None:
        """Command shows an error when 'Agent Definition' section is missing."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "crypto_expert", PROPOSAL_WITHOUT_DEFINITION)

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        output = (result.output or "").lower()
        has_message = any(w in output for w in ("definition", "agent definition", "missing", "not found", "error"))
        assert has_message, f"Expected error about missing definition. Output: {result.output!r}"

    def test_missing_positional_arg_exits_nonzero(self) -> None:
        """Command exits non-zero when agent_name positional argument is missing."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])

        assert result.exit_code != 0
