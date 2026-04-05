"""
Tests verifying that each required addition from § Agent Prompt Assessment
(DESIGN.md lines 888–1024) is present in the correct agent definition file.

All tests are expected to be RED until the Developer applies the changes.
"""

from pathlib import Path

AGENT_DEFS = Path(__file__).parent.parent / "plugins" / "core" / "agents"

ENG_MANAGER = AGENT_DEFS / "eng_manager.md"
ARCHITECT = AGENT_DEFS / "architect.md"
DEVELOPER = AGENT_DEFS / "developer.md"
QA_ENGINEER = AGENT_DEFS / "qa_engineer.md"
TDD_ENGINEER = AGENT_DEFS / "tdd_focused_engineer.md"


def _content(path: Path) -> str:
    return path.read_text()


# ---------------------------------------------------------------------------
# Universal: ## Your memory file — must appear in every agent file
# ---------------------------------------------------------------------------


class TestMemoryFileSectionAllAgents:
    """DESIGN.md §All agents: memory self-authorship block required in every file."""

    def _assert_memory_block(self, path: Path) -> None:
        content = _content(path)
        assert "## Your memory file" in content, f"{path.name} is missing '## Your memory file' section"

    def _assert_memory_path_instruction(self, path: Path) -> None:
        content = _content(path)
        assert "$AGENT_CORE_PLUGIN_DIR/memory/" in content, (
            f"{path.name} is missing the memory path '$AGENT_CORE_PLUGIN_DIR/memory/'"
        )

    def _assert_memory_update_triggers(self, path: Path) -> None:
        content = _content(path)
        assert "A human corrects or overrides something you proposed" in content, (
            f"{path.name} is missing memory update trigger about human corrections"
        )

    def _assert_memory_format(self, path: Path) -> None:
        content = _content(path)
        assert "## Corrections & Overrides" in content, (
            f"{path.name} is missing '## Corrections & Overrides' format example"
        )

    def _assert_no_permission_needed(self, path: Path) -> None:
        content = _content(path)
        assert "You do not need permission to update your own memory" in content, (
            f"{path.name} is missing 'You do not need permission to update your own memory'"
        )

    # eng_manager
    def test_eng_manager_has_memory_file_section(self):
        self._assert_memory_block(ENG_MANAGER)

    def test_eng_manager_has_memory_path(self):
        self._assert_memory_path_instruction(ENG_MANAGER)

    def test_eng_manager_has_memory_update_triggers(self):
        self._assert_memory_update_triggers(ENG_MANAGER)

    def test_eng_manager_has_memory_format_example(self):
        self._assert_memory_format(ENG_MANAGER)

    def test_eng_manager_has_no_permission_needed(self):
        self._assert_no_permission_needed(ENG_MANAGER)

    # architect
    def test_architect_has_memory_file_section(self):
        self._assert_memory_block(ARCHITECT)

    def test_architect_has_memory_path(self):
        self._assert_memory_path_instruction(ARCHITECT)

    def test_architect_has_memory_update_triggers(self):
        self._assert_memory_update_triggers(ARCHITECT)

    def test_architect_has_memory_format_example(self):
        self._assert_memory_format(ARCHITECT)

    def test_architect_has_no_permission_needed(self):
        self._assert_no_permission_needed(ARCHITECT)

    # developer
    def test_developer_has_memory_file_section(self):
        self._assert_memory_block(DEVELOPER)

    def test_developer_has_memory_path(self):
        self._assert_memory_path_instruction(DEVELOPER)

    def test_developer_has_memory_update_triggers(self):
        self._assert_memory_update_triggers(DEVELOPER)

    def test_developer_has_memory_format_example(self):
        self._assert_memory_format(DEVELOPER)

    def test_developer_has_no_permission_needed(self):
        self._assert_no_permission_needed(DEVELOPER)

    # qa_engineer
    def test_qa_engineer_has_memory_file_section(self):
        self._assert_memory_block(QA_ENGINEER)

    def test_qa_engineer_has_memory_path(self):
        self._assert_memory_path_instruction(QA_ENGINEER)

    def test_qa_engineer_has_memory_update_triggers(self):
        self._assert_memory_update_triggers(QA_ENGINEER)

    def test_qa_engineer_has_memory_format_example(self):
        self._assert_memory_format(QA_ENGINEER)

    def test_qa_engineer_has_no_permission_needed(self):
        self._assert_no_permission_needed(QA_ENGINEER)

    # tdd_focused_engineer
    def test_tdd_engineer_has_memory_file_section(self):
        self._assert_memory_block(TDD_ENGINEER)

    def test_tdd_engineer_has_memory_path(self):
        self._assert_memory_path_instruction(TDD_ENGINEER)

    def test_tdd_engineer_has_memory_update_triggers(self):
        self._assert_memory_update_triggers(TDD_ENGINEER)

    def test_tdd_engineer_has_memory_format_example(self):
        self._assert_memory_format(TDD_ENGINEER)

    def test_tdd_engineer_has_no_permission_needed(self):
        self._assert_no_permission_needed(TDD_ENGINEER)


