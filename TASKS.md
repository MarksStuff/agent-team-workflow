# TASKS.md — Phase 8: Retrospective

## Scope
§ "The Retrospective" + § "Retrospective Facilitator" (Agent Roster) + § "CLI Command Map (V2)" retro and apply-suggestion entries + § "Implementation Phases — Phase 8"

In scope:
1. `agent-design retro` command (new file: agent_design/cli/commands/retro.py)
2. `retrospective_facilitator.md` agent definition file (written to ~/.claude/agents/)
3. `agent-design apply-suggestion` command (new file: agent_design/cli/commands/apply_suggestion.py)
4. `build_retro_start()` and `build_apply_suggestion_start()` prompt builders in prompts.py
5. Register both commands in agent_design/cli/main.py
6. Tests for all of the above

Out of scope: hooks, domain experts, all other commands.

---

| Task | Owner | Status |
|---|---|---|
| **[ARCHITECT] Define interface contracts for `build_retro_start()` and `build_apply_suggestion_start()` (exact signatures, what each parameter carries)** | architect | ✅ done |
| **[ARCHITECT] Define which launcher function each command uses (`run_print_team` vs `run_team` vs `run_solo`)** | architect | ✅ done |
| **[ARCHITECT] Define `apply-suggestion` RETRO.md parsing contract (how suggestion ID maps to suggestion text)** | architect | ✅ done |
| **[QA] Write acceptance criteria for `retro` command (success path, error paths, edge cases)** | qa_engineer | ✅ done |
| **[QA] Write acceptance criteria for `apply-suggestion` command (success path, error paths, edge cases)** | qa_engineer | ✅ done |
| **[TDD] Write tests for `build_retro_start()` and `build_apply_suggestion_start()` in tests/test_prompts.py (RED first)** | tdd_focussed_engineer | ✅ done |
| **[TDD] Write tests for `agent-design retro` command in tests/test_retro.py (RED first)** | tdd_focussed_engineer | ✅ done |
| **[TDD] Write tests for `agent-design apply-suggestion` command in tests/test_apply_suggestion.py (RED first)** | tdd_focussed_engineer | ✅ done |
| **[TDD] Write tests for `retrospective_facilitator.md` agent definition in tests/test_retrospective_facilitator.py (RED first)** | tdd_focussed_engineer | ✅ done |
| **[TDD] Confirm all tests are RED; unblock Developer** | tdd_focussed_engineer | ✅ done |
| **[DEV] Implement `build_retro_start()` in agent_design/prompts.py** | developer | ✅ done |
| **[DEV] Implement `build_apply_suggestion_start()` in agent_design/prompts.py** | developer | ✅ done |
| **[DEV] Implement `agent_design/cli/commands/retro.py`** | developer | ✅ done |
| **[DEV] Implement `agent_design/cli/commands/apply_suggestion.py`** | developer | ✅ done |
| **[DEV] Register `retro` and `apply-suggestion` commands in `agent_design/cli/main.py`** | developer | ✅ done |
| **[DEV] Write `retrospective_facilitator.md` agent definition to `~/.claude/agents/`** | developer | ✅ done |
| **[QA] Final acceptance review: verify both commands satisfy all acceptance criteria; confirm tests pass** | qa_engineer | ✅ done |
| **[ARCHITECT] Final architecture review: confirm implementation matches design; no drift** | architect | ✅ done |
