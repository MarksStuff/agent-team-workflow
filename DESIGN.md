# Agent Team Workflow — Design Document

> **Status:** Draft — open questions marked 🔴, decisions made marked ✅

---

## Goals

- Get genuinely independent perspectives on a feature design before any code is written
- Make the agents' reasoning and disagreements visible in plain text (not a black box)
- Allow the human (Mark) to chime in at any point — via GitHub PR comments
- Support checkpoint and rollback so a bad prompt or crash doesn't lose progress
- Produce two durable artifacts per feature: a **Design Doc** and a **Decision Log**

---

## The Four Agents

### Lead (Orchestrator)
Not a design contributor. Responsible for sequencing the workflow, enforcing
phase boundaries (especially isolation in Round 1), writing state to disk,
committing checkpoints, and routing human feedback back into the next round.

### Architect
Focuses on: system boundaries, data flow, component responsibilities, extension
points, consistency with existing patterns, long-term maintainability. In Round 0,
the Architect performs the codebase analysis and writes `BASELINE.md`.

### Developer
Focuses on: concrete implementation approach, API shape, error handling, edge
cases, what's actually straightforward vs. deceptively hard to build, naming.

### Tester / Test-First Engineer
Focuses on: testability of the proposed design, what the test surface looks like,
which behaviors are hard to test and why, missing contracts, observability hooks.
Approaches design from the outside-in — what does a caller need? What can break?

---

## Workflow Phases

### Round 0 — Codebase Baseline

**Who:** Architect (solo)
**Input:** Feature request, path to codebase, last analyzed commit (if updating)
**Output:** `BASELINE.md` (created or incrementally updated)

The Architect reads the existing codebase and writes a shared baseline document
covering:
- Relevant directory structure and file layout
- Language, framework, and dependency conventions
- Dominant patterns (naming, error handling, async style, logging)
- Key existing components that the feature will interact with
- Anything surprising or non-obvious that a new contributor should know

**Incremental updates:** `BASELINE.md` stores the last analyzed commit ID in its
header. On subsequent runs (e.g. after merging new PRs), the Architect checks
`git log <last-commit>..HEAD --name-only` to find what changed and only
re-analyzes those sections — rather than re-reading the entire codebase.

```markdown
<!-- baseline-commit: abc123def456 -->
<!-- baseline-updated: 2026-03-18 -->
# Baseline — news_reader
...
```

All three specialist agents read `BASELINE.md` before doing any design work.
This ensures they share the same factual understanding of the codebase.

**Checkpoint:** `chk-round-0` after `BASELINE.md` is written.

---

### Round 1 — Independent Design Drafts

**Who:** Architect, Developer, Tester (sequentially spawned, isolated)
**Input:** Feature request + `BASELINE.md`
**Output:** `drafts/architect.md`, `drafts/developer.md`, `drafts/tester.md`

The Lead spawns agents **one at a time** and does not give the next agent its
task until the previous one has finished writing its draft file. This guarantees
isolation without relying on prompt discipline alone.

Sequence:
1. Lead spawns Architect → waits for `drafts/architect.md` to appear on disk
2. Lead spawns Developer → waits for `drafts/developer.md` to appear on disk
3. Lead spawns Tester → waits for `drafts/tester.md` to appear on disk
4. All three drafts exist → checkpoint → proceed to Round 2

Each draft covers:
- Proposed design / approach
- Key decisions and why
- Concerns or risks
- What they'd want to know from the other agents

**Checkpoint:** `chk-round-1` after all three drafts are written.

---

### Round 2 — Debate and Synthesis

**Who:** All three agents + Lead
**Input:** All three drafts
**Output:** `DESIGN.md`, `DECISIONS.md`

The Lead surfaces disagreements between the drafts and routes them to the
relevant agents for direct debate. Agents can agree, push back, or propose
a compromise. The Lead captures every resolution in `DECISIONS.md` — including
disagreements that resolved easily, not just hard cases.

After debate converges, the Lead writes the merged `DESIGN.md`.

`DECISIONS.md` entry format:
```
## Decision: <short title>

**Disagreement:** <what the agents disagreed on>
**Architect:** ...
**Developer:** ...
**Tester:** ...
**Resolution:** <what was decided and why>
**Still open:** <anything left for human review>
```

The Lead opens a PR against the target repo's `main` branch containing only:
- `docs/design/<feature-slug>/DESIGN.md`
- `docs/design/<feature-slug>/DECISIONS.md`

**Checkpoint:** `chk-round-2` before the PR is opened.

---

### Round N — Human Feedback Loop

**Who:** Mark (in GitHub PR UI), then all agents
**Input:** Mark's PR comments + current `DESIGN.md` + `DECISIONS.md`
**Output:** Updated `DESIGN.md`, updated `DECISIONS.md`, `feedback/round-N-mark.md`

