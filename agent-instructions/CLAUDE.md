# CLAUDE.md — Global Master Instructions for agent-team-workflow

> **This is the canonical source.** The `CLAUDE.md` at the repo root is a symlink to this file.
> Edit *this* file, not the symlink.
>
> This file is automatically loaded by Claude Code and all agent teammates
> whenever a session is launched from this repository.

---

## What this repo is

`agent-team-workflow` provides the `agent-design` CLI — a tool that runs
structured, multi-agent software design reviews and implementation sprints
using Claude Code's native agent teams. Each workflow stage runs as one
`claude` session; the CLI manages git state, design artefacts, and PR
lifecycle between sessions.

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
agent-instructions/  # ← you are here; canonical agent guidance
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

> **Spelling note:** The constant in `prompts.py` is `AGENT_TDD_FOCUSSED_ENGINEER`
> (double-S). Any reference to the single-S spelling is an F821 undefined name.

---

## Workflow stages

```
Stage 0  Architect solo   → writes BASELINE.md
Stage 1  Architect solo   → writes DESIGN.md, DISCUSSION.md, DECISIONS.md
Stage 2  Full team        → design review; refines DESIGN.md
Stage 3+ Full team        → incorporate human feedback rounds
Impl     Full team        → self-organising implementation sprint
```

Stages 0 and 1 run with `claude --print` (non-interactive).
Stages 2+ and impl run with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude`
(interactive, agent team mode).

---

## DISCUSSION.md protocol

`DISCUSSION.md` is the shared peer-to-peer channel for all agents in team
sessions. **Every agent appends to it; every agent reads it.**

Format for entries:

```markdown
## [Role Name]

<your contribution, question, or response>
```

Rules:
- Respond to what teammates wrote, not just to your own position.
- Tag the specific teammate when responding directly: `@Developer: ...`
- EM reads this file to assess status — do not duplicate information by
  DMing the EM separately.

---

## TASKS.md — impl sprint task board

Created at the **target repo root** during the impl phase. Format:

```markdown
| Task | Owner | Status |
|---|---|---|
| <description> | <role> | ⬜ unclaimed / 🔄 in progress / ✅ done / 🚫 blocked |
```

- Agents self-select tasks based on their expertise — nobody assigns work
- TDD Focussed Engineer claims and writes tests first; marks them 🔄 until RED
- Developer starts implementation only after TDD Engineer confirms tests are RED
- A task is ✅ only when all relevant tests pass

---

## Implementation sprint phases

### Phase 1 — Sprint Planning
Each agent reads `.agent-design/DESIGN.md` and claims tasks in `TASKS.md`.
Planning ends when every section of the design has at least one claimed task.

### Phase 2 — Implementation
Team works autonomously. EM's only role: surface unclaimed or stalled tasks.

### Phase 3 — Final Review
Triggered when every `TASKS.md` row is ✅.
- Architect walks through the design spec section by section
- QA verifies observable behavior and runbook checks
- Sprint is DONE only when both **Architect: LGTM** and **QA: LGTM** are given

---

## Non-negotiable rules

1. **Never push directly to `main`** — always branch + PR; the human merges.
2. **Commits as Roxy** — all commits in this workflow use:
   - `git config user.name "Roxy"`
   - `git config user.email "269813048+roxy-mstriebeck@users.noreply.github.com"`
3. **TDD first** — tests are written before implementation code, and must
   be RED before the Developer begins.
4. **Dependency injection is non-negotiable** — no component instantiates
   its own external dependencies; everything is passed in.
5. **Full file overwrite for multi-line changes** — the `edit` tool has
   caused silent failures on large diffs; prefer overwriting the full file.
6. **No `--no-verify` bypass in agent sessions** — hooks exist for a reason;
   fix the underlying issue instead.

---

## Key implementation details

### `_run_git_in_target` (in `agent_design/git_ops.py`)

```python
def _run_git_in_target(
    cmd_args: list[str],
    cwd: Path,
    env: dict[str, str],
    error_msg: str,
) -> None: ...
```

- Prepends `"git"` internally — callers **must not** include `"git"` as the
  first element.
- Example: `_run_git_in_target(["commit", "-m", "msg"], cwd, env, "commit failed")`

### `RoundState` serialisation

Use `dataclasses.asdict(state)` to serialise and `RoundState(**data)` to
deserialise. There is no `to_dict()` / `from_dict()` — do not add them.

### State module API

```python
load_round_state(worktree_path: Path) -> RoundState
save_round_state(worktree_path: Path, state: RoundState) -> None
generate_slug(feature_request: str) -> str
```

---

## Development workflow

```bash
# First time or after a pull:
bash scripts/setup.sh

# Activate the venv:
source .venv/bin/activate

# Lint, type-check, test:
scripts/lint.sh
.venv/bin/mypy agent_design/
.venv/bin/pytest tests/ -q

# Auto-fix ruff issues:
scripts/autofix.sh
```

CI runs on every PR: ruff format check, ruff lint, mypy, pytest.
