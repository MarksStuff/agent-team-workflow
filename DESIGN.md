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

## The Three Agents

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
header. On subsequent runs (e.g. after merging new PRs), the Architect diffs
`git log <last-commit>..HEAD --name-only` to find changed files and only
re-analyzes those sections — rather than re-reading the entire codebase.

```markdown
<!-- baseline-commit: abc123def456 -->
<!-- baseline-updated: 2026-03-18 -->
# Baseline — news_reader
...
```

All three specialist agents read `BASELINE.md` before doing any design work.
This ensures they share the same factual understanding of the codebase — they
can still disagree on design, but not on how the existing code works.

**Checkpoint:** `chk-round-0` — committed after `BASELINE.md` is written.

---

### Round 1 — Independent Design Drafts

**Who:** Architect, Developer, Tester (sequentially spawned, isolated)
**Input:** Feature request + `BASELINE.md`
**Output:** `drafts/architect.md`, `drafts/developer.md`, `drafts/tester.md`

Each agent writes their design draft independently. The Lead spawns agents one
at a time and does not give an agent the task until the previous one has finished
writing its draft. This guarantees isolation without relying on prompt discipline.

Sequence:
1. Lead spawns Architect → waits for `drafts/architect.md` to appear
2. Lead spawns Developer → waits for `drafts/developer.md` to appear
3. Lead spawns Tester → waits for `drafts/tester.md` to appear
4. All three drafts exist → proceed to Round 2

Each draft should cover:
- Proposed design / approach
- Key decisions and why
- Concerns or risks they see
- What they'd want to know from the other agents

**Checkpoint:** `chk-round-1` — committed after all three drafts are written.

---

### Round 2 — Debate and Synthesis

**Who:** All three agents + Lead
**Input:** All three drafts
**Output:** `DESIGN.md` (merged design), `DECISIONS.md` (decision log)

The Lead surfaces disagreements between the drafts and routes them to the
relevant agents for direct debate. Agents can agree, push back, or propose
a compromise. The Lead captures each resolution in `DECISIONS.md`.

After debate converges, the Lead writes `DESIGN.md` — the merged design
incorporating the resolved positions.

`DECISIONS.md` format:
```
## Decision: <short title>

**Disagreement:** <what the agents disagreed on>
**Architect position:** ...
**Developer position:** ...
**Tester position:** ...
**Resolution:** <what was decided and why>
**Open:** <anything left unresolved for human review>
```

The Lead then opens a GitHub PR (in the **target repo**, not this one) with
`DESIGN.md` and `DECISIONS.md` as the only changed files.

**Checkpoint:** `chk-round-2` — committed before PR is opened.

---

### Round N — Human Feedback Loop

**Who:** Mark (in GitHub PR), then all agents
**Input:** Mark's PR comments + `DESIGN.md` + `DECISIONS.md`
**Output:** Updated `DESIGN.md`, updated `DECISIONS.md`, `feedback/round-N-mark.md`

Mark reviews the PR in the GitHub UI and leaves comments. When ready, he
runs the CLI trigger to start the next round:

```bash
agent-design next
```

The Lead fetches PR comments via `gh` and writes them to
`feedback/round-N-mark.md`. Agents read Mark's feedback and respond to each
point — agreeing, pushing back, or proposing an alternative. The Lead updates
`DESIGN.md` and `DECISIONS.md` and pushes to the PR.

This loop repeats until Mark is satisfied and approves the PR.

**Checkpoint:** `chk-round-N` after each human feedback round.

---

## CLI Tool

The workflow is controlled via a CLI tool (`agent-design`) that lives in this
repo. It handles round triggering, status display, checkpoint listing, and rollback.

```bash
# Start a new design session for a feature
agent-design init <repo-path> "<feature request>"

# Show current state of the active session
agent-design status

# Trigger the next round (e.g. after reviewing PR comments)
agent-design next

# List available checkpoints
agent-design checkpoints

# Roll back to a specific checkpoint and restart from there
agent-design rollback chk-round-1

# Show diff between two checkpoints
agent-design diff chk-round-1 chk-round-2
```

`agent-design` reads `ROUND_STATE.json` from the `.agent-design/` directory in
the target repo to determine the current session state.

> 🔴 **Open:** Implementation language for the CLI. Options: bash (simple, no deps),
> Python (richer, easier to maintain), or Swift (consistent with news_reader stack).

---

## Checkpoint and Rollback

### Design Principle

**All state lives in files. Session memory is ephemeral and untrusted.**

Agent sessions are treated as stateless workers. They read inputs from files,
write outputs to files, and never rely on their conversation history surviving
a crash or restart. This makes every round independently replayable.

### File Location — `.agent-design/` in the Target Repo

Design session files live inside the target repo at `.agent-design/`, which is:
- Added to the target repo's `.gitignore` (never committed to the target repo)
- Initialized as its own independent git repo for checkpoint tracking
- Pushed to a per-session branch on this repo (`agent-team-workflow`) or a
  dedicated private repo

This keeps the target repo clean while still giving full git checkpoint/rollback
capability for the design session.

```
<target-repo>/
  .gitignore                  ← includes .agent-design/
  .agent-design/              ← its own git repo, NOT tracked by target repo
    .git/
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
      round-3-mark.md
```

### `ROUND_STATE.json` Schema

```json
{
  "round": 2,
  "phase": "awaiting_human_feedback",
  "feature_request": "Add news-admin CLI re-extract command",
  "target_repo": "/Users/mstriebeck/workspace/news_reader",
  "baseline_commit": "abc123def456",
  "completed": ["baseline", "independent_drafts", "debate", "design_doc_v1"],
  "pr_url": "https://github.com/MarksStuff/news_reader/pull/132",
  "checkpoint_tag": "chk-round-2"
}
```

