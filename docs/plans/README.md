- Purpose: Explain execution plan usage in this repository
- Scope: When to create a plan, where plans belong, and how plans relate to other docs; excludes task content itself
- Status: Active
- Last validated: 2026-05-09
- Source of truth for: Execution plan lifecycle and usage rules

# Execution Plans

Execution plans are temporary, task-scoped documents for work that spans multiple sessions or commits.

## When To Create A Plan

- Create a plan for feature work, bug fixes, migrations, refactors, or investigations that need handoff across sessions or commits.
- Do not create a plan for every small change.
- Do not use a plan as repo-global truth by default.

## Where Plans Live

- Use `docs/plans/` for plan templates and plan files.
- No active scoped plan currently exists.
- A completed scoped plan is retained at [completed/workflow-contract-and-interface-coherence.md](completed/workflow-contract-and-interface-coherence.md) for history.
- Active plans live under `docs/plans/active/`.
- Completed plans retained for history live under `docs/plans/completed/`.

## Relationship To Other Docs

- Plans do not replace [DEVNOTES.md](../../DEVNOTES.md) for repo-wide recent truth.
- Plans do not replace [INDEX.md](../../INDEX.md) for repository map and authority rules.
- Plans should link to stable owner docs instead of copying them.
- Completed plan files may be deleted once stable facts have been moved into the owner documents.
