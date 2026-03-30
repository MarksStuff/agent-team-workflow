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

V2 fixes all of these.

---

## Core Design Principles (Revised)

**Agents are files, not strings.**

Each agent is a Markdown file with YAML frontmatter, stored in `.claude/agents/`.
Claude Code loads them automatically at session start. The start prompt is just
the task — agent identities, tools, and memory live in their definition files.

**The EM composes the team, not the CLI.**

The Python CLI starts a session and hands off a task. The Eng Manager reads the
task, decides which specialists are needed, and spawns them. The CLI has no
knowledge of team composition.

**Memory is cumulative and owned by agents.**

Each agent has a persistent memory file updated across sessions. When a human
makes a decision, the relevant agent's memory is updated. Agents get better at
this specific codebase and team over time.

**Quality gates are enforced, not hoped for.**

Claude Code hooks reject task completion if tests don't pass. Agents cannot mark
work done until the gate passes.

**Retrospectives close the feedback loop.**

Every session ends with a retrospective. Lessons learned update agent memories
and prompts. The system is self-improving.

---

## The Agent Roster

### Core Engineering Team

These agents participate in most sessions. The EM decides the initial composition;
agents may request additional specialists mid-session.

---

#### Eng Manager
**Role:** Team lead, task board owner, gate keeper.
**Does not:** Make technical decisions, assign implementation work, or relay
messages between agents.
**Does:** Compose the initial team for a task, monitor TASKS.md for stalled or
unclaimed work, facilitate phase transitions, request additional specialists when
the team surfaces a domain it can't handle, call the session complete when
Architect and QA both sign off.

*Dynamic team composition is the EM's primary skill.* Given a task description,
the EM decides which 2–5 specialists to spawn. For a deployment task: SRE is
mandatory, Security Engineer likely, Performance Engineer probably not. For a
new API: Database Architect, Security Engineer, TDD Engineer all relevant.
The EM can spawn more agents mid-session if new concerns surface.

---

#### Architect
**Role:** Systems design, technical direction, design-drift detection.
**Does:** Own the design document, evaluate proposals against system-wide
constraints, detect when implementation diverges from agreed design, veto
changes that violate architectural principles.
**Does not:** Write implementation code, assign work to teammates.

---

#### Developer
**Role:** Implementation, pragmatic velocity.
**Does:** Write the actual code, raise practical concerns about implementation
approaches, implement to make TDD Engineer's tests pass.
**Does not:** Skip failing tests, mark tasks done before tests are green.

---

#### TDD-Focused Engineer
**Role:** Test-first discipline, testability, coverage.
**Does:** Write tests before implementation (red → green), validate that
tests are red before signalling Developer, verify tests are green before
signing off on tasks, raise concerns about untestable designs.
**Does not:** Let Developer begin until tests are written and confirmed red.

---

#### QA Engineer
**Role:** Acceptance criteria, observable behaviour, deployment readiness.
**Does:** Define what "done" looks like from a user/operator perspective,
verify implementation satisfies acceptance criteria from the design doc,
own the final "would this actually work in production" sign-off.
**Does not:** Write unit tests (that's TDD Engineer's job).

---

### Specialist Agents

Spawned by the EM when the task warrants it.

---

#### SRE (Site Reliability Engineer)
**Role:** Production readiness, deployment safety, observability.
**Spawned when:** The task involves deployment, infrastructure, scaling,
monitoring, on-call impact, rollback procedures, or runbooks.
**Does:** Review deployment procedures for safety and reversibility, define
SLIs/SLOs for new functionality, specify monitoring and alerting requirements,
write or review runbooks, flag single points of failure, require rollback
procedures before approving deployment-related tasks.

---

#### PM (Product Manager)
**Role:** Requirements clarity, scope control, user value.
**Spawned when:** Requirements are ambiguous, scope is creeping, or the team
is debating what to build rather than how.
**Does:** Sharpen acceptance criteria, ask "what problem does this solve for
the user", push back on over-engineering, define the minimal viable scope,
document deferred items explicitly.
**Does not:** Make technical decisions.

---

#### Security Engineer
**Role:** Threat modelling, security review, vulnerability detection.
**Spawned when:** The task touches authentication, authorisation, data
handling, external inputs, secrets, or public-facing surfaces.
**Does:** Identify attack vectors, review auth flows, flag injection risks,
check secrets handling, require security test coverage for sensitive paths,
apply OWASP standards.

---

