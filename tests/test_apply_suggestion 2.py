"""Tests for the `agent-design apply-suggestion` CLI command.

Derivation:
- Takes a positional argument `suggestion_id` (e.g. "PS-1" or "PS-2")
- Optional --repo-path (default: current dir)
- Reads RETRO.md from <repo_path>/.agent-design/RETRO.md
- Parses RETRO.md to find "- [PS-N] <agent_file>.md: <suggestion_text>" matching suggestion_id
- Calls build_apply_suggestion_start(suggestion_id, agent_file, suggestion_text)
- Calls run_apply_suggestion(worktree_path, target_repo, start_message)
- Raises click.UsageError (or Abort) if RETRO.md is missing
- Raises click.UsageError (or Abort) if the PS-N ID is not found in RETRO.md
- Non-zero exit from run_apply_suggestion is a warning, not an abort

All external dependencies are patched. No real subprocess, filesystem state
reads beyond what CliRunner provides, or git calls are made.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_RETRO_MD = """\
# Retrospective — my-feature — 2026-04-05

## What Went Well
- TDD handoff was clean

## Friction Points
- Architect proposed infra changes without checking BASELINE.md

## Prompt Suggestions (pending human review)
- [PS-1] architect.md: add "check BASELINE.md for deployment approach before proposing infrastructure changes"
- [PS-2] eng_manager.md: "prompt agents to post status in DISCUSSION.md if they haven't communicated in >3 turns"
"""


def _write_retro(tmp_path: Path, content: str = SAMPLE_RETRO_MD) -> Path:
    """Write a RETRO.md under <tmp_path>/.agent-design/ and return its path."""
    agent_design_dir = tmp_path / ".agent-design"
    agent_design_dir.mkdir(parents=True, exist_ok=True)
    retro_file = agent_design_dir / "RETRO.md"
    retro_file.write_text(content)
    return retro_file


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestApplySuggestionCommandRegistered:
    """The `apply-suggestion` command is importable and registered in main CLI."""

    def test_apply_suggestion_module_importable(self) -> None:
        """agent_design.cli.commands.apply_suggestion is importable."""
        from agent_design.cli.commands import apply_suggestion  # noqa: F401

    def test_apply_suggestion_command_callable(self) -> None:
        """The apply_suggestion Click command object is callable."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        assert callable(cmd)

    def test_apply_suggestion_registered_in_main_cli(self) -> None:
        """The 'apply-suggestion' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "apply-suggestion" in cli.commands, "'apply-suggestion' not registered in main.py"

    def test_apply_suggestion_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestApplySuggestionCommandArguments:
    """The `apply-suggestion` command argument surface."""

    def test_suggestion_id_is_required(self, tmp_path: Path) -> None:
        """Calling apply-suggestion with no suggestion_id must exit non-zero."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code != 0

    def test_suggestion_id_accepted_as_positional(self, tmp_path: Path) -> None:
        """suggestion_id is accepted as a positional argument without raising."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["PS-2", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# RETRO.md parsing
# ---------------------------------------------------------------------------


class TestApplySuggestionRetroMdParsing:
    """apply-suggestion parses RETRO.md to find the matching suggestion."""

    def test_parses_ps1_correctly(self, tmp_path: Path) -> None:
        """PS-1 resolves to architect.md with the correct suggestion text."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        captured: list[dict] = []

        def capture_build(suggestion_id: str, agent_file: str, suggestion_text: str) -> str:
            captured.append(
                {"suggestion_id": suggestion_id, "agent_file": agent_file, "suggestion_text": suggestion_text}
            )
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0]["suggestion_id"] == "PS-1"
        assert captured[0]["agent_file"] == "architect.md"
        assert "BASELINE.md" in captured[0]["suggestion_text"]

    def test_parses_ps2_correctly(self, tmp_path: Path) -> None:
        """PS-2 resolves to eng_manager.md with the correct suggestion text."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        captured: list[dict] = []

        def capture_build(suggestion_id: str, agent_file: str, suggestion_text: str) -> str:
            captured.append(
                {"suggestion_id": suggestion_id, "agent_file": agent_file, "suggestion_text": suggestion_text}
            )
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["PS-2", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0]["suggestion_id"] == "PS-2"
        assert captured[0]["agent_file"] == "eng_manager.md"
        assert "DISCUSSION.md" in captured[0]["suggestion_text"]

    def test_suggestion_id_case_insensitive_or_exact(self, tmp_path: Path) -> None:
        """A suggestion ID that exists in RETRO.md is resolved successfully."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# build_apply_suggestion_start is called with correct arguments
