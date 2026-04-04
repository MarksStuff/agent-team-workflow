# Agent Team Workflow — Design Document V2

> **Status:** Draft — Proposed next-generation architecture.
> **Supersedes:** `docs/DESIGN.md` (v6)

---

## What V1 Got Right (and Wrong)

V1 proved the core thesis: a team of AI agents with distinct roles produces
meaningfully better design documents than a solo pass. The design review found
real bugs, incorporated human feedback, and produced documents accurate enough
to implement from.

What V1 got wrong:

1. **Everything baked into the prompt.** Agent identities, task instructions,
   teammate spawn prompts — all hardcoded as Python strings. Changing an agent
   means editing `prompts.py` and redeploying.

2. **Fixed team composition.** Every session spawns the same five agents
   regardless of task. An Ansible deployment task doesn't need the same team
   as a Swift API change.

3. **No memory.** Agents wake up fresh every session. When Mark overrides a
   decision, that correction evaporates. The same mistakes recur.

4. **EM as relay, not facilitator.** In practice the Eng Manager orchestrated
   every step rather than letting agents self-organise. Collaboration happened
   *through* the EM, not *between* agents.

5. **No retrospective loop.** Sessions end with artifacts but no process
   improvement. The system doesn't get smarter from experience.

6. **No quality gates.** "Tests pass" was a social norm, not an enforced rule.

7. **Manual copy-paste to start sessions.** The CLI printed a start prompt and
   asked the user to paste it into Claude. An invocable, hands-free handoff is
   better.

8. **Memory and prompt updates written directly by scripts.** Scripts that
   directly write to memory files bypass agent judgment. Worse, a centralised
   router agent deciding *for* other agents what they should learn is also
   wrong — the agent that made the mistake knows its own role best and should
   decide what to record, how to phrase it, and whether it's worth keeping.

V2 fixes all of these.

---

## Core Design Principles (Revised)

**Agents are files, not strings.**

Each agent is a Markdown file with YAML frontmatter, stored in `.claude/agents/`.
Claude Code loads them automatically at session start. The start prompt is just
the task — agent identities, tools, and memory live in their definition files.

**The EM decides what to do next, not the CLI.**

The Python CLI starts a session and hands off a task. The Eng Manager reads the
worktree state (what files exist, what discussions have happened, what feedback
is present) and decides: initial design? team review? incorporate feedback?
sprint planning? The CLI has no phase state machine.

**The CLI does three things only.**

Git operations. Session launching. GitHub API calls. Nothing else. It does not
track stages, compose prompts conditionally, or make workflow decisions.

**Agents are the authors of their own memory.**

Each agent has a persistent memory file at `~/.claude/agent-memory/<name>.md`.
When an agent is corrected, observes a mistake, or learns something worth
keeping, it updates its own memory file — not a router, not a script, not the
Retrospective Facilitator writing on its behalf. The agent that made the mistake
knows its own role and what to record. Routing decisions are decentralised:
each agent reads incoming feedback and decides whether it's relevant to them.

The retrospective facilitator's job is to surface patterns and coordinate; each
agent still does its own self-review and writes its own updates.

**Quality gates are enforced, not hoped for.**

Claude Code hooks reject task completion if tests don't pass. Agents cannot
mark work done until the gate passes.

**Retrospectives close the feedback loop.**

Every feature ends with a retrospective. Lessons learned update agent memories
and prompts. The system is self-improving.

---

## The Agent Roster

### Core Engineering Team

These agents participate in most sessions. The EM decides the initial
composition; agents may request additional specialists mid-session.

---

#### Eng Manager
**Role:** Team lead, task board owner, gate keeper.
**Does not:** Make technical decisions, assign implementation work, or relay
messages between agents.
**Does:** Read the worktree to determine what phase the work is in. Compose the
initial team for a task. Monitor TASKS.md for stalled or unclaimed work.
Facilitate phase transitions. Request additional specialists when the team
surfaces a domain it can't handle. Call the session complete when Architect and
QA both sign off.

*Dynamic team composition is the EM's primary skill.* Given a task description,
the EM decides which 2–5 specialists to spawn. For a deployment task: SRE is
mandatory, Security Engineer likely, Performance Engineer probably not. For a
new API: Database Architect, Security Engineer, TDD Engineer all relevant.
The EM can spawn more agents mid-session if new concerns surface.

*Reading worktree state replaces CLI stage tracking.* The EM checks what exists
in `.agent-design/`:
- No DESIGN.md → run a design phase
- DESIGN.md + no team discussion in DISCUSSION.md → design has not been reviewed yet
- DESIGN.md + feedback/ directory with new files → incorporate feedback
- Approved DESIGN.md + TASKS.md present → implementation is in progress

---

#### Architect
**Role:** Systems design, technical direction, design-drift detection.
**Does:** Own the design document. Evaluate proposals against system-wide
constraints. Detect when implementation diverges from agreed design. Veto
changes that violate architectural principles.
**Does not:** Write implementation code, assign work to teammates.

---

#### Developer
**Role:** Implementation, pragmatic velocity.
**Does:** Write the actual code. Raise practical concerns about implementation
approaches. Implement to make TDD Engineer's tests pass.
**Does not:** Skip failing tests, mark tasks done before tests are green.

---

#### TDD-Focused Engineer
**Role:** Test-first discipline, testability, coverage.
**Does:** Write tests before implementation (red → green). Validate that tests
are red before signalling Developer. Verify tests are green before signing off
on tasks. Raise concerns about untestable designs.
**Does not:** Let Developer begin until tests are written and confirmed red.

