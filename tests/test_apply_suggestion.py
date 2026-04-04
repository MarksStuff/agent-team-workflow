"""Tests for the `agent-design apply-suggestion` CLI command.

Derivation: DESIGN.md § "The Retrospective" (apply-suggestion section) +
Architect contract (DISCUSSION.md):
- SUGGESTION_ID is a positional argument (normalised to uppercase before matching)
- Optional --repo-path (default: current dir)
- Reads <repo_path>/.agent-design/RETRO.md; click.UsageError if missing
- Parses out the suggestion text for the given ID; click.UsageError if not found
- Calls build_apply_suggestion_start(suggestion_id, suggestion_text, agents_dir)
- Calls run_solo(agent_name="architect", task_prompt, worktree_path, target_repo)
- Non-zero exit from run_solo → warning print, no exception

Parsing contract for RETRO.md (Architect DISCUSSION.md):
  - "Prompt Suggestions" section has lines like:
      - [PS-1] architect.md: add "..."
        (optional indented continuation lines)
  - Numeric suffix is matched: "ps-1", "PS-1", "1" all resolve to the same entry
  - Input is normalised to uppercase before matching

All external dependencies are patched. No real subprocess, filesystem I/O
beyond what tmp_path provides, or launcher calls are made.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRO_MD_WITH_SUGGESTIONS = """\
# Retrospective — test-feature — 2026-04-04

## What Went Well
- Handoff was clean.

## Friction Points
- EM relayed messages 3 times.

## Prompt Suggestions (pending human review)
- [PS-1] architect.md: add "check BASELINE.md before proposing infrastructure changes"
- [PS-2] eng_manager.md: add "prompt agents to post in DISCUSSION.md if idle >3 turns"
  (continuation line with more detail)
- [PS-3] developer.md: add "read TASKS.md before claiming work"
"""

_RETRO_MD_NO_SUGGESTIONS = """\
# Retrospective — test-feature — 2026-04-04

## What Went Well
- Handoff was clean.
"""

_RETRO_MD_MULTILINE_SUGGESTION = """\
# Retrospective — test-feature — 2026-04-04

## Prompt Suggestions (pending human review)
- [PS-1] architect.md: add guidance about reading BASELINE.md
  Additional detail on line two.
  And a third continuation line.
"""


def _write_retro(repo_path: Path, content: str = _RETRO_MD_WITH_SUGGESTIONS) -> None:
    """Write .agent-design/RETRO.md with given content."""
    agent_design_dir = repo_path / ".agent-design"
    agent_design_dir.mkdir(parents=True, exist_ok=True)
    (agent_design_dir / "RETRO.md").write_text(content)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestApplySuggestionCommandRegistered:
    """The `apply-suggestion` command is importable and registered in main CLI."""

    def test_apply_suggestion_module_importable(self) -> None:
        """agent_design.cli.commands.apply_suggestion is importable."""
        from agent_design.cli.commands import apply_suggestion  # noqa: F401

    def test_apply_suggestion_command_callable(self) -> None:
        """The apply_suggestion Click command object is callable."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        assert callable(apply_suggestion_cmd)

    def test_apply_suggestion_registered_in_main_cli(self) -> None:
        """The 'apply-suggestion' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "apply-suggestion" in cli.commands, "'apply-suggestion' command not registered in main.py"

    def test_apply_suggestion_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        runner = CliRunner()
        result = runner.invoke(apply_suggestion_cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestApplySuggestionArguments:
    """The `apply-suggestion` command argument surface."""

    def test_suggestion_id_is_required(self, tmp_path: Path) -> None:
        """Calling apply-suggestion with no positional arg exits non-zero."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        runner = CliRunner()
        result = runner.invoke(apply_suggestion_cmd, [])
        assert result.exit_code != 0

    def test_suggestion_id_accepted_as_positional(self, tmp_path: Path) -> None:
        """Suggestion ID accepted as a positional argument without raising."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(
                apply_suggestion_cmd,
                ["PS-1", "--repo-path", str(tmp_path)],
            )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Guard: missing RETRO.md → UsageError
# ---------------------------------------------------------------------------


class TestApplySuggestionRetroMdGuard:
    """apply-suggestion raises click.UsageError when RETRO.md is missing."""

    def test_missing_retro_md_exits_nonzero(self, tmp_path: Path) -> None:
        """When .agent-design/RETRO.md does not exist, exit code is non-zero."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        # No RETRO.md written
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_missing_retro_md_error_message_mentions_retro(self, tmp_path: Path) -> None:
        """Error message for missing RETRO.md mentions RETRO.md and retro command."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        assert "retro" in output, f"Expected error to mention 'retro', got: {result.output!r}"

    def test_missing_retro_md_run_solo_not_called(self, tmp_path: Path) -> None:
        """When RETRO.md is missing, run_solo is never called."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0) as mock_run,
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# RETRO.md parsing — _parse_retro_suggestion (isolated)
# ---------------------------------------------------------------------------


