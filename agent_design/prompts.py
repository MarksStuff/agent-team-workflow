"""Prompts for all agents and all workflow stages.

Structure:
  STAGE_*   — what to do right now: inputs, outputs, specific files to
              read/write. No agent identity here — that comes from agent files.

  build_*   — assemble a full start message for interactive team sessions
              by combining the Eng Manager identity, the stage task, and
              spawn prompts for each teammate.
"""

import re
from pathlib import Path

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

_CONTINUE_TASK = """\
Feature: {feature_request}

Task: continue the design workflow for the above feature.

Available specialists: {available_specialists}

Read the worktree before your first response:
- BASELINE.md — codebase context
- DESIGN.md — current draft (if it exists)
- DISCUSSION.md — prior team discussion
- feedback/ — any human feedback not yet incorporated

Based on what you read, decide what phase this session covers and tell the
team in your opening message. Do not wait to be told.
"""

_IMPL_START_MESSAGE = """\
Feature: {feature_request}

Task: implement the above feature using the design in .agent-design/DESIGN.md

Available specialists: {available_specialists}

Before spawning the team: read DESIGN.md and identify which section(s) are
relevant to this feature. State those section(s) explicitly in your opening
message — "We are implementing §X and §Y; everything else is out of scope."
Do not spawn the team until you have done this scoping step.
"""

_IMPL_RESUME_MESSAGE = """\
Feature: {feature_request}

Task: resume the implementation sprint for the above feature.

Available specialists: {available_specialists}

Before resuming: read DESIGN.md to re-establish which section(s) are in scope
for this feature, and read TASKS.md to see what is done and what remains.
State the current status in your opening message before calling on the team.
"""


def _parse_frontmatter_name(content: str) -> str | None:
    """Extract the name field from YAML frontmatter delimited by ---.

    Returns the name value as a string, or None if not found.
    """
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    frontmatter = match.group(1)
    name_match = re.search(r"^name:\s+(\S+)", frontmatter, re.MULTILINE)
    return name_match.group(1) if name_match else None


def get_available_specialists(agents_dir: Path | None = None) -> str:
    """Discover available specialist agents from ~/.claude/agents/.

    Reads the agents directory and returns a comma-separated list of agent
    names, excluding the eng_manager (who is already running the session).

    Args:
        agents_dir: Override the agents directory (for testing). Defaults to
                    ~/.claude/agents/.

    Returns:
        Comma-separated agent names, or an empty string if none found.
    """
    if agents_dir is None:
        agents_dir = Path.home() / ".claude" / "agents"
    if not agents_dir.exists():
        return ""

    names = []
    for path in sorted(agents_dir.glob("*.md")):
        if path.stem == "eng_manager":
            continue
        content = path.read_text()
        name = _parse_frontmatter_name(content)
        names.append(name if name else path.stem)

    return ", ".join(names)


def build_impl_start(feature_request: str, is_resume: bool = False, available_specialists: str | None = None) -> str:
    """Build the Eng Manager start message for the implementation sprint."""
    # EM is assumed to be running the session; its prompt is loaded automatically
    # by Claude Code from ~/.claude/agents/eng_manager.md
    template = _IMPL_RESUME_MESSAGE if is_resume else _IMPL_START_MESSAGE
    specialists = available_specialists if available_specialists is not None else get_available_specialists()
    return template.format(feature_request=feature_request, available_specialists=specialists).strip()


def build_continue_start(feature_request: str, available_specialists: str | None = None) -> str:
    """Build the Eng Manager start message for a continue session.

    Replaces build_review_start and build_feedback_start. The EM reads the
    worktree and infers what phase applies; this function emits a generic
    prompt with no hardcoded stage or round assumptions.
    """
    specialists = available_specialists if available_specialists is not None else get_available_specialists()
    return _CONTINUE_TASK.format(feature_request=feature_request, available_specialists=specialists).strip()


_REMEMBER_MESSAGE = """\
A human correction or override has been recorded.

Correction: {correction}
Project: {project_slug}
Date: {date}

Each agent: read this note. If it is relevant to your role and decisions you
might make, update your own memory file at ~/.claude/agent-memory/<your-name>.md.
Use the established format (## Corrections & Overrides, YYYY-MM-DD [project]).
If it is not relevant to you, do nothing.

After updates are complete, each agent that made a change reports: what they
wrote and why.

The Retrospective Facilitator verifies: at least one agent must have updated
their memory. If no agent self-updated after a non-trivial correction, the
Facilitator flags it and prompts the most relevant agent to reconsider.
"""

_REVIEW_FEEDBACK_MESSAGE = """\
A GitHub pull request review has been completed. The reviewer's comments are
provided below.

PR: {pr_url}

PR Review Comments:
{pr_comments}

Each agent: read all comments above. If any comment is relevant to your role
and decisions you might make in future sessions, update your own memory file
at ~/.claude/agent-memory/<your-name>.md.
Use the established format (## Corrections & Overrides, YYYY-MM-DD [project]).
If nothing is relevant to you, do nothing.

After updates are complete, each agent that made a change reports: what they
wrote and why.

The Retrospective Facilitator verifies: at least one agent must have updated
their memory. If no agent self-updated, the Facilitator flags it.
"""


def build_remember_start(
    correction: str, project_slug: str, date: str, available_specialists: str | None = None
) -> str:
    """Build the start message for a remember session.

    Broadcasts a human correction to all core agents in a --print session.
    Each agent reads it and self-updates their memory file if relevant.

    Args:
        correction: The human correction or override text
        project_slug: Short identifier for the project (e.g., 'news-reader')
        date: Date string for the correction (e.g., '2026-04-04')
        available_specialists: Unused; kept for API consistency (optional)

    Returns:
        Start message string for run_print_team()
    """
    return _REMEMBER_MESSAGE.format(
        correction=correction,
        project_slug=project_slug,
        date=date,
    ).strip()