#### Database Architect
**Role:** Schema design, migrations, data integrity, query performance.
**Spawned when:** The task involves schema changes, new tables, migrations,
data contracts between services, or complex queries.
**Does:** Review schema for normalisation and integrity, require migration
scripts to be reversible, flag missing indexes, define data contracts, prevent
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
**Does:** Define performance budgets, identify bottlenecks in proposed
implementations, require load tests for critical paths.

---

#### Retrospective Facilitator
**Role:** Process improvement, memory update, system self-improvement.
**Spawned at the end of every session** (not during implementation).
**Does:** Review DISCUSSION.md, TASKS.md, DECISIONS.md, and human intervention
events to identify what went well, what got stuck, and where humans had to
correct the team. Updates each relevant agent's memory file with lessons
learned. Produces RETRO.md. May suggest prompt changes.

---

## Agent Files: Structure and Storage

Each agent is a Markdown file with YAML frontmatter. Claude Code loads these
automatically — no Python plumbing required.

```
agent-team-workflow/
  .claude/
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
file for this agent at `.claude/agent-memory/architect.md`. This file is updated
by the Retrospective Facilitator and by human intervention events.

### Agent memory files

```
agent-team-workflow/
  .claude/
    agent-memory/
      architect.md        ← accumulated learnings across sessions
      developer.md
      tdd_engineer.md
      qa_engineer.md
      sre.md
      ...
```

**Format:**

```markdown
# Architect Memory

## Team & Codebase Context
- This codebase is a Swift news reader deploying to Proxmox LXC via Ansible
- Mark prefers interface-first design: protocols defined before implementations
- Tests live in separate targets, never mixed with production code

## Decisions & Preferences
- 2026-03-22: Mark overrode recommendation for async queue in favour of
  synchronous pipeline for Phase 5. Reason: simpler to operate at current scale.
  Apply this preference to future infrastructure proposals.

## Lessons Learned
- 2026-03-20: Attempted to use Docker for deployment; Mark corrected to Ansible.
  Always check BASELINE.md for deployment approach before proposing alternatives.
```

Memory files are committed to the repo so they persist across machines and
are visible to the whole team.

---

## The Start Prompt (Dramatically Simplified)

With agents defined as files, the start prompt shrinks from ~500 lines to ~20:

### Design phase

```
Task: design review for the feature described in .agent-design/FEATURE.md

Available specialists: architect, developer, tdd_engineer, qa_engineer, sre,
pm, security_engineer, database_architect, technical_writer

Spawn the specialists most relevant to this feature. Create DISCUSSION.md.
Run a free-form design discussion. Converge on DESIGN.md and DECISIONS.md.
```

### Implementation phase

```
Task: implement the design in .agent-design/DESIGN.md

Available specialists: architect, developer, tdd_engineer, qa_engineer, sre,
pm, security_engineer, database_architect, technical_writer

Spawn who you need. Create TASKS.md. Run three phases:
1. Sprint planning — self-assign tasks
2. Implementation — TDD first, tests gate completion
3. Final review — Architect + QA sign off before declaring done
```

Claude Code loads each spawned agent's full definition and memory automatically.
No Python string interpolation needed.

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

## Human Intervention → Memory Update

When Mark steps in to make a decision, correct an agent, or override a choice,
that event is high-signal feedback. The CLI captures it:

```
agent-design remember --agent architect \
  "Mark overrode async queue recommendation for synchronous pipeline. \
   Reason: simpler to operate at current scale."
```

Or interactively during a session: after intervening, the user types a note
and it's routed to the right agent's memory file automatically.

This is the tightest possible feedback loop: every human correction directly
improves the agent that made the mistake.

---

## The Retrospective

A first-class command run at the end of every session:

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
3. Updates each relevant agent's memory file with specific, dated lessons
4. Suggests prompt improvements for agent definition files
5. Produces `RETRO.md` in the worktree

**RETRO.md format:**
```markdown
# Retrospective — build-out-ansible-deployment — 2026-03-22

## What Went Well
- TDD Engineer and Developer handoff was clean (tests red → green in 2 cycles)
- SRE caught the missing rollback procedure before it reached the runbook draft

## Friction Points
- EM intervened 4 times to relay messages between Developer and Architect.
  Root cause: agents weren't writing status to DISCUSSION.md proactively.
  Fix: updated developer.md and architect.md memory to write to DISCUSSION.md
  after every significant decision.

- Architect initially proposed Docker for deployment (3 turns wasted).
  Fix: updated architect.md memory with deployment approach for this codebase.

## Human Interventions
- Mark corrected CI artifact download approach (gh run download → gh release download)
  Routed to: architect.md, sre.md, developer.md memories.

## Prompt Suggestions
- architect.md: add "check BASELINE.md for deployment approach before proposing
  infrastructure changes"