Mark reviews the PR and leaves comments. When ready:

```bash
agent-design next
```

The Lead fetches PR comments via `gh` and writes them to
`feedback/round-N-mark.md`. Agents read the feedback, respond to each point,
and the Lead updates the documents and pushes to the PR.

This repeats until Mark approves.

**Checkpoint:** `chk-round-N` after each human feedback round.

---

### Session Close

When the PR is merged, the Lead:
1. Updates `ROUND_STATE.json` with `"phase": "complete"`
2. Makes a final checkpoint commit
3. The CLI cleans up the git worktree and orphan branch from the target repo

The design artifacts persist permanently in the target repo at
`docs/design/<feature-slug>/`.

---

## CLI Tool

Implemented in **Python**. Installed from this repo. Invoked as `agent-design`.

```bash
# Start a new design session
agent-design init <repo-path> "<feature request>"

# Show current round, phase, and checkpoint state
agent-design status

# Trigger the next round (run after reviewing PR)
agent-design next

# List all checkpoints for the current session
agent-design checkpoints

# Roll back to a specific checkpoint and restart from there
agent-design rollback chk-round-1

# Diff the session state between two checkpoints
agent-design diff chk-round-1 chk-round-2

# Clean up worktree and orphan branch after session is complete
agent-design close
```

> 🔴 **Open:** Additional commands needed? e.g. `agent-design resume` to
> re-attach to an existing session from a fresh terminal.

---

## Checkpoint and Rollback

### Design Principle

**All state lives in files. Session memory is ephemeral and untrusted.**

Agent sessions are treated as stateless workers. They read inputs from files,
write outputs to files, and never rely on their conversation history surviving
a crash or restart. This makes every round independently replayable.

### Storage: Orphan Branch + Git Worktree

Session state is stored on an **orphan branch** in the target repo, named
`agent-design/<feature-slug>` (e.g. `agent-design/news-admin-cli`). Orphan
branches share no history with `main` — `git log main` never shows design
session commits.

A **git worktree** links the orphan branch to a `.agent-design/` directory
inside the target repo. This means:
- The main working tree stays on `main` at all times
- Agents read/write files in `.agent-design/` which commits to the orphan branch
- No branch switching required during a session

`.agent-design/` is listed in the target repo's `.gitignore` so it never
appears as untracked/staged content in the main working tree.

```
news_reader/                          ← main worktree (branch: main)
  .gitignore                          ← includes: .agent-design
  src/
  ...
  .agent-design/                      ← linked worktree (branch: agent-design/news-admin-cli)
    ROUND_STATE.json
    BASELINE.md
    drafts/
      architect.md
      developer.md
      tester.md
    DESIGN.md
    DECISIONS.md
    feedback/
      round-2-mark.md
```

### Setup (done by `agent-design init`)

```bash
# 1. Create the orphan branch
git checkout --orphan agent-design/news-admin-cli
git rm -rf .
git commit --allow-empty -m "init: agent design session — news-admin-cli"
git checkout main

# 2. Add as a linked worktree
git worktree add .agent-design agent-design/news-admin-cli

# 3. Add to .gitignore if not already present
echo ".agent-design" >> .gitignore
```

### Checkpoints (done by the Lead agent at end of each round)

All commits and tags happen inside `.agent-design/` (i.e. on the orphan branch):

```bash
cd .agent-design
git add -A
git commit -m "checkpoint: round-1 independent drafts complete"
git tag chk-round-1
git push origin agent-design/news-admin-cli --tags
```

### Rollback

```bash
# Via CLI:
agent-design rollback chk-round-1

# Under the hood:
cd .agent-design
git checkout chk-round-1   # detached HEAD at that checkpoint
# (fix the bad prompt or agent definition)
agent-design next           # Lead reads ROUND_STATE.json → resumes from round 1
```

### Session Close (done by `agent-design close`)

```bash
# Remove the worktree
git worktree remove .agent-design

# Optionally delete the orphan branch (history no longer needed)
git branch -D agent-design/news-admin-cli
git push origin --delete agent-design/news-admin-cli
```

Design artifacts are already in `docs/design/<feature-slug>/` via the merged
PR, so no history is lost.

---

### `ROUND_STATE.json` Schema

```json
{
  "feature_slug": "news-admin-cli",
  "feature_request": "Build a news-admin CLI with re-extract and dead-letter commands",
  "target_repo": "/Users/mstriebeck/workspace/news_reader",
  "round": 2,
  "phase": "awaiting_human_feedback",
  "baseline_commit": "abc123def456",
  "completed": ["baseline", "independent_drafts", "debate", "design_doc_v1"],
  "pr_url": "https://github.com/MarksStuff/news_reader/pull/132",
  "checkpoint_tag": "chk-round-2"
}
```

---

## Design Artifacts in the Target Repo

