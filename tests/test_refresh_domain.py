"""Tests for the `agent-design refresh-domain` CLI command.

Derivation:
- Requires --agent <name> option
- Checks that agent file exists at plugins/local/agents/<name>.md (via _get_local_agents_dir())
- Calls build_refresh_domain_start(agent_name, today)
- Calls run_solo(agent_name, prompt, worktree_path, repo_path)
  where worktree_path = repo_path / ".agent-design"
- Non-zero exit from run_solo is a warning, not an abort
- Missing --agent → Click usage error
- Agent file not found → abort with "Agent not found" message

All external dependencies are patched. No real subprocess, filesystem state
reads beyond what CliRunner provides, or git calls are made.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_agent_file(agents_dir: Path, agent_name: str) -> Path:
    """Write a stub agent file at agents_dir/<agent_name>.md."""
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agents_dir / f"{agent_name}.md"
    agent_file.write_text(f"# {agent_name} agent\nStub definition.")
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
# Happy path — calls build + run_solo with correct args
# ---------------------------------------------------------------------------


class TestRefreshDomainHappyPath:
    """refresh-domain calls build_refresh_domain_start and run_solo with correct arguments."""

    def test_calls_build_refresh_domain_start_with_agent_name(self, tmp_path: Path) -> None:
        """build_refresh_domain_start receives the agent name."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        _write_agent_file(agents_dir, "crypto_expert")

        captured: list[dict] = []

        def capture_build(agent_name: str, today: str) -> str:
            captured.append({"agent_name": agent_name, "today": today})
            return "mock prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir),
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                side_effect=capture_build,
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "crypto_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        assert len(captured) == 1
        assert captured[0]["agent_name"] == "crypto_expert"

    def test_calls_build_refresh_domain_start_with_today(self, tmp_path: Path) -> None:
        """build_refresh_domain_start receives today's date from the patched date."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        _write_agent_file(agents_dir, "crypto_expert")

        captured_dates: list[str] = []

        def capture_build(agent_name: str, today: str) -> str:
            captured_dates.append(today)
            return "mock prompt"

        mock_date = MagicMock()
        mock_date.today.return_value.isoformat.return_value = "2026-01-01"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir),
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                side_effect=capture_build,
            ),
            patch("agent_design.cli.commands.refresh_domain.date", mock_date),
        ):
            runner.invoke(cmd, ["--agent", "crypto_expert", "--repo-path", str(tmp_path)])

        assert len(captured_dates) == 1
        assert captured_dates[0] == "2026-01-01"

    def test_calls_run_solo_once(self, tmp_path: Path) -> None:
        """run_solo is called exactly once."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        _write_agent_file(agents_dir, "crypto_expert")

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir),
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=0) as mock_run,
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="mock prompt",
            ),
        ):
            runner.invoke(cmd, ["--agent", "crypto_expert", "--repo-path", str(tmp_path)])

        mock_run.assert_called_once()

    def test_run_solo_receives_prompt_from_build(self, tmp_path: Path) -> None:
        """run_solo receives the return value of build_refresh_domain_start."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        _write_agent_file(agents_dir, "crypto_expert")

        sentinel = "SENTINEL_REFRESH_DOMAIN_PROMPT"
        captured_prompts: list[str] = []

        def capture_run(agent_name: str, prompt: str, worktree_path: Path, repo_path: Path) -> int:
            captured_prompts.append(prompt)
            return 0

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir),
            patch("agent_design.cli.commands.refresh_domain.run_solo", side_effect=capture_run),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value=sentinel,
            ),
        ):
            runner.invoke(cmd, ["--agent", "crypto_expert", "--repo-path", str(tmp_path)])

        assert sentinel in captured_prompts

    def test_worktree_path_is_agent_design_subdir(self, tmp_path: Path) -> None:
        """run_solo receives worktree_path = repo_path / '.agent-design'."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        _write_agent_file(agents_dir, "crypto_expert")

        captured_worktrees: list[Path] = []

        def capture_run(agent_name: str, prompt: str, worktree_path: Path, repo_path: Path) -> int:
            captured_worktrees.append(worktree_path)
            return 0

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir),
            patch("agent_design.cli.commands.refresh_domain.run_solo", side_effect=capture_run),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="mock prompt",
            ),
        ):
            runner.invoke(cmd, ["--agent", "crypto_expert", "--repo-path", str(tmp_path)])

        assert len(captured_worktrees) == 1
        assert captured_worktrees[0] == tmp_path.resolve() / ".agent-design"

    def test_nonzero_run_solo_is_warning_exit_code_0(self, tmp_path: Path) -> None:
        """Non-zero run_solo return is a warning; CLI exits 0."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        _write_agent_file(agents_dir, "crypto_expert")

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir),
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=1),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="mock prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "crypto_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0

    def test_nonzero_run_solo_no_traceback(self, tmp_path: Path) -> None:
        """Non-zero run_solo does not produce an unhandled exception traceback."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        _write_agent_file(agents_dir, "crypto_expert")

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir),
            patch("agent_design.cli.commands.refresh_domain.run_solo", return_value=2),
            patch(
                "agent_design.cli.commands.refresh_domain.build_refresh_domain_start",
                return_value="mock prompt",
            ),
        ):
            result = runner.invoke(cmd, ["--agent", "crypto_expert", "--repo-path", str(tmp_path)])

        assert "Traceback" not in (result.output or "")


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestRefreshDomainErrorPaths:
    """refresh-domain handles error conditions correctly."""

    def test_missing_agent_option_exits_nonzero(self, tmp_path: Path) -> None:
        """Calling refresh-domain with no --agent option exits non-zero."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_agent_file_not_found_aborts(self, tmp_path: Path) -> None:
        """When agent file does not exist, command exits non-zero."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        # No agent file created

        runner = CliRunner()
        with patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir):
            result = runner.invoke(cmd, ["--agent", "nonexistent_agent", "--repo-path", str(tmp_path)])

        assert result.exit_code != 0

    def test_agent_file_not_found_shows_message(self, tmp_path: Path) -> None:
        """When agent file does not exist, command prints 'Agent not found' message."""
        from agent_design.cli.commands.refresh_domain import refresh_domain as cmd

        agents_dir = tmp_path / "plugins" / "local" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        runner = CliRunner()
        with patch("agent_design.cli.commands.refresh_domain._get_local_agents_dir", return_value=agents_dir):
            result = runner.invoke(cmd, ["--agent", "nonexistent_agent", "--repo-path", str(tmp_path)])

        output = (result.output or "").lower()
        has_message = any(w in output for w in ("agent not found", "not found", "nonexistent_agent"))
        assert has_message, f"Expected 'Agent not found' message. Output: {result.output!r}"