class TestParseRetroSuggestion:
    """_parse_retro_suggestion extracts suggestion text from RETRO.md content."""

    def test_parse_retro_suggestion_is_importable(self) -> None:
        """_parse_retro_suggestion is importable from apply_suggestion module."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion  # noqa: F401

    def test_parse_finds_ps1_by_uppercase_id(self) -> None:
        """PS-1 is found by exact uppercase ID."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "PS-1")
        assert result is not None
        assert "architect.md" in result
        assert "BASELINE.md" in result

    def test_parse_finds_ps2(self) -> None:
        """PS-2 is found and its text extracted."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "PS-2")
        assert result is not None
        assert "eng_manager.md" in result

    def test_parse_is_case_insensitive_lowercase_input(self) -> None:
        """Input ID is normalised to uppercase: ps-1 finds PS-1."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "ps-1")
        assert result is not None
        assert "architect.md" in result

    def test_parse_is_case_insensitive_mixed_input(self) -> None:
        """Mixed case input Ps-1 finds PS-1."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "Ps-1")
        assert result is not None

    def test_parse_returns_none_for_missing_id(self) -> None:
        """Returns None when the suggestion ID is not in the content."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "PS-99")
        assert result is None

    def test_parse_returns_none_for_no_suggestions_section(self) -> None:
        """Returns None when RETRO.md has no Prompt Suggestions section."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_NO_SUGGESTIONS, "PS-1")
        assert result is None

    def test_parse_includes_continuation_lines(self) -> None:
        """Indented continuation lines are included in the extracted text."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_MULTILINE_SUGGESTION, "PS-1")
        assert result is not None
        # The continuation text must appear in the result (stripped of leading whitespace)
        assert "Additional detail" in result

    def test_parse_all_continuation_lines_included(self) -> None:
        """All continuation lines are included, not just the first."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_MULTILINE_SUGGESTION, "PS-1")
        assert result is not None
        assert "third continuation line" in result

    def test_parse_strips_leading_whitespace_from_continuation(self) -> None:
        """Leading whitespace is stripped from continuation lines."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_MULTILINE_SUGGESTION, "PS-1")
        assert result is not None
        # Should not start with whitespace
        assert not result.startswith(" ")
        assert not result.startswith("\t")

    def test_parse_ps2_continuation_line_included(self) -> None:
        """PS-2 continuation line is included."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "PS-2")
        assert result is not None
        assert "continuation line" in result

    def test_parse_returns_string_not_none_for_valid_id(self) -> None:
        """Returns a non-empty string for a valid ID."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "PS-1")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Guard: suggestion ID not found in RETRO.md
# ---------------------------------------------------------------------------


class TestApplySuggestionIdNotFound:
    """apply-suggestion raises click.UsageError when suggestion ID not in RETRO.md."""

    def test_unknown_id_exits_nonzero(self, tmp_path: Path) -> None:
        """Unknown suggestion ID exits non-zero."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["PS-99", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_unknown_id_error_message_contains_id(self, tmp_path: Path) -> None:
        """Error message for unknown ID mentions the ID."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["PS-99", "--repo-path", str(tmp_path)])
        assert "PS-99" in (result.output or "") or "ps-99" in (result.output or "").lower(), (
            f"Expected error to mention the suggestion ID, got: {result.output!r}"
        )

    def test_unknown_id_run_solo_not_called(self, tmp_path: Path) -> None:
        """When suggestion ID not found, run_solo is never called."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0) as mock_run,
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-99", "--repo-path", str(tmp_path)])
        mock_run.assert_not_called()

    def test_lowercase_id_matched_against_uppercase_content(self, tmp_path: Path) -> None:
        """Lowercase input 'ps-1' successfully finds '[PS-1]' in RETRO.md."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["ps-1", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# build_apply_suggestion_start is called with correct arguments
# ---------------------------------------------------------------------------


