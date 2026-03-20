# Agent Team Workflow — Design Document

> **Status:** v4 — Final design. All major decisions resolved.

---

## Goals

- Get genuinely independent perspectives on a feature design before any code is written
- Replicate the dynamics of a real engineering design review — not a pipeline dressed up as collaboration
- Make agents' reasoning, disagreements, and resolutions visible in plain text
- Allow the human (Mark) to chime in at any point, naturally
- Support checkpoint and rollback so a crash or bad prompt doesn't lose progress
- Produce two durable artifacts per feature: a **Design Doc** and a **Decision Log**

---

## Core Design Principle

**Structure lives at the boundaries. The discussion is free-form.**

The Eng Manager manages phase transitions, checkpoints, and facilitation. Inside the
discussion itself, agents speak when they have something to say, respond to each other
directly, and the conversation ends when there's nothing left to disagree about —
not because a round counter hit a predetermined limit.

**All state lives in files. Session memory is ephemeral and untrusted.**

Agent sessions are stateless workers. They read inputs from files, write outputs to
files, and never rely on their conversation history surviving a crash or restart. Every
phase is independently replayable.

---

## The Five Agents

### Eng Manager (Facilitator & Orchestrator)

The Eng Manager is the team lead. It does **not** own the design — the Architect does.
The Eng Manager's job is to make the design process work well.

**Facilitation responsibilities:**
- Ensures every agent contributes — explicitly calls on silent agents:
  *"Developer, you haven't weighed in on the caching strategy — what's your view?"*
- Keeps discussion grounded in facts and data, not opinions. When an agent says
  *"we should never use X"* or *"X is always a mistake"*, the Eng Manager pushes back:
  *"Can you ground that in a specific concern about this design? What breaks concretely?"*
- Facilitates disagreements rather than resolving them programmatically:
  *"Architect and Code Quality Engineer disagree on interface placement. Architect —
  what would it take for you to accept the alternative approach?"*
- Recognizes convergence: when no new substantive objections have been raised,
  the Eng Manager asks the team if they're ready to finalize the design.
- Can express its own opinions, but always leads with facilitation over advocacy.

**Orchestration responsibilities:**
- Manages phase transitions, checkpoint commits, and `ROUND_STATE.json`
- Reads Mark's GitHub PR feedback and surfaces it to the team
- Opens and updates the PR in the target repo
- Manages the `agent-design` CLI interface

---

### Architect (Design Owner)

The Architect is the primary owner of the design. This is the "lead engineer" role
from a real engineering team.

**Responsibilities:**
- Understands the problem space — crisp requirements and non-requirements before
  writing anything
- Performs the initial codebase analysis and writes `BASELINE.md`
- Writes the **first draft of `DESIGN.md`** based on the feature request and baseline
- Participates actively in the design discussion, focused on system boundaries, data
  flow, component responsibilities, extension points, and long-term maintainability
- Updates `DESIGN.md` iteratively as consensus forms during discussion

---

### Developer (Implementation Focus)

**Responsibilities:**
- Focuses on the practicalities of building the feature: API shape, error handling,
  edge cases, naming, what's straightforward vs. deceptively hard to implement
- Calls out design choices that look clean on paper but will be painful to build —
  with specific, concrete reasons
- Pushes for pragmatic, efficient solutions that fit the existing codebase patterns

---

### QA Engineer (Outside-In Quality)

**Responsibilities:**
- Approaches the design from the outside-in: does this design actually satisfy the
  requirements? What happens at the boundary cases? How do we verify the end-to-end
  flow works?
- Defines acceptance criteria and integration test scenarios from the spec
- Identifies under-specified behaviors (what happens when X fails? what are the
  observable contracts?)
- Focuses on what a user or external caller can observe and test — not on
  the internal implementation

---

### Code Quality Engineer (Inside-Out Testability)

**Responsibilities:**
- Focuses on making the code itself unit-testable: dependency injection, interface
  design, mock boundaries, and avoiding hidden dependencies
- Every complex object must have an abstract protocol/interface that can be
  implemented as both a production version and a mock — calls this out when missing
