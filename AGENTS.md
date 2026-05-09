- Purpose: Short operating rules for LLM agents working in this repository
- Scope: How to start work, when to create a plan, when to stop and ask, and how to maintain handoff docs; excludes architecture, roadmap, and debt inventory
- Status: Active
- Last validated: 2026-05-09
- Source of truth for: LLM session procedure, stop-and-ask triggers, doc update expectations

# Agent Rules

## Start Here

1. Read [INDEX.md](INDEX.md).
2. Read [KNOWLEDGE.md](KNOWLEDGE.md).
3. Read [DEVNOTES.md](DEVNOTES.md).
4. Read an active execution plan only if the task spans multiple sessions or commits.
5. Expand into repository files only after the document context is clear.

## When To Create A Plan

- Create an execution plan only for scoped work that is likely to span multiple sessions or commits.
- Do not create a repo-global master plan by default.
- Store task-scoped plans under `docs/plans/` when they are needed.

## Stop-And-Ask Triggers

- The repository state conflicts with documented truth.
- A requested change would require inventing commands, architecture, or workflows not visible in the repository.
- A change would replace one source of truth with duplicated status across multiple files.
- A change needs product or implementation decisions that are still Unknown.

## Documentation Update Expectations

- Update [DEVNOTES.md](DEVNOTES.md) after verified work.
- Keep [DEVNOTES.md](DEVNOTES.md) at or below 500 lines; when it would exceed that cap, move the oldest complete dated entries into the archive files listed in [docs/devnotes/README.md](docs/devnotes/README.md) and keep each archive file at or below 500 lines too.
- Move reusable lessons into [KNOWLEDGE.md](KNOWLEDGE.md) only when they are general enough to reuse.
- Update [docs/tech-debt.md](docs/tech-debt.md) when debt is discovered, resolved, reprioritized, or dropped.
- Keep [README.md](README.md) strictly end-user-facing. Do not add developer workflow, testing, CI, planning, or contributor-process content there.

## Temporary Files And Handoff

- Treat execution plans as temporary task docs, not repo-wide truth.
- Completed plans are historical only.
- If temporary notes become stable knowledge, move that content into the correct owner document.
- If no active plan exists, handoff should rely on [DEVNOTES.md](DEVNOTES.md) plus stable docs.
