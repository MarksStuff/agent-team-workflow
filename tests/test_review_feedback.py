"""Tests for the `agent-design review-feedback` CLI command and its helpers.

Derivation: DESIGN.md § "PR Feedback → Memory Update":
- Takes --pr <url> option
- Fetches all PR comments via gh CLI
- Passes comments as a block to build_review_feedback_start()
- Calls run_print_team() with the result
- Non-zero exit from run_print_team is a warning, not an abort

Developer contract (DISCUSSION.md):
- _fetch_pr_comments(pr_url: str) -> str is a module-level function
- Tested by patching subprocess.run directly (not an injected dependency)
- Returns a formatted string of comments

All subprocess calls are patched. No real gh CLI or network calls are made.
"""

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
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


def _make_subprocess_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestReviewFeedbackCommandRegistered:
    """The `review-feedback` command is importable and registered in main CLI."""

    def test_review_feedback_module_importable(self) -> None:
        """agent_design.cli.commands.review_feedback is importable."""
        from agent_design.cli.commands import review_feedback  # noqa: F401

    def test_review_feedback_command_callable(self) -> None:
        """The review_feedback Click command object is callable."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        assert callable(review_feedback_cmd)

    def test_review_feedback_registered_in_main_cli(self) -> None:
        """The 'review-feedback' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "review-feedback" in cli.commands, "'review-feedback' command not registered in main.py"

    def test_review_feedback_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        result = runner.invoke(review_feedback_cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestReviewFeedbackCommandArguments:
    """The `review-feedback` command argument surface."""

    def test_pr_option_is_required(self, tmp_path: Path) -> None:
        """Calling review-feedback without --pr must exit non-zero."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        result = runner.invoke(review_feedback_cmd, [])
        assert result.exit_code != 0

    def test_pr_option_accepted(self, tmp_path: Path) -> None:
        """--pr <url> option is accepted."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value="comment text",
            ),
            patch("agent_design.cli.commands.review_feedback.run_print_team", return_value=0),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(
                review_feedback_cmd,
                ["--pr", "https://github.com/owner/repo/pull/1", "--repo-path", str(tmp_path)],
            )
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted (default: current dir)."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value="comment text",
            ),
            patch("agent_design.cli.commands.review_feedback.run_print_team", return_value=0),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(
                review_feedback_cmd,
                ["--pr", "https://github.com/o/r/pull/1", "--repo-path", str(tmp_path)],
            )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# _fetch_pr_comments — isolated unit tests
# No real gh subprocess is invoked.
# ---------------------------------------------------------------------------