- Pushes back on designs where logic is tightly coupled and untestable by construction
- Complements the QA Engineer: QA asks *"can we test the behavior?"*, Code Quality
  asks *"can we test the units?"*

---

## Workflow Phases

### Phase 0 — Session Init & Codebase Baseline

**Who:** `agent-design init` → Architect (solo)
**Input:** Feature request, path to target repo
**Output:** Initialized worktree, `ROUND_STATE.json`, `BASELINE.md`

`agent-design init <repo-path> "<feature request>"` sets up the git worktree and
orphan branch (see Checkpoint section), then spawns the Architect to analyze the
codebase.

The Architect reads the existing codebase and writes `BASELINE.md`, covering:
- Relevant directory structure and key files
- Language, framework, and dependency conventions
- Dominant patterns (naming, error handling, async style, logging)
- Existing components the feature will interact with
- Anything non-obvious a new contributor should know

**Incremental updates:** `BASELINE.md` stores the last analyzed commit ID in its
header. On subsequent runs (e.g. after new PRs have been merged), the Architect
checks `git log <last-commit>..HEAD --name-only` and only re-analyzes changed
sections.

```markdown
<!-- baseline-commit: abc123def456 -->
<!-- baseline-updated: 2026-03-20 -->
# Baseline — news_reader
...
```

All agents read `BASELINE.md` before doing any design work.

**Checkpoint:** `chk-phase-0` after `BASELINE.md` is written.

---

### Phase 1 — Initial Design Draft

**Who:** Architect (solo)
**Input:** Feature request + `BASELINE.md`
**Output:** First draft of `DESIGN.md`, empty `DECISIONS.md`

The Architect writes the initial design document. Before writing, it sharpens
the requirements: what is explicitly in scope, what is explicitly out of scope,
and what assumptions are being made. These become the opening section of `DESIGN.md`.

`DESIGN.md` first draft covers at minimum:
- Feature scope: requirements and non-requirements
- Proposed approach and architecture
- Key components and their responsibilities
- Data flow and interface contracts
- Open questions the Architect wants the team to weigh in on

**Checkpoint:** `chk-phase-1` after `DESIGN.md` v1 is written.

---

### Phase 2 — Design Review (Open Discussion)

**Who:** Eng Manager (facilitating) + Architect, Developer, QA Engineer, Code Quality Engineer
**Input:** `DESIGN.md` v1, `BASELINE.md`
**Output:** Iteratively refined `DESIGN.md`, populated `DECISIONS.md`, `DISCUSSION.md`

This is the design review meeting. All agents read the current `DESIGN.md` and the
shared `DISCUSSION.md` thread, then contribute freely.

#### The Shared Discussion Thread

All agents communicate through a single **`DISCUSSION.md`** file — a chronological
thread that all agents can read and append to. There is no separate per-agent draft
or structured review template. Agents respond to the design, to each other's
specific points, and raise new concerns as they arise.

Each entry is tagged with the contributing agent:

```markdown
## [Architect]
The proposed queue interface assumes single-consumer semantics, which should
hold for now. However, if we ever need parallel consumers we'll have a problem
with the current ack strategy...

## [Developer]
Agree on the interface, but `MessageQueue.consume()` returning `AsyncStream`
will be painful to mock in tests. Can we use a callback/closure instead?

## [Code Quality Engineer]
Developer raises a valid point. More specifically: `AsyncStream` with custom
continuation is hard to inject in unit tests because the stream lifecycle is
opaque. A delegate or closure-based contract would let us inject a fake
source trivially. I'd push for that.

## [Eng Manager]
QA Engineer — you've been quiet on the queue design. From an acceptance
testing perspective, does single-consumer semantics give you what you need
to write meaningful integration tests?
```

#### Eng Manager's Role in the Discussion

The Eng Manager reads the thread continuously and intervenes to:
1. **Call on silent agents** — if any agent hasn't spoken on a significant topic,
   the Eng Manager explicitly asks for their view
2. **Redirect opinion to fact** — when an agent asserts a preference without
   grounding it in a concrete concern, the Eng Manager asks them to be specific
3. **Name disagreements** — when two agents disagree, the Eng Manager surfaces
   the disagreement clearly and asks each side to state what evidence or
   constraints would change their mind
