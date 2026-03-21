# agent-team-workflow

A multi-agent design workflow that produces software design documents through
structured debate between five specialized Claude Code agents. Run it against
any repository to get a collaborative design review before writing a line of code.

**What you get:** a `DESIGN.md` and `DECISIONS.md` per feature, committed as a
PR to your target repo, capturing not just the design but every disagreement
and how it was resolved.

---

## How it works

Five agents collaborate on every design:

| Agent | Role |
|---|---|
| **Eng Manager** | Facilitates — ensures everyone speaks, keeps debate fact-based, drives convergence |
| **Architect** | Owns the design — writes baseline analysis and initial draft, updates as consensus forms |
| **Developer** | Implementation focus — what's hard to build and why, API shape, edge cases |
| **QA Engineer** | Outside-in quality — acceptance criteria, boundary cases, observable contracts |
| **Code Quality Engineer** | Inside-out testability — DI, interface boundaries, unit test design |

Each design session runs in **stages**, separated by git checkpoints:

1. **Baseline** (automated) — Architect analyses your codebase, writes `BASELINE.md`
2. **Initial draft** (automated) — Architect writes `DESIGN.md` v1
3. **Design review** (interactive) — all five agents debate in your terminal via Claude Code agent teams
4. **Feedback rounds** (interactive) — agents incorporate your PR comments, repeat until approved

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11+ | CLI runtime |
| `claude` CLI | v2.1.32+ | Agent execution |
| `gh` CLI | any | PR creation and comment fetching |
| Anthropic API key | — | Powers claude sessions |

Check your claude version:
```bash
claude --version
```

Enable agent teams in `~/.claude/settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

---

## Installation

Clone this repo and install the CLI:

```bash
git clone https://github.com/MarksStuff/agent-team-workflow.git
cd agent-team-workflow
scripts/setup.sh
source .venv/bin/activate
```

`setup.sh` creates a virtual environment, installs dependencies, and sets up
git hooks that block direct commits to `main`.

Verify the install:
```bash
agent-design --version
```

Your Anthropic API key must be in `~/.anthropic_api_key`:
```bash
echo 'sk-ant-api03-...' > ~/.anthropic_api_key
chmod 600 ~/.anthropic_api_key
```

---

## Using it in your repository

### 1. Start a design session

Point `agent-design` at your target repository and describe the feature:

```bash
agent-design init ~/projects/your-repo "Brief description of the feature you want designed"
```

This runs automatically:
- Architect reads your codebase and writes `.agent-design/BASELINE.md`
- Architect writes `.agent-design/DESIGN.md` v1 based on the feature request

When done, review the baseline and initial draft:
```bash
cat ~/projects/your-repo/.agent-design/BASELINE.md
cat ~/projects/your-repo/.agent-design/DESIGN.md
```

### 2. Run the design review

```bash
agent-design next --repo-path ~/projects/your-repo
```

The CLI prints the Eng Manager's start message to paste, then opens an
interactive Claude Code session in your terminal. The five agents debate the
design live — you can watch, or jump in with `Shift+Down` to message any agent
directly.

When the team reaches convergence, the CLI:
- Checkpoints the session to git
- Copies `DESIGN.md` and `DECISIONS.md` to `docs/design/<feature-slug>/` in your repo
- Opens a PR against your repo's `main`

### 3. Review the PR

Review `DESIGN.md` and `DECISIONS.md` in the PR. Leave comments on anything
you want changed, clarified, or reconsidered.

### 4. Incorporate your feedback

```bash
agent-design next --repo-path ~/projects/your-repo
```

The CLI fetches your PR comments, writes them to `feedback/human-round-1.md`,
and launches another agent team session to incorporate them. The team reads your
feedback, debates, and updates `DESIGN.md`. The CLI pushes the changes to the PR.

Repeat steps 3 and 4 until you're happy with the design, then merge the PR.

### 5. Close the session

```bash
agent-design close --repo-path ~/projects/your-repo
```

Removes the `.agent-design/` worktree and orphan branch. The design artifacts
stay permanently in `docs/design/<feature-slug>/`.

---

## What ends up in your repository

After the session closes, your repo contains:

```
docs/design/
  your-feature-slug/
    DESIGN.md      ← the agreed design, refined through agent debate and your feedback
    DECISIONS.md   ← every disagreement that came up and how it was resolved
```

No other files are modified. The `.agent-design/` worktree is cleaned up.

---

## Other commands

```bash
# Check current session state
agent-design status --repo-path ~/projects/your-repo

# Add feedback directly without going through a PR
agent-design feedback "I want the API to support batch operations" \
  --repo-path ~/projects/your-repo

# List all git checkpoints
agent-design checkpoints --repo-path ~/projects/your-repo

# Roll back to a specific checkpoint and re-run from there
agent-design rollback chk-initial-draft --repo-path ~/projects/your-repo

# Diff current state against a checkpoint
agent-design diff chk-baseline --repo-path ~/projects/your-repo

# Re-attach to a session after closing your terminal
agent-design resume ~/projects/your-repo
```

---

## How checkpointing works

Session state lives on an **orphan branch** (`agent-design/<slug>`) in your
target repo, linked via a git worktree at `.agent-design/`. The orphan branch
shares no history with `main` — your git log stays clean. The main working
tree never changes branch.

Each stage ends with a `git commit + tag` inside the worktree:

```
chk-baseline        ← after codebase analysis
chk-initial-draft   ← after Architect's first draft
chk-review          ← after agent team design review
chk-feedback-1      ← after first round of your feedback
chk-feedback-2      ← etc.
```

If a session crashes or produces a bad design, roll back to any checkpoint and
re-run from there.

---

## Switching machines / API keys

The Anthropic API key is read from `~/.anthropic_api_key` on each machine. No
config changes needed — just ensure the right key is in that file on each
machine you work from.

---

## Dev

If you're working on the tool itself:

```bash
scripts/lint.sh      # ruff + mypy
scripts/test.sh      # pytest
scripts/autofix.sh   # auto-fix ruff issues
```

See [docs/DESIGN.md](docs/DESIGN.md) for the full architecture documentation.
