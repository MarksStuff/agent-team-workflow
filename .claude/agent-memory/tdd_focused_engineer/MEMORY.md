# TDD Focussed Engineer — Project Memory

## Project: agent-team-workflow

### Test file locations and patterns
- `tests/test_prompts.py` — prompt builder tests (standalone functions, no fixtures)
- `tests/test_launcher.py` — launcher tests (patch `agent_design.launcher.subprocess.run`)
- `tests/test_remember.py` — CLI command tests (CliRunner + patch pattern)
- `tests/test_review_feedback.py` — CLI command tests + isolated `_fetch_pr_comments` tests
- `tests/test_continue.py` — reference pattern for CLI command tests

### Confirmed test patterns
- CLI commands: use `click.testing.CliRunner` + `unittest.mock.patch`
- Patch target must be the module that imports it, not the original module
  e.g. `patch("agent_design.cli.commands.remember.run_print_team")` not `patch("agent_design.launcher.run_print_team")`
- Subprocess-dependent helpers (`_fetch_pr_comments`): patch `subprocess.run` in the command module
- Mock subprocess result: `MagicMock()` with `.returncode`, `.stdout`, `.stderr` attributes

### Contract lessons
- `run_print_team()` does NOT use `--strict-mcp-config` (that's `run_solo` only)
- `build_review_feedback_start(pr_comments, pr_url, available_specialists=None)` — no date, no project_slug
- `build_remember_start(correction, project_slug, date, available_specialists=None)` — date IS injectable
- `_fetch_pr_comments` raises `click.UsageError` not `RuntimeError` for all error paths

### Sprint dynamics
- Developer moves fast — by the time tests were written, most implementation existed
- Always read DISCUSSION.md fully before writing tests — contracts are resolved there
- Architect and QA post contracts to DISCUSSION.md; treat that as source of truth over first-draft TASKS.md
- Mock signatures must match the Architect's contract, not the Developer's first implementation

## Corrections & Overrides
- 2026-04-04 [agent-team-workflow]: Initially used wrong mock data format for `_fetch_pr_comments` tests
  (used JSON array instead of `{"comments": [], "reviews": []}` dict). Always check the actual
  implementation's JSON parsing before writing mocks.
- 2026-04-04 [agent-team-workflow]: `build_review_feedback_start` signature was corrected by
  Architect mid-sprint — removed `project_slug` and `date`, replaced with `pr_url`.
  Always wait for Architect's interface spec before writing prompt builder tests.
