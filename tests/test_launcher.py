"""Tests for run_print_team() in agent_design/launcher.py.

Derivation: DESIGN.md Phase 7 specifies run_print_team() as a --print session
with CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 set. It is the launcher primitive
used by both `remember` and `review-feedback` commands.

Contract confirmed in DISCUSSION.md by Developer:
  run_print_team(worktree_path: Path, target_repo: Path, start_message: str) -> int
  - Sets CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in env (same as run_team)
  - Passes --print flag (same as run_solo)
  - Uses --agent eng_manager (same as run_team)
  - worktree_path is the cwd; target_repo is --add-dir
  - No --strict-mcp-config (that's only in run_solo)

All subprocess calls are patched — no real claude process is spawned.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_design.launcher import run_print_team

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_process(returncode: int = 0) -> MagicMock:
    mock = MagicMock()
    mock.returncode = returncode
    return mock


# ---------------------------------------------------------------------------
# Existence check
# ---------------------------------------------------------------------------


class TestRunPrintTeamExists:
    """run_print_team is importable and callable."""

    def test_run_print_team_is_callable(self) -> None:
        assert callable(run_print_team)


# ---------------------------------------------------------------------------
# Subprocess invocation contract
# ---------------------------------------------------------------------------


class TestRunPrintTeamSubprocessContract:
    """run_print_team builds the correct subprocess call."""

    def test_subprocess_run_is_called(self, tmp_path: Path) -> None:
        """subprocess.run is called exactly once."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "some message")

        mock_run.assert_called_once()

    def test_command_includes_print_flag(self, tmp_path: Path) -> None:
        """The command list passed to subprocess.run contains '--print'."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "my message")

        cmd = mock_run.call_args[0][0]
        assert "--print" in cmd, f"--print not in command: {cmd}"

    def test_command_includes_start_message(self, tmp_path: Path) -> None:
        """The start_message is passed as the final positional argument."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()
        message = "A specific memory correction message"

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, message)

        cmd = mock_run.call_args[0][0]
        assert message in cmd, f"start_message not in command: {cmd}"

    def test_command_starts_with_claude(self, tmp_path: Path) -> None:
        """The command begins with 'claude'."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "msg")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "claude", f"Command does not start with 'claude': {cmd}"

    def test_command_includes_dangerously_skip_permissions(self, tmp_path: Path) -> None:
        """--dangerously-skip-permissions is in the command."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "msg")

        cmd = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" in cmd

    def test_command_includes_agent_eng_manager(self, tmp_path: Path) -> None:
        """--agent eng_manager is in the command (consistent with other launchers)."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "msg")

        cmd = mock_run.call_args[0][0]
        assert "--agent" in cmd
        agent_idx = cmd.index("--agent")
        assert cmd[agent_idx + 1] == "eng_manager"

    def test_cwd_is_worktree_path(self, tmp_path: Path) -> None:
        """subprocess.run is called with cwd=worktree_path."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "msg")

        kwargs = mock_run.call_args[1]
        assert kwargs.get("cwd") == str(worktree)

    def test_add_dir_includes_target_repo(self, tmp_path: Path) -> None:
        """--add-dir <target_repo> is in the command."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "msg")

        cmd = mock_run.call_args[0][0]
        assert "--add-dir" in cmd
        add_dir_idx = cmd.index("--add-dir")
        assert cmd[add_dir_idx + 1] == str(target)


# ---------------------------------------------------------------------------
# Environment contract: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
# ---------------------------------------------------------------------------


class TestRunPrintTeamEnvContract:
    """run_print_team sets CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in the env."""

    def test_agent_teams_env_var_is_set(self, tmp_path: Path) -> None:
        """CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 is present in the subprocess env."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "msg")

        kwargs = mock_run.call_args[1]
        env = kwargs.get("env", {})
        assert env.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1", (
            f"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS not set to '1' in env: {env}"
        )

    def test_env_inherits_from_os_environ(self, tmp_path: Path) -> None:
        """The subprocess env is a copy of os.environ (not empty)."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_print_team(worktree, target, "msg")

        kwargs = mock_run.call_args[1]
        env = kwargs.get("env", {})
        # PATH must be present — it comes from os.environ
        assert "PATH" in env or len(env) > 1, "env appears to be empty or missing inherited vars"


# ---------------------------------------------------------------------------
# Return code contract
# ---------------------------------------------------------------------------


class TestRunPrintTeamReturnCode:
    """run_print_team returns the exit code from the subprocess."""

    def test_returns_zero_on_success(self, tmp_path: Path) -> None:
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process(0)):
            rc = run_print_team(worktree, target, "msg")

        assert rc == 0

    def test_returns_nonzero_on_failure(self, tmp_path: Path) -> None:
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process(1)):
            rc = run_print_team(worktree, target, "msg")

        assert rc == 1

    def test_returns_arbitrary_exit_code(self, tmp_path: Path) -> None:
        """Any non-zero exit code is passed through unchanged."""
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()
        target = tmp_path / "repo"
        target.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process(42)):
            rc = run_print_team(worktree, target, "msg")

        assert rc == 42


# ---------------------------------------------------------------------------
# MCP config contract (NOT required per Developer's contract — run_print_team
# does not use --strict-mcp-config unlike run_solo)
# ---------------------------------------------------------------------------
# No MCP config tests — run_print_team follows run_team pattern, not run_solo.
