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

from agent_design.config import PLUGIN_CORE

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

Read .agent-design/BASELINE.md.

Write the initial .agent-design/DESIGN.md. Before writing, identify explicitly:
- What is IN scope
- What is OUT of scope
- What assumptions you are making

.agent-design/DESIGN.md structure:
1. Scope — requirements, non-requirements, explicit assumptions
2. Proposed approach and high-level architecture
3. Key components and their responsibilities
4. Data flow and interface contracts
5. Open questions for the team

Also create:
- .agent-design/DISCUSSION.md with header: # Design Discussion
- .agent-design/DECISIONS.md with header: # Design Decisions

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
- .agent-design/BASELINE.md — codebase context
- .agent-design/DESIGN.md — current draft (if it exists)
- .agent-design/DISCUSSION.md — prior team discussion
- .agent-design/feedback/ — any human feedback not yet incorporated

Based on what you read, decide what phase this session covers and tell the
team in your opening message. Do not wait to be told.
"""

_IMPL_START_MESSAGE = """\
Feature: {feature_request}

Task: implement the above feature using the design in .agent-design/DESIGN.md

Available specialists: {available_specialists}

Before spawning the team: read .agent-design/DESIGN.md and identify which section(s) are
relevant to this feature. State those section(s) explicitly in your opening
message — "We are implementing §X and §Y; everything else is out of scope."
Do not spawn the team until you have done this scoping step.
"""

_IMPL_RESUME_MESSAGE = """\
Feature: {feature_request}

Task: resume the implementation sprint for the above feature.

Available specialists: {available_specialists}

Before resuming: read .agent-design/DESIGN.md to re-establish which section(s) are in scope
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
    """Discover available specialist agents from plugins/core/agents/.

    Reads the agents directory and returns a comma-separated list of agent
    names, excluding the eng_manager (who is already running the session).

    Args:
        agents_dir: Override the agents directory (for testing). Defaults to
                    PLUGIN_CORE / "agents".

    Returns:
        Comma-separated agent names, or an empty string if none found.
    """
    if agents_dir is None:
        agents_dir = PLUGIN_CORE / "agents"
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
might make, update your own memory file at <CORE>/memory/<your-name>.md (where CORE is the path from ~/.agent-design/core_plugin_dir).
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
at <CORE>/memory/<your-name>.md (where CORE is the path from ~/.agent-design/core_plugin_dir).
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


_RETRO_MESSAGE = """\
Sprint retrospective for project: {project_slug}
Date: {date}
{observation_block}
You are the Retrospective Facilitator. Your job is to FACILITATE — not to do the work yourself.
Spawn the full team immediately. Every agent must participate in every phase.

---

## Phase 1 — Gather and share the material

Read these files (if they exist) and write a concise factual summary:
- DISCUSSION.md — team discussion log
- DECISIONS.md — resolved and deadlocked decisions
- ../TASKS.md — implementation task board (one directory up, at the repo root)

Share the summary with the whole team via SendMessage. Do not editorialize.
This is facts only — what was built, what was decided, what was blocked.

---

## Phase 2 — Independent reflection (parallel)

Message every team member individually:
  "Read the sprint summary. Independently list:
   1. What went well? (observations and facts only — not solutions yet)
   2. What went badly? (observations and facts only — not solutions yet)
   Reply with your lists before discussing with others."

Wait for replies from all agents. If anyone is silent after a reasonable wait,
call them out by name: "I need your reflection list before we continue."

---

## Phase 3 — Pool and prioritise

Collect all items from all agents. Present the full combined list to the team:
  "Here are all the observations. Vote: which 3 items from the 'went well' list
   matter most? Which 3 from the 'went badly' list matter most?
   Reply with your top 3 from each."

Tally the votes. Announce the winning top 3 good and top 3 bad to the team.
If there are ties, facilitate a short discussion to break them.

---

## Phase 4 — Discuss and decide

For each of the 6 items (top 3 good, top 3 bad), facilitate a team discussion:
- Good items: "What specifically made this work? How do we reinforce it?"
- Bad items: "What specifically caused this? What would prevent it next time?"

Ensure every agent contributes to at least one item's discussion.
If someone is silent on an item that clearly touches their role, call them out.

---

## Phase 5 — Ownership

Present the consolidated action items to the full team:
  "For each action item below, which of you should act on it?
   If it's relevant to your role, say so and update your memory file now.
   Memory file: <CORE>/memory/<your-name>.md (CORE = path from ~/.agent-design/core_plugin_dir)
   Use the format: ## Corrections & Overrides / YYYY-MM-DD [project]"

**If any action item is claimed by nobody:**
Flag it explicitly: "No agent claimed this item — this may indicate we are
missing an agent role. Document it under 'Unowned Items' in RETRO.md."

---

## Phase 6 — Produce RETRO.md

Write RETRO.md in the current directory with this exact format:

# Retrospective — {project_slug} — {date}

## What Went Well (top 3)
1. <item> — <what to reinforce>

## What Went Badly (top 3)
1. <item> — <what to change>

## Action Items
- <who>: <what>

## Unowned Items (possible missing agent role)
- <item> — <why no agent claimed it>

## Prompt Suggestions (pending human review)
- [PS-1] <agent-file>.md: <concrete wording change that addresses a bad item>

Prompt Suggestions must be concrete wording edits to agent definition files —
not vague intentions. They address root causes of the bad items.
"""

