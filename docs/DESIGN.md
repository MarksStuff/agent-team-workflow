# Agent Team Workflow — Design Document

> **Status:** v6 — Reflects current implementation.

---

## Goals

- Get genuinely independent perspectives on a feature design before any code is written
- Replicate the dynamics of a real engineering design review — not a pipeline dressed up as collaboration
- Make agents' reasoning, disagreements, and resolutions visible in plain text as they happen
- Allow the human to chime in at any point, naturally
- Support checkpoint and rollback so a crash or bad prompt doesn't lose progress
- Produce two durable artifacts per feature: a **Design Doc** and a **Decision Log**

---

## Core Design Principles

**Structure lives at the boundaries. The discussion is free-form.**

The Python CLI manages phase transitions, git checkpoints, and PR creation.
Inside each phase, Claude Code runs the agents — the conversation is emergent,
not scripted. Agents speak when they have something to say, respond to each other
directly, and the session ends when convergence is reached, not when a round
counter hits a limit.

**Each stage is one `claude` session. Python handles the state between them.**

- Automated stages (baseline analysis, initial design draft): `claude --print`
  non-interactive, Architect writes files directly
- Collaborative stages (design review, feedback): `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude`
  interactive in your terminal — you watch the agents debate live

**All state lives in files. Session memory is ephemeral and untrusted.**

Agent sessions are stateless workers. They read from files, write to files, and
never rely on conversation history surviving a restart. Every stage is independently
replayable from the last checkpoint.

---

## The Five Agents

The agents are roles described in prompts. In automated stages (0 and 1) the
Architect runs as a solo `claude` session. In collaborative stages (2+) Claude
Code's agent team mechanism spawns all five as separate Claude instances that
communicate directly.

### Eng Manager (Facilitator)

Does **not** own the design. Owns the **process**.

- Ensures every agent contributes — calls out silent agents by name
- Keeps discussion grounded in facts: pushes back on "we should never use X"
  with "what concretely breaks in *this* situation if we do?"
- Names disagreements explicitly and asks what evidence would change each position
- Drives circling debates to a decision: "what's the minimum we need to decide
  now vs. what can be deferred?"
- When the team genuinely cannot agree after good-faith debate: surfaces the
  deadlock explicitly (each position + strongest argument) and flags it for
  human review — does not force false consensus
- May express opinions but always facilitates first

### Architect (Design Owner)

- Owns the design — writes `BASELINE.md` and the first draft of `DESIGN.md`
- Sharpens requirements before writing: what is explicitly in scope, out of scope,
  and what assumptions are being made
- Participates in discussion from a system-level perspective: boundaries, data flow,
  component responsibilities, long-term maintainability
- Updates `DESIGN.md` incrementally as consensus forms — doesn't wait for the end

### Developer (Pragmatism & Velocity)

- Focused on getting to a working system as fast as possible
- Defaults to the simplest thing that could work; resists gold-plating
- Catches mismatches between clean-looking designs and messy implementation reality
- Key question: "What is the minimum we need to implement to validate this works?"

### QA Engineer (Outside-In Quality)

- Approaches the system as a user or external caller would: what can be observed?
  What are the contracts? What happens at the boundaries and failure cases?
- Pushes to define concrete acceptance criteria before anything else is decided
- Identifies under-specified behaviors: what happens when X fails? When two
  requests arrive simultaneously?
- Does not weigh in on internal code structure — that's TDD Focused Engineer's role

### TDD Focused Engineer (Inside-Out Testability)

- Focused on making code unit-testable in isolation, without real infrastructure
- Dependency injection is non-negotiable: every component must accept its
  dependencies as parameters, never instantiate them internally
- For every significant component: is there an abstract interface so we can
  substitute a test double?
- Flags hidden dependencies (global state, singletons, static calls to services)
- Pushes to extract complex logic into small, individually testable methods
- Ensures exhaustive unit tests are written covering every branch and statement

---

## Workflow Stages

### Stage 0 — Codebase Baseline (automated)

**Triggered by:** `agent-design init`
**Agent:** Architect (solo `claude --print` session)
**Output:** `BASELINE.md`

The Architect analyses the target repository and writes `BASELINE.md` covering:
- Directory structure and key files
- Language, framework, and dependency conventions
- Dominant patterns (naming, error handling, async style, logging)
- Existing components the feature will interact with
- Anything non-obvious a new contributor should know