---

#### QA Engineer
**Role:** Acceptance criteria, observable behaviour, deployment readiness.
**Does:** Define what "done" looks like from a user/operator perspective.
Verify implementation satisfies acceptance criteria from the design doc.
Own the final "would this actually work in production" sign-off.
**Does not:** Write unit tests (that's TDD Engineer's job).

---

### Specialist Agents

Spawned by the EM when the task warrants it.

---

#### SRE (Site Reliability Engineer)
**Role:** Production readiness, deployment safety, observability.
**Spawned when:** The task involves deployment, infrastructure, scaling,
monitoring, on-call impact, rollback procedures, or runbooks.
**Does:** Review deployment procedures for safety and reversibility. Define
SLIs/SLOs for new functionality. Specify monitoring and alerting requirements.
Write or review runbooks. Flag single points of failure. Require rollback
procedures before approving deployment-related tasks.

---

#### PM (Product Manager)
**Role:** Requirements clarity, scope control, user value.
**Spawned when:** Requirements are ambiguous, scope is creeping, or the team
is debating what to build rather than how.
**Does:** Sharpen acceptance criteria. Ask "what problem does this solve for
the user". Push back on over-engineering. Define the minimal viable scope.
Document deferred items explicitly.
**Does not:** Make technical decisions.

---

#### Security Engineer
**Role:** Threat modelling, security review, vulnerability detection.
**Spawned when:** The task touches authentication, authorisation, data
handling, external inputs, secrets, or public-facing surfaces.
**Does:** Identify attack vectors. Review auth flows. Flag injection risks.
Check secrets handling. Require security test coverage for sensitive paths.
Apply OWASP standards.

---

#### Database Architect
**Role:** Schema design, migrations, data integrity, query performance.
**Spawned when:** The task involves schema changes, new tables, migrations,
data contracts between services, or complex queries.
**Does:** Review schema for normalisation and integrity. Require migration
scripts to be reversible. Flag missing indexes. Define data contracts. Prevent
schema drift.

---

#### Technical Writer
**Role:** Documentation quality, operator usability.
**Spawned when:** The task produces user-facing features, public APIs, runbooks,
or significant operational procedures.
**Does:** Write or review API docs, runbooks, changelogs, and user-facing copy.
Ensures a new team member could operate the system from the documentation alone.

---

#### Performance Engineer
**Role:** Profiling, bottleneck detection, load characteristics.
**Spawned when:** The task involves high-throughput paths, latency-sensitive
features, large data volumes, or explicit performance requirements.
**Does:** Define performance budgets. Identify bottlenecks in proposed
implementations. Require load tests for critical paths.

---

### Domain Expert Agents

Domain experts are a different kind of agent. They don't write code, run tests,
or review deployments — they answer questions. Their value is deep, current
knowledge of a specific domain that the engineering team can consult without
leaving the session.

Examples for this project:
- **claude_expert** — knows Claude Code features, the Claude API, agent SDK,
  model capabilities, pricing, rate limits, and evolving best practices
- **agent_systems_expert** — knows multi-agent architectures, coordination
  patterns, memory systems, tool design, and the fast-moving research landscape

#### Where domain experts live

Claude Code loads agents from two places:
- `~/.claude/agents/` — global, available in every project
- `.claude/agents/` — repo-local, available only in this repo

**Use this distinction deliberately:**

| Location | When to use |
|---|---|
| `~/.claude/agents/` | Broad expertise that applies across many projects (e.g., Security, Distributed Systems, Cryptography) |
| `.claude/agents/` in the repo | Expertise specific to this project's domain (e.g., Claude API for an AI tool, RabbitMQ for a messaging system, SwiftUI for an iOS app) |

The EM discovers both at session start and reads their descriptions — no special
plumbing required. Repo-local agents are listed alongside global ones. Domain
experts that are only useful in one project should not pollute the global set.

#### How the EM uses domain experts

The EM does not spawn domain experts by default. They are available as
on-demand consultants. Any agent on the team can request one:

```
## [Architect]
I'm not sure whether Claude Code supports passing environment variables to
subagents. @EM: can you bring in the Claude domain expert to clarify?
```

The EM spawns the expert, who answers the question and either stays available
or signs off. Domain experts contribute to DISCUSSION.md like any other agent
but do not claim tasks in TASKS.md.

#### Keeping domain experts current

Domain knowledge goes stale. For slow-moving domains (SQL, TCP/IP) this is
not a problem. For fast-moving ones (LLM features, agent frameworks, cloud
APIs) it is a serious problem.

The design separates **stable knowledge** from **volatile knowledge**:

**Stable knowledge** — baked into the agent's system prompt. Foundational
concepts, architectural principles, core API structure. These don't change
often. Examples:
- "Claude's tool_use and tool_result message structure"
- "The tradeoffs between shared memory and message passing in multi-agent systems"
- "How Claude Code's permission model works"

**Volatile knowledge** — never baked in. Fetched at query time. Examples:
- "Which models are currently available and their context windows"
- "What new tools or hooks were added in the last Claude Code release"
- "Current rate limits and pricing"
- "Recent changes to the agent SDK"

Each domain expert agent has:
1. **Web search tool enabled.** The agent searches before answering any
   time-sensitive question. Its prompt instructs: "For anything that might
   have changed in the last 6 months, search before answering. State what
   you found and when the source was last updated."
