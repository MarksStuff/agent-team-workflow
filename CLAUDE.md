# CLAUDE.md — agent-team-workflow

> Project-specific guidance for this repository.
> Global Claude Code guidelines live in `agent-instructions/CLAUDE.md`
> (symlinked to `~/.claude/CLAUDE.md`).

---

## What this repo is

`agent-team-workflow` provides the `agent-design` CLI — a tool that runs
structured, multi-agent software design reviews and self-organising
implementation sprints using Claude Code's native agent teams. Each workflow
stage runs as one `claude` session; the CLI manages git state, design
artefacts, and PR lifecycle between sessions.

---

## Project layout

```
agent_design/
  cli/commands/      # click CLI entry points (init, next, impl)
  agents/            # subagent definition files (future use)
  prompts.py         # AGENT_* identity constants + STAGE_* task prompts
  git_ops.py         # all git operations (_run_git_in_target helper)
  launcher.py        # run_solo() and run_team_in_repo()
  state.py           # load/save ROUND_STATE.json
  feature_extractor.py
agent-instructions/  # global CLAUDE.md canonical source (→ ~/.claude/CLAUDE.md)
scripts/             # setup.sh, lint.sh, test.sh, hooks
tests/               # pytest unit tests
```

Design artefacts for a feature live inside the **target repo**, not here:

```
<target_repo>/.agent-design/
  BASELINE.md        # codebase analysis (Stage 0)
  DESIGN.md          # design spec (Stage 1 → refined in Stage 2+)
  DISCUSSION.md      # shared discussion thread (all stages)
  DECISIONS.md       # resolved + deadlocked decisions
  feedback/          # human feedback per round
ROUND_STATE.json     # current workflow state
TASKS.md             # impl sprint task board (impl phase only)
```

---

## The 5-agent roster

| Role | Focus |
|---|---|
| **Eng Manager** | Facilitates; does not assign work or make technical decisions |
| **Architect** | System-level thinking; design ownership; calls out design drift |
| **Developer** | Pragmatic implementation; velocity; simplest-thing-that-works |
| **QA Engineer** | Observable behavior; acceptance criteria; outside-in perspective |
| **TDD Focussed Engineer** | Testability; dependency injection; exhaustive unit tests; goes first in impl |

> **Spelling:** The constant in `prompts.py` is `AGENT_TDD_FOCUSSED_ENGINEER`
> (double-S). Single-S = F821 undefined name.

---

## Workflow stages

```
Stage 0  Architect solo   → writes BASELINE.md          (claude --print)
Stage 1  Architect solo   → writes DESIGN.md, DISCUSSION.md, DECISIONS.md
Stage 2  Full team        → design review; refines DESIGN.md
Stage 3+ Full team        → incorporate human feedback rounds
Impl     Full team        → self-organising implementation sprint
```

Stages 0–1 use `claude --print` (non-interactive).
Stages 2+ and impl use `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude`.

---

## DISCUSSION.md protocol

Shared peer channel for all agents in team sessions. Every agent appends;
every agent reads. Format:

```markdown
## [Role Name]

<contribution, question, or response>
```

- Tag a specific teammate when responding directly: `@Developer: ...`
- EM reads this file to assess status — do not route everything via the EM

---

## TASKS.md — impl sprint task board

Created at the **target repo root** during the impl phase:

```markdown
| Task | Owner | Status |
|---|---|---|
| <description> | <role> | ⬜ unclaimed / 🔄 in progress / ✅ done / 🚫 blocked |
```

TDD Focussed Engineer goes first: claims and writes tests, must confirm
RED before Developer starts implementation.

---

## Key implementation details

### `_run_git_in_target` (in `agent_design/git_ops.py`)

Signature: `(cmd_args: list[str], cwd: Path, env: dict[str, str], error_msg: str) -> None`

Prepends `"git"` internally — callers **must not** include `"git"` as the
first element.

### `RoundState` serialisation

`dataclasses.asdict(state)` to serialise, `RoundState(**data)` to
deserialise. No `to_dict()` / `from_dict()`.

### State module API

```python
load_round_state(worktree_path: Path) -> RoundState
save_round_state(worktree_path: Path, state: RoundState) -> None
generate_slug(feature_request: str) -> str
```

---

## Development workflow

```bash
bash scripts/setup.sh        # first time or after a pull
source .venv/bin/activate
scripts/lint.sh               # ruff format + lint
.venv/bin/mypy agent_design/
.venv/bin/pytest tests/ -q
scripts/autofix.sh            # auto-fix ruff issues
```

CI runs on every PR: ruff format check, ruff lint, mypy, pytest.
