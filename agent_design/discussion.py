"""Discussion turn orchestration for agent collaboration."""

from pathlib import Path

from agent_design.agents.claude_agent import ClaudeAgent
from agent_design.agents.configs import AGENT_CONFIGS
from agent_design.agents.types import AgentType
from agent_design.state import RoundState, load_round_state, save_round_state


async def run_discussion_turn(worktree_path: Path, state: RoundState) -> bool:
    """Run one discussion turn with all agents contributing sequentially.

    Each agent reads the current state of DISCUSSION.md, DESIGN.md, and BASELINE.md,
    then appends their contribution to DISCUSSION.md.

    The order is:
    1. Developer
    2. QA Engineer
    3. Code Quality Engineer
    4. Architect
    5. Eng Manager (facilitates and checks for convergence)

    Args:
        worktree_path: Path to the .agent-design worktree
        state: Current round state

    Returns:
        True if convergence was declared, False otherwise
    """
    target_repo = Path(state.target_repo)

    # Define agent execution order
    agent_order = [
        AgentType.DEVELOPER,
        AgentType.QA_ENGINEER,
        AgentType.CODE_QUALITY_ENGINEER,
        AgentType.ARCHITECT,
        AgentType.ENG_MANAGER,
    ]

    convergence_declared = False

    for agent_type in agent_order:
        print(f"\n[{agent_type.value.upper()}] Starting contribution...")

        # Create agent
        config = AGENT_CONFIGS[agent_type]
        agent = ClaudeAgent(config)

        # Build user prompt based on agent type
        if agent_type == AgentType.DEVELOPER:
            user_prompt = """Read BASELINE.md, DESIGN.md, and DISCUSSION.md.

Contribute your perspective on the implementation concerns for this design.
Focus on: what's straightforward, what's hard, edge cases, API shape, naming.

Append your contribution to DISCUSSION.md following the format:
## [Developer]
<your response>"""

        elif agent_type == AgentType.QA_ENGINEER:
            user_prompt = """Read BASELINE.md, DESIGN.md, and DISCUSSION.md.

Contribute your perspective on the quality and acceptance criteria for this design.
Focus on: observable behavior, acceptance criteria, boundary cases, end-to-end flows.

Append your contribution to DISCUSSION.md following the format:
## [QA Engineer]
<your response>"""

        elif agent_type == AgentType.CODE_QUALITY_ENGINEER:
            user_prompt = """Read BASELINE.md, DESIGN.md, and DISCUSSION.md.

Contribute your perspective on the testability of this design.
Focus on: dependency injection, interface boundaries, mock surfaces, unit testability.

Append your contribution to DISCUSSION.md following the format:
## [Code Quality Engineer]
<your response>"""

        elif agent_type == AgentType.ARCHITECT:
            user_prompt = """Read BASELINE.md, DESIGN.md, and DISCUSSION.md.

Respond to specific points raised by other agents in the discussion.
Update DESIGN.md if consensus is forming around changes.

Append your contribution to DISCUSSION.md following the format:
## [Architect]
<your response>"""

        else:  # ENG_MANAGER
            user_prompt = """Read ROUND_STATE.json, BASELINE.md, DESIGN.md, DISCUSSION.md, and DECISIONS.md.

Facilitate the discussion:
- Call on any silent agents
- Redirect opinions to facts
- Name disagreements and ask for evidence
- Update DECISIONS.md with any resolved disagreements
- Check if all agents have contributed and no new objections remain

If convergence is achieved (all agents have spoken, no unresolved objections), output CONVERGENCE_DECLARED at the end of your response.

Append your contribution to DISCUSSION.md following the format:
## [Eng Manager]
<your response>"""

        # Execute agent
        result = await agent.execute(
            user_prompt=user_prompt,
            working_dir=worktree_path,
            additional_dirs=[target_repo],
            timeout=1800,  # 30 minutes per agent
        )

        if not result.success:
            print(f"[{agent_type.value.upper()}] FAILED: {result.error}")
            response = input("Retry this agent? (y/n): ")
            if response.lower() == "y":
                # Retry by running the same agent again (recursive call would be here)
                # For now, just report the error
                raise RuntimeError(f"Agent {agent_type.value} failed: {result.error}")
            else:
                print("Skipping this agent and continuing...")
                continue

        print(f"[{agent_type.value.upper()}] Completed ({result.execution_time:.1f}s)")

        # Check for convergence declaration (Eng Manager only)
        if agent_type == AgentType.ENG_MANAGER:
            if "CONVERGENCE_DECLARED" in result.output:
                convergence_declared = True
                print("\n✓ Convergence declared by Eng Manager")

        # Increment discussion turn counter after each agent
        state.discussion_turns += 1
        save_round_state(worktree_path, state)

    return convergence_declared


async def run_baseline_phase(worktree_path: Path, state: RoundState) -> None:
    """Run Phase 0: Architect analyzes codebase and writes BASELINE.md.

    Args:
        worktree_path: Path to the .agent-design worktree
        state: Current round state
    """
    target_repo = Path(state.target_repo)

    print("\n[PHASE 0] Baseline Analysis")
    print(f"Target repo: {target_repo}")

    # Create Architect agent
    config = AGENT_CONFIGS[AgentType.ARCHITECT]
    agent = ClaudeAgent(config)

    user_prompt = f"""Phase 0: Baseline Analysis

Analyze the codebase at: {target_repo}

Write BASELINE.md covering:
- Relevant directory structure and key files
- Language, framework, and dependency conventions
- Dominant patterns (naming, error handling, async style, logging)
- Existing components this feature will interact with
- Anything non-obvious a new contributor should know

Include this header at the top:
<!-- baseline-commit: <current HEAD sha> -->
<!-- baseline-updated: <current date YYYY-MM-DD> -->

Feature request for context:
{state.feature_request}
"""

    result = await agent.execute(
        user_prompt=user_prompt,
        working_dir=worktree_path,
        additional_dirs=[target_repo],
        timeout=1800,
    )

    if not result.success:
        raise RuntimeError(f"Baseline analysis failed: {result.error}")

    print(f"[PHASE 0] Completed ({result.execution_time:.1f}s)")


async def run_initial_draft_phase(worktree_path: Path, state: RoundState) -> None:
    """Run Phase 1: Architect writes initial DESIGN.md.

    Args:
        worktree_path: Path to the .agent-design worktree
        state: Current round state
    """
    print("\n[PHASE 1] Initial Design Draft")

    # Create Architect agent
    config = AGENT_CONFIGS[AgentType.ARCHITECT]
    agent = ClaudeAgent(config)

    user_prompt = f"""Phase 1: Initial Design Draft

Read BASELINE.md and write the initial DESIGN.md.

Before writing, identify:
- What is explicitly IN scope
- What is explicitly OUT of scope
- What assumptions you are making

Write DESIGN.md covering:
- Feature scope (requirements + non-requirements)
- Proposed approach and architecture
- Key components and responsibilities
- Data flow and interface contracts
- Open questions for the team

Also create empty files:
- DECISIONS.md (will be populated during discussion)
- DISCUSSION.md (will be populated during discussion)

Feature request:
{state.feature_request}
"""

    result = await agent.execute(
        user_prompt=user_prompt,
        working_dir=worktree_path,
        additional_dirs=[Path(state.target_repo)],
        timeout=1800,
    )

    if not result.success:
        raise RuntimeError(f"Initial draft failed: {result.error}")

    print(f"[PHASE 1] Completed ({result.execution_time:.1f}s)")