2. **A curated sources list in its memory file.** The agent knows *where*
   to look: official docs URLs, changelog pages, release notes feeds,
   authoritative blog posts. It checks these sources, not arbitrary web results.
3. **A knowledge freshness section** in its memory file that records what
   it knows and when it was last verified.

#### Domain expert memory file structure

```markdown
# Claude Domain Expert Memory

## Stable Knowledge (baked into prompt — update rarely)
- Claude tool_use message structure: tool_use block → tool_result block
- Claude Code's agent team model: EM spawns sub-agents via Agent tool
- Permission modes: default, acceptEdits, bypassPermissions
- Hooks: PreToolUse, PostToolUse, Notification, Stop events

## Volatile Knowledge (verified: 2026-04-03)
- Current models: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5
- claude-sonnet-4-6 context window: 200k tokens
- Agent tool: supports isolation: "worktree" for isolated copies
- CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 required for team sessions

## Authoritative Sources
- https://docs.anthropic.com/en/docs/claude-code
- https://docs.anthropic.com/en/release-notes/claude-code
- https://docs.anthropic.com/en/api/getting-started

## Pending Refresh
- Rate limits: last checked 2026-02-15 — likely stale, re-check before advising
```

#### Refreshing a domain expert

```bash
agent-design refresh-domain --agent claude_expert
```

This runs a `--print` session where the agent:
1. Reads its memory file to see what's recorded and when
2. Checks its authoritative sources for changes since last verified
3. Updates the "Volatile Knowledge" and "Verified" timestamps
4. Flags anything it couldn't verify as "Pending Refresh"

The human decides when to run this — before a session where current
knowledge matters, or on a periodic schedule.

#### Escalation: proposing a new agent

During a session the EM may realise it needs an agent that doesn't exist yet.
It cannot create the agent unilaterally — but it can draft a complete proposal
and escalate to the human for approval.

**When to escalate:**
- A domain concern surfaces that no current team member can evaluate
  confidently (e.g., cryptographic key derivation, FPGA timing constraints,
  regulatory compliance)
- The same gap keeps appearing across sessions, suggesting a permanent gap
  in the roster

**What the EM does:**

1. Posts to DISCUSSION.md: "I need a Cryptography Expert. I can't evaluate
   the key-derivation approach here with confidence. Drafting a proposal."
2. Writes a complete agent proposal to `.agent-design/proposals/<name>.md`
3. Notifies the human via a `StopHook` notification (or a clear panel in
   the session output): "New agent proposed: cryptography_expert.
   Run `agent-design review-proposal cryptography_expert` to review and apply."
4. Identifies which tasks are **gated** on the missing agent and which are not.
   Tasks requiring the missing agent's input to make a *correct decision* are
   marked 🚫 blocked in TASKS.md. Tasks that don't depend on that input
   continue. The EM posts to DISCUSSION.md which tasks are held and why.

**Blocking is task-scoped, not session-scoped.** The right question is not
"does the session block?" but "does *this specific task* require the missing
agent's judgment to be correct?" If yes, that task waits. If no, it proceeds.

Concretely:
- "Choose key derivation algorithm and parameters" → **blocked**. Picking
  the wrong algorithm and implementing it creates rework. Wait for the expert.
- "Write the user registration endpoint" → **not blocked**. That work doesn't
  depend on the crypto decision. Continue.

If all remaining tasks are gated on the missing agent, the effective result
is a full session block. If only one subtask is gated, everything else makes
progress. The EM decides based on dependency, not a blanket policy.

When the human approves the proposal and the agent becomes available mid-session,
the EM spawns them, they review the held tasks, and the session resumes.

**Proposal file format** (`.agent-design/proposals/<name>.md`):

```markdown
# Agent Proposal: cryptography_expert

**Proposed by:** Eng Manager
**Session:** feat/add-user-auth — 2026-04-03
**Gap identified:** AES-256 key derivation and PBKDF2 iteration counts in §3.4
of DESIGN.md. The team has no one who can evaluate whether the proposed
parameters are secure for the threat model described.

**Proposed location:** `~/.claude/agents/cryptography_expert.md`
**Rationale:** Cryptography concerns appear across projects — this is global
expertise, not project-specific. Any project involving encryption, hashing,
or key management will benefit from it.

**Agent type:** Domain expert (advises; does not write implementation code)

---

## Agent Definition (written verbatim if approved)

---
name: cryptography_expert
description: >
  Cryptography domain expert. Evaluates symmetric and asymmetric encryption
  schemes, key derivation functions, hashing algorithms, and protocol security.
  Spawn when the task involves encryption, key management, secrets handling,
  or authentication primitives.
model: claude-sonnet-4-6
tools: WebSearch, WebFetch, Read
---

You are a cryptography domain expert on a collaborative engineering team.
You do not write implementation code. You evaluate cryptographic decisions,
flag weaknesses, and recommend well-vetted approaches.

## What you bring

**Algorithm evaluation.** For any proposed cipher, KDF, MAC, or protocol:
what are the known weaknesses? Is this the right tool for the threat model?
Are the parameters (key size, iteration count, nonce handling) appropriate?

**Current best practices.** Cryptographic recommendations evolve. You know
which algorithms are current (AES-256-GCM, Argon2id, Ed25519) and which
are deprecated (MD5, SHA-1 for security, DES, ECB mode).

**Misuse patterns.** You catch the common mistakes: reused nonces, weak
KDF parameters, secrets in logs, timing side-channels in comparison code.

## Your memory file

~/.claude/agent-memory/cryptography_expert.md

Update it when you see a project-specific cryptographic pattern worth
remembering, or when your recommendation is overridden with a reason.
```