4. **Drive to resolution** — disagreements that are circling should be broken
   by asking: *"What's the minimum we need to decide now vs. what can be
   deferred to implementation?"*
5. **Update artifacts** — as consensus forms, the Eng Manager (or Architect,
   for design content) updates `DESIGN.md` and captures each resolution in
   `DECISIONS.md`

#### Convergence

The discussion continues until the Eng Manager determines convergence: no new
substantive objections have been raised in the most recent exchange. The Eng
Manager then asks each agent explicitly: *"Any unresolved concerns before we
finalize?"* If silence or agreement, the phase closes.

#### `DECISIONS.md` Entry Format

```markdown
## Decision: <short title>

**Disagreement:** <what was at stake>
**Positions:**
- Architect: ...
- Developer: ...
- QA Engineer: ...
- Code Quality Engineer: ...
**Resolution:** <what was decided and why>
**Deferred:** <anything explicitly left for implementation or human review>
```

**Checkpoint:** `chk-phase-2` when discussion converges and artifacts are finalized.

---

### Phase 3 — GitHub PR

**Who:** Eng Manager
**Input:** Final `DESIGN.md`, `DECISIONS.md`
**Output:** PR against target repo's `main`

The Eng Manager commits the finalized design artifacts to the target repo and
opens a PR containing:
- `docs/design/<feature-slug>/DESIGN.md`
- `docs/design/<feature-slug>/DECISIONS.md`

The PR description summarizes the feature, key decisions made, and any items
explicitly flagged for human input.

**Checkpoint:** `chk-phase-3` after PR is opened.

---

### Phase 4+ — Human Feedback Loop

**Who:** Mark (GitHub PR UI) → Eng Manager + agent team
**Input:** Mark's PR comments
**Output:** Updated `DESIGN.md`, updated `DECISIONS.md`, push to PR

Mark reviews the PR and leaves comments. When ready:

```bash
agent-design next
```

The Eng Manager fetches PR comments via `gh`, writes them to
`feedback/human-round-<N>.md`, and surfaces them in `DISCUSSION.md` as a new
thread entry. The agents respond directly to Mark's points. The Eng Manager
facilitates the same way as Phase 2 — keeping discussion grounded, calling on
silent agents, driving to resolution.

The Architect updates `DESIGN.md` as consensus forms. The Eng Manager pushes
the updated artifacts to the PR.

This repeats until Mark approves.

**Checkpoint:** `chk-phase-4`, `chk-phase-5`, etc. — one per human feedback round.

---

### Session Close

When the PR is merged:

```bash
agent-design close
```

The CLI:
1. Sets `ROUND_STATE.json` `"phase": "complete"`
2. Makes a final checkpoint commit and tag
3. Removes the git worktree: `git worktree remove .agent-design`
4. Deletes the orphan branch (locally and remote, with confirmation)

Design artifacts persist permanently in the target repo at
`docs/design/<feature-slug>/`.

---

## CLI Tool

Implemented in **Python**. Installed from this repo. Invoked as `agent-design`.

```bash
# Start a new design session
agent-design init <repo-path> "<feature request>"

# Show current phase, agents, and checkpoint state
agent-design status

# Trigger the next phase (run after reviewing the PR)
agent-design next

# Add human feedback directly from CLI (appends to DISCUSSION.md)
agent-design feedback "<your comment>"

# List all checkpoints for the current session
agent-design checkpoints

# Roll back to a specific checkpoint and restart from there
agent-design rollback chk-phase-1

# Diff the working tree against a checkpoint
agent-design diff chk-phase-1

# Re-attach to an existing session from a fresh terminal
agent-design resume <repo-path>

# Clean up worktree and orphan branch after session is complete
agent-design close
```

---

## Checkpoint and Rollback

### Storage: Orphan Branch + Git Worktree

Session state lives on an **orphan branch** in the target repo, named
`agent-design/<feature-slug>` (e.g. `agent-design/news-admin-cli`). Orphan
branches share no history with `main` — `git log main` never shows design
session commits.

A **git worktree** links the orphan branch to a `.agent-design/` directory
inside the target repo:
- The main working tree stays on `main` at all times
- Agents read/write files in `.agent-design/` which commits to the orphan branch
- No branch switching required during a session

