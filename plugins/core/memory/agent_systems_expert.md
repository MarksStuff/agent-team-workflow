# Agent Systems Expert Memory

## Stable Knowledge (baked into prompt — update rarely)
- Orchestrator-worker pattern: one agent coordinates, workers execute; EM is facilitator not director
- Task board coordination (TASKS.md): shared state visible to all agents; claim-before-start prevents conflicts
- Shared memory vs message passing: shared files (DISCUSSION.md, TASKS.md) for persistent state; SendMessage for real-time coordination
- Agent identity: system prompt defines role; spawned agent inherits context from spawn message + its own agent file
- EM-as-facilitator vs EM-as-relay: relay routes all communication through EM (bottleneck); facilitator lets agents talk directly (preferred)
- Domain experts: advise only; do not claim tasks or write implementation; consulted on-demand

## Volatile Knowledge (verified: 2026-04-05)
- Claude Code agent teams: Agent tool spawns subagents; SendMessage for peer-to-peer; TeamCreate for named teams
- Task isolation via worktree: Agent tool isolation:"worktree" gives each agent a clean git copy
- Memory self-authorship: agents update their own memory files; no central memory writer
- Retrospective pattern: facilitator reviews artifacts, asks agents to self-update, does not write on their behalf

## Authoritative Sources
- https://docs.anthropic.com/en/docs/claude-code/agents
- https://www.anthropic.com/research
- https://docs.anthropic.com/en/docs/build-with-claude/tool-use

## Pending Refresh
- Multi-agent framework landscape (LangGraph, AutoGen, CrewAI): evolving rapidly — search before comparing
- Latest agent coordination research: check Anthropic research page before sessions involving novel patterns