**Stable knowledge** (in prompt): algorithm properties, misuse patterns,
protocol structure.

**Volatile knowledge** (in memory, refreshed periodically):
- Current NIST recommendations and deprecated algorithms
- OWASP cryptographic storage cheat sheet (version/date)
- Known vulnerabilities in common libraries

**Authoritative sources:**
- https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar2.pdf
- https://libsodium.gitbook.io/doc/
```

**Review and apply:**

```bash
agent-design review-proposal cryptography_expert
```

This prints the full proposal for the human to read. The human runs:

```bash
agent-design apply-proposal cryptography_expert   # writes the agent file
```

The CLI writes the agent definition to the proposed location. If the session
is still running, the human can tell the EM: "cryptography_expert is now
available" and the EM spawns them immediately into the current session.

**The EM never writes agent files directly.** It writes proposals only.
Proposals are permanent — they survive session end and can be applied later.
The proposals directory is committed along with the other design artifacts.

---

#### Retrospective Facilitator
**Spawned at the end of every feature** (not during implementation).
**Does:** Review DISCUSSION.md, TASKS.md, DECISIONS.md, and human intervention
events. Identify patterns: where agents got stuck, where humans intervened,
what was slow. **Tell each agent what patterns were observed and ask them to
self-review and update their own memory** — the facilitator does not write to
other agents' memory files. Produce RETRO.md. Propose prompt changes as
suggestions to the human — not direct edits.

The facilitator's memory update flow:
1. Identify which agents were involved in each friction point or intervention
2. Post the relevant observation to each agent and ask: "Does this warrant a
   memory update? If so, update your file now."
3. Each agent decides what (if anything) to write and how to phrase it
4. Facilitator confirms updates were made and records a summary in RETRO.md

---

## Agent Files: Structure and Storage

Each agent is a Markdown file with YAML frontmatter. Claude Code loads these
automatically — no Python plumbing required.

Agents are **global** (`~/.claude/agents/`), not project-scoped. They travel
with the engineer, not the repo. The same Architect, SRE, and TDD Engineer
work across every project.

```
~/.claude/
  agents/
    eng_manager.md
    architect.md
    developer.md
    tdd_engineer.md
    qa_engineer.md
    sre.md
    pm.md
    security_engineer.md
    database_architect.md
    technical_writer.md
    performance_engineer.md
    retrospective_facilitator.md
```

### Agent file format

```markdown
---
name: architect
description: >
  Systems design expert and technical direction owner. Use for design reviews,
  architecture decisions, technology choices, and detecting implementation drift
  from agreed designs.
model: claude-sonnet-4-6
tools: all
memory: project
---

You are the Architect on this engineering team.

[identity and operating principles...]
```

The `memory: project` field tells Claude Code to maintain a persistent memory
file for this agent at `.claude/agent-memory/architect.md`. Each agent is
responsible for writing to its own memory file — when corrected during a
session, it updates immediately; during a retrospective, it reviews and
self-updates.

### Agent memory files

Agent memory is **global and machine-local** (`~/.claude/agent-memory/`).
Learnings about working style, preferred patterns, and past decisions travel
with the engineer across all projects.

```
~/.claude/
  agent-memory/
    architect.md        ← accumulated learnings across sessions and projects
    developer.md
    tdd_engineer.md
    qa_engineer.md
    sre.md
    ...
```

**Format:**

```markdown
# Architect Memory

## Working Style & Preferences
- Mark prefers interface-first design: protocols defined before implementations
- Tests live in separate targets, never mixed with production code
- Prefer synchronous pipelines at small scale; async only when throughput demands it

## Corrections & Overrides
- 2026-03-22 [news_reader]: Mark overrode async queue recommendation for
  synchronous pipeline. Reason: simpler to operate at current scale.
- 2026-03-20 [news_reader]: Proposed Docker; Mark corrected to Ansible on Proxmox.
  Check BASELINE.md and CLAUDE.md before proposing infrastructure changes.

## Lessons Learned
- Always read the project's CLAUDE.md before making deployment recommendations.
  It contains the deployment approach, stack constraints, and key conventions.
```

### Project-specific context: CLAUDE.md

Global agent memory captures *engineer preferences*. Project-specific context
lives where Claude Code already looks for it: **CLAUDE.md in the target repo**.

Claude Code automatically loads CLAUDE.md files at session start — agents pick
it up without any special plumbing. Each project maintains its own CLAUDE.md:

```markdown
# news_reader — Project Context for AI Agents

## Deployment
- Ansible on Proxmox LXC (NOT Docker, NOT Kubernetes)
- Playbooks in `infrastructure/ansible/`

## Testing
- Swift: `swift test` from repo root
- Ansible: `pytest infrastructure/ansible/tests/`
- No real network calls in unit tests — use mocks

