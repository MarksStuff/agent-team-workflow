## Corrections & Overrides

- 2026-04-04 [agent-team-workflow]: Always wait for Architect interface contracts and QA acceptance criteria before writing any tests at sprint start. (Context: Phase 7 — writing tests against assumed interfaces caused a rewrite when contracts arrived and differed from assumptions.)

- 2026-04-04 [agent-team-workflow]: Always post a DISCUSSION.md entry at sprint kick-off when claiming TDD tasks, explicitly declaring the dependency on Architect contracts and QA ACs and tagging both agents by name. Do not rely on teammates discovering the block by reading later entries. (Context: Phase 8 — "wait for contracts" protocol worked correctly but the dependency was not declared at task-claim time, so Architect and QA had to infer the block from a mid-thread DISCUSSION.md entry rather than being primed at kick-off.)
