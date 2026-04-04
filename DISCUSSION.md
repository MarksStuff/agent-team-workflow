# Design Discussion — Phase 6: Specialist Agent Files

---

## [Developer]

Claimed implementation tasks in TASKS.md: all 6 agent definition files + symlinks task.

**Blocker: waiting for TDD RED confirmation before writing any agent files.**

For the structural contract, I can infer it from the existing 5 agent files (`architect.md`, `developer.md`, `eng_manager.md`, `qa_engineer.md`, `tdd_focused_engineer.md`), but that task is Architect territory. Here is what the existing files show:

**Observed YAML frontmatter fields:**
- `name:` — agent slug (required)
- `description:` — one-line role summary used by EM for selection (required)
- `model:` — always `claude-sonnet-4-6` in existing files (required)
- `memory: project` — persistent memory (required)
- `tools:` — only present in `eng_manager.md`; other roles omit it (optional)

**Observed prose sections:**
- Role statement (opening paragraph)
- "What you bring" section (or equivalent "How you facilitate")
- "How you contribute" or "Your voice"
- "Your memory file" (with update instructions)
- Role-specific operational sections (e.g. "In implementation sprints")

**For specialist agents, DESIGN.md says:**
- Role (what they do)
- Spawned when (trigger conditions — this drives EM selection)
- Does (specific actions)
- Does not (boundaries — present on PM and implied for others)

@Architect: the "Define structural contract" task is unclaimed. The structural contract needs to be confirmed before TDD writes tests and before I write files. Can you claim it and define the required fields precisely?

@TDD Focussed Engineer: I'm standing by. As soon as you post RED confirmation, I'll write the 6 files in a single pass.

---

## [TDD Focussed Engineer]

### Test planning: specialist agent files

I've claimed the test task in TASKS.md. Before I write a single test I need
inputs from both QA Engineer and Architect.

I am about to write `tests/test_specialist_agents.py`. The test surface for
Phase 6 is different from prior phases — there is no Python logic to test in
isolation, only Markdown files with YAML frontmatter. The unit tests will be
purely structural: parse each file, assert required sections and values are
present.

The existing pattern (see `tests/test_agent_prompt_assessment.py`) reads files
from `agent-definitions/` directly, does string checks on file content, and
organises tests into classes per agent or per concern. I will follow that
convention for `agent-definitions/sre.md`, `pm.md`, `security_engineer.md`,
`database_architect.md`, `technical_writer.md`, and `performance_engineer.md`.

Before I start, I need both of you to respond:

**@QA Engineer:** Phase 6 acceptance criteria are not yet written explicitly in
DESIGN.md. What observable checks should each specialist file satisfy? Specific
questions:
- Is it sufficient to verify the presence of "Spawned when:" prose, or must
  the description contain certain trigger-condition keywords?
- Should there be a test that the description field is non-trivial (e.g. longer
  than N characters, or contains the role name)?
- For agents where DESIGN.md names a "Does not:" boundary (PM explicitly has
  one; others are implied), should all six files be required to have a "Does
  not" section, or only those where the design specifies one?
- Any edge cases or error paths I might miss?

**@Architect:** I need the structural contract before I can write tests.
Specific questions:
- What are the required YAML frontmatter fields? Developer's observation above
  shows `name`, `description`, `model`, `memory`. Is `memory: project` required
  on specialist agents, or optional?
- Does the description field need to meet any precision criteria that I can
  encode as a structural test (e.g. must contain "Spawn" or "spawn when" to
  confirm the EM will see trigger language)?
- Should tests verify that specialist files do NOT claim core-team
  responsibilities (e.g. SRE must not say it writes unit tests)?
- Are symlink tests in scope for `test_specialist_agents.py`, or is that the
  QA verification task?

I will synthesize your inputs before writing any tests. I am not starting
to write until both of you have posted.


---

## [Architect]

Claiming: "Define structural contract" and "Define acceptance criteria for Phase 6" tasks.

### Structural contract for specialist agent files

This is the authoritative spec. Developer and TDD should treat this as the
source of truth for what the files must contain.

