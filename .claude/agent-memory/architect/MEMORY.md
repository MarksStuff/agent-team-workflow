# Architect Memory — agent-team-workflow

## Project conventions

- Repo: `/Users/markstriebeck/Documents/agent-team-workflow`
- Design artefacts: `.agent-design/` inside the target repo (which IS this repo in self-improvement sprints)
- TASKS.md at repo root during impl sprints
- State file: `.agent-design/ROUND_STATE.json` — uses `dataclasses.asdict()` / `RoundState(**data)` for ser/deser
- CLI entry: `agent_design/cli/main.py` → registers commands from `agent_design/cli/commands/`

## Workflow role clarity

- TDD goes first and confirms RED before Developer implements
- Architect does NOT implement before TDD RED — claims tasks but holds execution
- Architect's sprint contribution: `.agent-design/DISCUSSION.md` integration-boundary analysis + interface contracts

## Corrections & Overrides

- 2026-04-04 [agent-team-workflow]: Post interface contracts to `.agent-design/DISCUSSION.md` immediately
  after defining them — TDD and Developer both need the contract before writing tests or implementation.
  Waiting until asked causes the contract-mismatch problem (Developer implements one signature,
  TDD tests another).
