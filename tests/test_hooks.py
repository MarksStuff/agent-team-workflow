"""Tests for Phase 9 — Hooks.

Covers:
  Group 1: CLI option tests — --test-cmd on `agent-design impl`
  Group 2: Hook scripts existence tests — scripts/hooks/*.sh
  Group 3: run_team_in_repo hook-wiring tests — settings.json written/cleaned
  Group 4: Hook settings.json content tests — correct hook structure

All subprocess calls are patched — no real claude process is spawned.
"""

import contextlib
import json
import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_process(returncode: int = 0) -> MagicMock:
    mock = MagicMock()
    mock.returncode = returncode
    return mock


# Path to the repo root (this file's grandparent)
REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Group 1: CLI option tests
# ---------------------------------------------------------------------------


class TestImplTestCmdOption:
    """--test-cmd option is declared on the impl command."""

    def test_impl_accepts_test_cmd_option(self) -> None:
        """--test-cmd appears in `agent-design impl --help` output."""
        from agent_design.cli.commands.impl import impl

        runner = CliRunner()
        result = runner.invoke(impl, ["--help"])
        assert result.exit_code == 0, f"--help failed: {result.output}"
        assert "--test-cmd" in result.output, f"--test-cmd not found in --help output:\n{result.output}"

    def test_test_cmd_default_value(self) -> None:
        """The default for --test-cmd is 'python -m pytest --tb=short -q'."""
        import click

        from agent_design.cli.commands.impl import impl

        # Walk the Click params to find the --test-cmd option
        test_cmd_param = None
        for param in impl.params:
            if isinstance(param, click.Option) and "--test-cmd" in param.opts:
                test_cmd_param = param
                break

        assert test_cmd_param is not None, "--test-cmd option not found on impl command"
        assert test_cmd_param.default == "python -m pytest --tb=short -q", (
            f"Unexpected default: {test_cmd_param.default!r}"
        )


# ---------------------------------------------------------------------------
# Group 2: Hook scripts existence tests
# ---------------------------------------------------------------------------


class TestHookScriptsExist:
    """scripts/hooks/*.sh exist and are executable."""

    def test_task_completed_sh_exists(self) -> None:
        """scripts/hooks/task_completed.sh exists."""
        hook = REPO_ROOT / "scripts" / "hooks" / "task_completed.sh"
        assert hook.exists(), f"File not found: {hook}"

    def test_teammate_idle_sh_exists(self) -> None:
        """scripts/hooks/teammate_idle.sh exists."""
        hook = REPO_ROOT / "scripts" / "hooks" / "teammate_idle.sh"
        assert hook.exists(), f"File not found: {hook}"

    def test_task_completed_sh_is_executable(self) -> None:
        """scripts/hooks/task_completed.sh has the executable bit set."""
        hook = REPO_ROOT / "scripts" / "hooks" / "task_completed.sh"
        assert hook.exists(), f"File not found: {hook}"
        file_stat = hook.stat()
        assert file_stat.st_mode & stat.S_IXUSR, f"task_completed.sh is not executable: mode={oct(file_stat.st_mode)}"

    def test_teammate_idle_sh_is_executable(self) -> None:
        """scripts/hooks/teammate_idle.sh has the executable bit set."""
        hook = REPO_ROOT / "scripts" / "hooks" / "teammate_idle.sh"
        assert hook.exists(), f"File not found: {hook}"
        file_stat = hook.stat()
        assert file_stat.st_mode & stat.S_IXUSR, f"teammate_idle.sh is not executable: mode={oct(file_stat.st_mode)}"


# ---------------------------------------------------------------------------
# Group 3: run_team_in_repo hook-wiring tests
# ---------------------------------------------------------------------------


