"""
Tests verifying structural contracts for the 6 Phase-6 specialist agent files.

Covers AC1–AC6 from DESIGN.md "Acceptance Criteria — Phase 6":
  AC1  — File exists and is non-empty
  AC2  — Required YAML frontmatter: name, description (>=50 chars),
          model: claude-sonnet-4-6, memory: project;
          name matches filename stem
  AC3  — description contains "spawn" (case-insensitive) — EM trigger language
  AC4  — Body contains "Spawned when:" section
  AC5  — Body contains "Does not" section (all 6 files, not just PM)
  AC6  — Body contains "## Your memory file" section, correct path pattern
          (~/.claude/agent-memory/<name>.md), and no-permission statement

AC7 (symlinks) is a manual QA verification task — not tested here.
AC8 (no regressions) is covered by running the full test suite.

Structural contract source:
  DISCUSSION.md — [Architect] and [QA Engineer] posts in Phase-6 thread.

All tests are expected to be RED until Developer writes the 6 agent files.
"""

from pathlib import Path

import yaml

AGENT_DEFS = Path(__file__).parent.parent / "agent-definitions"

# ---------------------------------------------------------------------------
# File paths — one constant per specialist agent
# ---------------------------------------------------------------------------

SRE = AGENT_DEFS / "sre.md"
PM = AGENT_DEFS / "pm.md"
SECURITY_ENGINEER = AGENT_DEFS / "security_engineer.md"
DATABASE_ARCHITECT = AGENT_DEFS / "database_architect.md"
TECHNICAL_WRITER = AGENT_DEFS / "technical_writer.md"
PERFORMANCE_ENGINEER = AGENT_DEFS / "performance_engineer.md"