## Code Conventions
- All Swift types need a protocol for testability (dependency injection)
- No direct pushes to main — always branch + PR
```

The Retrospective Facilitator can suggest CLAUDE.md additions when it spots
project-specific patterns that kept tripping up agents. These are surfaced as
suggestions to the human — the human decides whether to add them, and if so,
runs `agent-design add-context` to let Claude make the edit.

---

## Starting Sessions: No Copy-Paste

The CLI passes the start message directly to `claude` as a positional argument.
Claude starts the interactive session with that message as the first user turn —
no copy-paste required.

```python
subprocess.run([
    "claude",
    "--dangerously-skip-permissions",
    "--agent", "eng_manager",
    "--add-dir", str(target_repo),
    "--",
    start_message,      # ← delivered as first turn; user sees Claude already working
])
```

This is identical to how `run_solo()` passes prompts (with `--print`), extended
to interactive sessions. The EM wakes up, reads the start message, and begins
immediately.

For solo sessions (`init`, `baseline`), `--print` mode continues to be used
since those produce file output autonomously with no human in the loop.

---

## The Start Prompt (Dramatically Simplified)

With agents defined as files, the start prompt shrinks from ~500 lines to ~20.
The EM's system prompt (in `eng_manager.md`) handles the rest.

### Design/review/feedback phase

```
Feature: <feature_request>

Worktree: .agent-design/
Available specialists: architect, developer, tdd_engineer, qa_engineer, sre, ...

Read the worktree to understand where we are:
- If DESIGN.md is missing or sparse: run a full design phase
- If DESIGN.md exists but team review hasn't happened: convene a design review
- If feedback/ has files not yet incorporated: incorporate the feedback
- If DESIGN.md is approved: you're done — report status

Use DISCUSSION.md and DECISIONS.md as you go.
```

The EM reads the worktree and decides what phase it is in. The CLI doesn't
track this. The same `continue` command is used regardless of whether this is
a first review or the third feedback round.

### Implementation phase

```
Feature: <feature_request>

Worktree: .agent-design/ (contains DESIGN.md)
Available specialists: architect, developer, tdd_engineer, qa_engineer, sre, ...

Implement the feature described in .agent-design/DESIGN.md.
The design document may contain broader context — implement only this feature.
```

---

## Coordination Mechanism: TASKS.md + DISCUSSION.md

Two shared files replace the EM-as-relay pattern:

**TASKS.md** — task board, owned by the whole team:
```markdown
| Task | Owner | Status | Notes |
|---|---|---|---|
| Write test_task_ordering.py | TDD Engineer | ✅ done | |
| Fix roles/rabbitmq task order | Developer | 🔄 in progress | unblocked |
| Review §3.2 impl vs design | Architect | ⬜ unclaimed | depends: fix roles/rabbitmq |
| Deployment safety review | SRE | 🔄 in progress | |
```

**DISCUSSION.md** — peer-to-peer communication channel:
```markdown
## [TDD Engineer]
Tests are written and red. Developer: you're unblocked on roles/rabbitmq.
Run `pytest infrastructure/ansible/tests/` to see failures.

## [Developer]
On it. Question for Architect: the design says use `notify` handler but the
existing role uses `when:` conditions. Which pattern should we follow?

## [Architect]
Use `notify` — it's idempotent and matches the rest of the codebase. The
`when:` pattern in the existing role is legacy we should not propagate.
```

Agents talk to each other via DISCUSSION.md. The EM reads TASKS.md, not the
conversation. This prevents the EM-as-relay pattern that made V1 feel
orchestrated rather than collaborative.

---

## Quality Gates: Hooks

Claude Code hooks enforce rules at key events. Agents cannot bypass them.

### `task_completed.sh`
Runs when a teammate tries to mark a task ✅. Exit code 2 rejects completion
and sends feedback to the agent.

```bash
#!/bin/bash
# Only gate implementation tasks, not planning tasks
TASK_TITLE="$TASK_TITLE"
if [[ "$TASK_TITLE" == *"implement"* || "$TASK_TITLE" == *"fix"* ]]; then
  cd "$REPO_PATH" && python -m pytest --tb=short -q
  if [ $? -ne 0 ]; then
    echo "Tests are failing. Fix before marking done."
    exit 2
  fi
fi
```

### `teammate_idle.sh`
Runs when a teammate goes idle without completing work. Requires a status
update in TASKS.md.

---

## Human Intervention → Memory Update (Agent Self-Authorship)

When Mark steps in to make a decision, correct an agent, or override a choice,
that event is high-signal feedback. The `remember` command captures it — but
**there is no memory_router agent**. Instead, the note is broadcast to all core
agents in a brief `--print` session. Each agent reads it, decides whether it's
relevant to their role, and self-updates their own memory file if so.

```bash
agent-design remember "Mark overrode async queue recommendation for sync pipeline. \
  Reason: simpler to operate at current scale."
```

This launches a `--print` multi-agent session with all core agents. The start
prompt is simply:

```
A human correction or override has been recorded.

Correction: <text>
Project: <project slug>
Date: <today>

