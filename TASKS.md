# TASKS.md — Phase 7: Memory Infrastructure

## Scope
§ "Human Intervention → Memory Update" + § "PR Feedback → Memory Update" + § "CLI Command Map"

Two new commands:
- `agent-design remember "<correction>"` — `--print` multi-agent session; each agent self-updates if relevant; Retrospective Facilitator verifies pickup
- `agent-design review-feedback --pr <url>` — same pattern, using GitHub PR review comments fetched via `gh` CLI

Supporting additions:
- `run_print_team()` in `launcher.py` — `--print` session with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- `build_remember_start()` and `build_review_feedback_start()` in `prompts.py`
- Both commands registered in `cli/main.py`

Out of scope: Retrospective Facilitator agent definition, hooks, domain experts.

---

| Task | Owner | Status |
|---|---|---|
| Review interface contracts for `run_print_team()`, `build_remember_start()`, `build_review_feedback_start()`, and both commands; flag any design gaps before implementation begins | Architect | ✅ done |
| Define exact signatures and subprocess flag contract for `run_print_team()`, both `build_*` functions, and `_fetch_pr_comments()` | Architect | ✅ done |
| Define acceptance criteria for `remember` and `review-feedback` commands (success paths, error paths, edge cases) | QA Engineer | ✅ done |
| Write tests for `build_remember_start()` in `tests/test_prompts.py` (RED first) | TDD Focussed Engineer | ✅ done |
| Write tests for `build_review_feedback_start()` in `tests/test_prompts.py` (RED first) | TDD Focussed Engineer | ✅ done |
| Write tests for `run_print_team()` in `tests/test_launcher.py` (RED first) | TDD Focussed Engineer | ✅ done |
| Write tests for `remember` CLI command in `tests/test_remember.py` (RED first) | TDD Focussed Engineer | ✅ done |
| Write tests for `review_feedback` CLI command in `tests/test_review_feedback.py` (RED first) | TDD Focussed Engineer | ✅ done |
| Write tests for `_fetch_pr_comments()` helper in isolation (no real `gh` subprocess) in `tests/test_review_feedback.py` | TDD Focussed Engineer | ✅ done |
| Implement `run_print_team()` in `agent_design/launcher.py` | Developer | ✅ done |
| Implement `build_remember_start()` and `build_review_feedback_start()` in `agent_design/prompts.py` | Developer | ✅ done |
| Implement `agent_design/cli/commands/remember.py` | Developer | ✅ done |
| Implement `agent_design/cli/commands/review_feedback.py` (including `gh` CLI fetch for PR comments) | Developer | ✅ done |
| Wire `remember` and `review_feedback` commands into `agent_design/cli/main.py` | Developer | ✅ done |
| Final acceptance review: verify both commands satisfy all acceptance criteria; confirm tests pass; LGTM or raise issues | QA Engineer | ⬜ unclaimed |
| Final architecture review: confirm implementation matches design; no drift from design doc; LGTM or raise issues | Architect | ⬜ unclaimed |
