# CLAUDE.md — Global Agent Guidelines

> This file is the canonical source for global Claude Code instructions.
> It lives in `plugins/core/` in the agent-team-workflow repository and is
> loaded via `--plugin-dir`. The `~/.claude/CLAUDE.md` symlink is kept for
> backward compatibility during transition.
>
> Project-specific guidance lives in each repo's own `CLAUDE.md`.

---

## Git workflow

- **One branch per feature or fix.** Never work directly on `main`.
  Branch naming: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`.
- **Never push directly to `main`.** Always open a PR. The human merges.
- **Small, focused commits.** Each commit should do one thing and have a
  meaningful message. Prefer multiple small commits over one giant one.
- **Always rebase — never merge.** When updating a feature branch from
  `main`, use `git rebase`, not `git merge`.
- **`trash` over `rm`** for file deletions — recoverable beats gone forever.

### Commit signing

Before every `git commit`, check which GitHub server is the remote:

```bash
git remote get-url origin
```

- Remote contains `github.pie.apple.com` (Apple internal): use `git commit ...` normally — GPG signing is enabled and required.
- Remote contains `github.com` (public GitHub): use `git -c commit.gpgsign=false commit ...` — signing is disabled; bare `git commit` will fail if GPG is globally configured.

**Never run bare `git commit` without checking the remote first.**

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
- **Self-organise against the task board.** Agents claim tasks based on
  their expertise. Nobody assigns work to anyone else.

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

- **Never exfiltrate private data.**
- **Do not push half-baked changes.** If a task is incomplete, leave the
  branch in a state that is at least not broken.
