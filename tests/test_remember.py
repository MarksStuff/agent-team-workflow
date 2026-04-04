"""Tests for the `agent-design remember` CLI command.

Derivation: DESIGN.md § "Human Intervention → Memory Update":
- Takes a correction string as a positional argument
- Optional --repo-path (default: current dir) per Developer's DISCUSSION.md contract
- Derives project slug from ROUND_STATE.json if present, else from directory name
- Calls build_remember_start() with (correction, project_slug, date)
- Calls run_print_team() with the start message
- Non-zero exit from run_print_team is a warning, not an abort

All external dependencies are patched. No real subprocess, filesystem state
reads beyond what CliRunner provides, or git calls are made.
"""

import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from agent_design.state import RoundState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    *,
    feature_slug: str = "test-feature",
    feature_request: str = "Build something",
    target_repo: str = "/some/repo",
) -> RoundState:
    return RoundState(
        feature_slug=feature_slug,
        feature_request=feature_request,
        target_repo=target_repo,
        discussion_turns=0,
        pr_url=None,
        checkpoint_tag=None,
        baseline_commit=None,
        completed=[],
    )


def _write_state(worktree: Path, state: RoundState) -> None:
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / "ROUND_STATE.json").write_text(json.dumps(asdict(state)))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRememberCommandRegistered:
    """The `remember` command is importable and registered in main CLI."""

    def test_remember_module_importable(self) -> None:
        """agent_design.cli.commands.remember is importable."""
        from agent_design.cli.commands import remember  # noqa: F401

    def test_remember_command_callable(self) -> None:
        """The remember Click command object is callable."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        assert callable(remember_cmd)

    def test_remember_registered_in_main_cli(self) -> None:
        """The 'remember' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "remember" in cli.commands, "'remember' command not registered in main.py"

    def test_remember_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        runner = CliRunner()
        result = runner.invoke(remember_cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestRememberCommandArguments:
    """The `remember` command argument surface."""

    def test_correction_is_required(self, tmp_path: Path) -> None:
        """Calling remember with no correction text must exit non-zero."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        runner = CliRunner()
        result = runner.invoke(remember_cmd, [])
        assert result.exit_code != 0

    def test_correction_accepted_as_positional(self, tmp_path: Path) -> None:
        """Correction text is accepted as a positional argument without raising."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=0),
            patch("agent_design.cli.commands.remember.build_remember_start", return_value="prompt"),
        ):
            result = runner.invoke(remember_cmd, ["Some correction text", "--repo-path", str(tmp_path)])
        # Should not crash (might exit 0 or non-zero depending on other checks)
        assert "Error" not in (result.output or "") or result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=0),
            patch("agent_design.cli.commands.remember.build_remember_start", return_value="prompt"),
        ):
            result = runner.invoke(
                remember_cmd,
                ["A correction", "--repo-path", str(tmp_path)],
            )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Project slug derivation
# ---------------------------------------------------------------------------


class TestRememberProjectSlugDerivation:
    """remember derives the project slug from ROUND_STATE.json or directory name."""

    def test_slug_from_round_state_when_present(self, tmp_path: Path) -> None:
        """When ROUND_STATE.json is present, slug comes from feature_slug field."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        state = _make_state(feature_slug="my-feature-slug")
        worktree = tmp_path / ".agent-design"
        _write_state(worktree, state)

        captured: list[dict] = []

        def capture_build(correction: str, project_slug: str, date: str) -> str:
            captured.append({"project_slug": project_slug})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=0),
            patch("agent_design.cli.commands.remember.build_remember_start", side_effect=capture_build),
        ):
            runner.invoke(remember_cmd, ["A correction", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0]["project_slug"] == "my-feature-slug"

    def test_slug_falls_back_to_directory_name_when_no_state(self, tmp_path: Path) -> None:
        """When no ROUND_STATE.json, slug falls back to the directory name."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        # No ROUND_STATE.json written
        captured: list[dict] = []

        def capture_build(correction: str, project_slug: str, date: str) -> str:
            captured.append({"project_slug": project_slug})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=0),
            patch("agent_design.cli.commands.remember.build_remember_start", side_effect=capture_build),
        ):
            runner.invoke(remember_cmd, ["A correction", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        # The slug should be the directory basename or some non-empty string
        assert len(captured[0]["project_slug"]) > 0


# ---------------------------------------------------------------------------
# build_remember_start is called with correct arguments
# ---------------------------------------------------------------------------


class TestRememberCallsBuildRememberStart:
    """remember calls build_remember_start with the right arguments."""

    def test_build_remember_start_receives_correction(self, tmp_path: Path) -> None:
        """build_remember_start is called with the correction text."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        captured: list[str] = []

        def capture_build(correction: str, project_slug: str, date: str) -> str:
            captured.append(correction)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=0),
            patch("agent_design.cli.commands.remember.build_remember_start", side_effect=capture_build),
        ):
            runner.invoke(
                remember_cmd,
                ["Mark overrode the queue design.", "--repo-path", str(tmp_path)],
            )

        assert "Mark overrode the queue design." in captured

    def test_build_remember_start_receives_today_date(self, tmp_path: Path) -> None:
        """build_remember_start is called with today's date."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        captured_dates: list[str] = []

        def capture_build(correction: str, project_slug: str, date: str) -> str:
            captured_dates.append(date)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=0),
            patch("agent_design.cli.commands.remember.build_remember_start", side_effect=capture_build),
        ):
            runner.invoke(remember_cmd, ["Some correction", "--repo-path", str(tmp_path)])

        assert len(captured_dates) == 1
        # Date must be in ISO format (YYYY-MM-DD)
        import re

        assert re.match(r"\d{4}-\d{2}-\d{2}", captured_dates[0]), f"Date not in YYYY-MM-DD format: {captured_dates[0]}"