The Lead reads `ROUND_STATE.json` on every startup. If a checkpoint tag is
present, it knows the session can be safely resumed from that state.

### Git Checkpoint Tags

Each round ends with a commit and tag inside `.agent-design/`:

```bash
git add -A
git commit -m "checkpoint: round-0 baseline complete"
git tag chk-round-0
git push origin main --tags
```

### Rollback Procedure

```bash
# Via CLI:
agent-design rollback chk-round-1

# What this does under the hood:
cd <target-repo>/.agent-design
git checkout chk-round-1

# Fix the bad prompt or agent definition in the agent-team-workflow repo
# Then start a new session:
agent-design next
# Lead reads ROUND_STATE.json → sees round=1 → resumes from independent drafts
```

The new session reconstructs context entirely from files. The conversational
history of what led to the checkpoint is captured in `DECISIONS.md`, not in
session memory.

---

## Agent Role Definitions

> 🔴 **Open:** Full role prompts to be written. Starter sketches below.

### Lead Agent Prompt (sketch)

```
You are the Lead agent in a multi-agent design workflow. Your job is to
orchestrate — not to contribute design opinions of your own.

On startup:
1. Read ROUND_STATE.json to determine current round and phase.
2. Read BASELINE.md if it exists.
3. Proceed with the next uncompleted phase.

Rules:
- Write every output to a file before sharing it with other agents.
- Update ROUND_STATE.json at the start and end of every phase.
- Commit and tag at the end of every round before proceeding.
- In Round 1, spawn agents sequentially — do not spawn the next agent
  until the current one has written its draft file. Do not show any agent
  another agent's draft until all three are complete.
- In DECISIONS.md, capture every disagreement — including ones that resolved
  easily. The decision log is for the human, not just the hard cases.
```

### Architect Agent Prompt (sketch)

```
You are the Architect agent. Your focus is system design, component boundaries,
data flow, and long-term maintainability.

In Round 0: Read the relevant parts of the codebase. If BASELINE.md already
exists, check the baseline-commit header and use `git log <commit>..HEAD` to
find what changed. Only re-analyze changed sections. Write (or update)
BASELINE.md with the current commit ID in the header.

In Round 1: Read BASELINE.md and the feature request. Write your design draft
to drafts/architect.md. Do not read other agents' drafts.

In Round 2: You will see the other agents' drafts. Engage directly with
disagreements. Push back if you think a decision is wrong. Be specific.
```

### Developer Agent Prompt (sketch)

```
You are the Developer agent. Your focus is concrete implementation — what's
easy, what's hard, what the code will actually look like, edge cases.

In Round 1: Read BASELINE.md and the feature request. Write your design draft
to drafts/developer.md. Do not read other agents' drafts.

In Round 2: Engage with disagreements. If something looks clean on paper but
will be a mess to implement, say so clearly and explain why.
```

### Tester Agent Prompt (sketch)

```
You are the Tester agent. You approach design from the outside-in. Your focus
is testability, contracts, observability, and what can go wrong at the boundaries.

In Round 1: Read BASELINE.md and the feature request. Write your design draft
to drafts/tester.md. Ask: how would I test this? What behaviors are unspecified?
What can a caller do wrong?

In Round 2: Surface design choices that will make testing hard. If something
is untestable as proposed, that's a design flaw — say so.
```

---

## Open Questions

🔴 **CLI implementation language**
Options: bash (simple, no deps), Python (richer), Swift (consistent with
news_reader). Recommendation: bash for v1 (fewest moving parts), migrate later
if it grows complex.

🔴 **Where does `.agent-design/` push its git checkpoints?**
Options:
- A branch per session on this repo (`agent-team-workflow`)
- A dedicated private repo per target project
- Local-only git (no remote — simpler, but no off-machine backup)

🔴 **Full agent role prompts**
The sketches above need to be fully fleshed out and tested against a real feature.

🔴 **Claude Code version and agent teams flag**
Requires Claude Code v2.1.32+, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
Need to document exact setup and invocation.

🔴 **What gets included in the PR to the target repo?**
The PR contains `DESIGN.md` + `DECISIONS.md`. But should these live permanently
in the target repo (e.g. `docs/design/<feature>.md`) or just in `.agent-design/`?
Keeping them in the target repo makes them discoverable; keeping them in
`.agent-design/` keeps the target repo cleaner.

---

## Resolved Decisions

| Decision | Resolution |
|---|---|
| **State lives in files, not session memory** | ✅ Sessions are stateless workers, files are source of truth |
| **Checkpoint mechanism** | ✅ Git commits + tags inside `.agent-design/` |
| **Rollback mechanism** | ✅ `agent-design rollback <tag>` → `git checkout` + new session |
| **Three specialist agents** | ✅ Architect, Developer, Tester + Lead orchestrator |
| **Isolation in Round 1** | ✅ Sequential spawning — Lead spawns one agent at a time, waits for draft file before spawning next |
| **Human feedback trigger** | ✅ `agent-design next` CLI command |
| **Baseline updates** | ✅ Incremental — BASELINE.md stores last analyzed commit; Architect diffs git history to find changed files |
| **Working files location** | ✅ `.agent-design/` inside target repo, in target repo's `.gitignore`, own git repo for checkpoints |
| **Human feedback via GitHub** | ✅ PR with `DESIGN.md` + `DECISIONS.md`; Mark comments in GitHub UI |
