"""Tests for the `agent-design continue` CLI command.

All external dependencies (run_team, checkpoint, detect_existing_worktree,
load_round_state, save_round_state) are injected via mocking so no real
filesystem, subprocess, or git calls are made.

Covers AC3, AC4, AC5, EC4 from DESIGN.md Phase 5 acceptance criteria.
"""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from agent_design.cli.commands.continue_ import continue_cmd
from agent_design.state import RoundState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    *,
    feature_slug: str = "test-feature",
    feature_request: str = "Build something",
    target_repo: str = "/some/repo",
    discussion_turns: int = 0,
    pr_url: str | None = None,
    checkpoint_tag: str | None = None,
    baseline_commit: str | None = None,
    completed: list[str] | None = None,
) -> RoundState:
    """Construct a minimal RoundState for test use (no `phase` field — Phase 5)."""
    return RoundState(
        feature_slug=feature_slug,
        feature_request=feature_request,
        target_repo=target_repo,
        discussion_turns=discussion_turns,
        pr_url=pr_url,
        checkpoint_tag=checkpoint_tag,
        baseline_commit=baseline_commit,
        completed=completed if completed is not None else [],
    )


def _make_worktree(tmp_path: Path, state: RoundState, *, has_design_md: bool = True) -> Path:
    """Create a minimal .agent-design worktree structure in tmp_path."""
    worktree = tmp_path / ".agent-design"
    worktree.mkdir()

    # Write ROUND_STATE.json
    from dataclasses import asdict

    (worktree / "ROUND_STATE.json").write_text(json.dumps(asdict(state)))

    if has_design_md:
        (worktree / "DESIGN.md").write_text("# Design\n\nSome design content.\n")

    return worktree


# ---------------------------------------------------------------------------
# AC3: `continue` command is registered and runnable
# ---------------------------------------------------------------------------


class TestContinueCmdRegistered:
    """The `continue` command exists as a Click command."""

    def test_continue_cmd_is_callable(self) -> None:
        """The continue_cmd Click command object is importable and callable."""
        assert callable(continue_cmd)

    def test_continue_cmd_has_correct_name(self) -> None:
        """The Click command name is 'continue'."""
        # continue is a Python keyword so the function will be named continue_cmd
        # but registered with name='continue'. Check the registered name.
        assert continue_cmd.name in ("continue", "continue_cmd")

    def test_continue_cmd_help_runs(self) -> None:
        """--help does not raise."""
        runner = CliRunner()
        result = runner.invoke(continue_cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# AC3: No active session — must exit non-zero with error message
# ---------------------------------------------------------------------------


class TestContinueCmdNoSession:
    """continue command exits with error when no active session is found."""

    def test_no_worktree_exits_nonzero(self, tmp_path: Path) -> None:
        """No .agent-design directory → non-zero exit code (AC3, EC4)."""
        runner = CliRunner()

        with patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=False):
            result = runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        assert result.exit_code != 0

    def test_no_worktree_prints_error_not_traceback(self, tmp_path: Path) -> None:
        """Error output must not contain a Python stack trace (AC3, EC4)."""
        runner = CliRunner()

        with patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=False):
            result = runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        # The user-visible output must not contain a traceback
        assert "Traceback" not in (result.output or "")
        # The exception object (if any) must not itself be a traceback string —
        # convert to str safely so we are checking a string, not an arbitrary object.
        assert "Traceback" not in str(result.exception or "")

    def test_no_worktree_error_message_is_actionable(self, tmp_path: Path) -> None:
        """Error message must mention 'session' or 'init' so user knows what to do (AC3)."""
        runner = CliRunner()

        with patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=False):
            result = runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        output = result.output.lower()
        # Should mention session or init in the error message
        assert "session" in output or "init" in output


# ---------------------------------------------------------------------------
# AC3: Active session — loads state, calls run_team with build_continue_start
# ---------------------------------------------------------------------------