# ---------------------------------------------------------------------------
# run_print_team is called with the start message
# ---------------------------------------------------------------------------


class TestRememberCallsRunPrintTeam:
    """remember calls run_print_team with the message from build_remember_start."""

    def test_run_print_team_called_once(self, tmp_path: Path) -> None:
        """run_print_team is called exactly once."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=0) as mock_run,
            patch("agent_design.cli.commands.remember.build_remember_start", return_value="prompt"),
        ):
            runner.invoke(remember_cmd, ["A correction", "--repo-path", str(tmp_path)])

        mock_run.assert_called_once()

    def test_run_print_team_receives_start_message_from_build(self, tmp_path: Path) -> None:
        """run_print_team receives the return value of build_remember_start."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        sentinel = "SENTINEL_REMEMBER_PROMPT"
        captured_messages: list[str] = []

        def capture_run(worktree_path: Path, target_repo: Path, start_message: str) -> int:
            captured_messages.append(start_message)
            return 0

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", side_effect=capture_run),
            patch("agent_design.cli.commands.remember.build_remember_start", return_value=sentinel),
        ):
            runner.invoke(remember_cmd, ["A correction", "--repo-path", str(tmp_path)])

        assert sentinel in captured_messages


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRememberErrorHandling:
    """remember handles error conditions gracefully."""

    def test_nonzero_exit_from_run_print_team_is_warning_not_abort(self, tmp_path: Path) -> None:
        """If run_print_team returns non-zero, command still completes (no unhandled exception)."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=1),
            patch("agent_design.cli.commands.remember.build_remember_start", return_value="prompt"),
        ):
            result = runner.invoke(remember_cmd, ["A correction", "--repo-path", str(tmp_path)])

        # Must not propagate as an unhandled exception / traceback
        assert "Traceback" not in (result.output or "")

    def test_empty_correction_prints_error(self, tmp_path: Path) -> None:
        """An empty correction string results in an error, not a silent no-op."""
        from agent_design.cli.commands.remember import remember as remember_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.remember.run_print_team", return_value=0),
            patch("agent_design.cli.commands.remember.build_remember_start", return_value="prompt"),
        ):
            result = runner.invoke(remember_cmd, ["", "--repo-path", str(tmp_path)])

        # Either non-zero exit or an error message — empty correction is meaningless
        empty_correction_handled = result.exit_code != 0 or any(
            word in (result.output or "").lower() for word in ("error", "empty", "correction", "required")
        )
        assert empty_correction_handled, "Empty correction was silently accepted with exit 0 and no error message"


# ---------------------------------------------------------------------------
# Registration: remember is wired into main.py
# ---------------------------------------------------------------------------


class TestRememberRegisteredInMainCLI:
    """After Phase 7: 'remember' is registered in cli/main.py."""

    def test_remember_in_main_cli_commands(self) -> None:
        """agent_design.cli.main.cli has 'remember' registered."""
        from agent_design.cli.main import cli

        assert "remember" in cli.commands
