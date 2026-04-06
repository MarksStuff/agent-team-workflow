# Agent Systems Expert Memory

## Stable Knowledge (baked into prompt — update rarely)

- Orchestrator/subagent model: single orchestrator controls all delegation;
  simpler to reason about; bottleneck when orchestrator is a relay rather than
  a facilitator; works well when tasks are sequential
- Peer/collaborative model: agents communicate directly; higher coordination
  overhead; better for parallelisable tasks; requires shared state (files) or
  explicit message passing
- Shared state via files: durable, inspectable, no message-passing protocol
  needed; concurrent writes require either locks or a coordination convention
  (e.g. agents append to DISCUSSION.md rather than overwriting)
- Memory file tradeoffs: baked-in knowledge (fast, always available, goes
  stale); retrieved knowledge (always current, costs a tool call, depends on
  retrieval quality); external files (persistent across sessions, agent-authored,
  machine-local, requires Read tool call at session start)
- Stable vs. volatile knowledge split: architectural principles and protocol
  structures are stable (bake in); model versions, API changes, framework
  releases are volatile (retrieve or refresh)
- Tool description quality: the LLM selects tools by reading their description;
  vague descriptions cause over- or under-use; descriptions should state when
  to use the tool, not just what it does
- Known failure modes: cascading hallucination, context window exhaustion,
  coordination deadlock, memory inconsistency (concurrent writes), role drift
  under EM pressure, EM-as-relay anti-pattern

## Volatile Knowledge (verified: 2026-04-05)

- LangGraph: stateful multi-agent orchestration framework by LangChain;
  current stable series is 0.x as of early 2026 — verify for current version
- AutoGen (Microsoft): framework for conversational multi-agent systems; v0.4+
  introduced async and event-driven patterns — verify current version
- CrewAI: role-based agent framework with crew/task/agent primitives — verify
  current version and feature set before advising
- Claude Code sub-agents: native agent spawning via the Agent tool; worktree
  isolation available; `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` for multi-agent
  sessions — verify stability status

## Authoritative Sources

- https://langchain-ai.github.io/langgraph/
- https://microsoft.github.io/autogen/
- https://docs.crewai.com/
- https://docs.anthropic.com/en/docs/claude-code/sub-agents
- https://arxiv.org/abs/2308.11432 (AgentBench — multi-agent evaluation)
- https://arxiv.org/abs/2402.05929 (survey: LLM-based multi-agent systems)

## Pending Refresh

- LangGraph current stable version and API surface: verify before advising
- AutoGen v0.4+ async patterns: was in flux as of late 2025 — re-check
- Any new coordination protocols or standards from 2026 — not yet tracked
- CrewAI: fast-moving project; verify feature set and API before advising

## Corrections & Overrides