- eng_manager.md: "prompt agents to post status in DISCUSSION.md if they haven't
  communicated in >3 turns"
```

---

## Final PR Review → Memory Update

After the implementation PR is pushed and Mark reviews it:

```
agent-design review-feedback --pr https://github.com/.../pull/134
```

This command:
1. Fetches all of Mark's PR comments via GitHub REST API
2. Routes each comment to the most relevant agent's memory
   (implementation comments → developer.md, test comments → tdd_engineer.md, etc.)
3. Writes a summary of feedback to `RETRO.md`

Mark's PR review is the highest-signal feedback in the whole workflow — it
represents real corrections on real output. Capturing it as agent memory means
those mistakes don't recur.

---

## CLI Command Map (V2)

```
agent-design init        -- extract feature, write BASELINE.md, initial DESIGN.md
agent-design next        -- team design review + feedback incorporation
agent-design impl        -- implementation sprint (planning → impl → review)
agent-design retro       -- retrospective, update agent memories
agent-design remember    -- manually route a correction to an agent's memory
agent-design review-feedback --pr <url>  -- fetch PR comments, update memories
agent-design status      -- current session state
agent-design rollback    -- revert to a checkpoint
agent-design close       -- clean up worktree and session
```

---

## Migration from V1

V1 `prompts.py` → V2 agent files:

| V1 | V2 |
|---|---|
| `AGENT_ARCHITECT` string | `.claude/agents/architect.md` |
| `AGENT_ENG_MANAGER_IMPL` string | `.claude/agents/eng_manager.md` |
| `_STAGE_IMPL_TASK` string | Start prompt (20 lines) |
| `_IMPL_INSTRUCTIONS["Developer"]` | `developer.md` system prompt |
| `build_impl_start()` function | Deleted — Claude Code handles it |

The Python CLI shrinks significantly. It manages:
- Git state (branches, worktrees, checkpoints, PRs)
- Session phase tracking (ROUND_STATE.json)
- GitHub API calls (feedback fetch, PR creation)
- Memory routing (human interventions, retro output)

It no longer manages:
- Agent identities
- Team composition
- Teammate spawn prompts

---

## Open Questions

**OQ-1: Agent file location — project vs. global**
Option A: `.claude/agents/` in the `agent-team-workflow` repo (version-controlled,
team-shared, checked into the repo alongside the CLI).
Option B: `~/.claude/agents/` (global, available in any project).
Leaning A for most agents (they're project-workflow-specific), with the option
to promote stable agents to global later.

**OQ-2: Memory file location — project vs. machine**
Agent memories contain codebase-specific learnings that should persist across
machines (e.g., "this project uses Ansible, not Docker"). Committing them to
the repo solves persistence but exposes internal team context in a public repo.
Options: commit to repo, store in `~/.claude/agent-memory/` (machine-local),
or store in a private gist/repo.

**OQ-3: Retrospective timing**
Run retro automatically after every `impl` session, or as an explicit command
the human invokes? Automatic is better for building the habit; explicit gives
more control. Proposal: run automatically but with `--skip-retro` flag to opt out.

**OQ-4: Hook implementation**
The `task_completed.sh` hook needs to know the repo path and which test suite
to run. These are session-specific. Options: pass via environment variables
set by the CLI before launching Claude, or read from a config file in the worktree.

**OQ-5: EM decision logging**
When the EM decides to spawn a specialist mid-session, that decision should be
visible and reviewable. Proposal: EM writes a brief rationale to TASKS.md when
spawning additional agents ("Spawning SRE: deployment procedure review needed").

---

## Implementation Phases

### Phase 1 — Agent files (foundational)
Convert all `prompts.py` constants to `.claude/agents/*.md` files. Simplify
start prompts to ~20 lines. Validate that Claude Code loads them correctly.

### Phase 2 — Dynamic team composition
Update EM prompt to decide team composition from task description. Remove
hardcoded team lists from Python CLI. Add available specialists list to start prompt.

### Phase 3 — Memory infrastructure
Create `agent-memory/` directory structure. Implement `agent-design remember`
command. Implement `agent-design review-feedback` command.

### Phase 4 — Retrospective
Implement `agent-design retro` command. Define Retrospective Facilitator agent.
Wire retro to run automatically after `impl`.

### Phase 5 — Hooks
Implement `task_completed.sh` hook for test gating. Implement `teammate_idle.sh`
for TASKS.md enforcement.

### Phase 6 — Specialist agents
Add SRE, PM, Security Engineer, Database Architect, Technical Writer, Performance
Engineer agent files. Validate EM correctly identifies when to spawn each.