class TestRunTeamInRepoHookWiring:
    """run_team_in_repo writes and cleans up .claude/settings.json when test_cmd given."""

    def test_run_team_writes_settings_json_when_test_cmd_given(self, tmp_path: Path) -> None:
        """settings.json is written to repo_path/.claude/ before subprocess.run is called."""
        from agent_design.launcher import run_team_in_repo

        repo = tmp_path / "repo"
        repo.mkdir()
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()

        settings_path = repo / ".claude" / "settings.json"
        captured: list[dict] = []

        def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
            # Read settings.json at the moment subprocess.run is called
            if settings_path.exists():
                captured.append(json.loads(settings_path.read_text()))
            return _make_completed_process()

        with patch("agent_design.launcher.subprocess.run", side_effect=_fake_run):
            run_team_in_repo(repo, worktree, "start", test_cmd="pytest -q")

        assert len(captured) == 1, "settings.json was not present when subprocess.run was called"
        assert "hooks" in captured[0], f"'hooks' key missing from settings.json: {captured[0]}"

    def test_run_team_sets_test_cmd_env_var(self, tmp_path: Path) -> None:
        """TEST_CMD=pytest -q is present in the env passed to subprocess."""
        from agent_design.launcher import run_team_in_repo

        repo = tmp_path / "repo"
        repo.mkdir()
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_team_in_repo(repo, worktree, "start", test_cmd="pytest -q")

        kwargs = mock_run.call_args[1]
        env = kwargs.get("env", {})
        assert env.get("TEST_CMD") == "pytest -q", f"TEST_CMD not set correctly in env: {env.get('TEST_CMD')!r}"

    def test_run_team_sets_repo_path_env_var(self, tmp_path: Path) -> None:
        """REPO_PATH=str(repo_path) is present in the env passed to subprocess."""
        from agent_design.launcher import run_team_in_repo

        repo = tmp_path / "repo"
        repo.mkdir()
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()) as mock_run:
            run_team_in_repo(repo, worktree, "start", test_cmd="pytest -q")

        kwargs = mock_run.call_args[1]
        env = kwargs.get("env", {})
        assert env.get("REPO_PATH") == str(repo), f"REPO_PATH not set correctly in env: {env.get('REPO_PATH')!r}"

    def test_run_team_cleans_up_settings_json_after_session(self, tmp_path: Path) -> None:
        """settings.json is removed after run_team_in_repo returns."""
        from agent_design.launcher import run_team_in_repo

        repo = tmp_path / "repo"
        repo.mkdir()
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()):
            run_team_in_repo(repo, worktree, "start", test_cmd="pytest -q")

        settings_path = repo / ".claude" / "settings.json"
        assert not settings_path.exists(), f"settings.json still exists after session: {settings_path}"

    def test_run_team_cleans_up_settings_json_on_error(self, tmp_path: Path) -> None:
        """settings.json is removed even when subprocess raises an exception."""
        from agent_design.launcher import run_team_in_repo

        repo = tmp_path / "repo"
        repo.mkdir()
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()

        with (
            patch(
                "agent_design.launcher.subprocess.run",
                side_effect=RuntimeError("subprocess exploded"),
            ),
            contextlib.suppress(RuntimeError),
        ):
            run_team_in_repo(repo, worktree, "start", test_cmd="pytest -q")

        settings_path = repo / ".claude" / "settings.json"
        assert not settings_path.exists(), f"settings.json was not cleaned up after exception: {settings_path}"

    def test_run_team_no_settings_json_when_no_test_cmd(self, tmp_path: Path) -> None:
        """settings.json is NOT written when test_cmd=None (default)."""
        from agent_design.launcher import run_team_in_repo

        repo = tmp_path / "repo"
        repo.mkdir()
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()

        settings_path = repo / ".claude" / "settings.json"

        with patch("agent_design.launcher.subprocess.run", return_value=_make_completed_process()):
            run_team_in_repo(repo, worktree, "start")

        assert not settings_path.exists(), f"settings.json was written even though test_cmd=None: {settings_path}"


# ---------------------------------------------------------------------------
# Group 4: Hook settings.json content tests
# ---------------------------------------------------------------------------


class TestSettingsJsonContent:
    """The written settings.json has the expected hook structure."""

    def _capture_settings(self, tmp_path: Path, test_cmd: str = "pytest -q") -> dict:  # type: ignore[return]
        """Helper: run run_team_in_repo and capture the settings.json written."""
        from agent_design.launcher import run_team_in_repo

        repo = tmp_path / "repo"
        repo.mkdir()
        worktree = tmp_path / ".agent-design"
        worktree.mkdir()

        settings_path = repo / ".claude" / "settings.json"
        captured: list[dict] = []

        def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
            if settings_path.exists():
                captured.append(json.loads(settings_path.read_text()))
            return _make_completed_process()

        with patch("agent_design.launcher.subprocess.run", side_effect=_fake_run):
            run_team_in_repo(repo, worktree, "start", test_cmd=test_cmd)

        assert captured, "settings.json was never written"
        return captured[0]

    def test_settings_json_has_pretooluse_hook(self, tmp_path: Path) -> None:
        """settings.json contains a PreToolUse hook for TaskUpdate."""
        settings = self._capture_settings(tmp_path)
        hooks = settings.get("hooks", {})
        pre_tool_use_hooks = hooks.get("PreToolUse", [])
        assert pre_tool_use_hooks, "No PreToolUse hooks found in settings.json"

        # At least one hook should target TaskUpdate
        all_matchers = []
        for hook_entry in pre_tool_use_hooks:
            all_matchers.extend(hook_entry.get("matcher", ""))
        assert any("TaskUpdate" in str(m) for m in all_matchers) or any(
            "TaskUpdate" in str(hook_entry) for hook_entry in pre_tool_use_hooks
        ), f"No PreToolUse hook for TaskUpdate found: {pre_tool_use_hooks}"

    def test_settings_json_has_stop_hook(self, tmp_path: Path) -> None:
        """settings.json contains a Stop hook."""
        settings = self._capture_settings(tmp_path)
        hooks = settings.get("hooks", {})
        assert "Stop" in hooks, f"No Stop hook found in settings.json hooks: {hooks}"
        assert hooks["Stop"], "Stop hooks list is empty"

    def test_settings_json_hook_commands_are_absolute_paths(self, tmp_path: Path) -> None:
        """The hook command paths in settings.json are absolute paths."""
        settings = self._capture_settings(tmp_path)
        hooks = settings.get("hooks", {})

        for hook_type, hook_list in hooks.items():
            for hook_entry in hook_list:
                for hook in hook_entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    # Extract the script path (first token before any spaces/args)
                    script_path = cmd.split()[0] if cmd else ""
                    if script_path.endswith(".sh"):
                        assert os.path.isabs(script_path), (
                            f"Hook command in {hook_type} is not an absolute path: {script_path!r}"
                        )
