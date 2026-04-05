"""Tests for the `agent-design fix-ci` CLI command.

Contract:
- `--repo-path` (default: current dir) and `--pr` (optional) accepted
- If `--pr` given, use it; else auto-detect via _get_pr_info
- UsageError when both --pr and auto-detect fail
- When _fetch_ci_failures returns None → CI green, no launcher call, exit 0
- When _fetch_ci_failures returns text → run_team_in_repo called once with
  a start message built from build_fix_ci_start

All external dependencies (subprocess, launcher) are patched.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

_PR_INFO_STUB = {"url": "https://github.com/o/r/pull/1", "number": 1}

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestFixCiCommandRegistered:
    """fix-ci is importable, callable, and registered in main CLI."""

    def test_fix_ci_module_importable(self) -> None:
        from agent_design.cli.commands import fix_ci  # noqa: F401

    def test_fix_ci_command_callable(self) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        assert callable(fix_ci_cmd)

    def test_fix_ci_registered_in_main_cli(self) -> None:
        from agent_design.cli.main import cli

        assert "fix-ci" in cli.commands, "'fix-ci' not registered in main.py"

    def test_fix_ci_help_runs(self) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        result = runner.invoke(fix_ci_cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestFixCiArguments:
    """fix-ci accepts --repo-path and --pr, both optional."""

    def test_repo_path_accepted(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._get_pr_info", return_value=_PR_INFO_STUB),
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=None),
        ):
            result = runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path)])
        # exit 0 because failures is None (CI green path)
        assert result.exit_code == 0

    def test_pr_option_accepted(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=None):
            result = runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", "https://github.com/o/r/pull/42"])
        assert result.exit_code == 0

    def test_both_options_optional(self, tmp_path: Path) -> None:
        """fix-ci can be invoked with no options at all (uses defaults)."""
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._get_pr_info", return_value=_PR_INFO_STUB),
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=None),
        ):
            # invoke with no explicit args — defaults kick in
            result = runner.invoke(fix_ci_cmd, [])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# PR URL resolution
# ---------------------------------------------------------------------------


class TestFixCiPrUrlResolution:
    """--pr takes precedence; auto-detect called when --pr omitted; UsageError when both fail."""

    def test_pr_option_takes_precedence(self, tmp_path: Path) -> None:
        """When --pr is supplied, _get_pr_info is never called."""
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._get_pr_info") as mock_detect,
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=None),
        ):
            runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", "https://github.com/o/r/pull/7"])
        mock_detect.assert_not_called()

    def test_auto_detect_called_when_pr_omitted(self, tmp_path: Path) -> None:
        """When --pr is omitted, _get_pr_info is called."""
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.fix_ci._get_pr_info", return_value=_PR_INFO_STUB
            ) as mock_detect,
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=None),
        ):
            runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path)])
        mock_detect.assert_called_once()

    def test_usage_error_when_both_fail(self, tmp_path: Path) -> None:
        """UsageError (non-zero exit) when --pr omitted and auto-detect returns None."""
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with patch("agent_design.cli.commands.fix_ci._get_pr_info", return_value=None):
            result = runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_usage_error_message_mentions_pr(self, tmp_path: Path) -> None:
        """Error message when PR URL missing mentions PR or --pr."""
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with patch("agent_design.cli.commands.fix_ci._get_pr_info", return_value=None):
            result = runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        assert "pr" in output or "pull" in output


# ---------------------------------------------------------------------------
# Green path (CI passing)
# ---------------------------------------------------------------------------


class TestFixCiGreenPath:
    """When _fetch_ci_failures returns None, no launcher call and exit 0."""

    def test_no_launcher_call_when_green(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=None),
            patch("agent_design.cli.commands.fix_ci.run_team_in_repo") as mock_launcher,
        ):
            runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", "https://github.com/o/r/pull/1"])
        mock_launcher.assert_not_called()

    def test_exit_zero_when_green(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=None),
            patch("agent_design.cli.commands.fix_ci.run_team_in_repo"),
        ):
            result = runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", "https://github.com/o/r/pull/1"])
        assert result.exit_code == 0

    def test_green_message_printed(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=None),
            patch("agent_design.cli.commands.fix_ci.run_team_in_repo"),
        ):
            result = runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", "https://github.com/o/r/pull/1"])
        assert "passing" in (result.output or "").lower() or "green" in (result.output or "").lower()


# ---------------------------------------------------------------------------
# Failing path (CI failures present)
# ---------------------------------------------------------------------------


class TestFixCiFailingPath:
    """When _fetch_ci_failures returns text, run_team_in_repo called with correct start message."""

    _FAILURES = "Failing checks:\n  • lint\n  • typecheck"
    _PR_URL = "https://github.com/o/r/pull/5"

    def test_launcher_called_once_when_failing(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=self._FAILURES),
            patch("agent_design.cli.commands.fix_ci.run_team_in_repo", return_value=0) as mock_launcher,
            patch("agent_design.cli.commands.fix_ci._commit_and_push"),
            patch("agent_design.cli.commands.fix_ci._current_branch", return_value="feat/impl-ci-fix"),
        ):
            runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", self._PR_URL])
        mock_launcher.assert_called_once()

    def test_launcher_receives_start_message_with_pr_url(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        captured: list[str] = []

        def capture_launcher(repo_path: Path, worktree_path: Path, start_message: str) -> int:
            captured.append(start_message)
            return 0

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=self._FAILURES),
            patch("agent_design.cli.commands.fix_ci.run_team_in_repo", side_effect=capture_launcher),
            patch("agent_design.cli.commands.fix_ci._commit_and_push"),
            patch("agent_design.cli.commands.fix_ci._current_branch", return_value="feat/impl-ci-fix"),
        ):
            runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", self._PR_URL])

        assert len(captured) == 1
        assert self._PR_URL in captured[0]

    def test_launcher_receives_start_message_with_failures(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        captured: list[str] = []

        def capture_launcher(repo_path: Path, worktree_path: Path, start_message: str) -> int:
            captured.append(start_message)
            return 0

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=self._FAILURES),
            patch("agent_design.cli.commands.fix_ci.run_team_in_repo", side_effect=capture_launcher),
            patch("agent_design.cli.commands.fix_ci._commit_and_push"),
            patch("agent_design.cli.commands.fix_ci._current_branch", return_value="feat/impl-ci-fix"),
        ):
            runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", self._PR_URL])

        assert len(captured) == 1
        assert "lint" in captured[0] or "typecheck" in captured[0] or "Failing" in captured[0]

    def test_nonzero_launcher_exit_prints_warning(self, tmp_path: Path) -> None:
        from agent_design.cli.commands.fix_ci import fix_ci as fix_ci_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.fix_ci._fetch_ci_failures", return_value=self._FAILURES),
            patch("agent_design.cli.commands.fix_ci.run_team_in_repo", return_value=1),
            patch("agent_design.cli.commands.fix_ci._commit_and_push"),
            patch("agent_design.cli.commands.fix_ci._current_branch", return_value="feat/impl-ci-fix"),
        ):
            result = runner.invoke(fix_ci_cmd, ["--repo-path", str(tmp_path), "--pr", self._PR_URL])
        output_lower = (result.output or "").lower()
        assert any(word in output_lower for word in ("warn", "error", "fail", "exit", "code"))
