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
Task: design review for the feature described below.

Feature: {feature_request}

Available specialists: architect, developer, qa_engineer, tdd_focused_engineer

Spawn the specialists most relevant to this feature.

Files in this directory:
- BASELINE.md — codebase analysis (already written)
- DESIGN.md — initial draft to review and refine
- DISCUSSION.md — shared thread; all agents append entries here tagged with
  their role: ## [Role Name]
- DECISIONS.md — append resolved disagreements here using the format:
    ## Decision: <title>
    **Disagreement:** ...
    **Positions:** ...
    **Resolution:** ...

Run a free-form design discussion. Converge on DESIGN.md and DECISIONS.md.
If the team cannot reach agreement on a point, record the deadlock in
DECISIONS.md and flag it for human review — do not force a false consensus.
"""

_STAGE_3_TASK = """\
Task: incorporate human feedback (round {round_num})

Human feedback is in: feedback/human-round-{round_num}.md

Available specialists: architect, developer, qa_engineer, tdd_focused_engineer

Spawn the specialists most relevant to this task.

Files in this directory:
- BASELINE.md — codebase analysis
- DESIGN.md — current design (update as consensus forms)
- DISCUSSION.md — prior discussion; append new entries with a separator line
- DECISIONS.md — prior decisions; append new resolutions

Surface the feedback as a ## [Human] entry in DISCUSSION.md, facilitate
discussion, and update DESIGN.md with the agreed changes.
If any feedback point leads to unresolvable disagreement, record it as a
deadlock in DECISIONS.md for human review.
"""

_IMPL_START_MESSAGE = """\
Task: implement the design in .agent-design/DESIGN.md

Available specialists: architect, developer, qa_engineer, tdd_focused_engineer

Spawn who you need. Create TASKS.md. Run three phases:
1. Sprint planning — self-assign tasks
2. Implementation — TDD first, tests gate completion
3. Final review — Architect + QA sign off before declaring done
"""

_IMPL_RESUME_MESSAGE = """\
Task: resume existing implementation sprint / fix round

Review .agent-design/DESIGN.md for any new changes or clarifications.
Review TASKS.md for existing tasks, their status, and any new tasks.
Review .agent-design/DISCUSSION.md for any pending discussions or blockers.
Continue implementation, incorporating any new design changes and resolving
existing issues. The goal is still to implement everything in DESIGN.md.

Available specialists: architect, developer, qa_engineer, tdd_focused_engineer

Spawn who you need. Continue the three phases outlined above.
"""


def build_impl_start(is_resume: bool = False) -> str:
    """Build the Eng Manager start message for the implementation sprint."""
    # EM is assumed to be running the session; its prompt is loaded automatically
    # by Claude Code from ~/.claude/agents/eng_manager.md
    return _IMPL_RESUME_MESSAGE.strip() if is_resume else _IMPL_START_MESSAGE.strip()


def build_review_start(feature_request: str) -> str:
    """Build the Eng Manager start message for stage 2 (design review)."""
    return _STAGE_2_TASK.format(feature_request=feature_request).strip()


def build_feedback_start(round_num: int) -> str:
    """Build the Eng Manager start message for stage 3+ (feedback integration)."""
    return _STAGE_3_TASK.format(round_num=round_num).strip()
