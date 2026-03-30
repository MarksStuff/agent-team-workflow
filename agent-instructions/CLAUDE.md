# CLAUDE.md — Global Agent Guidelines

> This file is the canonical source for global Claude Code instructions.
> It is symlinked to `~/.claude/CLAUDE.md` and applies to **all** Claude Code
> sessions across all projects on this machine.
>
> Project-specific guidance lives in each repo's own `CLAUDE.md`.

---

## Git workflow

- **One branch per feature or fix.** Never work directly on `main`.
  Branch naming: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`.
- **Never push directly to `main`.** Always open a PR. The human merges.
- **Small, focused commits.** Each commit should do one thing and have a
  meaningful message. Prefer multiple small commits over one giant one.
- **Rebase over merge** when updating a feature branch from `main`.
- **`trash` over `rm`** for file deletions — recoverable beats gone forever.

---

## Test-driven development

- **Tests first.** Write tests before implementation code. Tests must be
  RED before the implementing agent begins writing production code.
- **Tests must be green before marking a task done.** Do not mark ✅ if
  any relevant test is still failing.
- **High unit test coverage is mandatory.** Complex logic must be broken
  into small, individually testable methods. If a method is hard to test,
  split it.
- **No real network, database, or filesystem in unit tests.** Use mocks,
  fakes, or in-memory substitutes via dependency injection.

---

## Dependency injection

- **Every external dependency is passed in — never instantiated inside.**
  Components that create their own dependencies (`let foo = FooService()`
  inside an init or method body) cannot be tested in isolation.
- **Every significant component has an abstract interface** (protocol,
  abstract base class) so it can be substituted with a test double.
- **No global state, singletons, or static calls to external services**
  in testable code paths — these make tests brittle and order-dependent.

---

## Code quality

- **Rule of Three for duplication.** One copy: leave it. Two copies:
  consider it. Three or more copies: refactor into a shared abstraction.
- **Logging must be able to reconstruct the code flow.** DEBUG-level
  entries at every significant branch, decision point, and state
  transition. INFO for lifecycle events. WARNING for non-fatal skips.
  ERROR for failures needing attention.
- **No business logic in the wrong layer.** DB queries belong in stores,
  not scrapers. Messaging belongs in publishers, not business logic.

---

## Agent team collaboration

- **Use `DISCUSSION.md` as the shared peer channel.** All agents append
  entries tagged with their role. Agents respond to each other directly —
  do not route everything through the Eng Manager.
  Entry format:
  ```
  ## [Role Name]
  <contribution, question, or response>
  ```
- **Eng Manager facilitates — does not assign or implement.** The EM's job
  is to surface gaps and blockers, not to direct technical work.
- **Self-organise against the task board.** Agents claim tasks based on
  their expertise. Nobody assigns work to anyone else.
- **Architect and QA must both sign off** ("Architect: LGTM" and
  "QA: LGTM") before an implementation sprint is declared complete.
- **TDD Focussed Engineer goes first** in every implementation sprint.

---

## PR hygiene

Before declaring a PR ready for review:
1. Read the full diff.
2. Verify it does what the description says.
3. Confirm CI is passing on the **latest commit SHA** (not a stale run).
4. No debug code, commented-out blocks, or TODO comments left in unless
   they are tracked issues.

---

## Safety

- **Ask before any action that leaves the machine** (emails, public posts,
  API calls with side effects).
- **Never exfiltrate private data.**
- **Do not push half-baked changes.** If a task is incomplete, leave the
  branch in a state that is at least not broken.