# ---------------------------------------------------------------------------


class TestApplySuggestionCallsBuildApplySuggestionStart:
    """apply-suggestion calls build_apply_suggestion_start with the right arguments."""

    def test_build_called_with_suggestion_id(self, tmp_path: Path) -> None:
        """build_apply_suggestion_start receives the suggestion_id argument."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        captured_ids: list[str] = []

        def capture_build(suggestion_id: str, agent_file: str, suggestion_text: str) -> str:
            captured_ids.append(suggestion_id)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert "PS-1" in captured_ids

    def test_build_called_with_agent_file(self, tmp_path: Path) -> None:
        """build_apply_suggestion_start receives the agent_file parsed from RETRO.md."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        captured_files: list[str] = []

        def capture_build(suggestion_id: str, agent_file: str, suggestion_text: str) -> str:
            captured_files.append(agent_file)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert "architect.md" in captured_files

    def test_build_called_with_suggestion_text(self, tmp_path: Path) -> None:
        """build_apply_suggestion_start receives non-empty suggestion_text."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        captured_texts: list[str] = []

        def capture_build(suggestion_id: str, agent_file: str, suggestion_text: str) -> str:
            captured_texts.append(suggestion_text)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert len(captured_texts) == 1
        assert len(captured_texts[0]) > 0


# ---------------------------------------------------------------------------
# run_apply_suggestion is called with the start message
# ---------------------------------------------------------------------------


class TestApplySuggestionCallsRunApplySuggestion:
    """apply-suggestion calls run_apply_suggestion with the message from build_apply_suggestion_start."""

    def test_run_apply_suggestion_called_once(self, tmp_path: Path) -> None:
        """run_apply_suggestion is called exactly once."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=0) as mock_run,
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])

        mock_run.assert_called_once()

    def test_run_apply_suggestion_receives_start_message_from_build(self, tmp_path: Path) -> None:
        """run_apply_suggestion receives the return value of build_apply_suggestion_start."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        sentinel = "SENTINEL_APPLY_SUGGESTION_PROMPT"
        captured_messages: list[str] = []

        def capture_run(worktree_path: Path, target_repo: Path, start_message: str) -> int:
            captured_messages.append(start_message)
            return 0

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.apply_suggestion.run_apply_suggestion",
                side_effect=capture_run,
            ),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value=sentinel,
            ),
        ):
            runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert sentinel in captured_messages


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestApplySuggestionErrorHandling:
    """apply-suggestion handles error conditions gracefully."""

    def test_missing_retro_md_raises_usage_error(self, tmp_path: Path) -> None:
        """If RETRO.md does not exist, command exits non-zero with an error."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        # No RETRO.md created
        runner = CliRunner()
        result = runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_missing_retro_md_shows_error_message(self, tmp_path: Path) -> None:
        """If RETRO.md does not exist, command prints an informative error."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        # Should mention RETRO or missing or not found
        has_message = any(word in output for word in ("retro", "missing", "not found", "error", "no such"))
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_unknown_suggestion_id_raises_usage_error(self, tmp_path: Path) -> None:
        """If PS-N ID is not in RETRO.md, command exits non-zero."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cmd, ["PS-99", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_unknown_suggestion_id_shows_error_message(self, tmp_path: Path) -> None:
        """If PS-N ID is not in RETRO.md, command prints an informative error."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cmd, ["PS-99", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(word in output for word in ("ps-99", "not found", "error", "unknown", "no suggestion"))
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_nonzero_exit_from_run_apply_suggestion_is_warning_not_abort(self, tmp_path: Path) -> None:
        """If run_apply_suggestion returns non-zero, command still completes (no unhandled exception)."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=1),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])

        # Must not propagate as an unhandled exception / traceback
        assert "Traceback" not in (result.output or "")

    def test_nonzero_exit_still_completes_with_exit_0(self, tmp_path: Path) -> None:
        """A non-zero run_apply_suggestion exit is a warning; command itself exits 0."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_apply_suggestion", return_value=2),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
