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

## Corrections & Overrides

- 2026-04-04 [agent-team-workflow]: Always check the actual implementation's JSON parsing before
  writing mocks — mock data must match the exact structure the code expects.
  (Wrote mocks using a JSON array for `_fetch_pr_comments`; code expected
  `{"comments": [], "reviews": []}` dict.)

- 2026-04-04 [agent-team-workflow]: Always wait for Architect's interface spec before writing
  prompt builder tests. If the spec isn't in DISCUSSION.md yet, message Architect directly
  and wait for the response before writing.
  (Wrote tests against Developer's first implementation; Architect later corrected the
  signature — tests had to be rewritten.)
