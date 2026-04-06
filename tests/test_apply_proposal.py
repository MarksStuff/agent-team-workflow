"""Tests for the `agent-design apply-proposal` CLI command.

Derivation (DESIGN.md § "Escalation: proposing a new agent"):
- Takes a positional argument `name` (proposal name, e.g. "cryptography_expert")
- Optional --repo-path (default: current dir)
- Reads .agent-design/proposals/<name>.md (appends .md if not already present)
- Parses the "## Agent Definition (written verbatim if approved)" section:
  the agent file content is the fenced block (triple backticks omitted) that
  starts with YAML frontmatter (---) after that heading
- Reads the "Proposed location:" line from the proposal to determine where
  to write the agent file
- Writes the agent definition to the declared location
- Shows a success message
- Missing proposal file → error, non-zero exit
- Malformed proposal (no "## Agent Definition" section) → error
- No "Proposed location:" line → error
- If proposed location already exists → does NOT overwrite; exits non-zero (QA AC-AP-9)
- If proposed location parent dir does not exist → exits non-zero (QA AC-AP-10)

Helpers tested in isolation:
- _parse_proposed_location(content): extracts path from '**Proposed location:**' line
- _parse_agent_definition(content): extracts content of the fenced block under
  '## Agent Definition (written verbatim if approved)'

All external dependencies that touch the filesystem use tmp_path.
No subprocess calls are made by this command.
"""

from pathlib import Path

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Proposal file fixtures
# ---------------------------------------------------------------------------

# Minimal valid proposal with a clear proposed location and agent definition
VALID_PROPOSAL_TEMPLATE = """\
# Agent Proposal: {agent_name}

**Proposed by:** Eng Manager
**Session:** feat/add-user-auth — 2026-04-03
**Gap identified:** Test gap description.

**Proposed location:** `{proposed_location}`
**Rationale:** Test rationale.

**Agent type:** Domain expert

---

## Agent Definition (written verbatim if approved)

---
name: {agent_name}
description: >
  Test domain expert.
model: claude-sonnet-4-6
tools: WebSearch, WebFetch, Read
---

You are a test domain expert.
"""

NO_AGENT_DEFINITION_PROPOSAL = """\
# Agent Proposal: incomplete_expert

**Proposed by:** Eng Manager
**Proposed location:** `~/.claude/agents/incomplete_expert.md`

(No Agent Definition section here)
"""

NO_PROPOSED_LOCATION_PROPOSAL = """\
# Agent Proposal: no_location_expert

**Proposed by:** Eng Manager

## Agent Definition (written verbatim if approved)

---
name: no_location_expert
description: Test agent.
model: claude-sonnet-4-6
tools: Read
---

You are a test agent.
"""


def _write_proposal(tmp_path: Path, name: str, content: str) -> Path:
    """Write a proposal file under <tmp_path>/.agent-design/proposals/ and return its path."""
    proposals_dir = tmp_path / ".agent-design" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    proposal_file = proposals_dir / f"{name}.md"
    proposal_file.write_text(content)
    return proposal_file


def _make_valid_proposal(tmp_path: Path, agent_name: str, proposed_location: Path) -> Path:
    """Write a valid proposal and return its path.

    Creates the proposed_location parent directory so that happy path tests
    have a writable target. Tests that intentionally pass a non-existent parent
    (e.g. test_proposed_location_parent_must_exist) must NOT use this helper —
    they call _write_proposal directly with a deep path whose parent is absent.
    """
    proposed_location.parent.mkdir(parents=True, exist_ok=True)
    content = VALID_PROPOSAL_TEMPLATE.format(
        agent_name=agent_name,
        proposed_location=str(proposed_location),
    )
    return _write_proposal(tmp_path, agent_name, content)


# ---------------------------------------------------------------------------
# Parser helper: _parse_proposed_location
# (Architect spec: private helper, testable in isolation)
# ---------------------------------------------------------------------------

# Use the DESIGN.md cryptography_expert example as canonical fixture
DESIGN_MD_EXAMPLE_PROPOSAL = """\
# Agent Proposal: cryptography_expert

**Proposed by:** Eng Manager
**Session:** feat/add-user-auth — 2026-04-03
**Gap identified:** AES-256 key derivation and PBKDF2 iteration counts in §3.4
of DESIGN.md. The team has no one who can evaluate whether the proposed
parameters are secure for the threat model described.

**Proposed location:** `~/.claude/agents/cryptography_expert.md`
**Rationale:** Cryptography concerns appear across projects.

**Agent type:** Domain expert (advises; does not write implementation code)

---

## Agent Definition (written verbatim if approved)

---
name: cryptography_expert
description: >
  Cryptography domain expert. Evaluates symmetric and asymmetric encryption
  schemes, key derivation functions, hashing algorithms, and protocol security.
  Spawn when the task involves encryption, key management, secrets handling,
  or authentication primitives.
model: claude-sonnet-4-6
tools: WebSearch, WebFetch, Read
---

You are a cryptography domain expert on a collaborative engineering team.
You do not write implementation code. You evaluate cryptographic decisions,
flag weaknesses, and recommend well-vetted approaches.
"""