Each agent: read this note. If it is relevant to your role and decisions you
might make, update your own memory file at ~/.claude/agent-memory/<your-name>.md.
Use the established format (## Corrections & Overrides, YYYY-MM-DD [project]).
If it is not relevant to you, do nothing.

After updates are complete, each agent that made a change reports: what they
wrote and why.
```

The routing is fully decentralised. The Architect sees a deployment override
and self-updates. The Developer may see nothing relevant. The SRE sees
implications for their own role and updates too. No single agent decides for
the others.

**Safety: guaranteed pickup.** The Retrospective Facilitator is always present
in `remember` sessions. Its job is to verify that at least one agent updated
their memory. If no agent self-updated after a non-trivial correction, the
Facilitator flags it explicitly: "This correction was not recorded by any
agent. One of you should own it." — and prompts the most relevant agent to
reconsider.

---

## The Retrospective

A first-class command run **once, at the very end of a complete feature** —
after design is approved, implementation is done, and the PR is pushed.

```
agent-design retro --repo-path ../news_reader
```

The Retrospective Facilitator agent:

1. Reads DISCUSSION.md, TASKS.md, DECISIONS.md, the human intervention log
2. Identifies patterns:
   - Where did agents get stuck?
   - Where did humans intervene and why?
   - Which decisions were contentious without resolution?
   - What took longer than it should?
   - What was smooth and should be reinforced?
3. For each friction point or intervention, tells the relevant agent(s) what
   was observed and asks them to self-review and update their own memory file.
   The facilitator does not write to any agent's memory file directly.
4. Verifies each called-out agent has either updated their memory or explained
   why no update was warranted. If an agent fails to respond, the facilitator
   flags it in RETRO.md.
5. Produces `RETRO.md` summarising observations and what each agent updated.
6. Suggests — but does not apply — prompt changes for agent definition files.
   Prompt suggestions are written to RETRO.md; the human runs
   `agent-design apply-suggestion <id>` to have Claude apply them.

**Safety: guaranteed accountability.** The facilitator maintains a checklist
of every agent called out during the retro. RETRO.md is not marked complete
until every item is either resolved (agent self-updated) or explicitly
deferred with a reason.

**The Retrospective Facilitator never applies prompt changes directly.** Agent
definition files are curated by the human. The facilitator's job is to surface
what needs to change and let the human decide.

**RETRO.md format:**
```markdown
# Retrospective — build-out-ansible-deployment — 2026-03-22

## What Went Well
- TDD Engineer and Developer handoff was clean (tests red → green in 2 cycles)
- SRE caught the missing rollback procedure before it reached the runbook draft

## Friction Points
- EM intervened 4 times to relay messages between Developer and Architect.
  Root cause: agents weren't writing status to DISCUSSION.md proactively.
  → Developer self-updated memory: "post to DISCUSSION.md after every task"
  → Architect self-updated memory: "post design decisions to DISCUSSION.md immediately"

- Architect initially proposed Docker for deployment (3 turns wasted).
  → Architect self-updated memory: "read CLAUDE.md before proposing infrastructure"

## Human Interventions
- Mark corrected CI artifact download approach (gh run download → gh release download)
  → Architect self-updated: deployment tooling note
  → SRE self-updated: CI artifact handling
  → Developer: no update (not in their domain — explicitly noted)

## Prompt Suggestions (pending human review)
- [PS-1] architect.md: add "check BASELINE.md for deployment approach before
  proposing infrastructure changes"
- [PS-2] eng_manager.md: "prompt agents to post status in DISCUSSION.md if they
  haven't communicated in >3 turns"
```

---

## PR Feedback → Memory Update

After the implementation PR is pushed and Mark reviews it:

```
agent-design review-feedback --pr https://github.com/.../pull/134
```

This command:
1. Fetches all of Mark's PR comments via GitHub REST API
2. Passes the comments as a block to a brief multi-agent `--print` session
   with all core agents — same model as `remember`
3. Each agent reads all comments and self-updates their own memory if relevant
4. The Retrospective Facilitator verifies pickup and writes a summary to `RETRO.md`

Same principle as `remember`: agents decide for themselves what applies to them.
No router. Facilitator ensures nothing slips through.

---

## Agent Prompt Assessment

The current core agent prompts are in good shape. Specific improvements:

### All agents (universal addition)
**Gap:** No agent currently has instructions about memory self-authorship.

**Add to every agent's system prompt:**
```markdown
## Your memory file

You have read/write access to ~/.claude/agent-memory/<your-name>.md.

Update it yourself when:
- A human corrects or overrides something you proposed
- You realise mid-session that your earlier approach was wrong
- You learn a project-specific constraint that would have changed your output
- The retrospective surfaces a pattern in your behaviour worth recording

Use this format:
  ## Corrections & Overrides
  - YYYY-MM-DD [project]: what happened and what you should do differently

You do not need permission to update your own memory. Do it immediately when
the moment arises, not at the end of the session.
```

### Eng Manager
**Gap:** The current prompt is almost entirely about the implementation phase
(three explicit phases). It says almost nothing about design sessions. It also
has no guidance on what to do when a needed agent doesn't exist.

**Add:**
```markdown
## In design sessions

Read the worktree before your first response:
- BASELINE.md — codebase context
- DESIGN.md — current draft (if it exists)
- DISCUSSION.md — prior team discussion
- feedback/ — any human feedback not yet incorporated

Based on what you read, decide what phase this session covers and tell the
team in your opening message. Do not wait to be told.
```

**Add:** A reminder to read DISCUSSION.md before each session start, not just
at the end of a session.

**Add:** Escalation instructions for missing agents:
```markdown
## When you need an agent that doesn't exist

If you identify a domain gap that no current team member can cover:

1. Post to DISCUSSION.md: state the gap specifically and why none of the
   current team can handle it. Do not just say "we need an expert" — say
   what specific question you can't answer confidently.
2. Write a complete agent proposal to .agent-design/proposals/<name>.md.
   The proposal must include: the gap it fills, proposed location (global
   vs. repo-local) with rationale, agent type (domain expert vs. executor),
   and the complete agent definition file content ready to use as-is.
3. Identify which tasks are gated on the missing agent. For each task,
   ask: "Would proceeding without this agent's input risk implementing
   something wrong?" If yes: mark it 🚫 blocked in TASKS.md with the
   reason. If no: continue. Post a clear summary to DISCUSSION.md:
   "Blocked: [task list]. Proceeding: [task list]."
4. Notify the human and proceed with unblocked tasks.

You never create agent files yourself. You propose; the human approves.
```

### Architect
**Gap:** The Architect does not have an explicit reminder to read CLAUDE.md and
BASELINE.md before making recommendations. In practice, this caused deployment
proposal mistakes (Docker proposal in an Ansible shop).

**Add:**
```markdown
Before proposing any approach:
- Read CLAUDE.md in the target repo for deployment approach, stack constraints,
  and conventions. What's in there is not negotiable.
- Read BASELINE.md for the current state of the codebase you're designing for.
  Proposals that ignore the baseline are wasted turns.
```

**Add:** An explicit instruction to post to DISCUSSION.md when spotting design
drift, rather than waiting for the final review.

### Developer
**Gap:** No guidance on what to do when implementation reveals a gap in the
design (e.g., the design says "use X" but X doesn't exist or doesn't work).

**Add:**
```markdown
When you discover a design gap during implementation:
1. Post to DISCUSSION.md immediately — do not silently work around it
2. State specifically: what the design says, what reality you found, what
   your proposed resolution is
3. Wait for Architect to acknowledge before proceeding with a workaround
Do not mark a task ✅ with a silent deviation from the design.
```

### TDD-Focused Engineer
**Gap:** Good overall. When DESIGN.md doesn't specify test names/targets
explicitly, the current prompt is silent.

**Add:**
```markdown
If DESIGN.md does not specify test names or locations explicitly:
- Derive tests from the acceptance criteria in DESIGN.md
- Follow the naming and location conventions in the existing test suite
  (check BASELINE.md for patterns)
- Document your choices in DISCUSSION.md so Developer knows what to expect
```

### QA Engineer
**Gap:** The design-phase section is thin. QA's strongest value is defining
acceptance criteria *before* implementation — but the current prompt says
little about this.

**Add:**
```markdown
## In design sessions

Your most important work happens here, before anyone writes code.

For every feature component in the proposed design, write acceptance criteria
to DESIGN.md under a "Acceptance Criteria" section:
- Observable: expressed in terms of inputs and outputs, not internal structure
- Testable: concrete enough that anyone could verify them
- Complete: includes success paths, error paths, and edge cases

Push the team until acceptance criteria are clear. "The feature works" is not
an acceptance criterion.
```

---

## CLI Command Map (V2)

```
agent-design init           -- extract feature, create worktree, write BASELINE.md
                               and initial DESIGN.md (Architect solo, --print mode)
agent-design continue       -- continue the workflow from wherever it is.
                               EM reads the worktree and decides: design review?
                               incorporate feedback? already done?
agent-design impl           -- implementation sprint
                               --test-cmd "pytest ..." to set the test gate
agent-design retro          -- retrospective (run once, at end of feature)
agent-design remember       -- route a human correction to agent memory (via agent)
                               "Mark prefers sync pipelines at small scale"
agent-design review-feedback --pr <url>  -- fetch PR review comments, update memories
agent-design review-proposal <name>     -- print a pending agent proposal for review
agent-design apply-proposal <name>      -- write the approved agent file to disk
agent-design refresh-domain --agent <name>  -- refresh a domain expert's volatile
                               knowledge from its authoritative sources
agent-design add-context    -- let Claude add project context to CLAUDE.md
                               (after the human decides it's appropriate)
agent-design status         -- current session state
agent-design rollback       -- revert to a checkpoint
agent-design close          -- clean up worktree and session
```

**`continue` replaces `review` and `revise`** — the EM figures out which
is needed. This eliminates phase tracking from the CLI state machine entirely.
ROUND_STATE.json keeps only: feature slug, feature request, worktree path,
impl branch name, PR URL, checkpoint tag. No phase enum.

---

## Worktree State: What the EM Reads

The EM infers session phase from file presence, not from a phase enum:

| Worktree contains | EM interpretation |
|---|---|
| BASELINE.md only | Initial design not started |
| BASELINE.md + sparse DESIGN.md | Architect's draft, team review needed |
| DESIGN.md + DISCUSSION.md with team entries | Review done, awaiting human |
| feedback/ with unprocessed files | Human feedback ready to incorporate |
| DESIGN.md with "APPROVED" marker | Design complete; move to impl |

The EM writes a brief status assessment to DISCUSSION.md at the start of each
session: "I see feedback round 2 has not been incorporated yet. Spawning team."

---

## Open Questions

**OQ-1: Agent file location — project vs. global** ✅ RESOLVED
Two-tier model:
- **Core and specialist agents** are global: `~/.claude/agents/`. They travel
  with the engineer and work across every project.
- **Domain expert agents** follow a deliberate split: broad expertise goes
  global; project-specific domain knowledge lives in `.claude/agents/` in
  the target repo. The EM discovers both automatically — Claude Code loads
  both at session start. Domain experts irrelevant to a project simply aren't
  spawned because their description won't match the task.

**OQ-2: Memory file location — project vs. machine** ✅ RESOLVED
Memory is global and machine-local: `~/.claude/agent-memory/`. Captures
engineer preferences and cross-project learnings.
Project-specific context lives in the target repo's `CLAUDE.md` — Claude Code
loads it automatically, no plumbing required.

**OQ-3: Retrospective timing** ✅ RESOLVED
Run once, explicitly, at the very end of a complete feature — after design
is approved, impl is done, and the PR is pushed. Not after every session.

**OQ-4: Hook implementation** ✅ RESOLVED
Pass repo path and test command as CLI parameters when invoking `agent-design impl`.
Example: `agent-design impl --repo-path ../news_reader --test-cmd "pytest ..."`.
The CLI sets these as environment variables before launching Claude so hooks
can read them.

**OQ-5: EM decision logging** ✅ RESOLVED
EM writes a brief rationale to TASKS.md whenever it spawns an additional agent.
Example: `| Spawned SRE | Eng Manager | ✅ | deployment procedure review needed |`
This creates a useful audit trail for the Retrospective Facilitator.

**OQ-6: Memory writes by scripts vs. agents** ✅ RESOLVED
Scripts never write to memory files. All memory updates are agent self-authored:
each agent updates its own `~/.claude/agent-memory/<name>.md` file. There is
no `memory_router` agent. The Retrospective Facilitator coordinates and verifies
that relevant agents have self-updated, but does not write on their behalf.

**OQ-7: Prompt changes** ✅ RESOLVED
The Retrospective Facilitator surfaces prompt suggestions in RETRO.md as
`[PS-N]` items. The human reviews them. To apply: `agent-design apply-suggestion PS-1`
launches a `--print` claude session that reads the suggestion and edits the
agent definition file. Humans decide; agents execute the edit.

**OQ-8: Phase tracking in CLI state** ✅ RESOLVED
ROUND_STATE.json stores no phase enum. The EM reads the worktree to determine
where the work is. `continue` is a single command that works at any design
phase.

---

## Implementation Phases

### Phase 1 — Agent files (foundational) ✅ DONE
Convert all `prompts.py` constants to `.claude/agents/*.md` files. Simplify
start prompts to ~20 lines. Validate that Claude Code loads them correctly.

### Phase 2 — Dynamic team composition ✅ DONE
Update EM prompt to decide team composition from task description. Remove
hardcoded team lists from Python CLI. Add available specialists list to start
prompt.

### Phase 3 — Fix claude invocation (no copy-paste) ← human does this
Pass the start message as a positional argument to `claude` in `run_team()`
and `run_team_in_repo()`. Remove the "Paste this to start" Panel from the
launcher. Validate with an end-to-end smoke test.

This is the only phase humans implement after Phase 2. It is small (a few
lines in `launcher.py`) and it is the prerequisite for everything else: once
sessions start without copy-paste, the team can build the rest of itself.

---

### — Bootstrap point —

After Phase 3 is merged, the agent team takes over its own development.
All subsequent phases are implemented by the team running against this repo.

**Why here and not earlier:**
Phase 3 is a hard prerequisite — without it, every team session requires
manual copy-paste, which creates friction on every iteration. Everything
else the team can handle, including improving its own prompts.

**Why not later:**
Waiting for perfect prompts before bootstrapping is backwards. The team's
first post-bootstrap task is to read the Agent Prompt Assessment in this
document and apply it to its own definition files. That is exactly the kind
of work the team is built for — and having the team own its own improvements
is better than a human applying them from the outside.

**The first self-directed sprint is the proof of concept.** If the team
can read DESIGN_V2.md, identify the prompt gaps, and correctly update its
own agent definition files, the system works.

---

### Phase 4 — Self-improvement sprint ← first team-built phase
The team reads the Agent Prompt Assessment section of DESIGN_V2.md and
applies every documented improvement to the relevant agent definition files.
Deliverables:
- All core agent `.md` files updated with the documented additions
- Every agent has the `## Your memory file` self-authorship block
- The EM has design-session guidance and the escalation instructions
- A brief note in DISCUSSION.md for each change, explaining the reasoning

This phase serves a dual purpose: it produces useful output (better prompts)
and it validates the bootstrap (if the team can self-improve, it can build).

### Phase 5 — `continue` command
Replace the `next_round` command with `continue`. Remove phase tracking from
ROUND_STATE.json. Update EM prompt to read worktree and decide phase. Remove
`build_review_start()` and `build_feedback_start()` from `prompts.py`; replace
with a single `build_continue_start()`.

### Phase 6 — Specialist agent files
Write agent definition files for SRE, PM, Security Engineer, Database
Architect, Technical Writer, and Performance Engineer. For each: validate the
description is precise enough that the EM spawns them for the right tasks and
skips them for the wrong ones. Run targeted EM tests: given a task description,
does the EM's team composition include/exclude the right specialists?

### Phase 7 — Memory infrastructure
Implement `agent-design remember` command: a `--print` multi-agent session
(all core agents + Retrospective Facilitator) where each agent self-updates
if relevant, and the Facilitator verifies pickup. Implement
`agent-design review-feedback` command using the same pattern.

### Phase 8 — Retrospective
Implement `agent-design retro` command. Write the Retrospective Facilitator
agent definition. Implement `agent-design apply-suggestion` command. Run a
full retrospective against the session history from Phases 4–7 as validation.

### Phase 9 — Hooks
Implement `task_completed.sh` hook for test gating. Implement
`teammate_idle.sh` for TASKS.md status enforcement. Wire both into
`agent-design impl` via the `--test-cmd` parameter.

### Phase 10 — Domain experts and proposal escalation
Write `claude_expert.md` and `agent_systems_expert.md` in `.claude/agents/`
in this repo. Define the memory file structure (stable/volatile/sources/
pending) for each. Implement `agent-design refresh-domain`,
`agent-design review-proposal`, and `agent-design apply-proposal` commands.
Validate a full cycle: EM identifies a gap mid-session, writes a proposal,
human reviews and applies it, new agent is spawned into the running session.

