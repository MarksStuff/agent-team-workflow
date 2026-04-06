"""Tests for the `agent-design refresh-domain` CLI command.

Derivation (DESIGN.md § "Refreshing a domain expert"):
- Required --agent option: name of the domain expert agent
- Optional --repo-path (default: current dir)
- Resolves the agent's memory file path from plugins/local/agents/<agent>.md location
- Calls build_refresh_domain_start(agent_name, memory_path)
- Calls run_solo(agent_name, task_prompt, worktree_path, target_repo)
- Missing --agent option: fails with usage error
- Non-zero exit from run_solo is a warning, not an abort

All external dependencies are patched. No real subprocess or filesystem writes
beyond CliRunner's isolated environment.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

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


class TestRefreshDomainCommandArguments:
    """The `refresh-domain` command argument surface."""

    def test_missing_agent_option_fails(self) -> None:
        """Calling refresh-domain with no --agent must exit non-zero."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code != 0

    def test_missing_agent_option_shows_usage_error(self) -> None:
        """Calling refresh-domain with no --agent shows a usage error message."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        output = (result.output or "").lower()
        has_message = any(word in output for word in ("agent", "missing", "required", "error", "usage"))
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_agent_option_accepted(self, tmp_path: Path) -> None:
        """--agent option is accepted without error."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "claude_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(
                cmd, ["--agent", "agent_systems_expert", "--repo-path", str(tmp_path)]
            )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# build_refresh_domain_start is called with correct arguments
# ---------------------------------------------------------------------------


class TestRefreshDomainCallsBuildPrompt:
    """refresh-domain calls build_refresh_domain_start with the right arguments."""

    def test_build_called_with_agent_name(self, tmp_path: Path) -> None:
        """build_refresh_domain_start receives the agent_name argument."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        captured: list[dict] = []

        def capture_build(agent_name: str, memory_path: Path) -> str:
            captured.append({"agent_name": agent_name, "memory_path": memory_path})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["--agent", "claude_expert", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0]["agent_name"] == "claude_expert"

    def test_build_called_with_memory_path(self, tmp_path: Path) -> None:
        """build_refresh_domain_start receives a memory_path argument (a Path object)."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        captured: list[dict] = []

        def capture_build(agent_name: str, memory_path: Path) -> str:
            captured.append({"agent_name": agent_name, "memory_path": memory_path})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(cmd, ["--agent", "claude_expert", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert isinstance(captured[0]["memory_path"], Path)


# ---------------------------------------------------------------------------
# run_solo is called with the correct arguments
# ---------------------------------------------------------------------------


class TestRefreshDomainCallsRunSolo:
    """refresh-domain calls run_solo with the correct arguments."""

    def test_run_solo_called_once(self, tmp_path: Path) -> None:
        """run_solo is called exactly once."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=0) as mock_run,
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(cmd, ["--agent", "claude_expert", "--repo-path", str(tmp_path)])

        mock_run.assert_called_once()

    def test_run_solo_called_with_agent_name(self, tmp_path: Path) -> None:
        """run_solo receives the agent_name as its first argument."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        captured_args: list[tuple] = []

        def capture_run(agent_name: str, task_prompt: str, worktree_path: Path, target_repo: Path) -> int:
            captured_args.append((agent_name, task_prompt, worktree_path, target_repo))
            return 0

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.refresh_domain.run_solo",
                side_effect=capture_run,
            ),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="the_prompt",
            ),
        ):
            runner.invoke(cmd, ["--agent", "claude_expert", "--repo-path", str(tmp_path)])

        assert len(captured_args) == 1
        assert captured_args[0][0] == "claude_expert"

    def test_run_solo_receives_prompt_from_build(self, tmp_path: Path) -> None:
        """run_solo receives the return value of build_refresh_domain_start as task_prompt."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        sentinel = "SENTINEL_REFRESH_DOMAIN_PROMPT"
        captured_prompts: list[str] = []

        def capture_run(agent_name: str, task_prompt: str, worktree_path: Path, target_repo: Path) -> int:
            captured_prompts.append(task_prompt)
            return 0

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.refresh_domain.run_solo",
                side_effect=capture_run,
            ),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value=sentinel,
            ),
        ):
            runner.invoke(cmd, ["--agent", "claude_expert", "--repo-path", str(tmp_path)])

        assert sentinel in captured_prompts


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRefreshDomainErrorHandling:
    """refresh-domain handles error conditions gracefully."""

    def test_nonzero_exit_from_run_solo_does_not_raise(self, tmp_path: Path) -> None:
        """If run_solo returns non-zero, command still completes without unhandled exception."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=1),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "claude_expert", "--repo-path", str(tmp_path)])

        assert "Traceback" not in (result.output or "")

    def test_nonzero_exit_still_completes_with_exit_0(self, tmp_path: Path) -> None:
        """A non-zero run_solo exit is a warning; command itself exits 0."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=2),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "claude_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