class TestContinueCmdWithSession:
    """continue command with an active session: loads state, calls run_team."""

    def test_calls_run_team(self, tmp_path: Path) -> None:
        """continue must call run_team() exactly once (AC3)."""
        state = _make_state(feature_request="My feature")
        _make_worktree(tmp_path, state)
        runner = CliRunner()

        with (
            patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=True),
            patch("agent_design.cli.commands.continue_.load_round_state", return_value=state),
            patch("agent_design.cli.commands.continue_.run_team_in_repo", return_value=0) as mock_run_team,
            patch("agent_design.cli.commands.continue_.save_round_state"),
            patch("agent_design.cli.commands.continue_.checkpoint"),
        ):
            runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        mock_run_team.assert_called_once()

    def test_start_message_contains_feature_request(self, tmp_path: Path) -> None:
        """The start_message passed to run_team must contain the feature request (AC3)."""
        state = _make_state(feature_request="Build a special widget")
        _make_worktree(tmp_path, state)
        runner = CliRunner()

        captured_message: list[str] = []

        def capture_run_team(repo_path: Path, worktree_path: Path, start_message: str) -> int:
            captured_message.append(start_message)
            return 0

        with (
            patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=True),
            patch("agent_design.cli.commands.continue_.load_round_state", return_value=state),
            patch("agent_design.cli.commands.continue_.run_team_in_repo", side_effect=capture_run_team),
            patch("agent_design.cli.commands.continue_.save_round_state"),
            patch("agent_design.cli.commands.continue_.checkpoint"),
        ):
            runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        assert len(captured_message) == 1
        assert "Build a special widget" in captured_message[0]

    def test_start_message_built_by_build_continue_start(self, tmp_path: Path) -> None:
        """run_team receives a message from build_continue_start (AC3).

        We verify this by patching build_continue_start and checking its return
        value ends up as the argument to run_team.
        """
        state = _make_state(feature_request="My feature")
        _make_worktree(tmp_path, state)
        runner = CliRunner()
        sentinel = "SENTINEL_PROMPT_VALUE"

        with (
            patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=True),
            patch("agent_design.cli.commands.continue_.load_round_state", return_value=state),
            patch("agent_design.cli.commands.continue_.build_continue_start", return_value=sentinel),
            patch("agent_design.cli.commands.continue_.run_team_in_repo", return_value=0) as mock_run_team,
            patch("agent_design.cli.commands.continue_.save_round_state"),
            patch("agent_design.cli.commands.continue_.checkpoint"),
        ):
            runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        # The sentinel must be the start_message arg to run_team
        _repo_arg, _worktree_arg, start_message_arg = mock_run_team.call_args[0]
        assert start_message_arg == sentinel

    def test_state_saved_after_run_team(self, tmp_path: Path) -> None:
        """save_round_state is called after run_team completes (AC3)."""
        state = _make_state()
        _make_worktree(tmp_path, state)
        runner = CliRunner()

        with (
            patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=True),
            patch("agent_design.cli.commands.continue_.load_round_state", return_value=state),
            patch("agent_design.cli.commands.continue_.run_team_in_repo", return_value=0),
            patch("agent_design.cli.commands.continue_.save_round_state") as mock_save,
            patch("agent_design.cli.commands.continue_.checkpoint"),
        ):
            runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        mock_save.assert_called_once()

    def test_checkpoint_created_after_run_team(self, tmp_path: Path) -> None:
        """checkpoint() is called after run_team completes (AC3)."""
        state = _make_state()
        _make_worktree(tmp_path, state)
        runner = CliRunner()

        with (
            patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=True),
            patch("agent_design.cli.commands.continue_.load_round_state", return_value=state),
            patch("agent_design.cli.commands.continue_.run_team_in_repo", return_value=0),
            patch("agent_design.cli.commands.continue_.save_round_state"),
            patch("agent_design.cli.commands.continue_.checkpoint") as mock_checkpoint,
        ):
            runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        mock_checkpoint.assert_called_once()

    def test_discussion_turns_incremented(self, tmp_path: Path) -> None:
        """discussion_turns is incremented before save_round_state is called."""
        state = _make_state(discussion_turns=2)
        _make_worktree(tmp_path, state)
        runner = CliRunner()

        saved_states: list[RoundState] = []

        def capture_save(path: Path, s: RoundState) -> None:
            saved_states.append(s)

        with (
            patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=True),
            patch("agent_design.cli.commands.continue_.load_round_state", return_value=state),
            patch("agent_design.cli.commands.continue_.run_team_in_repo", return_value=0),
            patch("agent_design.cli.commands.continue_.save_round_state", side_effect=capture_save),
            patch("agent_design.cli.commands.continue_.checkpoint"),
        ):
            runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        assert len(saved_states) >= 1
        assert saved_states[0].discussion_turns == 3

    def test_run_team_nonzero_exit_does_not_abort(self, tmp_path: Path) -> None:
        """If run_team returns nonzero, the command still saves state (warning, not abort)."""
        state = _make_state()
        _make_worktree(tmp_path, state)
        runner = CliRunner()

        with (
            patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=True),
            patch("agent_design.cli.commands.continue_.load_round_state", return_value=state),
            patch("agent_design.cli.commands.continue_.run_team_in_repo", return_value=1),
            patch("agent_design.cli.commands.continue_.save_round_state") as mock_save,
            patch("agent_design.cli.commands.continue_.checkpoint"),
        ):
            runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        # State must still be saved even if claude exited non-zero
        mock_save.assert_called_once()

    def test_build_continue_start_receives_feature_request_from_state(self, tmp_path: Path) -> None:
        """build_continue_start is called with feature_request from loaded state."""
        state = _make_state(feature_request="My important feature")
        _make_worktree(tmp_path, state)
        runner = CliRunner()

        with (
            patch("agent_design.cli.commands.continue_.detect_existing_worktree", return_value=True),
            patch("agent_design.cli.commands.continue_.load_round_state", return_value=state),
            patch("agent_design.cli.commands.continue_.build_continue_start", return_value="prompt") as mock_build,
            patch("agent_design.cli.commands.continue_.run_team_in_repo", return_value=0),
            patch("agent_design.cli.commands.continue_.save_round_state"),
            patch("agent_design.cli.commands.continue_.checkpoint"),
        ):
            runner.invoke(continue_cmd, ["--repo-path", str(tmp_path)])

        # Must be called with the feature request from state
        call_kwargs = mock_build.call_args
        # feature_request must be "My important feature" either positionally or by keyword
        args = call_kwargs[0] if call_kwargs[0] else ()
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        called_with_feature = "My important feature" in args or kwargs.get("feature_request") == "My important feature"
        assert called_with_feature, f"Expected feature_request in call args: {call_kwargs}"


