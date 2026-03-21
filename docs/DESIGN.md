# Agent Team Workflow — Design Document

> **Status:** v5 — Reflects current implementation.

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
- Keeps discussion grounded in facts, not opinions: pushes back on "we should
  never use X" with "what concretely breaks in *this* design if we do?"
- Names disagreements explicitly and asks what evidence would change each position
- Drives circling debates to a decision: "what's the minimum we need to decide
  now vs. what can be deferred to implementation?"
- Updates `DECISIONS.md` with every resolved disagreement
- May express opinions but always facilitates first

### Architect (Design Owner)

- Owns the design — writes `BASELINE.md` and the first draft of `DESIGN.md`
- Sharpens requirements before writing: what is explicitly in scope, out of scope,
  and what assumptions are being made
- Participates in discussion from a system-level perspective: boundaries, data flow,
  component responsibilities, long-term maintainability
- Updates `DESIGN.md` incrementally as consensus forms — doesn't wait for the end

### Developer (Implementation Focus)

- Focuses on what implementation will actually look like: API shape, error handling,
  edge cases, what's straightforward vs. deceptively hard
- Grounds every concern in a specific, concrete implementation problem — not general principles
- Does not restate the design; adds new information or responds to specific points

### QA Engineer (Outside-In Quality)

- Approaches the design from the outside-in: does it satisfy the requirements?
  What are the acceptance criteria? What happens at the boundary cases?
- Identifies under-specified observable contracts: what does a user or caller see
  when X fails? What are the integration test scenarios?
- Does not care about internal structure — that's Code Quality's role

### Code Quality Engineer (Inside-Out Testability)

- Focuses on unit testability: dependency injection, interface design, mock boundaries
- For every interface: "how would I write a unit test for this without touching
  the network, database, or filesystem?"
- Every complex object needs an abstract protocol/interface so it can be implemented
  as both a production version and a test mock
- Calls out designs where dependencies are instantiated internally rather than injected

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
**Agents:** Eng Manager + Architect + Developer + QA Engineer + Code Quality Engineer
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

Prompts live in `agent_design/prompts.py`. Four templates:

| Constant | Stage | Mode |
|---|---|---|
| `ARCHITECT_BASELINE` | 0 — codebase analysis | solo, non-interactive |
| `ARCHITECT_INITIAL_DRAFT` | 1 — initial design draft | solo, non-interactive |
| `ENG_MANAGER_REVIEW_START` | 2 — design review | agent team, interactive |
| `ENG_MANAGER_FEEDBACK_START` | 3+ — incorporate feedback | agent team, interactive |

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
| **Five agents** | ✅ Eng Manager, Architect, Developer, QA Engineer, Code Quality Engineer |
| **Eng Manager is facilitator, not designer** | ✅ Architect owns the design; Eng Manager owns the process |
| **Tester split into two roles** | ✅ QA Engineer (outside-in) and Code Quality Engineer (inside-out) |
| **Eng Manager calls on silent agents** | ✅ Explicitly prompts any agent that hasn't weighed in |
| **Eng Manager enforces fact-based discussion** | ✅ Pushes assertions to concrete concerns about the specific design |
| **Design artifact location** | ✅ `docs/design/<feature-slug>/` in target repo |
| **Session close** | ✅ `agent-design close` → worktree removal + orphan branch cleanup |
