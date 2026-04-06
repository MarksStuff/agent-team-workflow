# TASKS.md — Phase 10: Domain Experts and Proposal Escalation

## Scope
§ "Domain Expert Agents" + three new CLI commands from § "CLI Command Map":
`refresh-domain`, `review-proposal`, `apply-proposal`

**Deliverables:**
1. `plugins/local/agents/claude_expert.md` — project-local domain expert for Claude Code / Claude API / agent SDK
2. `plugins/local/agents/agent_systems_expert.md` — project-local domain expert for multi-agent systems
3. Memory file stubs for each in `plugins/core/memory/` (stable/volatile/sources/pending structure)
4. `agent_design/cli/commands/refresh_domain.py` — `--print` solo session where the expert refreshes volatile knowledge
5. `agent_design/cli/commands/review_proposal.py` — prints `.agent-design/proposals/<name>.md` for human review
6. `agent_design/cli/commands/apply_proposal.py` — writes the approved agent definition file to disk
7. Tests for all three commands
8. Wire new commands into `cli/main.py`
9. `build_refresh_domain_start()` helper in `prompts.py`

**Out of scope:** core team agent prompts, hooks, retrospective, remember, review-feedback, phases 1–9.

---

| Task | Owner | Status | Notes |
|---|---|---|---|
| Review interface contracts for the three new commands and `build_refresh_domain_start()`; flag design gaps; define exact signatures | Architect | ✅ done | Posted to DISCUSSION.md |
| Define acceptance criteria for `refresh-domain`, `review-proposal`, `apply-proposal` | QA Engineer | ✅ done | Posted to DISCUSSION.md |
| Write `claude_expert.md` and `agent_systems_expert.md` in `plugins/local/agents/` | Architect | ✅ done | |
| Write memory stubs for each domain expert in `plugins/core/memory/` | Architect | ✅ done | |
| Write tests for `build_refresh_domain_start()` in `tests/test_prompts.py` (RED first) (RED first) | TDD Focussed Engineer | ✅ done | 9 tests RED confirmed |
| Write tests for `refresh-domain` CLI command in `tests/test_refresh_domain.py` (RED first) | TDD Focussed Engineer | ✅ done | 15 tests RED confirmed |
| Write tests for `review-proposal` CLI command in `tests/test_review_proposal.py` (RED first) | TDD Focussed Engineer | ✅ done | 16 tests RED confirmed |
| Write tests for `apply-proposal` CLI command in `tests/test_apply_proposal.py` (RED first) | TDD Focussed Engineer | ✅ done | 20 tests RED confirmed |
| Implement `build_refresh_domain_start()` in `agent_design/prompts.py` | Developer | ✅ done | 9/9 GREEN |
| Implement `agent_design/cli/commands/refresh_domain.py` | Developer | ✅ done | 15/15 GREEN |
| Implement `agent_design/cli/commands/review_proposal.py` | Developer | ✅ done | 16/16 GREEN |
| Implement `agent_design/cli/commands/apply_proposal.py` | Developer | ✅ done | 33/33 GREEN — fixture corrected by TDD |
| Wire `refresh_domain`, `review_proposal`, `apply_proposal` into `cli/main.py` | Developer | ✅ done | all three registered |
| Final acceptance review: verify all three commands satisfy acceptance criteria; confirm tests pass; LGTM or raise issues | QA Engineer | ✅ done | 31/31 ACs covered. QA: LGTM |
| Final architecture review: confirm implementation matches design; no drift; LGTM or raise issues | Architect | ✅ done | LGTM — all checklist items pass |
