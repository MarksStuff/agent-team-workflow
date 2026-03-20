# agent-team-workflow

A multi-agent design workflow that produces software design documents through
structured debate between five specialized Claude Code agents. Outputs a
`DESIGN.md` and `DECISIONS.md` per feature, committed as a PR to your target repo.

## How it works

Five agents collaborate on every design:

| Agent | Role |
|---|---|
| **Eng Manager** | Facilitates discussion — ensures everyone speaks, keeps debate fact-based, drives convergence |
| **Architect** | Owns the design — writes the initial draft, updates it as consensus forms |
| **Developer** | Implementation focus — what's hard to build and why, API shape, edge cases |
| **QA Engineer** | Outside-in quality — acceptance criteria, boundary cases, observable contracts |
| **Code Quality Engineer** | Inside-out testability — DI, interface boundaries, unit test design |

All state lives in files. Sessions are stateless — crash and resume any time.

## Setup

```bash
# One-time per machine
scripts/setup.sh
source .venv/bin/activate
```

Requires:
- Python 3.11+
- `claude` CLI installed and on PATH
- `~/.anthropic_api_key` with your Anthropic API key
- `gh` CLI for PR creation

## Usage

```bash
# Start a new design session
agent-design init /path/to/repo "describe the feature you want designed"

# Check current state
agent-design status

# Run the next discussion round (or after leaving PR feedback)
agent-design next

# Add your own feedback mid-discussion
agent-design feedback "I think we should also support batch re-extraction"

# Checkpoint history
agent-design checkpoints

# Roll back to a specific checkpoint
agent-design rollback chk-phase-1

# Diff against a checkpoint
agent-design diff chk-phase-1

# Re-attach to an existing session from a fresh terminal
agent-design resume /path/to/repo

# Clean up after the PR is merged
agent-design close
```

## What gets produced

After `agent-design init`:
- `.agent-design/BASELINE.md` — codebase analysis
- `.agent-design/DESIGN.md` — initial design draft (Architect)

After `agent-design next` (discussion):
- `.agent-design/DISCUSSION.md` — full agent conversation thread
- `.agent-design/DECISIONS.md` — resolved disagreements
- Updated `DESIGN.md`

After convergence — a PR against your target repo with:
- `docs/design/<feature-slug>/DESIGN.md`
- `docs/design/<feature-slug>/DECISIONS.md`

## Checkpointing

State is stored on an orphan branch `agent-design/<feature-slug>` in your
target repo via a git worktree at `.agent-design/`. The main branch is never
touched. Clean up with `agent-design close` after the PR merges.

## Dev

```bash
scripts/lint.sh      # ruff + mypy
scripts/test.sh      # pytest
scripts/autofix.sh   # auto-fix ruff issues
```

See [DESIGN.md](DESIGN.md) for full architecture documentation.
