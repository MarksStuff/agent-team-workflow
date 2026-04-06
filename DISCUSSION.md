# Design Discussion — Phase 10: Domain Experts and Proposal Escalation

---

## [Eng Manager]

**Phase 10 sprint begins.**

**Scope:** We are implementing § Domain Expert Agents (DESIGN.md lines 230–481) and the three CLI commands for domain expert management (`refresh-domain`, `review-proposal`, `apply-proposal`).

**Deliverables:**
1. Two repo-local domain expert agent files in `.claude/agents/`: `claude_expert.md` and `agent_systems_expert.md`
2. Memory file structure for both (stable/volatile/sources/pending sections)
3. Three CLI commands: `refresh-domain`, `review-proposal`, `apply-proposal`
4. Full test coverage and end-to-end validation

**Team spawned:**
- Architect — design review, interface contracts, drift detection
- QA Engineer — acceptance criteria definition and final verification
- TDD Focussed Engineer — tests first (RED → GREEN)
- Developer — implementation after tests are RED

**Sprint Planning:** Each agent should now claim tasks in TASKS.md based on your expertise. TDD-Focused Engineer: you go first — claim test tasks and write tests RED before Developer starts any implementation.

**Everything else in DESIGN.md is out of scope for this phase.**

---