`.agent-design/` is listed in the target repo's `.gitignore`.

```
news_reader/                           ← main worktree (branch: main)
  .gitignore                           ← includes .agent-design
  src/
  ...
  .agent-design/                       ← linked worktree (branch: agent-design/news-admin-cli)
    ROUND_STATE.json
    BASELINE.md
    DESIGN.md
    DECISIONS.md
    DISCUSSION.md
    feedback/
      human-round-1.md
```

### Setup (`agent-design init`)

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

If `.agent-design` worktree already exists (crash recovery), `agent-design init`
detects this and resumes rather than failing with "worktree already exists".

### Checkpoints (Eng Manager, end of each phase)

```bash
cd .agent-design
git add -A
git commit -m "checkpoint: phase-2 design review complete"
git tag chk-phase-2
git push origin agent-design/news-admin-cli --tags
```

### Rollback

```bash
agent-design rollback chk-phase-1

# Under the hood:
cd .agent-design
git checkout chk-phase-1    # detached HEAD at that checkpoint
# fix the prompt or design approach
agent-design next            # Eng Manager reads ROUND_STATE.json → resumes from phase 1
```

### Resume (re-attach from fresh terminal)

```bash
agent-design resume <repo-path>
# Reads .agent-design/ROUND_STATE.json → restores session state → continues from last checkpoint
```

---

## `ROUND_STATE.json` Schema

```json
{
  "feature_slug": "news-admin-cli",
  "feature_request": "Build a news-admin CLI with re-extract and dead-letter commands",
  "target_repo": "/Users/mstriebeck/workspace/news_reader",
  "phase": "open_discussion",
  "discussion_turns": 3,
  "baseline_commit": "abc123def456",
  "completed": ["baseline", "initial_draft"],
  "pr_url": null,
  "checkpoint_tag": "chk-phase-1"
}
```

**`phase` values:** `"baseline"` → `"initial_draft"` → `"open_discussion"` →
`"awaiting_human"` → `"complete"`

---

## Design Artifacts in the Target Repo

Approved design docs live permanently in the target repo under
`docs/design/<feature-slug>/`, one subdirectory per feature:

```
docs/design/
  news-admin-cli/
    DESIGN.md
    DECISIONS.md
  embedder-daemon/
    DESIGN.md
    DECISIONS.md
```

---

## Agent Prompt Sketches

> These are starting-point sketches. Full prompts will be refined through
> live testing.

### Eng Manager Prompt (sketch)

```
You are the Eng Manager in a multi-agent design workflow. You facilitate and
orchestrate — you are not the primary design contributor.

On startup: read ROUND_STATE.json to determine the current phase, then proceed.

Facilitation rules:
- If an agent hasn't contributed on a significant topic, explicitly ask them.
- If an agent states an opinion without a concrete grounding ("we should never X"),
  ask them to specify what concretely breaks in this design if X is used.
- When two agents disagree, name the disagreement clearly and ask each side what
  evidence or constraint would change their position.
- Recognize when a disagreement is circling — ask what can be decided now vs. deferred.
- When no new substantive objections arise, ask each agent explicitly if they have
  unresolved concerns before declaring convergence.

You may express your own opinion, but always facilitate first.

Orchestration rules:
- Write every output to a file before routing it to other agents.
- Update ROUND_STATE.json at the start and end of every phase.
- Commit and tag at the end of every phase. Do not proceed without checkpointing.
- Update DECISIONS.md with every resolved disagreement — not just the hard ones.
```

### Architect Prompt (sketch)

```
You are the Architect in a multi-agent design workflow. You own the design.

Phase 0: Read the codebase. If BASELINE.md exists, check baseline-commit and
use `git log <commit>..HEAD --name-only` to find what changed. Only re-analyze
changed sections. Update BASELINE.md with the current commit in the header.

Phase 1: Read BASELINE.md and the feature request. Before writing, sharpen the
requirements — what is in scope, what is out of scope, what assumptions are you
making? Write the first draft of DESIGN.md.

Discussion: Read DISCUSSION.md fully before adding your entry. Respond to
specific points raised by other agents — not just your own position. If you
change your mind, say so explicitly and explain why.
```

