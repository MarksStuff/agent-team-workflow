"""Tests for the retrospective_facilitator.md agent definition file.

Derivation: DESIGN.md § "Retrospective Facilitator" (Agent Roster) +
QA acceptance criteria AC-RF1 through AC-RF6.

These tests verify the *structure* of the agent definition file — not its
behaviour at runtime. The file is a static .md artifact; the tests read it
and assert its structural properties.

AC-RF7 (symlink resolves) is a MANUAL check only — not tested here.

All tests reference the file at agent-definitions/retrospective_facilitator.md
(checked into the repo so CI can access it).
"""

from pathlib import Path

AGENT_FILE_PATH = Path(__file__).parent.parent / "agent-definitions" / "retrospective_facilitator.md"


# ---------------------------------------------------------------------------
# AC-RF1: file exists and is non-empty
# ---------------------------------------------------------------------------


class TestRetroFacilitatorFileExists:
    """AC-RF1: retrospective_facilitator.md exists at ~/.claude/agents/ and is non-empty."""

    def test_file_exists(self) -> None:
        """retrospective_facilitator.md exists at ~/.claude/agents/."""
        assert AGENT_FILE_PATH.exists(), (
            f"retrospective_facilitator.md not found at {AGENT_FILE_PATH}. "
            "Developer must write this file as part of Phase 8."
        )

    def test_file_is_not_empty(self) -> None:
        """retrospective_facilitator.md is non-empty."""
        assert AGENT_FILE_PATH.exists()
        content = AGENT_FILE_PATH.read_text()
        assert len(content.strip()) > 0, "retrospective_facilitator.md is empty"


# ---------------------------------------------------------------------------
# AC-RF2: YAML frontmatter with name and description
# ---------------------------------------------------------------------------


class TestRetroFacilitatorFrontmatter:
    """AC-RF2: file has YAML frontmatter with 'name' and 'description' fields."""

    def _read(self) -> str:
        assert AGENT_FILE_PATH.exists(), f"File not found: {AGENT_FILE_PATH}"
        return AGENT_FILE_PATH.read_text()

    def test_has_yaml_frontmatter_delimiters(self) -> None:
        """File starts with --- and has a closing --- (YAML frontmatter)."""
        content = self._read()
        assert content.startswith("---"), "File must start with YAML frontmatter (---)"
        # Find closing delimiter
        body = content[3:]  # Skip opening ---
        assert "---" in body, "YAML frontmatter must have a closing --- delimiter"

    def test_frontmatter_has_name_field(self) -> None:
        """YAML frontmatter contains a 'name:' field."""
        import re

        content = self._read()
        # Extract frontmatter block
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, "Could not parse YAML frontmatter"
        frontmatter = match.group(1)
        assert re.search(r"^name:\s+\S", frontmatter, re.MULTILINE), (
            "Frontmatter must contain a 'name:' field with a value"
        )

    def test_frontmatter_name_is_retrospective_facilitator(self) -> None:
        """The 'name' field is 'retrospective_facilitator'."""
        import re

        content = self._read()
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, "Could not parse YAML frontmatter"
        frontmatter = match.group(1)
        name_match = re.search(r"^name:\s+(\S+)", frontmatter, re.MULTILINE)
        assert name_match, "No 'name:' field found in frontmatter"
        assert name_match.group(1) == "retrospective_facilitator", (
            f"Expected name: retrospective_facilitator, got: {name_match.group(1)!r}"
        )

    def test_frontmatter_has_description_field(self) -> None:
        """YAML frontmatter contains a 'description:' field."""
        import re

        content = self._read()
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, "Could not parse YAML frontmatter"
        frontmatter = match.group(1)
        assert re.search(r"^description:", frontmatter, re.MULTILINE), "Frontmatter must contain a 'description:' field"

    def test_frontmatter_description_is_non_empty(self) -> None:
        """The 'description:' field has non-empty text."""
        import re

        content = self._read()
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, "Could not parse YAML frontmatter"
        frontmatter = match.group(1)
        # Description may be inline or multi-line (> block scalar)
        desc_match = re.search(r"^description:\s*(.+)", frontmatter, re.MULTILINE)
        assert desc_match, "description: field is empty or missing"
        assert len(desc_match.group(1).strip()) > 0


# ---------------------------------------------------------------------------
# AC-RF3: description has spawn-trigger language
# ---------------------------------------------------------------------------


