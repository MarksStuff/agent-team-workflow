"""Tests for the `agent-design retro` CLI command.

Derivation:
- No required positional arguments
- Optional --repo-path (default: current dir)
- Derives project slug from ROUND_STATE.json if present, else from directory name
- Calls build_retro_start() with (project_slug, date)
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


class TestRetroCommandRegistered:
    """The `retro` command is importable and registered in main CLI."""

    def test_retro_module_importable(self) -> None:
        """agent_design.cli.commands.retro is importable."""
        from agent_design.cli.commands import retro  # noqa: F401

    def test_retro_command_callable(self) -> None:
        """The retro Click command object is callable."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        assert callable(retro_cmd)

    def test_retro_registered_in_main_cli(self) -> None:
        """The 'retro' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "retro" in cli.commands, "'retro' command not registered in main.py"

    def test_retro_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        result = runner.invoke(retro_cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestRetroCommandArguments:
    """The `retro` command argument surface."""

    def test_no_positional_args_required(self, tmp_path: Path) -> None:
        """retro can be invoked with no positional arguments."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_default_repo_path_is_current_dir(self, tmp_path: Path) -> None:
        """When --repo-path is not passed, the command still runs without error."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, [])
        # Should not crash with missing required argument
        assert "Missing argument" not in (result.output or "")


# ---------------------------------------------------------------------------
# Project slug derivation
# ---------------------------------------------------------------------------


class TestRetroProjectSlugDerivation:
    """retro derives the project slug from ROUND_STATE.json or directory name."""

    def test_slug_from_round_state_when_present(self, tmp_path: Path) -> None:
        """When ROUND_STATE.json is present, slug comes from feature_slug field."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        state = _make_state(feature_slug="my-feature-slug")
        worktree = tmp_path / ".agent-design"
        _write_state(worktree, state)

        captured: list[dict] = []

        def capture_build(project_slug: str, date: str) -> str:
            captured.append({"project_slug": project_slug})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0]["project_slug"] == "my-feature-slug"

    def test_slug_falls_back_to_directory_name_when_no_state(self, tmp_path: Path) -> None:
        """When no ROUND_STATE.json, slug falls back to the directory name."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        # No ROUND_STATE.json written
        captured: list[dict] = []

        def capture_build(project_slug: str, date: str) -> str:
            captured.append({"project_slug": project_slug})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert len(captured[0]["project_slug"]) > 0


# ---------------------------------------------------------------------------
# build_retro_start is called with correct arguments
# ---------------------------------------------------------------------------


class TestRetroCallsBuildRetroStart:
    """retro calls build_retro_start with the right arguments."""

    def test_build_retro_start_receives_project_slug(self, tmp_path: Path) -> None:
        """build_retro_start is called with the project slug."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        state = _make_state(feature_slug="slug-check")
        worktree = tmp_path / ".agent-design"
        _write_state(worktree, state)

        captured_slugs: list[str] = []

        def capture_build(project_slug: str, date: str) -> str:
            captured_slugs.append(project_slug)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert "slug-check" in captured_slugs

    def test_build_retro_start_receives_today_date(self, tmp_path: Path) -> None:
        """build_retro_start is called with today's date in ISO format."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        captured_dates: list[str] = []

        def capture_build(project_slug: str, date: str) -> str:
            captured_dates.append(date)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured_dates) == 1
        import re

        assert re.match(r"\d{4}-\d{2}-\d{2}", captured_dates[0]), f"Date not in YYYY-MM-DD format: {captured_dates[0]}"


# ---------------------------------------------------------------------------
# run_print_team is called with the start message
# ---------------------------------------------------------------------------


class TestRetroCallsRunPrintTeam:
    """retro calls run_print_team with the message from build_retro_start."""

    def test_run_print_team_called_once(self, tmp_path: Path) -> None:
        """run_print_team is called exactly once."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0) as mock_run,
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        mock_run.assert_called_once()

    def test_run_print_team_receives_start_message_from_build(self, tmp_path: Path) -> None:
        """run_print_team receives the return value of build_retro_start."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        sentinel = "SENTINEL_RETRO_PROMPT"
        captured_messages: list[str] = []

        def capture_run(worktree_path: Path, target_repo: Path, start_message: str) -> int:
            captured_messages.append(start_message)
            return 0

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", side_effect=capture_run),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value=sentinel),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert sentinel in captured_messages


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRetroErrorHandling:
    """retro handles error conditions gracefully."""

    def test_nonzero_exit_from_run_print_team_is_warning_not_abort(self, tmp_path: Path) -> None:
        """If run_print_team returns non-zero, command still completes (no unhandled exception)."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=1),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        # Must not propagate as an unhandled exception / traceback
        assert "Traceback" not in (result.output or "")

    def test_nonzero_exit_still_completes_with_exit_0(self, tmp_path: Path) -> None:
        """A non-zero run_print_team exit is a warning; command itself exits 0."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=2),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert result.exit_code == 0