ALL_SPECIALIST_FILES = [
    SRE,
    PM,
    SECURITY_ENGINEER,
    DATABASE_ARCHITECT,
    TECHNICAL_WRITER,
    PERFORMANCE_ENGINEER,
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIN_DESCRIPTION_LEN = 50


def _content(path: Path) -> str:
    """Read the full file content."""
    return path.read_text()


def _frontmatter(path: Path) -> dict:
    """
    Parse and return the YAML frontmatter of a Markdown agent file.

    Agent files use triple-dash fences:
        ---
        name: foo
        ...
        ---
    We extract the text between the first pair of --- markers and parse it
    with yaml.safe_load.  The call must not raise.
    """
    content = _content(path)
    assert content.startswith("---"), f"{path.name}: file must start with '---' YAML frontmatter fence"
    end_fence = content.index("---", 3)  # find the closing fence
    yaml_text = content[3:end_fence].strip()
    return yaml.safe_load(yaml_text)


def _body(path: Path) -> str:
    """
    Return the prose body of the file — everything after the closing frontmatter fence.
    """
    content = _content(path)
    assert content.startswith("---"), f"{path.name}: file must start with '---' YAML frontmatter fence"
    end_fence = content.index("---", 3)
    return content[end_fence + 3 :]  # everything after the closing ---


# ---------------------------------------------------------------------------
# AC1 — File existence
# ---------------------------------------------------------------------------


class TestSpecialistFilesExist:
    """AC1: All 6 specialist files must exist at agent-definitions/<slug>.md."""

    def test_sre_file_exists(self):
        assert SRE.exists(), "agent-definitions/sre.md does not exist"

    def test_sre_file_is_nonempty(self):
        assert SRE.stat().st_size > 0, "agent-definitions/sre.md is empty"

    def test_pm_file_exists(self):
        assert PM.exists(), "agent-definitions/pm.md does not exist"

    def test_pm_file_is_nonempty(self):
        assert PM.stat().st_size > 0, "agent-definitions/pm.md is empty"

    def test_security_engineer_file_exists(self):
        assert SECURITY_ENGINEER.exists(), "agent-definitions/security_engineer.md does not exist"

    def test_security_engineer_file_is_nonempty(self):
        assert SECURITY_ENGINEER.stat().st_size > 0, "agent-definitions/security_engineer.md is empty"

    def test_database_architect_file_exists(self):
        assert DATABASE_ARCHITECT.exists(), "agent-definitions/database_architect.md does not exist"

    def test_database_architect_file_is_nonempty(self):
        assert DATABASE_ARCHITECT.stat().st_size > 0, "agent-definitions/database_architect.md is empty"

    def test_technical_writer_file_exists(self):
        assert TECHNICAL_WRITER.exists(), "agent-definitions/technical_writer.md does not exist"

    def test_technical_writer_file_is_nonempty(self):
        assert TECHNICAL_WRITER.stat().st_size > 0, "agent-definitions/technical_writer.md is empty"

    def test_performance_engineer_file_exists(self):
        assert PERFORMANCE_ENGINEER.exists(), "agent-definitions/performance_engineer.md does not exist"

    def test_performance_engineer_file_is_nonempty(self):
        assert PERFORMANCE_ENGINEER.stat().st_size > 0, "agent-definitions/performance_engineer.md is empty"


# ---------------------------------------------------------------------------
# AC2 — Required YAML frontmatter
# ---------------------------------------------------------------------------


class TestFrontmatterRequiredFields:
    """
    AC2: Every specialist file must have valid YAML frontmatter containing
    name (non-empty, matches filename stem), description (>=50 chars),
    model: claude-sonnet-4-6, and memory: project.
    """

    # --- helpers shared across all per-file test methods ---

    def _assert_parseable(self, path: Path) -> dict:
        fm = _frontmatter(path)
        assert isinstance(fm, dict), f"{path.name}: frontmatter did not parse to a dict"
        return fm

    def _assert_name_present_and_nonempty(self, path: Path) -> None:
        fm = self._assert_parseable(path)
        assert "name" in fm, f"{path.name}: frontmatter missing 'name' field"
        assert fm["name"], f"{path.name}: frontmatter 'name' field is empty"

    def _assert_name_matches_filename_stem(self, path: Path) -> None:
        fm = self._assert_parseable(path)
        assert fm.get("name") == path.stem, (
            f"{path.name}: 'name' field '{fm.get('name')}' must match filename stem '{path.stem}'"
        )

    def _assert_description_present_and_nonempty(self, path: Path) -> None:
        fm = self._assert_parseable(path)
        assert "description" in fm, f"{path.name}: frontmatter missing 'description' field"
        desc = fm["description"]
        assert desc and str(desc).strip(), f"{path.name}: frontmatter 'description' field is empty"

    def _assert_description_length(self, path: Path) -> None:
        fm = self._assert_parseable(path)
        desc = str(fm.get("description", "")).strip()
        assert len(desc) >= _MIN_DESCRIPTION_LEN, (
            f"{path.name}: description is {len(desc)} chars, minimum is {_MIN_DESCRIPTION_LEN}"
        )

    def _assert_model_field(self, path: Path) -> None:
        fm = self._assert_parseable(path)
        assert "model" in fm, f"{path.name}: frontmatter missing 'model' field"
        assert fm["model"] == "claude-sonnet-4-6", (
            f"{path.name}: 'model' must be 'claude-sonnet-4-6', got '{fm.get('model')}'"
        )

    def _assert_memory_field(self, path: Path) -> None:
        fm = self._assert_parseable(path)
        assert "memory" in fm, f"{path.name}: frontmatter missing 'memory' field"
        assert fm["memory"] == "project", f"{path.name}: 'memory' must be 'project', got '{fm.get('memory')}'"

    # --- SRE ---

    def test_sre_frontmatter_parses(self):
        self._assert_parseable(SRE)

    def test_sre_name_present_and_nonempty(self):
        self._assert_name_present_and_nonempty(SRE)

    def test_sre_name_matches_filename_stem(self):
        self._assert_name_matches_filename_stem(SRE)

    def test_sre_description_present_and_nonempty(self):
        self._assert_description_present_and_nonempty(SRE)

    def test_sre_description_minimum_length(self):
        self._assert_description_length(SRE)

    def test_sre_model_field(self):
        self._assert_model_field(SRE)

    def test_sre_memory_field(self):
        self._assert_memory_field(SRE)

    # --- PM ---

    def test_pm_frontmatter_parses(self):
        self._assert_parseable(PM)

    def test_pm_name_present_and_nonempty(self):
        self._assert_name_present_and_nonempty(PM)

    def test_pm_name_matches_filename_stem(self):
        self._assert_name_matches_filename_stem(PM)

    def test_pm_description_present_and_nonempty(self):
        self._assert_description_present_and_nonempty(PM)

    def test_pm_description_minimum_length(self):
        self._assert_description_length(PM)

    def test_pm_model_field(self):
        self._assert_model_field(PM)

    def test_pm_memory_field(self):
        self._assert_memory_field(PM)

    # --- Security Engineer ---

    def test_security_engineer_frontmatter_parses(self):
        self._assert_parseable(SECURITY_ENGINEER)

    def test_security_engineer_name_present_and_nonempty(self):
        self._assert_name_present_and_nonempty(SECURITY_ENGINEER)

    def test_security_engineer_name_matches_filename_stem(self):
        self._assert_name_matches_filename_stem(SECURITY_ENGINEER)

    def test_security_engineer_description_present_and_nonempty(self):
        self._assert_description_present_and_nonempty(SECURITY_ENGINEER)

    def test_security_engineer_description_minimum_length(self):
        self._assert_description_length(SECURITY_ENGINEER)

    def test_security_engineer_model_field(self):
        self._assert_model_field(SECURITY_ENGINEER)

    def test_security_engineer_memory_field(self):
        self._assert_memory_field(SECURITY_ENGINEER)

    # --- Database Architect ---

    def test_database_architect_frontmatter_parses(self):
        self._assert_parseable(DATABASE_ARCHITECT)

    def test_database_architect_name_present_and_nonempty(self):
        self._assert_name_present_and_nonempty(DATABASE_ARCHITECT)

    def test_database_architect_name_matches_filename_stem(self):
        self._assert_name_matches_filename_stem(DATABASE_ARCHITECT)

    def test_database_architect_description_present_and_nonempty(self):
        self._assert_description_present_and_nonempty(DATABASE_ARCHITECT)

    def test_database_architect_description_minimum_length(self):
        self._assert_description_length(DATABASE_ARCHITECT)

    def test_database_architect_model_field(self):
        self._assert_model_field(DATABASE_ARCHITECT)

    def test_database_architect_memory_field(self):
        self._assert_memory_field(DATABASE_ARCHITECT)

    # --- Technical Writer ---

    def test_technical_writer_frontmatter_parses(self):
        self._assert_parseable(TECHNICAL_WRITER)

    def test_technical_writer_name_present_and_nonempty(self):
        self._assert_name_present_and_nonempty(TECHNICAL_WRITER)

    def test_technical_writer_name_matches_filename_stem(self):
        self._assert_name_matches_filename_stem(TECHNICAL_WRITER)

    def test_technical_writer_description_present_and_nonempty(self):
        self._assert_description_present_and_nonempty(TECHNICAL_WRITER)

    def test_technical_writer_description_minimum_length(self):
        self._assert_description_length(TECHNICAL_WRITER)

    def test_technical_writer_model_field(self):
        self._assert_model_field(TECHNICAL_WRITER)

    def test_technical_writer_memory_field(self):
        self._assert_memory_field(TECHNICAL_WRITER)

    # --- Performance Engineer ---

    def test_performance_engineer_frontmatter_parses(self):
        self._assert_parseable(PERFORMANCE_ENGINEER)

    def test_performance_engineer_name_present_and_nonempty(self):
        self._assert_name_present_and_nonempty(PERFORMANCE_ENGINEER)

    def test_performance_engineer_name_matches_filename_stem(self):
        self._assert_name_matches_filename_stem(PERFORMANCE_ENGINEER)

    def test_performance_engineer_description_present_and_nonempty(self):
        self._assert_description_present_and_nonempty(PERFORMANCE_ENGINEER)

    def test_performance_engineer_description_minimum_length(self):
        self._assert_description_length(PERFORMANCE_ENGINEER)

    def test_performance_engineer_model_field(self):
        self._assert_model_field(PERFORMANCE_ENGINEER)

    def test_performance_engineer_memory_field(self):
        self._assert_memory_field(PERFORMANCE_ENGINEER)


# ---------------------------------------------------------------------------
# AC2 edge-case: no 'tools' field allowed on specialist agents
# ---------------------------------------------------------------------------


class TestNoToolsFieldOnSpecialists:
    """
    Structural contract: 'tools:' is EM-only. Specialist agents must NOT
    declare a 'tools:' frontmatter field.
    """

    def _assert_no_tools_field(self, path: Path) -> None:
        fm = _frontmatter(path)
        assert "tools" not in fm, f"{path.name}: specialist agents must not have a 'tools' frontmatter field (EM-only)"

    def test_sre_has_no_tools_field(self):
        self._assert_no_tools_field(SRE)

    def test_pm_has_no_tools_field(self):
        self._assert_no_tools_field(PM)

    def test_security_engineer_has_no_tools_field(self):
        self._assert_no_tools_field(SECURITY_ENGINEER)

    def test_database_architect_has_no_tools_field(self):
        self._assert_no_tools_field(DATABASE_ARCHITECT)

    def test_technical_writer_has_no_tools_field(self):
        self._assert_no_tools_field(TECHNICAL_WRITER)

    def test_performance_engineer_has_no_tools_field(self):
        self._assert_no_tools_field(PERFORMANCE_ENGINEER)


# ---------------------------------------------------------------------------
# AC3 — Description contains EM spawn-trigger language
# ---------------------------------------------------------------------------


class TestDescriptionContainsSpawnTrigger:
    """
    AC3: The 'description' frontmatter field must contain "spawn"
    (case-insensitive). This is the EM's primary selection signal — it reads
    only this field when scanning available agents to decide whether to spawn.
    """

    def _assert_spawn_in_description(self, path: Path) -> None:
        fm = _frontmatter(path)
        desc = str(fm.get("description", ""))
        assert "spawn" in desc.lower(), (
            f"{path.name}: 'description' frontmatter must contain 'spawn' (case-insensitive) for EM trigger selection"
        )

    def test_sre_description_contains_spawn(self):
        self._assert_spawn_in_description(SRE)

    def test_pm_description_contains_spawn(self):
        self._assert_spawn_in_description(PM)

    def test_security_engineer_description_contains_spawn(self):
        self._assert_spawn_in_description(SECURITY_ENGINEER)

    def test_database_architect_description_contains_spawn(self):
        self._assert_spawn_in_description(DATABASE_ARCHITECT)

    def test_technical_writer_description_contains_spawn(self):
        self._assert_spawn_in_description(TECHNICAL_WRITER)

    def test_performance_engineer_description_contains_spawn(self):
        self._assert_spawn_in_description(PERFORMANCE_ENGINEER)


# ---------------------------------------------------------------------------
# AC4 — Body contains "Spawned when:" section
# ---------------------------------------------------------------------------


class TestSpawnedWhenSectionInBody:
    """
    AC4: The prose body (after frontmatter) must contain a "Spawned when:"
    section. This is the explicit trigger list the EM reads in the full file.
    Both the frontmatter description (AC3) and this section must carry
    consistent trigger language — testing both ensures no divergence.
    """

    def _assert_spawned_when_in_body(self, path: Path) -> None:
        body = _body(path)
        assert "Spawned when:" in body, f"{path.name}: body must contain 'Spawned when:' section"

    def test_sre_has_spawned_when_section(self):
        self._assert_spawned_when_in_body(SRE)

    def test_pm_has_spawned_when_section(self):
        self._assert_spawned_when_in_body(PM)

    def test_security_engineer_has_spawned_when_section(self):
        self._assert_spawned_when_in_body(SECURITY_ENGINEER)

    def test_database_architect_has_spawned_when_section(self):
        self._assert_spawned_when_in_body(DATABASE_ARCHITECT)

    def test_technical_writer_has_spawned_when_section(self):
        self._assert_spawned_when_in_body(TECHNICAL_WRITER)

    def test_performance_engineer_has_spawned_when_section(self):
        self._assert_spawned_when_in_body(PERFORMANCE_ENGINEER)


# ---------------------------------------------------------------------------
# AC5 — Body contains "Does not" scope boundary section (all 6 files)
# ---------------------------------------------------------------------------


class TestDoesNotBoundarySectionInBody:
    """
    AC5: All 6 specialist files must have a "Does not" section.
    DESIGN.md explicitly names this for PM; Architect ruled it required for
    all specialists — multi-specialist sessions degrade silently without
    explicit scope boundaries.
    """

    def _assert_does_not_in_body(self, path: Path) -> None:
        body = _body(path)
        assert "Does not" in body, (
            f"{path.name}: body must contain 'Does not' section (scope boundary required on all specialists)"
        )

    def test_sre_has_does_not_section(self):
        self._assert_does_not_in_body(SRE)

    def test_pm_has_does_not_section(self):
        self._assert_does_not_in_body(PM)

    def test_security_engineer_has_does_not_section(self):
        self._assert_does_not_in_body(SECURITY_ENGINEER)

    def test_database_architect_has_does_not_section(self):
        self._assert_does_not_in_body(DATABASE_ARCHITECT)

    def test_technical_writer_has_does_not_section(self):
        self._assert_does_not_in_body(TECHNICAL_WRITER)

    def test_performance_engineer_has_does_not_section(self):
        self._assert_does_not_in_body(PERFORMANCE_ENGINEER)


# ---------------------------------------------------------------------------
# AC6 — Memory file section: header, correct path, no-permission statement
# ---------------------------------------------------------------------------


class TestMemoryFileSectionSpecialists:
    """
    AC6: Every specialist file must have:
    1. "## Your memory file" header in the body
    2. The correct memory path pattern: ~/.claude/agent-memory/<name>.md
       where <name> matches the frontmatter 'name' field exactly
    3. "You do not need permission to update your own memory" statement
    """

    def _assert_memory_header(self, path: Path) -> None:
        body = _body(path)
        assert "## Your memory file" in body, f"{path.name}: body must contain '## Your memory file' section"

    def _assert_memory_path_matches_name(self, path: Path) -> None:
        fm = _frontmatter(path)
        name = fm.get("name", "")
        body = _body(path)
        expected_path = f"~/.claude/agent-memory/{name}.md"
        assert expected_path in body, (
            f"{path.name}: memory section must reference path '{expected_path}' (name from frontmatter: '{name}')"
        )

    def _assert_no_permission_statement(self, path: Path) -> None:
        body = _body(path)
        assert "You do not need permission to update your own memory" in body, (
            f"{path.name}: memory section must contain 'You do not need permission to update your own memory'"
        )

    # --- SRE ---

    def test_sre_has_memory_file_header(self):
        self._assert_memory_header(SRE)

    def test_sre_memory_path_matches_name(self):
        self._assert_memory_path_matches_name(SRE)

    def test_sre_has_no_permission_statement(self):
        self._assert_no_permission_statement(SRE)

    # --- PM ---

    def test_pm_has_memory_file_header(self):
        self._assert_memory_header(PM)

    def test_pm_memory_path_matches_name(self):
        self._assert_memory_path_matches_name(PM)

    def test_pm_has_no_permission_statement(self):
        self._assert_no_permission_statement(PM)

    # --- Security Engineer ---

    def test_security_engineer_has_memory_file_header(self):
        self._assert_memory_header(SECURITY_ENGINEER)

    def test_security_engineer_memory_path_matches_name(self):
        self._assert_memory_path_matches_name(SECURITY_ENGINEER)

    def test_security_engineer_has_no_permission_statement(self):
        self._assert_no_permission_statement(SECURITY_ENGINEER)

    # --- Database Architect ---

    def test_database_architect_has_memory_file_header(self):
        self._assert_memory_header(DATABASE_ARCHITECT)

    def test_database_architect_memory_path_matches_name(self):
        self._assert_memory_path_matches_name(DATABASE_ARCHITECT)

    def test_database_architect_has_no_permission_statement(self):
        self._assert_no_permission_statement(DATABASE_ARCHITECT)

    # --- Technical Writer ---

    def test_technical_writer_has_memory_file_header(self):
        self._assert_memory_header(TECHNICAL_WRITER)

    def test_technical_writer_memory_path_matches_name(self):
        self._assert_memory_path_matches_name(TECHNICAL_WRITER)

    def test_technical_writer_has_no_permission_statement(self):
        self._assert_no_permission_statement(TECHNICAL_WRITER)

    # --- Performance Engineer ---

    def test_performance_engineer_has_memory_file_header(self):
        self._assert_memory_header(PERFORMANCE_ENGINEER)

    def test_performance_engineer_memory_path_matches_name(self):
        self._assert_memory_path_matches_name(PERFORMANCE_ENGINEER)

    def test_performance_engineer_has_no_permission_statement(self):
        self._assert_no_permission_statement(PERFORMANCE_ENGINEER)


# ---------------------------------------------------------------------------
# Frontmatter helper unit tests — test the helpers themselves in isolation
# ---------------------------------------------------------------------------


class TestFrontmatterHelpers:
    """
    Unit tests for the _frontmatter() and _body() helpers.
    These parse real agent files (which exist) so they execute without
    touching any network, database, or filesystem path outside the repo.
    We use an existing core agent file as the fixture — no specialist files
    required, so these pass even when specialists don't exist yet.
    """

    _EXISTING_FILE = AGENT_DEFS / "architect.md"

    def test_frontmatter_returns_dict(self):
        result = _frontmatter(self._EXISTING_FILE)
        assert isinstance(result, dict)

    def test_frontmatter_name_is_string(self):
        result = _frontmatter(self._EXISTING_FILE)
        assert isinstance(result["name"], str)

    def test_frontmatter_model_present(self):
        result = _frontmatter(self._EXISTING_FILE)
        assert "model" in result

    def test_body_does_not_contain_opening_fence(self):
        body = _body(self._EXISTING_FILE)
        # The body starts after the closing ---, so the very first ---
        # should not appear at position 0 of body
        assert not body.startswith("---")

    def test_body_is_nonempty_string(self):
        body = _body(self._EXISTING_FILE)
        assert isinstance(body, str)
        assert len(body.strip()) > 0
