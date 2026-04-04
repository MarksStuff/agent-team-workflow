# TASKS.md — Phase 5: `continue` command

| Task | Owner | Status | Notes |
|---|---|---|---|
| Write tests for `build_continue_start()` in `test_prompts.py` (RED first) | TDD Focussed Engineer | ✅ done | RED confirmed: ImportError |
| Write tests for `continue` command in new `test_continue.py` (RED first) | TDD Focussed Engineer | ✅ done | RED confirmed: ModuleNotFoundError |
| Write tests for `RoundState` without `phase` field in `test_state.py` (RED first) | TDD Focussed Engineer | ✅ done | RED confirmed: 5 failures |
| Add `build_continue_start()` to `prompts.py`; remove `build_review_start()` and `build_feedback_start()` | Developer | ✅ done | |
| Remove `phase` field and `PhaseType` from `state.py`; ensure backward-compat loading of old JSON | Developer | ✅ done | |
| Create `agent_design/cli/commands/continue_.py` with `continue` command | Developer | ✅ done | |
| Update `next_round.py` to use `build_continue_start()` or deprecate it as `continue` fully replaces it | Developer | ✅ done | |
| Update `feedback.py` to call `build_continue_start()` instead of `build_feedback_start()` | Developer | ✅ done | |
| Register `continue` in `main.py`; remove or alias `next` | Developer | ✅ done | |
| Update `test_prompts.py` to remove or adapt tests for deleted `build_review_start()` / `build_feedback_start()` | TDD Focussed Engineer | ✅ done | Removed broken imports + old tests; all 24 prompts tests GREEN |
| Update `test_state.py` to remove references to `phase` field | TDD Focussed Engineer | ✅ done | Removed 4 old phase-referencing tests; replaced with phase-free equivalents; 17 state tests GREEN |
| Define acceptance criteria for Phase 5 in DESIGN.md | QA Engineer | ✅ done | |
| Run full CI check (ruff format, ruff lint, mypy, pytest) | QA Engineer | ✅ done | 126/126 passed; ruff, mypy clean |