# ---------------------------------------------------------------------------
# Eng Manager: design-session guidance
# ---------------------------------------------------------------------------


class TestEngManagerDesignSessionGuidance:
    """DESIGN.md §Eng Manager: design session section required."""

    def test_has_in_design_sessions_section(self):
        content = _content(ENG_MANAGER)
        assert "## In design sessions" in content, "eng_manager.md is missing '## In design sessions' section"

    def test_reads_baseline_md_in_design_sessions(self):
        content = _content(ENG_MANAGER)
        assert "BASELINE.md" in content, "eng_manager.md is missing instruction to read BASELINE.md in design sessions"

    def test_reads_design_md_in_design_sessions(self):
        content = _content(ENG_MANAGER)
        # DESIGN.md appears in a list under "In design sessions"
        assert "DESIGN.md" in content, "eng_manager.md is missing instruction to read DESIGN.md in design sessions"

    def test_reads_discussion_md_before_session(self):
        content = _content(ENG_MANAGER)
        assert "DISCUSSION.md" in content, (
            "eng_manager.md is missing instruction to read DISCUSSION.md before session start"
        )

    def test_reads_feedback_dir_in_design_sessions(self):
        content = _content(ENG_MANAGER)
        assert "feedback/" in content, "eng_manager.md is missing instruction to check feedback/ directory"

    def test_decides_phase_from_reading(self):
        content = _content(ENG_MANAGER)
        assert "decide what phase this session covers" in content, (
            "eng_manager.md is missing instruction to decide what phase this session covers"
        )


# ---------------------------------------------------------------------------
# Eng Manager: missing-agent escalation
# ---------------------------------------------------------------------------


class TestEngManagerMissingAgentEscalation:
    """DESIGN.md §Eng Manager: escalation instructions for missing agents."""

    def test_has_missing_agent_section(self):
        content = _content(ENG_MANAGER)
        assert "## When you need an agent that doesn't exist" in content, (
            "eng_manager.md is missing '## When you need an agent that doesn't exist' section"
        )

    def test_instructs_posting_gap_to_discussion(self):
        content = _content(ENG_MANAGER)
        assert "state the gap specifically" in content, (
            "eng_manager.md is missing instruction to state the gap specifically in DISCUSSION.md"
        )

    def test_instructs_writing_agent_proposal(self):
        content = _content(ENG_MANAGER)
        assert ".agent-design/proposals/" in content, (
            "eng_manager.md is missing instruction to write agent proposal to .agent-design/proposals/"
        )

    def test_proposal_must_include_gap_filled(self):
        content = _content(ENG_MANAGER)
        assert "the gap it fills" in content, (
            "eng_manager.md is missing requirement that proposal includes 'the gap it fills'"
        )

    def test_instructs_identifying_blocked_tasks(self):
        content = _content(ENG_MANAGER)
        assert "gated on the missing agent" in content, (
            "eng_manager.md is missing instruction to identify tasks gated on missing agent"
        )

    def test_human_approves_not_em(self):
        content = _content(ENG_MANAGER)
        assert "You never create agent files yourself" in content, (
            "eng_manager.md is missing 'You never create agent files yourself. You propose; the human approves.'"
        )


# ---------------------------------------------------------------------------
# Architect: read CLAUDE.md and BASELINE.md before proposing
# ---------------------------------------------------------------------------


class TestArchitectReadBeforeProposing:
    """DESIGN.md §Architect: must read CLAUDE.md and BASELINE.md before any recommendation."""

    def test_has_read_claude_md_instruction(self):
        content = _content(ARCHITECT)
        assert "Read CLAUDE.md" in content, "architect.md is missing instruction to read CLAUDE.md before proposing"

    def test_claude_md_is_not_negotiable(self):
        content = _content(ARCHITECT)
        assert "not negotiable" in content, (
            "architect.md is missing statement that CLAUDE.md constraints are 'not negotiable'"
        )

    def test_has_read_baseline_md_instruction(self):
        content = _content(ARCHITECT)
        assert "Read BASELINE.md" in content, "architect.md is missing instruction to read BASELINE.md before proposing"

    def test_baseline_proposals_warning(self):
        content = _content(ARCHITECT)
        assert "Proposals that ignore the baseline are wasted turns" in content, (
            "architect.md is missing 'Proposals that ignore the baseline are wasted turns'"
        )


# ---------------------------------------------------------------------------
# Architect: post to DISCUSSION.md immediately on design drift
# ---------------------------------------------------------------------------


class TestArchitectDesignDriftPosting:
    """DESIGN.md §Architect: post to DISCUSSION.md immediately when spotting design drift."""

    def test_posts_design_drift_immediately(self):
        content = _content(ARCHITECT)
        # The existing file already mentions "Call out design drift the moment you see it"
        # but DESIGN.md requires an explicit instruction to post to DISCUSSION.md
        assert "post to .agent-design/DISCUSSION.md" in content, (
            "architect.md is missing explicit instruction to post to .agent-design/DISCUSSION.md when spotting design drift"
        )