Approved design docs live permanently in the target repo under
`docs/design/<feature-slug>/`, one subdirectory per feature. This prevents
co-mingling across features and makes designs discoverable alongside the code.

```
docs/design/
  news-admin-cli/
    DESIGN.md
    DECISIONS.md
  embedder-daemon/           ← future feature, fully isolated
    DESIGN.md
    DECISIONS.md
```

The Lead creates this directory and opens the PR when Round 2 completes.

---

## Agent Role Definitions

> 🔴 **Open:** Full role prompts need to be fleshed out and tested against a
> real feature. Sketches below capture intent only.

### Lead Agent Prompt (sketch)

```
You are the Lead agent in a multi-agent design workflow. You orchestrate —
you do not contribute design opinions.

On startup:
1. Read ROUND_STATE.json to determine the current round and phase.
2. Proceed with the next uncompleted step.

Rules:
- Write every output to a file before sharing it with other agents.
- Update ROUND_STATE.json at the start and end of every phase.
- Commit and tag at the end of every round. Do not proceed without checkpointing.
- In Round 1: spawn agents one at a time. Do not spawn the next agent until
  the current one's draft file exists on disk. Never show an agent another
  agent's draft until all three are complete.
- Capture every disagreement in DECISIONS.md — not just the hard ones.
```

### Architect Agent Prompt (sketch)

```
You are the Architect agent. You focus on system boundaries, data flow,
component responsibilities, and long-term maintainability.

Round 0: Read the codebase. If BASELINE.md already exists, check
baseline-commit and use `git log <commit>..HEAD --name-only` to find changed
files. Only re-analyze what changed. Write/update BASELINE.md with the current
commit ID in the header.

Round 1: Read BASELINE.md and the feature request. Write your design draft to
drafts/architect.md. Do not read other agents' drafts.

Round 2: Read all drafts. Engage directly with disagreements. Be specific about
why you agree or disagree. Do not be diplomatic at the cost of correctness.
```

### Developer Agent Prompt (sketch)

```
You are the Developer agent. You focus on what the implementation actually
looks like — what's easy, what's hard, edge cases, naming, API shape.

Round 1: Read BASELINE.md and the feature request. Write your draft to
drafts/developer.md. Do not read other agents' drafts.

Round 2: If something looks clean in a design but will be painful to implement,
say so and explain concretely why. Vague concerns don't help anyone.
```

### Tester Agent Prompt (sketch)

```
You are the Tester agent. You approach design from the outside-in. You focus
on testability, observable contracts, and failure modes.

Round 1: Read BASELINE.md and the feature request. Write your draft to
drafts/tester.md. For every proposed interface, ask: how do I test this?
What inputs are unspecified? What can a caller do wrong?

Round 2: Call out design choices that make testing hard. Untestable design
is a design flaw, not a testing problem.
```

---

## Open Questions

🔴 **Full agent role prompts**
Sketches above need fleshing out and live testing.

🔴 **`agent-design resume` command**
If the terminal is closed mid-session, how does the user re-attach?
Likely: `agent-design resume <repo-path>` reads `ROUND_STATE.json` from the
existing worktree and restarts the agent team from the last checkpoint.

🔴 **Claude Code setup**
Requires Claude Code v2.1.32+, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
Document exact invocation from the Python CLI.

🔴 **Handling the case where `.agent-design` worktree already exists**
If a session crashes mid-init, `agent-design init` needs to detect and recover
rather than failing on "worktree already exists".

---

## Resolved Decisions

| Decision | Resolution |
|---|---|
| **State lives in files, not session memory** | ✅ Sessions are stateless workers; files are source of truth |
| **CLI language** | ✅ Python |
| **Checkpoint mechanism** | ✅ Orphan branch in target repo + git worktree at `.agent-design/`; commit + tag per round |
| **Why orphan branch + worktree** | ✅ No history pollution on `main`; no separate repo; main working tree stays on `main`; full git tooling; auto-cleaned on `agent-design close` |
| **Rollback mechanism** | ✅ `agent-design rollback <tag>` → `git checkout <tag>` inside worktree → new session reads files |
| **Three specialist agents** | ✅ Architect, Developer, Tester + Lead orchestrator |
| **Isolation in Round 1** | ✅ Sequential spawning — Lead waits for each draft file before spawning next agent |
| **Human feedback trigger** | ✅ `agent-design next` CLI command |
| **Baseline updates** | ✅ Incremental — `BASELINE.md` stores last analyzed commit; Architect diffs git history to find changed files only |
| **Working files location** | ✅ `.agent-design/` as linked git worktree on orphan branch; listed in target repo's `.gitignore` |
| **Human feedback via GitHub** | ✅ PR against target repo with `docs/design/<feature-slug>/DESIGN.md` + `DECISIONS.md` |
| **Design artifact naming** | ✅ `docs/design/<feature-slug>/` subdirectory per feature; no co-mingling across features |