class TestParseProposedLocation:
    """Unit tests for _parse_proposed_location(content: str) -> str | None."""

    def test_importable(self) -> None:
        """_parse_proposed_location is importable from apply_proposal module."""
        from agent_design.cli.commands.apply_proposal import _parse_proposed_location  # noqa: F401

    def test_extracts_path_from_design_md_example(self) -> None:
        """Extracts the path from the DESIGN.md cryptography_expert example."""
        from agent_design.cli.commands.apply_proposal import _parse_proposed_location

        result = _parse_proposed_location(DESIGN_MD_EXAMPLE_PROPOSAL)
        assert result == "~/.claude/agents/cryptography_expert.md"

    def test_extracts_backtick_wrapped_path(self) -> None:
        """Handles path wrapped in backticks (the canonical proposal format)."""
        from agent_design.cli.commands.apply_proposal import _parse_proposed_location

        content = "**Proposed location:** `~/.claude/agents/foo.md`"
        result = _parse_proposed_location(content)
        assert result is not None
        assert "foo.md" in result
        # Backticks should be stripped from the returned value
        assert "`" not in result

    def test_returns_none_when_missing(self) -> None:
        """Returns None when no 'Proposed location:' line is present."""
        from agent_design.cli.commands.apply_proposal import _parse_proposed_location

        result = _parse_proposed_location("No location here.\n\nJust text.")
        assert result is None

    def test_extracts_absolute_path(self) -> None:
        """Handles an absolute path without tilde."""
        from agent_design.cli.commands.apply_proposal import _parse_proposed_location

        content = "**Proposed location:** `/home/user/.claude/agents/my_expert.md`"
        result = _parse_proposed_location(content)
        assert result is not None
        assert "my_expert.md" in result


# ---------------------------------------------------------------------------
# Parser helper: _parse_agent_definition
# (Architect spec: private helper, testable in isolation)
# ---------------------------------------------------------------------------


class TestParseAgentDefinition:
    """Unit tests for _parse_agent_definition(content: str) -> str | None."""

    def test_importable(self) -> None:
        """_parse_agent_definition is importable from apply_proposal module."""
        from agent_design.cli.commands.apply_proposal import _parse_agent_definition  # noqa: F401

    def test_extracts_definition_from_design_md_example(self) -> None:
        """Extracts agent definition from the DESIGN.md cryptography_expert example."""
        from agent_design.cli.commands.apply_proposal import _parse_agent_definition

        result = _parse_agent_definition(DESIGN_MD_EXAMPLE_PROPOSAL)
        assert result is not None
        assert "name: cryptography_expert" in result

    def test_extracted_definition_contains_yaml_frontmatter(self) -> None:
        """The extracted block contains YAML frontmatter (--- delimiters are inside the block)."""
        from agent_design.cli.commands.apply_proposal import _parse_agent_definition

        result = _parse_agent_definition(DESIGN_MD_EXAMPLE_PROPOSAL)
        assert result is not None
        assert "---" in result

    def test_extracted_definition_contains_body_text(self) -> None:
        """The extracted block contains the prompt body text after the YAML frontmatter."""
        from agent_design.cli.commands.apply_proposal import _parse_agent_definition

        result = _parse_agent_definition(DESIGN_MD_EXAMPLE_PROPOSAL)
        assert result is not None
        assert "cryptography domain expert" in result

    def test_returns_none_when_no_agent_definition_section(self) -> None:
        """Returns None when the '## Agent Definition' heading is absent."""
        from agent_design.cli.commands.apply_proposal import _parse_agent_definition

        result = _parse_agent_definition("# Just a proposal\n\nNo definition here.")
        assert result is None

    def test_definition_content_does_not_include_heading_line(self) -> None:
        """The returned content does not include the '## Agent Definition' heading itself."""
        from agent_design.cli.commands.apply_proposal import _parse_agent_definition

        result = _parse_agent_definition(DESIGN_MD_EXAMPLE_PROPOSAL)
        assert result is not None
        assert "## Agent Definition" not in result

    def test_definition_does_not_include_backtick_fence_markers(self) -> None:
        """The returned content does not include backtick fence (```) markers.

        The DESIGN.md format wraps the agent definition in triple-backtick fences.
        The command writes the inner content verbatim — fence markers are stripped.
        """
        from agent_design.cli.commands.apply_proposal import _parse_agent_definition

        # Build a proposal with backtick-fenced definition block
        proposal_with_backtick_fence = """\
# Agent Proposal: test_agent

**Proposed location:** `~/.claude/agents/test_agent.md`

## Agent Definition (written verbatim if approved)

```
---
name: test_agent
description: Test agent.
model: claude-sonnet-4-6
tools: Read
---

You are a test agent.
```
"""
        result = _parse_agent_definition(proposal_with_backtick_fence)
        assert result is not None
        assert "```" not in result
        assert "name: test_agent" in result


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestApplyProposalCommandRegistered:
    """The `apply-proposal` command is importable and registered in main CLI."""

    def test_apply_proposal_module_importable(self) -> None:
        """agent_design.cli.commands.apply_proposal is importable."""
        from agent_design.cli.commands import apply_proposal  # noqa: F401

    def test_apply_proposal_command_callable(self) -> None:
        """The apply_proposal Click command object is callable."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        assert callable(cmd)

    def test_apply_proposal_registered_in_main_cli(self) -> None:
        """The 'apply-proposal' command is registered in agent_design.cli.main.cli."""
        from agent_design.cli.main import cli

        assert "apply-proposal" in cli.commands, "'apply-proposal' not registered in main.py"

    def test_apply_proposal_help_runs(self) -> None:
        """--help does not raise and exits 0."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Argument contract
