"""Tests for the `agent-design retro` CLI command.

Derivation: DESIGN.md § "The Retrospective" + Architect contract (DISCUSSION.md):
- Takes optional --repo-path (default: current dir)
- Requires .agent-design/DISCUSSION.md to exist; raises click.UsageError if missing
- Passes paths to build_retro_start() — not file content
- TASKS.md and DECISIONS.md missing → non-fatal; None is passed
- Calls run_print_team(worktree_path, repo_path, start_message)
- Non-zero exit from run_print_team → warning print, no exception

All external dependencies are patched. No real subprocess, filesystem I/O
beyond what tmp_path provides, or launcher calls are made.
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


def _write_discussion(repo_path: Path) -> None:
    """Write a minimal .agent-design/DISCUSSION.md so the guard passes."""
    agent_design_dir = repo_path / ".agent-design"
    agent_design_dir.mkdir(parents=True, exist_ok=True)
    (agent_design_dir / "DISCUSSION.md").write_text("# Design Discussion\n\n## [Architect]\nSome content.\n")


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

    def test_no_arguments_required(self, tmp_path: Path) -> None:
        """retro can be called with no arguments (--repo-path defaults to cwd)."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            # invoke with --repo-path to avoid cwd dependency
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Guard: missing DISCUSSION.md → UsageError
# ---------------------------------------------------------------------------


class TestRetroDiscussionMdGuard:
    """retro raises click.UsageError when .agent-design/DISCUSSION.md is missing."""

    def test_missing_discussion_md_exits_nonzero(self, tmp_path: Path) -> None:
        """When .agent-design/DISCUSSION.md does not exist, exit code is non-zero."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        # No DISCUSSION.md written — guard should fire
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_missing_discussion_md_error_message(self, tmp_path: Path) -> None:
        """Error message when DISCUSSION.md is missing mentions the path and init command."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        assert "discussion" in output or "init" in output, (
            f"Expected error message to mention DISCUSSION.md or init, got: {result.output!r}"
        )

    def test_missing_discussion_md_run_print_team_not_called(self, tmp_path: Path) -> None:
        """When DISCUSSION.md is missing, run_print_team is never called."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0) as mock_run,
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        mock_run.assert_not_called()

    def test_existing_discussion_md_does_not_error(self, tmp_path: Path) -> None:
        """When DISCUSSION.md exists, command proceeds without error."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# build_retro_start is called with correct arguments
# ---------------------------------------------------------------------------


class TestRetroCallsBuildRetroStart:
    """retro calls build_retro_start with the right arguments."""

    def test_build_retro_start_called_once(self, tmp_path: Path) -> None:
        """build_retro_start is called exactly once."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt") as mock_build,
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])
        mock_build.assert_called_once()

    def test_build_retro_start_receives_discussion_path(self, tmp_path: Path) -> None:
        """build_retro_start is called with the path to DISCUSSION.md."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert "discussion_path" in captured[0]
        assert "DISCUSSION.md" in str(captured[0]["discussion_path"])

    def test_build_retro_start_receives_project_slug(self, tmp_path: Path) -> None:
        """build_retro_start is called with a non-empty project_slug."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        state = _make_state(feature_slug="my-retro-slug")
        _write_state(tmp_path / ".agent-design", state)
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert "project_slug" in captured[0]
        assert captured[0]["project_slug"] == "my-retro-slug"

    def test_build_retro_start_receives_date(self, tmp_path: Path) -> None:
        """build_retro_start is called with a date string in YYYY-MM-DD format."""
        import re

        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert "date" in captured[0]
        assert re.match(r"\d{4}-\d{2}-\d{2}", str(captured[0]["date"])), (
            f"Expected YYYY-MM-DD date, got: {captured[0]['date']!r}"
        )

    def test_build_retro_start_receives_none_tasks_path_when_missing(self, tmp_path: Path) -> None:
        """When TASKS.md is absent, build_retro_start receives None for tasks_path (non-fatal)."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        # No TASKS.md written
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        # Must still succeed
        assert result.exit_code == 0
        assert len(captured) == 1
        assert captured[0].get("tasks_path") is None

    def test_build_retro_start_receives_tasks_path_when_present(self, tmp_path: Path) -> None:
        """When TASKS.md exists, build_retro_start receives a non-None tasks_path."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        (tmp_path / "TASKS.md").write_text("# Tasks\n")
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0].get("tasks_path") is not None
        assert "TASKS.md" in str(captured[0]["tasks_path"])

    def test_build_retro_start_receives_none_decisions_path_when_missing(self, tmp_path: Path) -> None:
        """When DECISIONS.md is absent, build_retro_start receives None for decisions_path."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        # No DECISIONS.md written
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        assert len(captured) == 1
        assert captured[0].get("decisions_path") is None


# ---------------------------------------------------------------------------
# run_print_team is called correctly
# ---------------------------------------------------------------------------