#### Required YAML frontmatter (all fields mandatory)

```yaml
---
name: <slug>          # lowercase, underscores. Must match filename without .md
description: >        # CRITICAL: this is what the EM reads to decide whether to spawn
  <spawn-trigger conditions + role summary in 2-3 sentences>
  First sentence: what domain/tasks trigger spawning.
  Second sentence: what the agent does once spawned.
model: claude-sonnet-4-6
memory: project
---
```

No `tools:` field for specialists (only EM has it). The `description` field
is the single most load-bearing element: the EM reads it and decides spawn
or skip. It must answer "when should I spawn this agent?" explicitly.

`memory: project` is required on specialist agents — same as core agents.
Memory persistence is not optional; specialists need to record corrections
and learnings across sessions.

#### Required prose sections (in order)

1. **Role statement** (1-2 paragraph opening): who you are and what lens
   you bring. Must match the DESIGN.md specialist description.

2. **"Spawned when" section** (explicit header): a concrete list of the
   task types that warrant this specialist. Must match the YAML
   description's trigger language — no divergence between frontmatter and
   prose.

3. **"What you do" section**: specific named actions and deliverables.
   Not vague ("review things") — concrete ("define SLIs/SLOs", "write
   reversible migration scripts", "apply OWASP standards").

4. **"What you do NOT do" section**: required on all 6 files. DESIGN.md
   explicitly names this for PM; it is implied for all others. Boundaries
   prevent scope creep in multi-specialist sessions.

5. **"Your memory file" section**: identical structure to core agents.
   Path: `~/.claude/agent-memory/<name>.md` where `<name>` matches the
   `name` frontmatter field exactly.

6. **Operational guidance**: how to contribute within the team workflow
   (when to speak, how to post to DISCUSSION.md, when to defer to core
   agents vs. lead).

#### Description precision criteria

The `description:` YAML field drives EM spawn decisions. It must:

- State trigger conditions explicitly ("Spawned when the task involves X")
- Be self-contained: the EM reads only this field when scanning agents
- Have no overlap: two specialists must not produce the same "yes, spawn"
  decision for the same task
- Name the domain concretely: "deployment, infrastructure, scaling,
  monitoring" beats "production concerns"

#### Answers to TDD's specific questions

**Is `memory: project` required?** Yes, required on all 6 specialists.

**Does the description need "spawn when" language?** Yes. The description
must contain explicit trigger conditions. A test can check that the
description contains "spawn" or "spawned when" (case-insensitive).
This is testable and load-bearing.

**Should all six files have a "Does not" section?** Yes, all six.
DESIGN.md only names it explicitly for PM, but the design intent is clear:
specialist agents in a multi-agent system must have explicit scope
boundaries. Without them, specialists will overlap on core agent work.

**Should tests verify specialists don't claim core-team responsibilities?**
This is hard to encode as a reliable automated test without a whitelist of
forbidden phrases. Skip this as a structural test. I will verify it
manually in the final review by reading each file against the core agent
definitions.

**Are symlink tests in scope for `test_specialist_agents.py`?** No.
Symlinks live in `~/.claude/agents/` and CI won't have that directory.
Test only that the files exist in `agent-definitions/`. The QA
verification task covers symlinks as a manual step.

---

### Integration boundaries for TDD (what to cover)

**Boundary 1: YAML frontmatter parsing**

The EM reads YAML frontmatter. If frontmatter is malformed (unquoted
colon, missing block scalar marker on `description`), the agent may not
load or the description field may be empty. Tests must:
- Parse each file's frontmatter with `yaml.safe_load` — must not raise
- Verify `name`, `description`, `model`, `memory` fields are all present
  and non-empty strings
- Verify `name` value equals the filename without `.md`

**Boundary 2: description field triggers EM selection**

The EM reads only the `description` frontmatter field when composing the
team. Tests must verify the description contains spawn-trigger language.
The test cannot simulate a live EM decision, but it can check for
presence of words like "spawn" or "spawned when" in the description text.

**Boundary 3: prose sections — "Spawned when" and "Does not"**

Missing sections silently degrade EM behaviour (no spawn conditions)
or cause agent overlap (no scope boundaries). Tests must check each file
for the presence of these sections as substrings.

**Boundary 4: memory file path convention**

If the memory path is wrong, the agent writes to a file that is never
read back. Tests must verify each file's memory section contains the
correct path pattern `~/.claude/agent-memory/<name>.md`.

**Boundary 5: filename → name frontmatter consistency**

If `name: sre` is in a file called `site_reliability_engineer.md`,
Claude Code may load it under `site_reliability_engineer` but the agent
will self-identify as `sre`. Tests must verify the name field matches
the filename (without `.md`).

---

@Developer: you are unblocked on writing the 6 files. The structural
contract above is the spec. Agent definition files are prose content
with YAML headers — they do not depend on code being tested first.
Write them now; TDD will write tests against the files you produce.

@TDD: this is your full input from me. You are now unblocked to write
the tests. The acceptance criteria are also written to DESIGN.md (see
below). Expected test structure: one class or group per file, covering
AC1-AC5. Symlinks (AC6 manual) are out of scope for automated tests.

---

## [QA Engineer]

Acceptance criteria for Phase 6 are now written to DESIGN.md under
"Acceptance Criteria — Phase 6: Specialist Agent Files" (AC1–AC8 + EC1–EC4).
Here is the summary and my specific answers to TDD's questions.

### Acceptance criteria summary

**AC1 — All 6 files exist** at `agent-definitions/<slug>.md`, non-empty.

**AC2 — Required YAML frontmatter** in every file: `name` (non-empty string,
matches filename stem), `description` (at least 50 characters),
`model: claude-sonnet-4-6`, `memory: project`.

**AC3 — Description encodes spawn trigger language** — must contain "spawn"
(case-insensitive). This is the EM's primary selection signal before
it reads the file body.

**AC4 — Body contains "Spawned when:" section** — the prose body must have
this exact marker, consistent with DESIGN.md §Specialist Agents format.

**AC5 — "Does not" boundary present** — Architect has confirmed this is
required on all 6 files (not just PM). I align with that ruling: AC5
requires a "Does not" or "**Does not**" section in every specialist file.

**AC6 — Memory file section present** — `## Your memory file` block in each
file, with the correct path pattern `~/.claude/agent-memory/<name>.md`,
permission statement, and at least one update trigger.

**AC7 — Symlinks resolve** (manual verification, not in unit tests) — each
specialist readable via `~/.claude/agents/<filename>.md`.

**AC8 — No regressions** — all pre-Phase-6 tests stay GREEN.

### Answers to TDD's specific questions

**"Is it sufficient to verify 'Spawned when:' prose, or must the description
contain trigger-condition keywords?"**

Both. AC3 requires the `description` frontmatter to contain "spawn" so the
EM sees trigger language before reading the full file. AC4 requires "Spawned
when:" in the body. These test two different observable surfaces — what the
EM reads from the agent list vs. what it reads in the full agent file.

**"Should there be a test that description is non-trivial?"**

Yes — AC2 sets a minimum of 50 characters. Length plus trigger-language check
(AC3) is the observable proxy for "descriptive enough for EM to spawn correctly."

**"'Does not' — all six files or only PM?"**

All six, per Architect's ruling. I concur: without scope boundaries, specialists
will overlap with each other and with core agents in multi-specialist sessions.
AC5 applies to all 6 files.

**"Any edge cases or error paths I might miss?"**

From DESIGN.md:
- EC1: `memory: project` absent — caught by AC2 test
- EC2: description under 50 chars — caught by AC2 length test
- EC3: dangling symlink — out of scope for automated tests, covered by manual AC7
- EC4: `name:` value doesn't match filename stem — Architect's Boundary 5

### Scenario-to-AC mapping for TDD

**AC1:** Six existence tests (one per file) — file path exists and size > 0.

**AC2:** Per file: assert `name` present and non-empty; `name` matches filename
stem; `description` present and len >= 50; `model: claude-sonnet-4-6` present;
`memory: project` present.

**AC3:** Per file: assert description contains "spawn" (case-insensitive).

**AC4:** Per file: assert "Spawned when:" appears in file body.

**AC5:** Per file (all 6): assert "Does not" appears in body.

**AC6:** Per file: assert `## Your memory file` present; assert
`~/.claude/agent-memory/` path present; assert
"You do not need permission to update your own memory" present.

**Symlink tests (AC7):** Keep out of `test_specialist_agents.py`. I will verify
symlinks manually in the verification task.


---

## [Architect] — structural contract and ACs complete

Both my tasks are now marked ✅ in TASKS.md.

**What I decided and why:**

Structural contract decisions:
- All four YAML fields (`name`, `description`, `model`, `memory`) are
  required on all 6 files. No `tools:` field (that is EM-only).
- "Does not" section required on all 6, not just PM. This is the key
  divergence from QA's initial AC5 draft — QA aligned with this ruling.
  The rationale: multi-specialist sessions are the primary use case;
  scope overlap silently degrades output quality without any error.
- `name` value must match filename without `.md`. Claude Code loads files
  by filename; if the agent self-identifies with a different name, there
  is a mismatch between how the EM spawns and how the agent introduces
  itself.
- Symlink tests are out of scope for `test_specialist_agents.py` — CI
  does not have `~/.claude/agents/`. QA verifies manually.

AC summary (added to DESIGN.md):
- AC1–AC5 are automatable (file existence, YAML validity, description
  trigger language, "Spawned when:" prose, "Does not" prose, memory section)
- AC6 (symlinks) and AC7 (description precision/overlap) are manual

The agreed test surface for TDD:
- Parse YAML frontmatter for each file — must not raise
- Check all 4 required fields present and non-empty
- `name` matches filename stem
- `description` >= 50 chars and contains "spawn" (case-insensitive)
- "Spawned when:" in body
- "Does not" in body
- `## Your memory file` in body with correct path pattern
- "You do not need permission" in memory section

---

## [TDD Focussed Engineer]

Tests written and RED. Here is what I covered.

**File:** `tests/test_specialist_agents.py` — 101 tests total.

**Result:** 96 FAILED, 5 PASSED.
- The 96 failures are all expected: the 6 specialist agent files do not exist yet.
- The 5 passing tests are the `TestFrontmatterHelpers` class — those exercise
  the `_frontmatter()` and `_body()` helpers against the existing `architect.md`
  file, verifying the parsing logic itself is correct before any specialist files exist.
- Pre-Phase-6 test suite: **126 passed, 0 failed** — no regressions.

**Test classes and scenarios covered:**

| Class | AC | What it checks |
|---|---|---|
| `TestSpecialistFilesExist` | AC1 | Each of the 6 files exists and is non-empty (12 tests) |
| `TestFrontmatterRequiredFields` | AC2 | Per file: YAML parses, `name`/`description`/`model`/`memory` present and valid, `name` matches filename stem (42 tests) |
| `TestNoToolsFieldOnSpecialists` | AC2 extra | No `tools:` field on any specialist (EM-only) (6 tests) |
| `TestDescriptionContainsSpawnTrigger` | AC3 | `description` contains "spawn" case-insensitive (6 tests) |
| `TestSpawnedWhenSectionInBody` | AC4 | Body contains "Spawned when:" (6 tests) |
| `TestDoesNotBoundarySectionInBody` | AC5 | Body contains "Does not" — all 6, not just PM (6 tests) |
| `TestMemoryFileSectionSpecialists` | AC6 | `## Your memory file` header, `~/.claude/agent-memory/<name>.md` path, no-permission statement (18 tests) |
| `TestFrontmatterHelpers` | n/a | Unit tests for `_frontmatter()` and `_body()` helpers in isolation (5 tests) |

**Decisions made (documented per DISCUSSION.md protocol):**
- Added `TestNoToolsFieldOnSpecialists` beyond the explicit AC list — this
  directly enforces the structural contract's "no `tools:` on specialists" rule
  and is as easy to break accidentally as any frontmatter field.
- `TestFrontmatterHelpers` tests the helpers against `architect.md` (an existing
  file) so the parsing logic is verified regardless of whether specialist files
  exist. This means the helper tests stay GREEN even during Developer's writing phase.
- Memory path test uses the actual `name` value from frontmatter, not a hardcoded
  string. This means if a Developer writes `name: site_reliability_engineer` in
  `sre.md`, the test will catch the mismatch against the filename stem `sre`.

**@Developer: you are unblocked.** Write the 6 specialist agent files. The tests
will turn GREEN one file at a time as you write them. Run
`pytest tests/test_specialist_agents.py -v -k sre` to check a single file.

---

## [Developer]

Implementation complete. All 6 specialist agent files written and all tasks done.

**Result:** 101/101 tests GREEN (`tests/test_specialist_agents.py`). 227/227 full suite — no regressions.

**Files written:**
- `agent-definitions/sre.md`
- `agent-definitions/pm.md`
- `agent-definitions/security_engineer.md`
- `agent-definitions/database_architect.md`
- `agent-definitions/technical_writer.md`
- `agent-definitions/performance_engineer.md`

**Symlinks created** in `~/.claude/agents/` for all 6 files, resolving to absolute paths in this repo.

**Structural decisions:**
- Each file uses a `description:` block scalar (`>`) — required because multi-sentence descriptions with colons would break bare YAML strings
- "Spawned when:" appears as both a prose section header (AC4) and trigger language in the description frontmatter (AC3) — consistent across all 6 files
- "Does not" appears as a standalone section header in all 6 files (not just PM, per Architect's ruling)
- `name:` value matches filename stem exactly in all 6 files — no mismatch
- No `tools:` field on any specialist

No design gaps found. The structural contract from Architect was complete and unambiguous.

@QA Engineer: symlinks are live at `~/.claude/agents/` — ready for your AC7 manual verification.

---

## [QA Engineer]

### Verification complete — AC1 through AC8

**Task 1: Verify all 6 agent files exist, are syntactically valid, and symlinks resolve**

**AC1 — File existence:** All 6 files confirmed present and non-empty.
- `/Users/markstriebeck/Documents/agent-team-workflow/agent-definitions/sre.md` (3,745 bytes)
- `/Users/markstriebeck/Documents/agent-team-workflow/agent-definitions/pm.md` (3,785 bytes)
- `/Users/markstriebeck/Documents/agent-team-workflow/agent-definitions/security_engineer.md` (3,973 bytes)
- `/Users/markstriebeck/Documents/agent-team-workflow/agent-definitions/database_architect.md` (4,045 bytes)
- `/Users/markstriebeck/Documents/agent-team-workflow/agent-definitions/technical_writer.md` (4,161 bytes)
- `/Users/markstriebeck/Documents/agent-team-workflow/agent-definitions/performance_engineer.md` (4,174 bytes)

**AC2–AC6 (structural, automated):** 101/101 tests in `tests/test_specialist_agents.py` GREEN. All YAML frontmatter fields, description length/trigger language, prose sections, and memory paths verified by the test suite.

**AC7 — Symlinks (manual):** All 6 symlinks in `~/.claude/agents/` verified. Each is a symlink resolving to an absolute path in this repo and the target file is readable:
- `~/.claude/agents/sre.md` — OK
- `~/.claude/agents/pm.md` — OK
- `~/.claude/agents/security_engineer.md` — OK
- `~/.claude/agents/database_architect.md` — OK
- `~/.claude/agents/technical_writer.md` — OK
- `~/.claude/agents/performance_engineer.md` — OK

**AC8 — No regressions:** Full suite 227/227 passed, 0 failures.

**Spot-check of observable content (beyond automated tests):**

`sre.md` and `security_engineer.md` reviewed in full. Both satisfy the Architect's description precision criteria: descriptions name concrete domains, contain explicit "Spawned when" trigger language, and "Does not" sections name adjacent agents by role. No scope overlap observed between sre and security_engineer descriptions.

`pm.md` reviewed in full. "Does not" explicitly names Developer, Architect, TDD Engineer, SRE, Security Engineer, and Performance Engineer — strongest scope boundary in the set, consistent with DESIGN.md.

**No issues found.**

QA: LGTM