`BASELINE.md` header stores the analysed commit SHA for incremental updates:
```
<!-- baseline-commit: abc123def456 -->
<!-- baseline-updated: 2026-03-20 -->
```

**Checkpoint:** `chk-baseline`

---

### Stage 1 — Initial Design Draft (automated)

**Triggered by:** `agent-design init` (immediately after stage 0)
**Agent:** Architect (solo `claude --print` session)
**Output:** `DESIGN.md` v1, empty `DISCUSSION.md`, empty `DECISIONS.md`

The Architect reads `BASELINE.md` and the feature request, then writes the initial
design document. Before writing, it sharpens the requirements: what is in scope,
out of scope, and what assumptions are being made.

`DESIGN.md` first draft covers:
1. Scope — requirements, non-requirements, explicit assumptions
2. Proposed approach and architecture
3. Key components and their responsibilities
4. Data flow and interface contracts
5. Open questions for the team to weigh in on

**Checkpoint:** `chk-initial-draft`

---

### Stage 2 — Design Review (interactive agent team)

**Triggered by:** `agent-design next`
**Agents:** Eng Manager + Architect + Developer + QA Engineer + TDD Focused Engineer
**Mode:** Interactive `claude` session with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

The CLI prints the Eng Manager's start message, then hands the terminal to Claude
Code. The Eng Manager creates a team of 4 teammates and facilitates the design
review. You watch the debate live in your terminal. Use Shift+Down to cycle
between agents; interact with any of them directly.

The shared `DISCUSSION.md` file is the conversation thread. All agents append
to it. `DESIGN.md` is updated by the Architect as consensus forms. Resolved
disagreements go into `DECISIONS.md`.

**Convergence:** the Eng Manager declares convergence when no new substantive
objections remain, then finalizes `DESIGN.md`.

**On exit:** CLI checkpoints, copies design artifacts to the target repo's
`docs/design/<feature-slug>/`, and creates a PR.

**Checkpoint:** `chk-review`

---

### Stage 3+ — Incorporate Human Feedback (interactive agent team)

**Triggered by:** `agent-design next` (after leaving PR feedback)
**Agents:** Same five-agent team
**Mode:** Interactive `claude` session with agent teams

The CLI fetches PR comments via `gh`, writes them to
`feedback/human-round-<N>.md`, then launches a new agent team session. The Eng
Manager surfaces the feedback to the team in `DISCUSSION.md` and facilitates
discussion. The Architect updates `DESIGN.md` as consensus forms.

On exit: CLI checkpoints and pushes updated artifacts to the PR.

Repeats until the PR is approved.

**Checkpoint:** `chk-feedback-1`, `chk-feedback-2`, etc.

---

### Session Close

```bash
agent-design close
```

Sets phase to `complete`, makes a final checkpoint, removes the git worktree,
and optionally deletes the orphan branch. Design artifacts remain permanently
in the target repo under `docs/design/<feature-slug>/`.

---

## CLI Reference

```
agent-design init <repo-path> "<feature request>"
    Set up worktree, run stages 0 and 1 (automated).

agent-design next [--repo-path <path>]
    Run the next stage: design review (stage 2) or feedback integration (stage 3+).

agent-design feedback "<comment>" [--repo-path <path>]
    Inject feedback directly (without going through a PR) and run a team session.

agent-design status [--repo-path <path>]
    Show current phase, feature slug, last checkpoint, PR URL.

agent-design checkpoints [--repo-path <path>]
    List all git checkpoints for the current session.

agent-design rollback <tag> [--repo-path <path>]
    Roll back to a checkpoint and restart from there.

agent-design diff <tag> [--repo-path <path>]
    Diff current worktree state against a checkpoint.

agent-design resume <repo-path>
    Re-attach to an existing session from a fresh terminal.

agent-design close [--repo-path <path>]
    Finalize, clean up worktree and orphan branch.
```

---

## Checkpoint and Rollback

### Storage: Orphan Branch + Git Worktree

Session state lives on an **orphan branch** in the target repo, named
`agent-design/<feature-slug>`. Orphan branches share no history with `main`.

A **git worktree** links the orphan branch to `.agent-design/` inside the
target repo. The main working tree always stays on `main` — no branch switching.