# ---------------------------------------------------------------------------


class TestApplyProposalCommandArguments:
    """The `apply-proposal` command argument surface."""

    def test_name_is_required(self) -> None:
        """Calling apply-proposal with no name argument must exit non-zero."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code != 0

    def test_repo_path_option_accepted(self, tmp_path: Path) -> None:
        """--repo-path option is accepted."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        proposed_location = tmp_path / "agents" / "test_expert.md"
        _make_valid_proposal(tmp_path, "test_expert", proposed_location)
        runner = CliRunner()
        result = runner.invoke(cmd, ["test_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Happy path: proposal file with valid content → agent file written
# ---------------------------------------------------------------------------


class TestApplyProposalHappyPath:
    """apply-proposal writes the agent file when proposal is valid."""

    def test_agent_file_is_written_to_proposed_location(self, tmp_path: Path) -> None:
        """The agent definition is written to the path declared in 'Proposed location:'."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        proposed_location = tmp_path / "agents" / "crypto_expert.md"
        _make_valid_proposal(tmp_path, "crypto_expert", proposed_location)

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        assert proposed_location.exists(), (
            f"Agent file was not written to {proposed_location}"
        )

    def test_agent_file_contains_frontmatter(self, tmp_path: Path) -> None:
        """The written agent file contains the YAML frontmatter from the definition block."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        proposed_location = tmp_path / "agents" / "crypto_expert.md"
        _make_valid_proposal(tmp_path, "crypto_expert", proposed_location)

        runner = CliRunner()
        runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert proposed_location.exists()
        content = proposed_location.read_text()
        assert "name: crypto_expert" in content

    def test_agent_file_contains_definition_body(self, tmp_path: Path) -> None:
        """The written agent file contains the body text from the definition block."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        proposed_location = tmp_path / "agents" / "crypto_expert.md"
        _make_valid_proposal(tmp_path, "crypto_expert", proposed_location)

        runner = CliRunner()
        runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert proposed_location.exists()
        content = proposed_location.read_text()
        assert "You are a test domain expert" in content

    def test_success_message_shown(self, tmp_path: Path) -> None:
        """A success message is shown after writing the agent file."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        proposed_location = tmp_path / "agents" / "crypto_expert.md"
        _make_valid_proposal(tmp_path, "crypto_expert", proposed_location)

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        output = result.output.lower()
        has_success = any(word in output for word in ("written", "created", "applied", "success", "done"))
        assert has_success, f"No success message shown. Output: {result.output!r}"

    def test_name_without_md_extension_works(self, tmp_path: Path) -> None:
        """Passing name without .md extension still resolves the proposal correctly."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        proposed_location = tmp_path / "agents" / "my_expert.md"
        _make_valid_proposal(tmp_path, "my_expert", proposed_location)

        runner = CliRunner()
        result = runner.invoke(cmd, ["my_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        assert proposed_location.exists()

    def test_proposed_location_parent_must_exist(self, tmp_path: Path) -> None:
        """If the parent directory of proposed_location does not exist, command exits non-zero.

        Per QA AC-AP-10 and Architect spec: command does not silently create
        parent directories. Missing parent → error.
        """
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        # Propose a location whose parent does NOT exist.
        # Use _write_proposal directly (not _make_valid_proposal) to avoid
        # the helper creating the parent directory.
        proposed_location = tmp_path / "deep" / "nested" / "dir" / "expert.md"
        content = VALID_PROPOSAL_TEMPLATE.format(
            agent_name="expert",
            proposed_location=str(proposed_location),
        )
        _write_proposal(tmp_path, "expert", content)

        runner = CliRunner()
        result = runner.invoke(cmd, ["expert", "--repo-path", str(tmp_path)])

        assert result.exit_code != 0

    def test_proposed_location_parent_missing_shows_error(self, tmp_path: Path) -> None:
        """Missing parent directory → informative error message."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        # Use _write_proposal directly so the parent is not created.
        proposed_location = tmp_path / "nonexistent_dir" / "expert.md"
        content = VALID_PROPOSAL_TEMPLATE.format(
            agent_name="expert",
            proposed_location=str(proposed_location),
        )
        _write_proposal(tmp_path, "expert", content)

        runner = CliRunner()
        result = runner.invoke(cmd, ["expert", "--repo-path", str(tmp_path)])

        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("director", "parent", "exist", "error", "missing", "not found")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_existing_location_is_not_overwritten(self, tmp_path: Path) -> None:
        """If the proposed location already exists, command exits non-zero (does NOT overwrite).

        Per QA AC-AP-9: agent files are curated — silent overwrite is dangerous.
        The operator must remove the existing file manually.
        """
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        proposed_location = tmp_path / "agents" / "crypto_expert.md"
        proposed_location.parent.mkdir(parents=True, exist_ok=True)
        proposed_location.write_text("old content")

        _make_valid_proposal(tmp_path, "crypto_expert", proposed_location)

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        assert result.exit_code != 0
        # Original content must be preserved
        assert proposed_location.read_text() == "old content"

    def test_existing_location_shows_conflict_message(self, tmp_path: Path) -> None:
        """If proposed location already exists, output states the file already exists."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        proposed_location = tmp_path / "agents" / "crypto_expert.md"
        proposed_location.parent.mkdir(parents=True, exist_ok=True)
        proposed_location.write_text("old content")

        _make_valid_proposal(tmp_path, "crypto_expert", proposed_location)

        runner = CliRunner()
        result = runner.invoke(cmd, ["crypto_expert", "--repo-path", str(tmp_path)])

        output = result.output.lower()
        has_message = any(
            word in output
            for word in ("already exist", "exist", "conflict", "overwr", "error")
        )
        assert has_message, f"No conflict message shown. Output: {result.output!r}"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestApplyProposalErrorHandling:
    """apply-proposal handles error conditions gracefully."""

    def test_missing_proposal_file_exits_nonzero(self, tmp_path: Path) -> None:
        """If proposal file does not exist, command exits non-zero."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_missing_proposal_file_shows_error_message(self, tmp_path: Path) -> None:
        """If proposal file does not exist, command shows an informative error."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        runner = CliRunner()
        result = runner.invoke(cmd, ["nonexistent_expert", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("not found", "missing", "error", "no such", "proposal", "nonexistent")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_malformed_proposal_no_agent_definition_section_exits_nonzero(self, tmp_path: Path) -> None:
        """Proposal with no '## Agent Definition' section → non-zero exit."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "incomplete_expert", NO_AGENT_DEFINITION_PROPOSAL)
        runner = CliRunner()
        result = runner.invoke(cmd, ["incomplete_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_malformed_proposal_no_agent_definition_shows_error(self, tmp_path: Path) -> None:
        """Proposal with no '## Agent Definition' section → informative error message."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "incomplete_expert", NO_AGENT_DEFINITION_PROPOSAL)
        runner = CliRunner()
        result = runner.invoke(cmd, ["incomplete_expert", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("agent definition", "definition", "missing", "error", "malformed", "not found")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"

    def test_no_proposed_location_exits_nonzero(self, tmp_path: Path) -> None:
        """Proposal with no 'Proposed location:' line → non-zero exit."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "no_location_expert", NO_PROPOSED_LOCATION_PROPOSAL)
        runner = CliRunner()
        result = runner.invoke(cmd, ["no_location_expert", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_no_proposed_location_shows_error(self, tmp_path: Path) -> None:
        """Proposal with no 'Proposed location:' line → informative error message."""
        from agent_design.cli.commands.apply_proposal import apply_proposal as cmd

        _write_proposal(tmp_path, "no_location_expert", NO_PROPOSED_LOCATION_PROPOSAL)
        runner = CliRunner()
        result = runner.invoke(cmd, ["no_location_expert", "--repo-path", str(tmp_path)])
        output = (result.output or "").lower()
        has_message = any(
            word in output
            for word in ("location", "proposed location", "missing", "error", "malformed")
        )
        assert has_message, f"No helpful error message shown. Output: {result.output!r}"
