# Claude Domain Expert Memory

## Stable Knowledge (baked into prompt — update rarely)

- Claude tool_use message structure: assistant turn contains `tool_use` block
  with fields `id`, `name`, `input`; next user turn contains `tool_result`
  block with `tool_use_id` and `content`
- Claude Code agent team model: EM spawns sub-agents via the Agent tool;
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` required for multi-agent sessions
- Permission modes: default (user confirms), `acceptEdits` (edits auto-accepted),
  `bypassPermissions` (all tool use auto-accepted)
- Hooks: `PreToolUse`, `PostToolUse`, `Notification`, `Stop` events; wired via
  `.claude/settings.json`; exit code 2 from hook blocks action and sends
  feedback to agent
- `--print` mode: non-interactive; stdout is session output; used for
  automated stages and headless sessions
- `--agent <name>`: loads agent identity from `--plugin-dir` or `.claude/agents/`
- `--plugin-dir <path>`: adds agent and memory directories to Claude's search
  path; multiple flags may be passed
- Agent tool `isolation: "worktree"`: creates isolated git worktree for safe
  parallel file writes

## Volatile Knowledge (verified: 2026-04-05)

- Current models: claude-opus-4-5, claude-sonnet-4-6, claude-haiku-4-5
- claude-sonnet-4-6 context window: 200k tokens
- claude-opus-4-5 context window: 200k tokens
- CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 required for team sessions (as of
  2026-04-05; may be stabilised in a future release)
- Agent file locations Claude Code searches: `~/.claude/agents/` (global) and
  `.claude/agents/` in the project (repo-local); `--plugin-dir` flags add
  additional search paths

## Authoritative Sources

- https://docs.anthropic.com/en/docs/claude-code
- https://docs.anthropic.com/en/release-notes/claude-code
- https://docs.anthropic.com/en/api/getting-started
- https://docs.anthropic.com/en/docs/about-claude/models/overview
- https://docs.anthropic.com/en/docs/claude-code/hooks
- https://docs.anthropic.com/en/docs/claude-code/sub-agents

## Pending Refresh

- Rate limits and tier-based token budgets: not yet verified for current models
- Pricing per million tokens for all current models: check before advising
- Whether CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS flag has been stabilised
  (graduated out of experimental) — re-check at next session

## Corrections & Overrides