class TestApplySuggestionCallsBuildStart:
    """apply-suggestion calls build_apply_suggestion_start with the right arguments."""

    def test_build_called_once(self, tmp_path: Path) -> None:
        """build_apply_suggestion_start is called exactly once."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ) as mock_build,
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])
        mock_build.assert_called_once()

    def test_build_receives_normalised_suggestion_id(self, tmp_path: Path) -> None:
        """build_apply_suggestion_start receives the normalised (uppercase) suggestion_id."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        captured: list[dict] = []

        def capture_build(suggestion_id: str, suggestion_text: str, agents_dir: str) -> str:
            captured.append({"suggestion_id": suggestion_id, "suggestion_text": suggestion_text})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["ps-1", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0]["suggestion_id"] == "PS-1"

    def test_build_receives_extracted_suggestion_text(self, tmp_path: Path) -> None:
        """build_apply_suggestion_start receives the text extracted from RETRO.md."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        captured: list[dict] = []

        def capture_build(suggestion_id: str, suggestion_text: str, agents_dir: str) -> str:
            captured.append({"suggestion_text": suggestion_text})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        # The extracted text must contain the content from _RETRO_MD_WITH_SUGGESTIONS for PS-1
        assert "architect.md" in captured[0]["suggestion_text"]

    def test_build_receives_agents_dir(self, tmp_path: Path) -> None:
        """build_apply_suggestion_start receives a non-empty agents_dir path."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        captured: list[dict] = []

        def capture_build(suggestion_id: str, suggestion_text: str, agents_dir: str) -> str:
            captured.append({"agents_dir": agents_dir})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert len(captured[0]["agents_dir"]) > 0
        assert "agents" in captured[0]["agents_dir"]


# ---------------------------------------------------------------------------
# run_solo is called correctly
# ---------------------------------------------------------------------------


class TestApplySuggestionCallsRunSolo:
    """apply-suggestion calls run_solo with the architect agent and the built prompt."""

    def test_run_solo_called_once(self, tmp_path: Path) -> None:
        """run_solo is called exactly once."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0) as mock_run,
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])
        mock_run.assert_called_once()

    def test_run_solo_uses_architect_agent(self, tmp_path: Path) -> None:
        """run_solo is called with agent_name='architect'."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        captured_agent_names: list[str] = []

        def capture_run(agent_name: str, task_prompt: str, worktree_path: Path, target_repo: Path) -> int:
            captured_agent_names.append(agent_name)
            return 0

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.apply_suggestion.run_solo",
                side_effect=capture_run,
            ),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert "architect" in captured_agent_names

    def test_run_solo_receives_built_prompt(self, tmp_path: Path) -> None:
        """run_solo receives the return value of build_apply_suggestion_start as task_prompt."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        sentinel = "SENTINEL_APPLY_SUGGESTION_PROMPT"
        captured_prompts: list[str] = []

        def capture_run(agent_name: str, task_prompt: str, worktree_path: Path, target_repo: Path) -> int:
            captured_prompts.append(task_prompt)
            return 0

        runner = CliRunner()
        with (
            patch(
                "agent_design.cli.commands.apply_suggestion.run_solo",
                side_effect=capture_run,
            ),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value=sentinel,
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert sentinel in captured_prompts


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestApplySuggestionErrorHandling:
    """apply-suggestion handles error conditions gracefully."""

    def test_nonzero_exit_from_run_solo_is_warning_not_abort(self, tmp_path: Path) -> None:
        """If run_solo returns non-zero, command still completes without traceback."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=1),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert "Traceback" not in (result.output or "")

    def test_nonzero_exit_from_run_solo_prints_warning(self, tmp_path: Path) -> None:
        """If run_solo returns non-zero, a warning is printed."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=1),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])

        output_lower = (result.output or "").lower()
        assert "warn" in output_lower or "error" in output_lower or "fail" in output_lower or "exit" in output_lower, (
            f"Expected warning for non-zero run_solo exit, got: {result.output!r}"
        )

    def test_no_traceback_for_unknown_suggestion_id(self, tmp_path: Path) -> None:
        """Unknown suggestion ID produces a clean error message, not a Python traceback."""
        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                return_value="prompt",
            ),
        ):
            result = runner.invoke(apply_suggestion_cmd, ["PS-99", "--repo-path", str(tmp_path)])

        assert "Traceback" not in (result.output or "")


# ---------------------------------------------------------------------------
# Registration: apply-suggestion is wired into main.py
# ---------------------------------------------------------------------------


class TestApplySuggestionRegisteredInMainCLI:
    """After Phase 8: 'apply-suggestion' is registered in cli/main.py."""

    def test_apply_suggestion_in_main_cli_commands(self) -> None:
        """agent_design.cli.main.cli has 'apply-suggestion' registered."""
        from agent_design.cli.main import cli

        assert "apply-suggestion" in cli.commands


# ---------------------------------------------------------------------------
# AC-AS4: agents_dir is specifically str(Path.home() / ".claude" / "agents")
# ---------------------------------------------------------------------------


class TestApplySuggestionAgentsDirValue:
    """AC-AS4: build_apply_suggestion_start receives agents_dir = ~/.claude/agents."""

    def test_agents_dir_is_home_dot_claude_agents(self, tmp_path: Path) -> None:
        """build_apply_suggestion_start receives str(Path.home() / '.claude' / 'agents')."""
        from pathlib import Path as _Path

        from agent_design.cli.commands.apply_suggestion import apply_suggestion as apply_suggestion_cmd

        _write_retro(tmp_path)
        expected_agents_dir = str(_Path.home() / ".claude" / "agents")
        captured: list[dict] = []

        def capture_build(suggestion_id: str, suggestion_text: str, agents_dir: str) -> str:
            captured.append({"agents_dir": agents_dir})
            return "prompt"

        runner = CliRunner()
        with (
            patch("agent_design.cli.commands.apply_suggestion.run_solo", return_value=0),
            patch(
                "agent_design.cli.commands.apply_suggestion.build_apply_suggestion_start",
                side_effect=capture_build,
            ),
        ):
            runner.invoke(apply_suggestion_cmd, ["PS-1", "--repo-path", str(tmp_path)])

        assert len(captured) == 1
        assert captured[0]["agents_dir"] == expected_agents_dir


# ---------------------------------------------------------------------------
# AC-AS5: continuation-line boundary — exactly 2+ spaces = continuation
# ---------------------------------------------------------------------------


_RETRO_MD_BOUNDARY_TEST = """\
# Retrospective

