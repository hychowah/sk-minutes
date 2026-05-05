- Purpose: Explain execution plan usage in this repository
- Scope: When to create a plan, where plans belong, and how plans relate to other docs; excludes task content itself
- Status: Active
- Last validated: 2026-05-05
- Source of truth for: Execution plan lifecycle and usage rules

# Execution Plans

Execution plans are temporary, task-scoped documents for work that spans multiple sessions or commits.

## When To Create A Plan

- Create a plan for feature work, bug fixes, migrations, refactors, or investigations that need handoff across sessions or commits.
- Do not create a plan for every small change.
- Do not use a plan as repo-global truth by default.

## Where Plans Live

- Use `docs/plans/` for plan templates and plan files.
- The current active scoped plan lives directly at [docs/plans/2026-05-05-local-minutes-implementation.md](2026-05-05-local-minutes-implementation.md).
- If active and completed plan folders are added later, active plans should live under `docs/plans/active/` and completed plans should move to `docs/plans/completed/`.
- Those folders do not exist yet because one active plan is still manageable directly under `docs/plans/`.

## Relationship To Other Docs

- Plans do not replace [DEVNOTES.md](../../DEVNOTES.md) for repo-wide recent truth.
- Plans do not replace [INDEX.md](../../INDEX.md) for repository map and authority rules.
- Plans should link to stable owner docs instead of copying them.
