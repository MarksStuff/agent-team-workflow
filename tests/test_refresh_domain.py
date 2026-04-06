"""Tests for the `agent-design refresh-domain` CLI command.

Derivation:
- Takes --agent <name> (required option)
- Optional --repo-path (default: current dir)
- Validates .claude/agents/<agent_name>.md exists in repo_path; errors if not
- Calls build_refresh_domain_start(agent_name, date) from agent_design.prompts
- Calls run_refresh_domain(repo_path, agent_name, task_prompt) from agent_design.launcher
- Non-zero return from run_refresh_domain is a warning (printed), command exits 0
- Registered as 'refresh-domain' in agent_design.cli.main.cli

All external dependencies are patched. No real subprocess or filesystem writes
are made beyond what the tests themselves set up.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_agent_file(tmp_path: Path, agent_name: str) -> Path:
    """Write a .claude/agents/<agent_name>.md file under tmp_path."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agents_dir / f"{agent_name}.md"
    agent_file.write_text(f"---\nname: {agent_name}\n---\nYou are {agent_name}.\n")
    return agent_file


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRefreshDomainCommandRegistered:
    """The `refresh-domain` command is importable and registered in main CLI."""

    def test_refresh_domain_module_importable(self) -> None:
        """agent_design.cli.commands.refresh_domain is importable."""
        from agent_design.cli.commands import refresh_domain  # noqa: F401

    def test_refresh_domain_command_callable(self) -> None:
        """The refresh_domain Click command object is callable."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        assert callable(cmd)

    def test_refresh_domain_registered_in_main_cli(self) -> None:
        """The 'refresh-domain' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "refresh-domain" in cli.commands, "'refresh-domain' not registered in main.py"

    def test_refresh_domain_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestRefreshDomainArguments:
    """The `refresh-domain` command argument surface."""

    def test_agent_option_is_required(self, tmp_path: Path) -> None:
        """Calling refresh-domain without --agent must exit non-zero."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_agent_option_accepted(self, tmp_path: Path) -> None:
        """--agent <name> is accepted and command proceeds."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "architect")
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_refresh_domain", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "architect", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "developer")
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_refresh_domain", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "developer", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Agent file validation
# ---------------------------------------------------------------------------


class TestRefreshDomainAgentValidation:
    """refresh-domain validates that the agent file exists before proceeding."""

    def test_errors_if_agent_file_missing(self, tmp_path: Path) -> None:
        """Exits non-zero if .claude/agents/<name>.md does not exist."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        # No agent file created
        runner = CliRunner()
        result = runner.invoke(cmd, ["--agent", "nonexistent_agent", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_error_message_mentions_missing_file(self, tmp_path: Path) -> None:
        """Error output mentions the missing agent file path."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["--agent", "nonexistent_agent", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("not found", "missing", "does not exist", "error", "nonexistent_agent")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_proceeds_if_agent_file_exists(self, tmp_path: Path) -> None:
        """Command proceeds normally when .claude/agents/<name>.md exists."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "architect")
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_refresh_domain", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "architect", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# build_refresh_domain_start is called with correct arguments
# ---------------------------------------------------------------------------


class TestRefreshDomainCallsBuild:
    """refresh-domain calls build_refresh_domain_start with agent_name and date."""

    def test_build_called_with_agent_name(self, tmp_path: Path) -> None:
        """build_refresh_domain_start receives the agent_name argument."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "qa_engineer")
        captured_names: list[str] = []

        def capture_build(agent_name: str, date: str) -> str:
            captured_names.append(agent_name)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_refresh_domain", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["--agent", "qa_engineer", "--repo-path", str(tmp_path)])

        assert "qa_engineer" in captured_names

    def test_build_called_with_date(self, tmp_path: Path) -> None:
        """build_refresh_domain_start receives a non-empty date string."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "architect")
        captured_dates: list[str] = []

        def capture_build(agent_name: str, date: str) -> str:
            captured_dates.append(date)
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_refresh_domain", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["--agent", "architect", "--repo-path", str(tmp_path)])

        assert len(captured_dates) == 1
        assert len(captured_dates[0]) > 0


# ---------------------------------------------------------------------------
# run_refresh_domain is called with the correct arguments
# ---------------------------------------------------------------------------


class TestRefreshDomainCallsRunRefreshDomain:
    """refresh-domain calls run_refresh_domain with repo_path, agent_name, task_prompt."""

    def test_run_called_once(self, tmp_path: Path) -> None:
        """run_refresh_domain is called exactly once."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "architect")
        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.refresh_domain.run_refresh_domain", return_value=0
            ) as mock_run,
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(cmd, ["--agent", "architect", "--repo-path", str(tmp_path)])

        mock_run.assert_called_once()

    def test_run_receives_task_prompt_from_build(self, tmp_path: Path) -> None:
        """run_refresh_domain receives the return value of build_refresh_domain_start."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "architect")
        sentinel = "SENTINEL_REFRESH_DOMAIN_PROMPT"
        captured_prompts: list[str] = []

        def capture_run(repo_path: Path, agent_name: str, task_prompt: str) -> int:
            captured_prompts.append(task_prompt)
            return 0

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.refresh_domain.run_refresh_domain",
                side_effect=capture_run,
            ),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value=sentinel,
            ),
        ):
            runner.invoke(cmd, ["--agent", "architect", "--repo-path", str(tmp_path)])

        assert sentinel in captured_prompts

    def test_run_receives_agent_name(self, tmp_path: Path) -> None:
        """run_refresh_domain receives the agent_name argument."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "developer")
        captured_agent_names: list[str] = []

        def capture_run(repo_path: Path, agent_name: str, task_prompt: str) -> int:
            captured_agent_names.append(agent_name)
            return 0

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.refresh_domain.run_refresh_domain",
                side_effect=capture_run,
            ),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(cmd, ["--agent", "developer", "--repo-path", str(tmp_path)])

        assert "developer" in captured_agent_names


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRefreshDomainErrorHandling:
    """refresh-domain handles non-zero run exit as a warning, exits 0."""

    def test_nonzero_exit_from_run_is_not_abort(self, tmp_path: Path) -> None:
        """If run_refresh_domain returns non-zero, command still completes (no traceback)."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "architect")
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_refresh_domain", return_value=1),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "architect", "--repo-path", str(tmp_path)])

        assert "Traceback" not in (result.output or "")

    def test_nonzero_exit_still_exits_0(self, tmp_path: Path) -> None:
        """A non-zero run_refresh_domain exit is a warning; command exits 0."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        _write_agent_file(tmp_path, "architect")
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_refresh_domain", return_value=2),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "architect", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
