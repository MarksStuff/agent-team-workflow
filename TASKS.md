# TASKS.md — Phase 6: Specialist Agent Files

## Scope
Implement §Specialist Agents (DESIGN.md lines 164–228).
Six specialist agent definition files + tests for EM selection behaviour.
Domain Expert Agents (Phase 10) and CLI commands are out of scope.

## Task Board

| Task | Owner | Status |
|---|---|---|
| Define structural contract for specialist agent files: required YAML frontmatter fields, required prose sections, and description precision criteria | Architect | ✅ done |
| Write `agent-definitions/sre.md` — SRE specialist agent | Developer | ✅ done |
| Write `agent-definitions/pm.md` — PM specialist agent | Developer | ✅ done |
| Write `agent-definitions/security_engineer.md` — Security Engineer specialist agent | Developer | ✅ done |
| Write `agent-definitions/database_architect.md` — Database Architect specialist agent | Developer | ✅ done |
| Write `agent-definitions/technical_writer.md` — Technical Writer specialist agent | Developer | ✅ done |
| Write `agent-definitions/performance_engineer.md` — Performance Engineer specialist agent | Developer | ✅ done |
| Create symlinks in `~/.claude/agents/` for all 6 new specialist files (run `bash scripts/setup.sh` or create manually) | Developer | ✅ done |
| Write tests in `tests/test_specialist_agents.py` verifying each agent file has correct frontmatter (name, description, model), spawn-condition prose, does-not-do boundaries where applicable, and memory file section | TDD Focussed Engineer | ✅ done |
| Define acceptance criteria for Phase 6: observable checks for each specialist file | Architect | ✅ done |
| Verify all 6 agent files exist, are syntactically valid, and symlinks resolve correctly | QA Engineer | ✅ done |
| Run full test suite and confirm all tests pass (no regressions) | QA Engineer | ✅ done |