class TestRetroFacilitatorSpawnTrigger:
    """AC-RF3: description includes language that triggers spawning for retro sessions."""

    def _read(self) -> str:
        assert AGENT_FILE_PATH.exists(), f"File not found: {AGENT_FILE_PATH}"
        return AGENT_FILE_PATH.read_text()

    def test_description_mentions_retrospective(self) -> None:
        """Description mentions 'retrospective' to trigger the right spawn decisions."""
        content = self._read()
        # The description field may span multiple lines in multi-line YAML
        assert "retrospective" in content.lower(), (
            "Agent description must mention 'retrospective' to serve as spawn-trigger language"
        )

    def test_description_is_specific_enough(self) -> None:
        """Description is not generic — references a specific role or task."""
        import re

        content = self._read()
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, "Could not parse YAML frontmatter"
        frontmatter = match.group(1)
        # Description must be at least 20 chars (not just "Retrospective agent")
        desc_match = re.search(r"^description:\s*>?\s*(.*)", frontmatter, re.MULTILINE | re.DOTALL)
        if desc_match:
            desc_text = desc_match.group(1).strip()
            assert len(desc_text) >= 20, (
                f"Description too short ({len(desc_text)} chars). Must be specific enough to guide spawn decisions."
            )


# ---------------------------------------------------------------------------
# AC-RF4: body has "Spawned when:" section
# ---------------------------------------------------------------------------


class TestRetroFacilitatorSpawnedWhenSection:
    """AC-RF4: body includes a 'Spawned when:' section."""

    def _body(self) -> str:
        assert AGENT_FILE_PATH.exists(), f"File not found: {AGENT_FILE_PATH}"
        content = AGENT_FILE_PATH.read_text()
        # Skip past the frontmatter
        import re

        match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
        if match:
            return content[match.end() :]
        return content

    def test_body_has_spawned_when_section(self) -> None:
        """Body contains 'Spawned when:' header or label."""
        body = self._body()
        assert "spawned when" in body.lower(), (
            "Agent body must include a 'Spawned when:' section to guide EM spawn decisions"
        )


# ---------------------------------------------------------------------------
# AC-RF5: body has "Does not" section with specific prohibitions
# ---------------------------------------------------------------------------


class TestRetroFacilitatorDoesNotSection:
    """AC-RF5: body has explicit prohibitions against writing to other agents' memory
    files directly and against applying prompt changes directly."""

    def _body(self) -> str:
        assert AGENT_FILE_PATH.exists(), f"File not found: {AGENT_FILE_PATH}"
        content = AGENT_FILE_PATH.read_text()
        import re

        match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
        if match:
            return content[match.end() :]
        return content

    def test_body_prohibits_writing_to_other_agents_memory(self) -> None:
        """Body explicitly states facilitator does NOT write to other agents' memory files."""
        body = self._body().lower()
        # Must mention not writing to other agents' memory files directly
        assert "memory" in body, "Body must mention memory files"
        # Some combination of 'not', 'never', "does not", "do not" + writing to others' memory
        has_prohibition = (
            "does not write" in body or "never write" in body or "do not write" in body or "not write" in body
        )
        assert has_prohibition, (
            "Body must explicitly state facilitator does not write to other agents' memory files directly"
        )

    def test_body_prohibits_applying_prompt_changes_directly(self) -> None:
        """Body explicitly states facilitator does NOT apply prompt changes directly."""
        body = self._body().lower()
        # Must reference not applying prompt changes
        has_prohibition = (
            "does not apply" in body or "never apply" in body or "do not apply" in body or "not apply" in body
        )
        assert has_prohibition, "Body must explicitly state facilitator does not apply prompt changes directly"


# ---------------------------------------------------------------------------
# AC-RF6: memory file section with correct path and read/write statement
# ---------------------------------------------------------------------------


class TestRetroFacilitatorMemorySection:
    """AC-RF6: body has a memory file section referencing the correct path."""

    def _body(self) -> str:
        assert AGENT_FILE_PATH.exists(), f"File not found: {AGENT_FILE_PATH}"
        content = AGENT_FILE_PATH.read_text()
        import re

        match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
        if match:
            return content[match.end() :]
        return content

    def test_body_references_memory_file_path(self) -> None:
        """Body references the correct memory file path."""
        body = self._body()
        expected_path = "~/.claude/agent-memory/retrospective_facilitator.md"
        assert expected_path in body, f"Body must reference memory file path: {expected_path}"

    def test_body_states_read_write_access(self) -> None:
        """Body states read/write access to the memory file."""
        body = self._body().lower()
        assert "read" in body and "write" in body, "Body must state read/write access to the memory file"