### Developer Prompt (sketch)

```
You are the Developer in a multi-agent design workflow.

Read BASELINE.md and DESIGN.md before contributing. Read DISCUSSION.md fully
before adding your entry.

Focus on: what will implementation actually look like? What's easy, what's hard,
what are the edge cases? If something looks clean on paper but will be painful
to build, say so — with a specific, concrete reason. Vague concerns don't help.

Do not restate the design back. Add new information or a direct response to
something another agent said.
```

### QA Engineer Prompt (sketch)

```
You are the QA Engineer in a multi-agent design workflow.

Read BASELINE.md and DESIGN.md before contributing. Read DISCUSSION.md fully
before adding your entry.

Focus on: does this design actually satisfy the requirements? What are the
acceptance criteria? What happens at the boundary cases? What observable
contracts are under-specified? How do we verify end-to-end correctness?

Approach from the outside-in: you care about what a user or caller can observe,
not about implementation internals.
```

### Code Quality Engineer Prompt (sketch)

```
You are the Code Quality Engineer in a multi-agent design workflow.

Read BASELINE.md and DESIGN.md before contributing. Read DISCUSSION.md fully
before adding your entry.

Focus on: can this design be unit tested? Every complex object must have an
abstract protocol/interface so it can be both a production implementation and
a mock. Dependency injection is non-negotiable — call out any design where
dependencies are instantiated internally rather than injected.

Your question for every interface: "How would I write a unit test for this
without touching the network, database, or file system?"
```

---

## Open Questions

🔴 **Full agent prompts**
Sketches above need fleshing out and live testing against a real feature.

🔴 **Claude Code setup**
Requires Claude Code v2.1.32+. Document exact invocation from the Python CLI,
including whether `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is needed or whether
individual `claude` instances are sufficient for this workflow pattern.

---

## Resolved Decisions

| Decision | Resolution |
|---|---|
| **State lives in files, not session memory** | ✅ Sessions are stateless workers; files are the source of truth |
| **CLI language** | ✅ Python |
| **Structure lives at boundaries, discussion is free-form** | ✅ No predetermined round counts; convergence is natural |
| **Checkpoint mechanism** | ✅ Orphan branch + git worktree at `.agent-design/`; commit + tag per phase |
| **Why orphan branch + worktree** | ✅ No history pollution on `main`; no repo sprawl; main tree stays on `main`; full git tooling; cleaned up on `agent-design close` |
| **Rollback mechanism** | ✅ `agent-design rollback <tag>` → `git checkout <tag>` inside worktree |
| **Resume mechanism** | ✅ `agent-design resume <repo-path>` reads `ROUND_STATE.json` from existing worktree |
| **Crash recovery on init** | ✅ `agent-design init` detects existing worktree and resumes rather than failing |
| **Five agents** | ✅ Eng Manager (facilitator/orchestrator), Architect (design owner), Developer, QA Engineer, Code Quality Engineer |
| **Eng Manager is facilitator, not designer** | ✅ Architect owns the design; Eng Manager owns the process |
| **Tester split into two roles** | ✅ QA Engineer (outside-in, spec/acceptance) and Code Quality Engineer (inside-out, DI/mocks/unit testability) |
| **Shared discussion thread** | ✅ Single `DISCUSSION.md` that all agents append to; no per-agent draft files |
| **Eng Manager calls on silent agents** | ✅ Explicitly asks any agent that hasn't weighed in on a significant topic |
| **Eng Manager enforces fact-based discussion** | ✅ Pushes agents to ground assertions in concrete concerns about the specific design |
| **Baseline updates** | ✅ Incremental — `BASELINE.md` stores last analyzed commit; Architect diffs git history |
| **Human feedback trigger** | ✅ `agent-design next` CLI command |
| **Human feedback via GitHub** | ✅ PR against target repo; `agent-design next` fetches comments via `gh` |
| **Design artifact location** | ✅ `docs/design/<feature-slug>/` in target repo; one subdirectory per feature |
| **Session close** | ✅ `agent-design close` → worktree removal + orphan branch cleanup |