## Prompt Suggestions (pending human review)
- [PS-1] architect.md: first line text
  two-space continuation
   three-space continuation

- [PS-2] developer.md: second suggestion standalone
"""

_RETRO_MD_ONE_SPACE_NOT_CONTINUATION = """\
# Retrospective

## Prompt Suggestions (pending human review)
- [PS-1] architect.md: first line text
 one-space line (NOT a continuation — ends the entry)
- [PS-2] developer.md: second suggestion
"""


class TestParseRetroSuggestionContinuationBoundary:
    """AC-AS5: continuation boundary: 2+ spaces = continuation; 0-1 spaces = end of entry."""

    def test_two_space_indent_is_continuation(self) -> None:
        """A line with exactly 2 leading spaces is a continuation of the previous entry."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_BOUNDARY_TEST, "PS-1")
        assert result is not None
        assert "two-space continuation" in result

    def test_three_space_indent_is_continuation(self) -> None:
        """A line with 3+ leading spaces is also a continuation."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_BOUNDARY_TEST, "PS-1")
        assert result is not None
        assert "three-space continuation" in result

    def test_blank_line_ends_entry(self) -> None:
        """A blank line ends the current entry; PS-1 does not include PS-2 content."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_BOUNDARY_TEST, "PS-1")
        assert result is not None
        assert "second suggestion standalone" not in result

    def test_continuation_whitespace_stripped(self) -> None:
        """Continuation lines have their leading whitespace stripped in the output."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_BOUNDARY_TEST, "PS-1")
        assert result is not None
        # Result must not start with leading spaces
        assert not result.startswith(" ")


# ---------------------------------------------------------------------------
# Edge cases for _parse_retro_suggestion
# ---------------------------------------------------------------------------


class TestParseRetroSuggestionEdgeCases:
    """Edge cases: duplicate IDs, malformed IDs, empty content."""

    def test_first_match_used_when_duplicate_id(self) -> None:
        """If PS-1 appears twice, the first match is used."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        content = """\
## Prompt Suggestions (pending human review)
- [PS-1] architect.md: first occurrence text
- [PS-1] eng_manager.md: duplicate should be ignored
"""
        result = _parse_retro_suggestion(content, "PS-1")
        assert result is not None
        assert "first occurrence text" in result
        # Second occurrence must not be included
        assert "duplicate should be ignored" not in result

    def test_malformed_id_no_numeric_suffix_returns_none(self) -> None:
        """ID 'PS-' with no numeric suffix returns None (not found), no crash."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "PS-")
        assert result is None

    def test_empty_retro_md_returns_none(self) -> None:
        """Empty RETRO.md content returns None for any ID."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        result = _parse_retro_suggestion("", "PS-1")
        assert result is None

    def test_numeric_only_id_not_supported(self) -> None:
        """Input '1' (without PS- prefix) returns None or raises — not silently matched."""
        from agent_design.cli.commands.apply_suggestion import _parse_retro_suggestion

        # The Architect contract says input is normalised to uppercase before matching.
        # Numeric-only input "1" does not match "[PS-1]" — either None or ValueError is
        # acceptable; an accidental match is not.
        result = _parse_retro_suggestion(_RETRO_MD_WITH_SUGGESTIONS, "1")
        # Must be None (not found) — numeric-only IDs do not match [PS-N] format
        assert result is None