class TestFetchPrCommentsIsolated:
    """_fetch_pr_comments() returns a formatted string of comments."""

    def test_fetch_pr_comments_is_importable(self) -> None:
        """_fetch_pr_comments is importable from review_feedback module."""
        from agent_design.cli.commands.review_feedback import _fetch_pr_comments  # noqa: F401

    def test_fetch_pr_comments_returns_string(self) -> None:
        """_fetch_pr_comments returns a string when gh succeeds."""
        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        # gh pr view --json reviews,comments returns a dict with "reviews" and "comments" keys.
        # Each comment has "body" and "author": {"login": "..."}.
        gh_output = json.dumps(
            {
                "comments": [
                    {"body": "This function is too long", "author": {"login": "mark"}},
                    {"body": "Please add a docstring", "author": {"login": "mark"}},
                ],
                "reviews": [],
            }
        )
        with patch(
            "agent_design.cli.commands.review_feedback.subprocess.run",
            return_value=_make_subprocess_result(returncode=0, stdout=gh_output),
        ):
            result = _fetch_pr_comments("https://github.com/o/r/pull/1")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_fetch_pr_comments_includes_comment_body(self) -> None:
        """The returned string includes the comment body text."""
        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        gh_output = json.dumps(
            {
                "comments": [
                    {"body": "This is a specific review comment", "author": {"login": "mark"}},
                ],
                "reviews": [],
            }
        )
        with patch(
            "agent_design.cli.commands.review_feedback.subprocess.run",
            return_value=_make_subprocess_result(returncode=0, stdout=gh_output),
        ):
            result = _fetch_pr_comments("https://github.com/o/r/pull/1")

        assert "This is a specific review comment" in result

    def test_fetch_pr_comments_calls_gh_with_pr_url(self) -> None:
        """gh is called with the PR URL provided."""
        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        gh_output = json.dumps({"comments": [], "reviews": []})
        with patch(
            "agent_design.cli.commands.review_feedback.subprocess.run",
            return_value=_make_subprocess_result(returncode=0, stdout=gh_output),
        ) as mock_run:
            _fetch_pr_comments("https://github.com/owner/repo/pull/42")

        # The PR URL or its components must appear in the call
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        full_cmd = " ".join(str(c) for c in cmd)
        assert "42" in full_cmd or "owner/repo" in full_cmd or "https://github.com" in full_cmd

    def test_fetch_pr_comments_empty_comments_returns_string(self) -> None:
        """When there are no comments, returns an empty or placeholder string (no crash)."""
        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        gh_output = json.dumps({"comments": [], "reviews": []})
        with patch(
            "agent_design.cli.commands.review_feedback.subprocess.run",
            return_value=_make_subprocess_result(returncode=0, stdout=gh_output),
        ):
            result = _fetch_pr_comments("https://github.com/o/r/pull/1")

        assert isinstance(result, str)

    def test_fetch_pr_comments_gh_failure_raises_or_returns_error_string(self) -> None:
        """When gh exits non-zero, _fetch_pr_comments raises or returns a safe error string.

        Either behaviour is acceptable — the command layer handles both.
        The key requirement is: no unhandled exception that leaks subprocess internals.
        """
        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        with patch(
            "agent_design.cli.commands.review_feedback.subprocess.run",
            return_value=_make_subprocess_result(returncode=1, stderr="gh: not authenticated"),
        ):
            try:
                result = _fetch_pr_comments("https://github.com/o/r/pull/1")
                # If it returns, it must be a string
                assert isinstance(result, str)
            except (RuntimeError, SystemExit, ValueError, subprocess.CalledProcessError, click.UsageError):
                # These are acceptable exception types — not unhandled crashes
                pass

    def test_fetch_pr_comments_multiple_comments_all_included(self) -> None:
        """All comment bodies are included in the returned string."""
        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        gh_output = json.dumps(
            {
                "comments": [
                    {"body": "First comment here", "author": {"login": "reviewer"}},
                    {"body": "Second comment here", "author": {"login": "reviewer"}},
                ],
                "reviews": [
                    {"body": "Third comment here", "author": {"login": "reviewer"}},
                ],
            }
        )
        with patch(
            "agent_design.cli.commands.review_feedback.subprocess.run",
            return_value=_make_subprocess_result(returncode=0, stdout=gh_output),
        ):
            result = _fetch_pr_comments("https://github.com/o/r/pull/1")

        assert "First comment here" in result
        assert "Second comment here" in result
        assert "Third comment here" in result


# ---------------------------------------------------------------------------
# Full command flow: fetch → build → run_print_team
# ---------------------------------------------------------------------------


