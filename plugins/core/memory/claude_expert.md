# Claude Domain Expert Memory

## Stable Knowledge (baked into prompt — update rarely)
- tool_use message structure: tool_use block (id, name, input) → tool_result block (tool_use_id, content)
- Claude Code agent team model: requires CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1; EM spawns subagents via Agent tool
- Permission modes: default (prompts user), acceptEdits (auto-accept file edits), bypassPermissions (skip all prompts), dangerouslySkipPermissions (CLI flag)
- Hooks: PreToolUse, PostToolUse, Stop, Notification events; configured in .claude/settings.json
- Plugin loading: --plugin-dir loads agents/ and CLAUDE.md from that directory; two dirs supported (core + local)
- --agent flag: sets the agent identity from an agents/ file; --print runs non-interactively

## Volatile Knowledge (verified: 2026-04-05)
- Current models: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5-20251001
- claude-sonnet-4-6 context window: 200k tokens
- Agent tool: supports isolation: "worktree" for isolated git worktrees; run_in_background for async agents
- CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 required for SendMessage and TeamCreate tools
- claude --print mode: non-interactive, outputs to stdout; used for automated sessions

## Authoritative Sources
- https://docs.anthropic.com/en/docs/claude-code
- https://docs.anthropic.com/en/release-notes/claude-code
- https://docs.anthropic.com/en/api/getting-started

## Pending Refresh
- Rate limits and pricing: last baked in at project start — verify before advising on production quotas
- Latest Claude Code release features: check release notes before each major session