# ---------------------------------------------------------------------------
# AC5: feedback.py uses build_continue_start, not build_feedback_start
# ---------------------------------------------------------------------------


class TestFeedbackCommandUsesBuildContinueStart:
    """feedback command must use build_continue_start, not build_feedback_start (AC5)."""

    def test_feedback_imports_build_continue_start_not_build_feedback_start(self) -> None:
        """After Phase 5: agent_design.cli.commands.feedback must not import build_feedback_start."""
        import ast
        from pathlib import Path

        feedback_path = Path(__file__).parent.parent / "agent_design" / "cli" / "commands" / "feedback.py"
        source = feedback_path.read_text()
        tree = ast.parse(source)

        # Check all import statements in feedback.py
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.ImportFrom, ast.Import)):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)

        assert "build_feedback_start" not in imported_names, (
            "feedback.py still imports build_feedback_start — it must use build_continue_start after Phase 5"
        )

    def test_feedback_imports_build_continue_start(self) -> None:
        """After Phase 5: agent_design.cli.commands.feedback must import build_continue_start."""
        import ast
        from pathlib import Path

        feedback_path = Path(__file__).parent.parent / "agent_design" / "cli" / "commands" / "feedback.py"
        source = feedback_path.read_text()
        tree = ast.parse(source)

        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)

        assert "build_continue_start" in imported_names, "feedback.py must import build_continue_start after Phase 5"


# ---------------------------------------------------------------------------
# AC4: `next` is removed or aliased to `continue`
# ---------------------------------------------------------------------------


class TestNextCommandRemovedOrAliased:
    """After Phase 5: `next` command must be removed or aliased to `continue` (AC4)."""

    def test_main_cli_registers_continue_command(self) -> None:
        """agent-design CLI has a 'continue' command registered (AC3, AC4)."""
        from agent_design.cli.main import cli

        assert "continue" in cli.commands, (
            "'continue' command is not registered in main.py — it must be added in Phase 5"
        )

    def test_next_round_not_the_primary_command_in_main(self) -> None:
        """After Phase 5: 'next' is either gone or aliased — not the primary command.

        This test verifies structural intent: the command registered as 'next'
        must either not exist (removed) or point to the continue implementation,
        not the old next_round function.
        """
        from agent_design.cli.main import cli

        if "next" in cli.commands:
            # If 'next' still exists, it must be the same object as 'continue'
            # (i.e., an alias), not a separate command with the old next_round logic
            next_cmd = cli.commands["next"]
            continue_cmd_obj = cli.commands.get("continue")
            assert continue_cmd_obj is not None, "If 'next' exists, 'continue' must also exist"
            # Both must point to the same underlying callback
            assert next_cmd.callback == continue_cmd_obj.callback, (
                "'next' command exists but has a different callback from 'continue' — "
                "it must be an alias, not the old next_round implementation"
            )
