# Architect Memory — agent-team-workflow

## Project conventions

- Repo: `/Users/markstriebeck/Documents/agent-team-workflow`
- Design artefacts: `.agent-design/` inside the target repo (which IS this repo in self-improvement sprints)
- TASKS.md at repo root during impl sprints; DISCUSSION.md also at repo root
- State file: `.agent-design/ROUND_STATE.json` — uses `dataclasses.asdict()` / `RoundState(**data)` for ser/deser
- CLI entry: `agent_design/cli/main.py` → registers commands from `agent_design/cli/commands/`

## Workflow role clarity

- TDD goes first and confirms RED before Developer implements
- Architect does NOT implement before TDD RED — claims tasks but holds execution
- Architect's sprint contribution: DISCUSSION.md integration-boundary analysis + architectural decisions

## Phase 5 key decisions (2026-04-04)

- `build_continue_start(feature_request, available_specialists=None)` — no `round_num`; EM infers phase from worktree
- `RoundState.phase` field and `PhaseType` are removed; `load_round_state()` must strip unknown keys to support old JSON
- `next` command kept as alias to `continue` for this sprint (removal is follow-up)
- `_CONTINUE_TASK` template is generic — no "Stage N" language; EM reads worktree and decides