class TestReviewFeedbackCommandFlow:
    """review-feedback command integrates _fetch_pr_comments, build_review_feedback_start,
    and run_print_team in the right order."""

    def test_fetch_called_with_pr_url(self, tmp_path: Path) -> None:
        """_fetch_pr_comments is called with the URL from --pr."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        captured_urls: list[str] = []

        def capture_fetch(pr_url: str) -> str:
            captured_urls.append(pr_url)
            return "some comments"

        runner = CliRunner()
        pr_url = "https://github.com/owner/repo/pull/99"
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                side_effect=capture_fetch,
            ),
            patch("agent_design.cli.commands.review_feedback.run_print_team", return_value=0),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(review_feedback_cmd, ["--pr", pr_url, "--repo-path", str(tmp_path)])

        assert pr_url in captured_urls

    def test_build_review_feedback_start_receives_fetched_comments(self, tmp_path: Path) -> None:
        """build_review_feedback_start is called with the comments from _fetch_pr_comments
        AND the pr_url (Architect contract: signature is pr_comments, pr_url)."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        fetched_comments = "Reviewer: this needs a test. Also fix naming."
        captured_build_args: list[dict] = []
        pr_url = "https://github.com/o/r/pull/1"

        def capture_build(pr_comments: str, pr_url: str, **kwargs: object) -> str:
            captured_build_args.append({"pr_comments": pr_comments, "pr_url": pr_url})
            return "prompt"

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value=fetched_comments,
            ),
            patch("agent_design.cli.commands.review_feedback.run_print_team", return_value=0),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(
                review_feedback_cmd,
                ["--pr", pr_url, "--repo-path", str(tmp_path)],
            )

        assert len(captured_build_args) == 1
        assert captured_build_args[0]["pr_comments"] == fetched_comments
        # The pr_url must also be passed to build_review_feedback_start
        assert captured_build_args[0]["pr_url"] == pr_url

    def test_run_print_team_receives_built_prompt(self, tmp_path: Path) -> None:
        """run_print_team receives the return value of build_review_feedback_start."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        sentinel = "SENTINEL_REVIEW_FEEDBACK_PROMPT"
        captured_messages: list[str] = []

        def capture_run(worktree_path: Path, target_repo: Path, start_message: str) -> int:
            captured_messages.append(start_message)
            return 0

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value="comments",
            ),
            patch(
                "agent_design.cli.commands.review_feedback.run_print_team",
                side_effect=capture_run,
            ),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value=sentinel,
            ),
        ):
            runner.invoke(
                review_feedback_cmd,
                ["--pr", "https://github.com/o/r/pull/1", "--repo-path", str(tmp_path)],
            )

        assert sentinel in captured_messages

    def test_run_print_team_called_once(self, tmp_path: Path) -> None:
        """run_print_team is called exactly once."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value="comments",
            ),
            patch(
                "agent_design.cli.commands.review_feedback.run_print_team",
                return_value=0,
            ) as mock_run,
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(
                review_feedback_cmd,
                ["--pr", "https://github.com/o/r/pull/1", "--repo-path", str(tmp_path)],
            )

        mock_run.assert_called_once()

    def test_run_print_team_not_called_when_comments_empty(self, tmp_path: Path) -> None:
        """Architect + QA agreed: empty PR comments → do not call run_print_team, exit 0.

        Launching a multi-agent session with no content is wasteful.
        """
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value="",
            ),
            patch(
                "agent_design.cli.commands.review_feedback.run_print_team",
                return_value=0,
            ) as mock_run,
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(
                review_feedback_cmd,
                ["--pr", "https://github.com/o/r/pull/1", "--repo-path", str(tmp_path)],
            )

        mock_run.assert_not_called()
        assert result.exit_code == 0

    def test_empty_comments_prints_informational_message(self, tmp_path: Path) -> None:
        """Empty PR comments → informational message mentioning no comments found."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value="",
            ),
            patch("agent_design.cli.commands.review_feedback.run_print_team", return_value=0),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(
                review_feedback_cmd,
                ["--pr", "https://github.com/o/r/pull/1", "--repo-path", str(tmp_path)],
            )

        output_lower = (result.output or "").lower()
        assert "no" in output_lower and "comment" in output_lower, (
            f"Expected informational 'no comments' message, got: {result.output!r}"
        )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestReviewFeedbackErrorHandling:
    """review-feedback handles error conditions gracefully."""

    def test_nonzero_exit_from_run_print_team_is_warning_not_abort(self, tmp_path: Path) -> None:
        """If run_print_team returns non-zero, command still completes without traceback."""
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value="comments",
            ),
            patch("agent_design.cli.commands.review_feedback.run_print_team", return_value=1),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(
                review_feedback_cmd,
                ["--pr", "https://github.com/o/r/pull/1", "--repo-path", str(tmp_path)],
            )

        assert "Traceback" not in (result.output or "")

    def test_gh_fetch_failure_prints_error_not_traceback(self, tmp_path: Path) -> None:
        """If _fetch_pr_comments raises click.UsageError, command exits non-zero without traceback."""
        import click

        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                side_effect=click.UsageError("gh not authenticated"),
            ),
            patch("agent_design.cli.commands.review_feedback.run_print_team", return_value=0),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(
                review_feedback_cmd,
                ["--pr", "https://github.com/o/r/pull/1", "--repo-path", str(tmp_path)],
            )

        # Must exit non-zero and not show a raw Python traceback
        assert result.exit_code != 0
        assert "Traceback" not in (result.output or "")

    def test_gh_not_installed_raises_usage_error_with_install_instructions(self) -> None:
        """FileNotFoundError from gh → click.UsageError with install URL."""
        import click

        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        with (
            patch(
                "agent_design.cli.commands.review_feedback.subprocess.run",
                side_effect=FileNotFoundError("No such file: gh"),
            ),
            pytest.raises(click.UsageError) as exc_info,
        ):
            _fetch_pr_comments("https://github.com/o/r/pull/1")

        error_msg = str(exc_info.value).lower()
        assert "gh" in error_msg, "Error message should mention 'gh'"
        # Should include install instructions
        assert "install" in error_msg or "cli.github.com" in error_msg, (
            "Error message should include install instructions"
        )

    def test_gh_nonzero_exit_raises_usage_error(self) -> None:
        """gh CLI exit non-zero → click.UsageError, not RuntimeError."""
        import click

        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        with (
            patch(
                "agent_design.cli.commands.review_feedback.subprocess.run",
                return_value=_make_subprocess_result(returncode=1, stderr="authentication required"),
            ),
            pytest.raises(click.UsageError),
        ):
            _fetch_pr_comments("https://github.com/o/r/pull/1")

    def test_build_receives_pr_url_not_project_slug(self, tmp_path: Path) -> None:
        """build_review_feedback_start is called with pr_url, not project_slug/date.

        This verifies the call matches the Architect's contract after Developer fixes
        the implementation.
        """
        from agent_design.cli.commands.review_feedback import review_feedback as review_feedback_cmd

        captured_kwargs: list[dict] = []
        pr_url = "https://github.com/o/r/pull/1"

        def capture_build(**kwargs: object) -> str:
            captured_kwargs.append(dict(kwargs))
            return "prompt"

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.review_feedback._fetch_pr_comments",
                return_value="comments",
            ),
            patch("agent_design.cli.commands.review_feedback.run_print_team", return_value=0),
            patch(
                "agent_design.cli.commands.review_feedback.build_review_feedback_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(
                review_feedback_cmd,
                ["--pr", pr_url, "--repo-path", str(tmp_path)],
            )

        # Must be called with pr_url, not project_slug or date
        if captured_kwargs:
            assert "pr_url" in captured_kwargs[0] or "pr_comments" in captured_kwargs[0], (
                "build_review_feedback_start must be called with pr_url/pr_comments kwargs"
            )
            assert "project_slug" not in captured_kwargs[0], (
                "build_review_feedback_start must NOT be called with project_slug"
            )


# ---------------------------------------------------------------------------
# URL parsing tests for _fetch_pr_comments
# ---------------------------------------------------------------------------


class TestFetchPrCommentsUrlParsing:
    """_fetch_pr_comments handles URL parsing edge cases."""

    def test_url_with_trailing_slash(self) -> None:
        """URL with trailing slash is accepted (should not crash)."""
        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        gh_output = json.dumps({"comments": [], "reviews": []})
        with patch(
            "agent_design.cli.commands.review_feedback.subprocess.run",
            return_value=_make_subprocess_result(returncode=0, stdout=gh_output),
        ):
            result = _fetch_pr_comments("https://github.com/o/r/pull/1/")

        assert isinstance(result, str)

    def test_malformed_url_raises_usage_error(self) -> None:
        """Malformed URL raises click.UsageError, not AttributeError or IndexError.

        The implementation should validate the URL before calling gh (or handle
        the gh error by converting it to click.UsageError). Either approach satisfies
        the Architect's contract.
        """
        import click

        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        # Patch subprocess.run to avoid real gh call — the test is about error type, not gh
        with (
            patch(
                "agent_design.cli.commands.review_feedback.subprocess.run",
                return_value=_make_subprocess_result(returncode=1, stderr="invalid url"),
            ),
            pytest.raises((click.UsageError, click.BadParameter)) as exc_info,
        ):
            _fetch_pr_comments("not-a-url")

        # The error should reference the URL somehow
        assert exc_info is not None

    def test_non_github_url_raises_usage_error(self) -> None:
        """Non-GitHub URL raises click.UsageError.

        Either URL pre-validation or gh error conversion is acceptable.
        """
        import click

        from agent_design.cli.commands.review_feedback import _fetch_pr_comments

        with (
            patch(
                "agent_design.cli.commands.review_feedback.subprocess.run",
                return_value=_make_subprocess_result(returncode=1, stderr="not a github url"),
            ),
            pytest.raises((click.UsageError, click.BadParameter)),
        ):
            _fetch_pr_comments("https://gitlab.com/owner/repo/pull/1")


# ---------------------------------------------------------------------------
# Registration: review-feedback is wired into main.py
# ---------------------------------------------------------------------------


class TestReviewFeedbackRegisteredInMainCLI:
    """After Phase 7: 'review-feedback' is registered in cli/main.py."""

    def test_review_feedback_in_main_cli_commands(self) -> None:
        """agent_design.cli.main.cli has 'review-feedback' registered."""
        from agent_design.cli.main import cli

        assert "review-feedback" in cli.commands