# ---------------------------------------------------------------------------
# Developer: design-gap protocol
# ---------------------------------------------------------------------------


class TestDeveloperDesignGapProtocol:
    """DESIGN.md §Developer: protocol for when implementation reveals a design gap."""

    def test_has_design_gap_instruction(self):
        content = _content(DEVELOPER)
        assert "design gap" in content, "developer.md is missing instruction for handling a discovered design gap"

    def test_posts_to_discussion_on_gap(self):
        content = _content(DEVELOPER)
        assert "Post to .agent-design/DISCUSSION.md immediately" in content, (
            "developer.md is missing 'Post to .agent-design/DISCUSSION.md immediately' for design gaps"
        )

    def test_states_what_design_says_vs_reality(self):
        content = _content(DEVELOPER)
        assert "what the design says" in content, (
            "developer.md is missing instruction to state 'what the design says' when reporting gap"
        )

    def test_waits_for_architect_acknowledgment(self):
        content = _content(DEVELOPER)
        assert "Wait for Architect to acknowledge" in content, (
            "developer.md is missing 'Wait for Architect to acknowledge before proceeding with a workaround'"
        )

    def test_no_silent_deviation(self):
        content = _content(DEVELOPER)
        assert "silent deviation from the design" in content, (
            "developer.md is missing warning against 'silent deviation from the design'"
        )


# ---------------------------------------------------------------------------
# TDD-Focused Engineer: test derivation when DESIGN.md is silent on names
# ---------------------------------------------------------------------------


class TestTDDEngineerTestDerivationGuidance:
    """DESIGN.md §TDD-Focused Engineer: guidance when DESIGN.md doesn't specify test names."""

    def test_has_derive_from_acceptance_criteria_instruction(self):
        content = _content(TDD_ENGINEER)
        assert "Derive tests from the acceptance criteria" in content, (
            "tdd_focused_engineer.md is missing 'Derive tests from the acceptance criteria in DESIGN.md'"
        )

    def test_references_baseline_for_naming_conventions(self):
        content = _content(TDD_ENGINEER)
        assert "BASELINE.md for patterns" in content, (
            "tdd_focused_engineer.md is missing instruction to check BASELINE.md for naming patterns"
        )

    def test_documents_choices_in_discussion(self):
        content = _content(TDD_ENGINEER)
        assert "Document your choices in .agent-design/DISCUSSION.md" in content, (
            "tdd_focused_engineer.md is missing 'Document your choices in .agent-design/DISCUSSION.md'"
        )


# ---------------------------------------------------------------------------
# QA Engineer: ## In design sessions section
# ---------------------------------------------------------------------------


class TestQAEngineerDesignSessionSection:
    """DESIGN.md §QA Engineer: design session section with acceptance criteria guidance."""

    def test_has_in_design_sessions_section(self):
        content = _content(QA_ENGINEER)
        assert "## In design sessions" in content, "qa_engineer.md is missing '## In design sessions' section"

    def test_most_important_work_happens_before_code(self):
        content = _content(QA_ENGINEER)
        assert "Your most important work happens here, before anyone writes code" in content, (
            "qa_engineer.md is missing 'Your most important work happens here, before anyone writes code'"
        )

    def test_writes_acceptance_criteria_to_design_md(self):
        content = _content(QA_ENGINEER)
        assert "write acceptance criteria" in content, (
            "qa_engineer.md is missing instruction to write acceptance criteria to DESIGN.md"
        )

    def test_acceptance_criteria_under_acceptance_criteria_section(self):
        content = _content(QA_ENGINEER)
        assert '"Acceptance Criteria" section' in content, (
            'qa_engineer.md is missing instruction to add an "Acceptance Criteria" section to DESIGN.md'
        )

    def test_observable_criterion(self):
        content = _content(QA_ENGINEER)
        assert "Observable:" in content, "qa_engineer.md is missing 'Observable:' acceptance criteria property"

    def test_testable_criterion(self):
        content = _content(QA_ENGINEER)
        assert "Testable:" in content, "qa_engineer.md is missing 'Testable:' acceptance criteria property"

    def test_complete_criterion(self):
        content = _content(QA_ENGINEER)
        assert "Complete:" in content, "qa_engineer.md is missing 'Complete:' acceptance criteria property"

    def test_push_until_criteria_are_clear(self):
        content = _content(QA_ENGINEER)
        assert "Push the team until acceptance criteria are clear" in content, (
            "qa_engineer.md is missing 'Push the team until acceptance criteria are clear'"
        )

    def test_feature_works_not_a_criterion(self):
        content = _content(QA_ENGINEER)
        assert '"The feature works" is not' in content, (
            "qa_engineer.md is missing '\"The feature works\" is not an acceptance criterion'"
        )