```
your-repo/
  .gitignore          ← includes .agent-design/
  src/
  ...
  .agent-design/      ← linked worktree (orphan branch: agent-design/feature-slug)
    ROUND_STATE.json
    BASELINE.md
    DESIGN.md
    DECISIONS.md
    DISCUSSION.md
    feedback/
      human-round-1.md
```

### `ROUND_STATE.json` Schema

```json
{
  "feature_slug": "news-admin-cli",
  "feature_request": "Build a news-admin CLI with re-extract and dead-letter commands",
  "target_repo": "/path/to/your/repo",
  "phase": "open_discussion",
  "discussion_turns": 1,
  "baseline_commit": "abc123def456",
  "completed": ["baseline", "initial_draft"],
  "pr_url": "https://github.com/owner/repo/pull/42",
  "checkpoint_tag": "chk-initial-draft"
}
```

**`phase` values:** `baseline` → `initial_draft` → `open_discussion` → `awaiting_human` → `complete`

### Rollback

```bash
agent-design rollback chk-initial-draft
# Rewinds .agent-design to that checkpoint
# Run 'agent-design next' to re-run from there with a different prompt
```

---

## Design Artifacts in the Target Repo

Finalized design docs are committed permanently to the target repo:

```
docs/design/
  news-admin-cli/
    DESIGN.md      ← the agreed design
    DECISIONS.md   ← every disagreement and how it was resolved
  embedder-daemon/
    DESIGN.md
    DECISIONS.md
```

---

## Agent Prompts

Prompts live in `agent_design/prompts.py`. Two types:

**Agent identity constants** (who each agent is — generic, applicable to any stage):

| Constant | Agent |
|---|---|
| `AGENT_ENG_MANAGER` | Eng Manager |
| `AGENT_ARCHITECT` | Architect |
| `AGENT_DEVELOPER` | Developer |
| `AGENT_QA_ENGINEER` | QA Engineer |
| `AGENT_TDD_FOCUSSED_ENGINEER` | TDD Focused Engineer |

**Stage task constants** (what to do right now — no agent identity):

| Constant | Stage | Mode |
|---|---|---|
| `STAGE_0_BASELINE` | 0 — codebase analysis | solo, non-interactive |
| `STAGE_1_INITIAL_DRAFT` | 1 — initial design draft | solo, non-interactive |
| `build_review_start()` | 2 — design review | agent team, interactive |
| `build_feedback_start()` | 3+ — incorporate feedback | agent team, interactive |

Team session start messages are assembled by `build_review_start()` and
`build_feedback_start()`, which combine the Eng Manager identity, the stage
task, and spawn prompts for all 4 teammates.

---

## Resolved Decisions

| Decision | Resolution |
|---|---|
| **Agent execution mechanism** | ✅ Native Claude Code agent teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), not Python subprocess orchestration |
| **Stage structure** | ✅ Each stage = one `claude` session; Python CLI handles git state between them |
| **Solo vs. team stages** | ✅ Stages 0+1: `claude --print` solo (Architect); Stages 2+: interactive agent team |
| **State lives in files** | ✅ Sessions are stateless; files are the source of truth |
| **CLI language** | ✅ Python |
| **Structure lives at boundaries, discussion is free-form** | ✅ No scripted round counts; convergence is natural |
| **Checkpoint mechanism** | ✅ Orphan branch + git worktree; commit + tag per stage |
| **Five agents** | ✅ Eng Manager, Architect, Developer, QA Engineer, TDD Focused Engineer |
| **Eng Manager is facilitator, not designer** | ✅ Does not own the design; owns the process |
| **Quality split into two roles** | ✅ QA Engineer (outside-in, acceptance criteria) and TDD Focused Engineer (inside-out, unit testability, DI, exhaustive tests) |
| **Agent prompts are generic** | ✅ `AGENT_*` constants describe who each agent is — applicable to any stage (investigation, design, implementation, review) |
| **Eng Manager calls on silent agents** | ✅ Explicitly prompts any agent that hasn't weighed in |
| **Eng Manager enforces fact-based discussion** | ✅ Pushes assertions to concrete concerns about the specific situation |
| **Eng Manager surfaces deadlocks** | ✅ If team can't agree, records each position and flags for human review — no forced consensus |
| **Design artifact location** | ✅ `docs/design/<feature-slug>/` in target repo |
| **Session close** | ✅ `agent-design close` → worktree removal + orphan branch cleanup |
