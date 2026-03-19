# agent-team-workflow

A multi-agent design workflow using Claude Code agent teams. Produces design documents and decision logs through structured debate between specialized agents, with full checkpoint/rollback support.

## Status

🚧 Design phase — see [DESIGN.md](DESIGN.md)

## Overview

Three specialized agents (Architect, Developer, Tester) collaborate on feature design with a Lead agent orchestrating the process. All state lives in files, making every round checkpointable and rollback-able via git.

## Docs

- [DESIGN.md](DESIGN.md) — full system design and open questions
