# Agent Team Workflow — Design Document

> **Status:** Draft — open questions marked 🔴, decisions made marked ✅

---

## Goals

- Get genuinely independent perspectives on a feature design before any code is written
- Make the agents' reasoning and disagreements visible in plain text (not a black box)
- Allow the human (Mark) to chime in at any point — ideally via GitHub PR comments
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
**Input:** Feature request, path to codebase
**Output:** `BASELINE.md`

The Architect reads the existing codebase and writes a shared baseline document
covering:
- Relevant directory structure and file layout
- Language, framework, and dependency conventions
- Dominant patterns (naming, error handling, async style, logging)
- Key existing components that the feature will interact with
- Anything surprising or non-obvious that a new contributor should know

All three specialist agents read `BASELINE.md` before doing any design work.
This ensures they share the same factual understanding of the codebase — they
can still disagree on design, but not on how the existing code works.

**Checkpoint:** `chk-round-0` — committed after `BASELINE.md` is written.

---

### Round 1 — Independent Design Drafts

**Who:** Architect, Developer, Tester (in parallel, isolated from each other)
**Input:** Feature request + `BASELINE.md`
**Output:** `drafts/architect.md`, `drafts/developer.md`, `drafts/tester.md`

Each agent writes their design draft independently. The Lead enforces isolation:
no agent sees another's draft until all three are complete.

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

The Lead then opens a GitHub PR with `DESIGN.md` and `DECISIONS.md` as the
only changed files.

**Checkpoint:** `chk-round-2` — committed before PR is opened.

---

### Round N — Human Feedback Loop

**Who:** Mark (in GitHub PR), then all agents
**Input:** Mark's PR comments + `DESIGN.md` + `DECISIONS.md`
**Output:** Updated `DESIGN.md`, updated `DECISIONS.md`, new `feedback/round-N-mark.md`

Mark reviews the PR in the GitHub UI and leaves comments. When ready, he
triggers the next round (by messaging the Lead, or via a manual trigger TBD).

The Lead fetches PR comments and writes them to `feedback/round-N-mark.md`.
Agents read Mark's feedback and respond to each point — agreeing, pushing back,
or proposing an alternative. The Lead updates `DESIGN.md` and `DECISIONS.md`
and pushes to the PR.

This loop repeats until Mark is satisfied and approves the PR.

**Checkpoint:** `chk-round-N` after each human feedback round.

---

## Checkpoint and Rollback

### Design Principle

**All state lives in files. Session memory is ephemeral and untrusted.**

Agent sessions are treated as stateless workers. They read inputs from files,
write outputs to files, and never rely on their conversation history surviving
a crash or restart. This makes every round independently replayable.

### State Files

```
agent-team-workflow/
  ROUND_STATE.json          ← current round, phase, completed steps
  BASELINE.md               ← Round 0 output
  drafts/
    architect.md            ← Round 1 independent draft
    developer.md
    tester.md
  DESIGN.md                 ← Current merged design doc
  DECISIONS.md              ← Full decision log
  feedback/
    round-2-mark.md         ← Human feedback per round
    round-3-mark.md
    ...
```

### `ROUND_STATE.json` Schema

```json
{
  "round": 2,
  "phase": "awaiting_human_feedback",
  "feature_request": "Add news-admin CLI re-extract command",
  "completed": ["baseline", "independent_drafts", "debate", "design_doc_v1"],
  "pr_url": "https://github.com/MarksStuff/news_reader/pull/132",
  "checkpoint_tag": "chk-round-2"
}
```

The Lead reads `ROUND_STATE.json` on every startup. If a checkpoint tag is
present, the Lead knows the session can be safely resumed from that state.

### Git Checkpoint Tags

Each round ends with a commit and tag before any inter-agent communication
that could cause side effects:

```bash
git add -A
git commit -m "checkpoint: round-0 baseline complete"
git tag chk-round-0
git push origin main --tags
```

### Rollback Procedure

```bash
# Roll back to round 1 state (e.g., to fix a bad agent prompt)
git checkout chk-round-1

# Fix the prompt or role definition
# (edit agent definitions in agents/)

# Start a new agent team session
# Lead reads ROUND_STATE.json → round=1, phase=debate → resumes from there
```

The new session reconstructs context entirely from files. The conversational
history of what led to the checkpoint is captured in `DECISIONS.md`, not in
session memory. If rolling back to fix a bad prompt, the new session will
produce different reasoning — which is the intent.

---

## Agent Role Definitions

> 🔴 **Open:** Full role prompts to be written. Starter sketch below.

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
- Enforce isolation in Round 1: do not share any agent's draft until all
  three drafts are complete.
- In DECISIONS.md, capture every disagreement — including ones that resolved
  easily. The decision log is for the human, not just the hard cases.
```

### Architect Agent Prompt (sketch)

```
You are the Architect agent. Your focus is system design, component boundaries,
data flow, and long-term maintainability.

In Round 0: Read the codebase. Write BASELINE.md — a factual summary of
patterns, structure, and conventions. Do not propose any design yet.

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

🔴 **Trigger mechanism for human feedback loop**
When Mark has finished reviewing the PR and is ready for the next round, how
does he signal this? Options:
- Message the Lead directly (via Telegram/OpenClaw)
- A specific GitHub label on the PR (`ready-for-round-3`)
- A CLI command (`./run-round.sh next`)

🔴 **How much of the codebase does Round 0 read?**
The full codebase for a large repo is expensive (tokens). Options:
- Architect reads only the files relevant to the feature
- A summary is pre-written by the human before kicking off the workflow
- The feature request includes explicit pointers to relevant files

🔴 **Isolation enforcement in Round 1**
How do we guarantee agents don't talk to each other before all drafts are done?
Lead agent prompt discipline alone may not be reliable. Consider explicit
file-locking or the Lead spawning agents sequentially (simpler but not parallel).

🔴 **Where does this workflow live relative to the target repo?**
Options:
- Subdir inside the target repo (e.g. `.agent-design/`)
- This repo as a sibling (`../agent-team-workflow/`)
- Fully separate, pointed at the target repo by config

🔴 **Full agent role prompts**
The sketches above need to be fully fleshed out and tested.

🔴 **Claude Code version and agent teams flag**
Requires Claude Code v2.1.32+, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
Need to document exact setup steps.

---

## Resolved Decisions

| Decision | Resolution |
|---|---|
| **State lives in files, not session memory** | Yes — sessions are stateless workers, files are source of truth |
| **Checkpoint mechanism** | Git commits + tags per round |
| **Rollback mechanism** | `git checkout <tag>` + new session reads files |
| **Three specialist agents** | Architect, Developer, Tester + Lead orchestrator |
| **Isolation in Round 1** | Agents write independently before any cross-agent communication |
| **Human feedback via GitHub** | PR with `DESIGN.md` + `DECISIONS.md`; Mark comments in GitHub UI |
