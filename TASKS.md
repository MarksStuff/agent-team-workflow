# TASKS.md — Phase 10: Domain Experts and Proposal Escalation

## Scope

**§ Domain Expert Agents** (DESIGN.md lines 230–481)
- Domain experts as question-answering consultants (don't write code)
- Global vs repo-local placement strategy
- On-demand spawning by EM when requested
- Stable vs volatile knowledge separation
- Memory file structure (stable/volatile/sources/pending)
- **Escalation flow**: EM proposes new agent, blocks relevant tasks, notifies human
- Proposal file format and review/apply cycle

**§ CLI Commands** (DESIGN.md lines 1027–1050)
- `agent-design refresh-domain --agent <name>`
- `agent-design review-proposal <name>`
- `agent-design apply-proposal <name>`

**§ Deliverables**
1. Two domain expert agent files for this repo:
   - `.claude/agents/claude_expert.md` (Claude Code/API expertise)
   - `.claude/agents/agent_systems_expert.md` (multi-agent systems expertise)
2. Memory file structure defined for both
3. Three CLI commands implemented and tested
4. End-to-end validation: full escalation cycle works

**Out of scope:** Other phases, retrospective facilitator, hooks.

---

## Sprint Planning (Phase 1)

Agents: claim tasks below based on your expertise. TDD goes first.

| Task | Owner | Status |
|---|---|---|
| Review design §Domain Expert Agents and flag any ambiguities or gaps before implementation begins | Architect | ⬜ unclaimed |
| Define acceptance criteria for the two domain expert agent files (observable structure, content requirements) | QA Engineer | ⬜ unclaimed |
| Define acceptance criteria for `refresh-domain`, `review-proposal`, and `apply-proposal` commands | QA Engineer | ⬜ unclaimed |
| Write tests for domain expert agent file structure (RED first) | TDD Focussed Engineer | ⬜ unclaimed |
| Write tests for `refresh-domain` command (RED first) | TDD Focussed Engineer | ⬜ unclaimed |
| Write tests for `review-proposal` command (RED first) | TDD Focussed Engineer | ⬜ unclaimed |
| Write tests for `apply-proposal` command (RED first) | TDD Focussed Engineer | ⬜ unclaimed |
| Write `claude_expert.md` agent file with stable/volatile knowledge structure | Developer | ⬜ unclaimed |
| Write `agent_systems_expert.md` agent file with stable/volatile knowledge structure | Developer | ⬜ unclaimed |
| Implement `refresh-domain` command in `agent_design/cli/commands/` | Developer | ⬜ unclaimed |
| Implement `review-proposal` command in `agent_design/cli/commands/` | Developer | ⬜ unclaimed |
| Implement `apply-proposal` command in `agent_design/cli/commands/` | Developer | ⬜ unclaimed |
| Wire all three commands into `agent_design/cli/main.py` | Developer | ⬜ unclaimed |
| Final acceptance review: verify domain expert files and commands satisfy all acceptance criteria | QA Engineer | ⬜ unclaimed |
| Final architecture review: confirm implementation matches design, no drift | Architect | ⬜ unclaimed |