def build_retro_start(
    project_slug: str,
    date: str,
    discussion_path: str,
    tasks_path: str | None,
    decisions_path: str | None,
    human_observation: str | None = None,
    available_specialists: str | None = None,
) -> str:
    """Build the Eng Manager start message for a retrospective session.

    Launches a --print multi-agent session where the Retrospective Facilitator
    reads DISCUSSION.md, TASKS.md, and DECISIONS.md, identifies friction points,
    tells each relevant agent what was observed, asks each to self-update their
    memory file, verifies pickup, and produces RETRO.md.

    Args:
        project_slug: Short identifier for the project (e.g., 'news-reader')
        date: Date string for the retrospective (e.g., '2026-04-04')
        discussion_path: Absolute path to DISCUSSION.md (for inclusion in prompt)
        tasks_path: Absolute path to TASKS.md (for inclusion in prompt), or None if absent
        decisions_path: Absolute path to DECISIONS.md (for inclusion in prompt), or None if absent
        human_observation: Optional human-provided observation to include in the retro prompt
        available_specialists: Unused; kept for API consistency (optional)

    Returns:
        Start message string for run_print_team()
    """
    tasks_line = f"- Tasks:     {tasks_path}" if tasks_path is not None else "- Tasks:     (not present)"
    decisions_line = f"- Decisions: {decisions_path}" if decisions_path is not None else "- Decisions: (not present)"

    observation_block = (
        f"\nHuman observation (treat this as a first-class input alongside the artefacts above):\n{human_observation}\n"
        if human_observation
        else ""
    )

    return f"""\
Retrospective session for project: {project_slug}
Date: {date}

Read the following artefacts to understand what happened this sprint:
- Discussion: {discussion_path}
{tasks_line}
{decisions_line}
{observation_block}
Your task:
1. Identify friction points and patterns from the discussion and task board.
2. For each agent involved in a friction point, tell them specifically what was observed.
3. Ask each relevant agent to self-update their memory file at ~/.claude/agent-memory/<name>.md.
4. Verify pickup: each agent that self-updated reports what they wrote and why.
5. Produce RETRO.md in the current directory with the following structure:
   - Project, date, What Went Well, Friction Points, Action Items
   - A "Prompt Suggestions (pending human review)" section with entries formatted as:
     - [PS-1] <agent-file>.md: <suggestion text>
     - [PS-2] <agent-file>.md: <suggestion text>
     (use [PS-N] tags for each suggestion)

Write RETRO.md now. Do not ask for confirmation.""".strip()


def build_apply_suggestion_start(
    suggestion_id: str,
    suggestion_text: str,
    agents_dir: str,
) -> str:
    """Build the task prompt for an apply-suggestion session.

    A --print single-agent (architect) session that reads the prompt suggestion
    and edits the relevant agent definition file in agents_dir.

    Args:
        suggestion_id: Suggestion identifier as it appears in RETRO.md (e.g., 'PS-1')
        suggestion_text: Full suggestion text extracted from RETRO.md
        agents_dir: Absolute path to the agents directory (e.g., '/Users/foo/.claude/agents')

    Returns:
        Task prompt string for run_solo()
    """
    return f"""\
Apply prompt suggestion {suggestion_id} to the relevant agent definition file.

Suggestion text:
{suggestion_text}

Agents directory: {agents_dir}

Instructions:
1. Identify which agent definition file the suggestion refers to (the filename is in the suggestion text).
2. Read the current content of that file from {agents_dir}/<agent-file>.md.
3. Edit the agent definition file to incorporate the suggestion.
4. Write the updated file back to {agents_dir}/<agent-file>.md.

Apply the change now. Do not ask for confirmation.""".strip()


def build_fix_ci_start(
    ci_failures: str,
    pr_url: str,
    available_specialists: str | None = None,
) -> str:
    """Build the Eng Manager start message for a fix-ci session.

    Tells the team what CI failures were reported and instructs them to
    fix only the failing checks.

    Args:
        ci_failures: Verbatim CI failure output
        pr_url: GitHub PR URL
        available_specialists: Comma-separated agent names (auto-detected if None)

    Returns:
        Start message string for run_team_in_repo()
    """
    specialists = available_specialists if available_specialists is not None else get_available_specialists()
    return f"""\
CI fix session for PR: {pr_url}

Available specialists: {specialists}

The following CI checks are failing:

{ci_failures}

Your task as Eng Manager:
1. Read the CI failure output above carefully and identify what type of failure it is
   (test failure, lint error, type error, etc.).
2. Spawn the appropriate specialist(s) to fix it — do not fix it yourself.
   For test/code failures: spawn tdd_focused_engineer and developer.
   For lint/type errors: developer is sufficient.
   For ambiguous failures: spawn the full team.
3. Instruct the specialist(s) to fix ONLY what CI reports as failing — no unrelated
   refactors — and to run tests locally to confirm green before finishing.
4. Do not introduce new failures while fixing existing ones.

Spawn the team now. Do not ask for confirmation.""".strip()


def build_review_feedback_start(pr_comments: str, pr_url: str, available_specialists: str | None = None) -> str:
    """Build the start message for a review-feedback session.

    Broadcasts PR review comments to all core agents in a --print session.
    Each agent reads and self-updates their memory file if relevant.

    Args:
        pr_comments: Formatted string of PR review comments
        pr_url: GitHub PR URL for context
        available_specialists: Unused; kept for API consistency (optional)

    Returns:
        Start message string for run_print_team()
    """
    return _REVIEW_FEEDBACK_MESSAGE.format(
        pr_comments=pr_comments,
        pr_url=pr_url,
    ).strip()