class TestRetroCallsRunPrintTeam:
    """retro calls run_print_team with the message from build_retro_start."""

    def test_run_print_team_called_once(self, tmp_path: Path) -> None:
        """run_print_team is called exactly once."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
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

        _write_discussion(tmp_path)
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
        """If run_print_team returns non-zero, command still completes without traceback."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=1),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert "Traceback" not in (result.output or "")

    def test_nonzero_exit_from_run_print_team_prints_warning(self, tmp_path: Path) -> None:
        """If run_print_team returns non-zero, a warning is printed."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=1),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        output_lower = (result.output or "").lower()
        assert "warn" in output_lower or "error" in output_lower or "fail" in output_lower or "exit" in output_lower, (
            f"Expected warning output for non-zero run_print_team exit, got: {result.output!r}"
        )


# ---------------------------------------------------------------------------
# Project slug derivation
# ---------------------------------------------------------------------------


class TestRetroProjectSlugDerivation:
    """retro derives project_slug from ROUND_STATE.json or directory name."""

    def test_slug_from_round_state_when_present(self, tmp_path: Path) -> None:
        """When ROUND_STATE.json is present, slug comes from feature_slug field."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        state = _make_state(feature_slug="retro-feature-slug")
        _write_state(tmp_path / ".agent-design", state)
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0]["project_slug"] == "retro-feature-slug"

    def test_slug_falls_back_to_directory_name_when_no_state(self, tmp_path: Path) -> None:
        """When no ROUND_STATE.json, slug falls back to the directory name."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        # No ROUND_STATE.json
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
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
# Registration: retro is wired into main.py
# ---------------------------------------------------------------------------


class TestRetroRegisteredInMainCLI:
    """After Phase 8: 'retro' is registered in cli/main.py."""

    def test_retro_in_main_cli_commands(self) -> None:
        """agent_design.cli.main.cli has 'retro' registered."""
        from agent_design.cli.main import cli

        assert "retro" in cli.commands


# ---------------------------------------------------------------------------
# AC-R3: worktree_path is repo_path / ".agent-design"
# ---------------------------------------------------------------------------


class TestRetroWorktreePath:
    """AC-R3: run_print_team is called with worktree_path = repo_path / '.agent-design'."""

    def test_run_print_team_worktree_path_is_agent_design_subdir(self, tmp_path: Path) -> None:
        """run_print_team receives worktree_path = <repo_path>/.agent-design."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        captured_worktree: list[Path] = []

        def capture_run(worktree_path: Path, target_repo: Path, start_message: str) -> int:
            captured_worktree.append(worktree_path)
            return 0

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", side_effect=capture_run),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured_worktree) == 1
        assert captured_worktree[0] == tmp_path / ".agent-design"


# ---------------------------------------------------------------------------
# AC-R4: run_print_team still called when TASKS.md + DECISIONS.md absent;
#         start_message notes absence
# ---------------------------------------------------------------------------


class TestRetroAbsentOptionalFiles:
    """AC-R4: missing TASKS.md and DECISIONS.md are non-fatal; absence noted in prompt."""

    def test_run_print_team_called_when_both_optional_files_absent(self, tmp_path: Path) -> None:
        """run_print_team is still called when TASKS.md and DECISIONS.md are absent."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        # Neither TASKS.md nor DECISIONS.md written
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0) as mock_run,
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        mock_run.assert_called_once()
        assert result.exit_code == 0

    def test_both_tasks_and_decisions_none_when_absent(self, tmp_path: Path) -> None:
        """When both TASKS.md and DECISIONS.md absent, both kwargs passed as None."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0].get("tasks_path") is None
        assert captured[0].get("decisions_path") is None

    def test_start_message_produced_even_when_optional_files_absent(self, tmp_path: Path) -> None:
        """When both optional files are absent, build_retro_start is still called."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt") as mock_build,
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        mock_build.assert_called_once()


# ---------------------------------------------------------------------------
# Edge case: .agent-design/ exists but is empty (DISCUSSION.md not present)
# ---------------------------------------------------------------------------


class TestRetroAgentDesignDirEmpty:
    """Edge case: .agent-design/ directory exists but DISCUSSION.md not inside."""

    def test_empty_agent_design_dir_triggers_usage_error(self, tmp_path: Path) -> None:
        """If .agent-design/ exists but DISCUSSION.md is absent, guard fires."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        agent_design_dir = tmp_path / ".agent-design"
        agent_design_dir.mkdir(parents=True)
        # Directory exists but DISCUSSION.md is not inside it

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# --observation option
# ---------------------------------------------------------------------------


class TestRetroObservationOption:
    """--observation passes human input to build_retro_start."""

    def test_observation_option_accepted(self, tmp_path: Path) -> None:
        """--observation option is accepted without error."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", return_value="prompt"),
        ):
            result = runner.invoke(
                retro_cmd,
                ["--repo-path", str(tmp_path), "--observation", "Agents were not collaborating."],
            )
        assert result.exit_code == 0

    def test_observation_passed_to_build_retro_start(self, tmp_path: Path) -> None:
        """When --observation is given, build_retro_start receives it as human_observation."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(
                retro_cmd,
                ["--repo-path", str(tmp_path), "--observation", "EM was too directive."],
            )

        assert len(captured) == 1
        assert captured[0].get("human_observation") == "EM was too directive."

    def test_no_observation_passes_none_to_build_retro_start(self, tmp_path: Path) -> None:
        """When --observation is omitted, build_retro_start receives None for human_observation."""
        from agent_design.cli.commands.retro import retro as retro_cmd

        _write_discussion(tmp_path)
        captured: list[dict] = []

        def capture_build(**kwargs: object) -> str:
            captured.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.retro.run_print_team", return_value=0),
            patch("agent_design.cli.commands.retro.build_retro_start", side_effect=capture_build),
        ):
            runner.invoke(retro_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0].get("human_observation") is None
