# QA Engineer Memory

## Project: agent-team-workflow

### Workflow patterns confirmed

- Acceptance criteria go into `.agent-design/DESIGN.md` under a
  `## Acceptance Criteria — <Phase Title>` section (use the phase title,
  not a phase number).
- A summary of ACs and scenario-to-AC mapping also goes into DISCUSSION.md
  for TDD's immediate use — TDD reads DISCUSSION.md before writing tests.
- Symlink verification (files in `~/.claude/agents/`) is a manual/scripted
  check, not a pytest unit test — CI won't have that directory.
- The structural contract task belongs to Architect; QA writes the observable
  acceptance criteria (what an external observer checks). These are related
  but distinct outputs.

### AC structure for agent definition file phases

When a phase produces agent definition files, the standard AC set is:
- AC1: file existence (path + non-empty)
- AC2: required YAML frontmatter fields with constraints
- AC3: description contains spawn-trigger language (EM selection surface)
- AC4: body contains "Spawned when:" section
- AC5: body contains "Does not" boundary section
- AC6: memory file section with correct path, permission statement, trigger
- AC7: symlinks in `~/.claude/agents/` resolve (manual check)
- AC8: no regressions in pre-phase tests
