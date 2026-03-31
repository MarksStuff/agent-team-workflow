"""Prompts for all agents and all workflow stages.

Structure:
  STAGE_*   — what to do right now: inputs, outputs, specific files to
              read/write. No agent identity here — that comes from agent files.

  build_*   — assemble a full start message for interactive team sessions
              by combining the Eng Manager identity, the stage task, and
              spawn prompts for each teammate.
"""

# =============================================================================
# Stage task prompts (solo sessions — Architect running alone)
# No agent identity here. That goes in architect.md via --append-system-prompt.
# =============================================================================

STAGE_0_BASELINE = """\
Read the codebase at {target_repo}.

Write BASELINE.md to the current directory. Cover:
- Relevant directory structure and key files
- Language, framework, and dependency conventions
- Dominant patterns: naming, error handling, async style, logging
- Existing components the new feature will interact with
- Anything non-obvious a new contributor should know

Include this header at the very top of BASELINE.md:
  <!-- baseline-commit: <current HEAD sha of {target_repo}> -->
  <!-- baseline-updated: <today's date> -->

Feature being designed: {feature_request}

Write BASELINE.md now. Do not ask for confirmation.
"""

STAGE_1_INITIAL_DRAFT = """\
Feature request: {feature_request}

Read BASELINE.md in the current directory.

Write the initial DESIGN.md. Before writing, identify explicitly:
- What is IN scope
- What is OUT of scope
- What assumptions you are making

DESIGN.md structure:
1. Scope — requirements, non-requirements, explicit assumptions
2. Proposed approach and high-level architecture
3. Key components and their responsibilities
4. Data flow and interface contracts
5. Open questions for the team

Also create:
- DISCUSSION.md with header: # Design Discussion
- DECISIONS.md with header: # Design Decisions

Write all three files now. Do not ask for confirmation.
"""


# =============================================================================
# Team session start messages (interactive agent team sessions)
# Assembled from agent identities + stage task by the build_* functions.
# =============================================================================

_STAGE_2_TASK = """\
Feature: {feature_request}

Task: run a design review for the above feature.

Files in this directory:
- BASELINE.md — codebase analysis
- DESIGN.md — initial draft to review and refine
- DISCUSSION.md — shared discussion thread
- DECISIONS.md — resolved decisions and deadlocks
"""

_STAGE_3_TASK = """\
Feature: {feature_request}

Task: incorporate human feedback (round {round_num}).

Human feedback is in: feedback/human-round-{round_num}.md

Files in this directory:
- BASELINE.md — codebase analysis
- DESIGN.md — current design
- DISCUSSION.md — prior discussion
- DECISIONS.md — prior decisions
"""

_IMPL_START_MESSAGE = """\
Feature: {feature_request}

Task: implement the above feature using the design in .agent-design/DESIGN.md

The design document may contain broader context or future phases — implement
ONLY the feature listed above.
"""

_IMPL_RESUME_MESSAGE = """\
Feature: {feature_request}

Task: resume the implementation sprint for the above feature.

The design document may contain broader context or future phases — stay
scoped to the feature listed above.
"""


def build_impl_start(feature_request: str, is_resume: bool = False) -> str:
    """Build the Eng Manager start message for the implementation sprint."""
    # EM is assumed to be running the session; its prompt is loaded automatically
    # by Claude Code from ~/.claude/agents/eng_manager.md
    template = _IMPL_RESUME_MESSAGE if is_resume else _IMPL_START_MESSAGE
    return template.format(feature_request=feature_request).strip()


def build_review_start(feature_request: str) -> str:
    """Build the Eng Manager start message for stage 2 (design review)."""
    return _STAGE_2_TASK.format(feature_request=feature_request).strip()


def build_feedback_start(round_num: int) -> str:
    """Build the Eng Manager start message for stage 3+ (feedback integration)."""
    return _STAGE_3_TASK.format(round_num=round_num).strip()