_APPLY_SUGGESTION_MESSAGE = """\
Apply prompt suggestion {suggestion_id} to an agent definition file.

Suggestion ID: {suggestion_id}
Agent file: {agent_file}
Change to make: {suggestion_text}

The full path to the agent definition file is:
  <AGENT_CORE_PLUGIN_DIR>/agents/{agent_file}

where AGENT_CORE_PLUGIN_DIR is available as an environment variable.

Steps:
1. Read the agent definition file at the path above.
2. Make the minimal targeted edit described in the suggestion text.
3. Write the updated content back to the file.
4. Confirm what was changed (quote the before and after).
"""


def build_retro_start(project_slug: str, date: str, human_observation: str | None = None) -> str:
    """Build the start message for a retrospective session.

    Instructs the Retrospective Facilitator to run a team retrospective:
    independent reflection, pooled voting, discussion, ownership assignment,
    and RETRO.md production.

    Args:
        project_slug: Short identifier for the project (e.g., 'news-reader')
        date: Date string for the retrospective (e.g., '2026-04-05')
        human_observation: Optional human observation to seed the retro

    Returns:
        Start message string for run_print_team()
    """
    if human_observation:
        observation_block = f"\nHuman observation (treat as a first-class input alongside the sprint artifacts):\n  {human_observation}\n"
    else:
        observation_block = ""
    return _RETRO_MESSAGE.format(
        project_slug=project_slug,
        date=date,
        observation_block=observation_block,
    ).strip()


def build_apply_suggestion_start(suggestion_id: str, agent_file: str, suggestion_text: str) -> str:
    """Build the start message for an apply-suggestion session.

    Instructs Claude to edit a specific agent definition file with the
    minimal change described in the suggestion.

    Args:
        suggestion_id: Suggestion identifier (e.g., 'PS-1')
        agent_file: Agent definition filename (e.g., 'architect.md')
        suggestion_text: The wording change to apply

    Returns:
        Start message string for run_apply_suggestion()
    """
    return _APPLY_SUGGESTION_MESSAGE.format(
        suggestion_id=suggestion_id,
        agent_file=agent_file,
        suggestion_text=suggestion_text,
    ).strip()


_REFRESH_DOMAIN_MESSAGE = """\
You are a domain expert agent. Your task is to refresh your volatile knowledge.

Steps:
1. Read ~/.agent-design/core_plugin_dir to get the absolute path to the core plugin (CORE).
2. Read your memory file at <CORE>/memory/{agent_name}.md.
3. For each URL listed in your "Authoritative Sources" section:
   - Fetch the page and compare its content to what you have recorded.
   - Note any additions, removals, or changes.
4. Update the "Volatile Knowledge" section with current information.
5. Update the "verified:" date in the Volatile Knowledge header to: {today}.
6. If a source was unreachable or you could not verify an entry, move it to "Pending Refresh"
   with a note explaining what you could not verify.
7. Write the updated memory file back to <CORE>/memory/{agent_name}.md.

After writing, confirm: state what changed and what was verified without changes.
"""


def build_refresh_domain_start(agent_name: str, today: str) -> str:
    """Build the start message for a refresh-domain session.

    Instructs the named domain expert to refresh its volatile knowledge
    by checking its authoritative sources.

    Args:
        agent_name: Name of the domain expert agent (e.g., 'claude_expert')
        today: ISO date string (e.g., '2026-04-05')

    Returns:
        Start message string for run_solo()
    """
    return _REFRESH_DOMAIN_MESSAGE.format(
        agent_name=agent_name,
        today=today,
    ).strip()


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
