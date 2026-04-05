# DESIGN_v2.md — Agent Team Workflow: Plugin-Based Architecture

## Problem

All agent configuration currently lives in `~/.claude`:
- Agent definitions → `~/.claude/agents/*.md`
- Agent memory → `~/.claude/agent-memory/*.md`
- Skills → `~/.claude/skills/` (future)

This creates three problems:

1. **Not portable.** Every new machine requires manual setup — copy files from the repo to
   `~/.claude`, keep them in sync, remember what goes where.
2. **Split source of truth.** Agent definitions are maintained in this repository but must
   be copied to `~/.claude` to take effect. Changes drift.
3. **No separation of concerns.** General-purpose agents (developer, architect, TDD engineer…)
   are mixed with project-specific or domain-specific agents, all in one flat directory.

---

## Proposed Architecture: Claude Plugins

Claude Code supports `--plugin-dir <path>` flags on the CLI invocation. A plugin directory
is a self-contained bundle that can include:
- Agent definitions (`agents/*.md`)
- Skills (`skills/*.md`)
- Memory files (`memory/*.md`)
- CLAUDE.md instructions
- MCP server config (`.mcp.json`)

Multiple `--plugin-dir` flags can be passed in a single invocation.

### Two plugins in this repository

```
agent-team-workflow/
  plugins/
    core/          # general-purpose agents used across all projects
      agents/
        architect.md
        developer.md
        eng_manager.md
        qa_engineer.md
        tdd_focused_engineer.md
        retrospective_facilitator.md
        ... (all current ~/.claude/agents/*.md)
      CLAUDE.md    # global agent team guidelines
    local/         # project/domain-specific agents for this repo
      agents/
        # e.g. future domain-specific agents
      CLAUDE.md    # project-specific overrides
```

### CLI invocation

```bash
claude --plugin-dir ./plugins/core --plugin-dir ./plugins/local
```

The `agent-design` CLI will pass these flags automatically when launching all Claude sessions
(`run_solo`, `run_team`, `run_print_team`, `run_team_in_repo`).

---

## Migration Plan

1. Create `plugins/core/agents/` and move all `~/.claude/agents/*.md` into it (keeping
   copies in `~/.claude/agents/` temporarily for backward compatibility during transition).
2. Create `plugins/core/CLAUDE.md` with the global agent team guidelines (currently in
   `~/.claude/CLAUDE.md` / `agent-instructions/CLAUDE.md`).
3. Create `plugins/local/` as an empty scaffold for future domain-specific agents.
4. Update `launcher.py` (`run_solo`, `run_team`, `run_print_team`, `run_team_in_repo`) to
   pass `--plugin-dir` flags pointing at both plugin directories.
5. Validate: run the full test suite; do a manual smoke test of `agent-design impl`.
6. Once validated, remove the agent files from `~/.claude/agents/` — the plugin directories
   are the sole source of truth.

---

## Agent Memory

Agent memory files (`~/.claude/agent-memory/*.md`) are session-persistent notes written by
agents themselves. Because memory is agent-written at runtime (not human-authored config),
it stays in `~/.claude/agent-memory/` for now. A future decision point: whether to move
memory into the plugin directory (e.g. `plugins/core/memory/`) so it is also versioned.

---

## Open Questions

- Does `--plugin-dir` support agent memory files, or only agents/skills/CLAUDE.md?
- Should `plugins/local/` live in this repo or in each target repo's `.agent-design/`?
- Do we need a `--plugin-dir` for the target repo's `.agent-design/` directory as well?
