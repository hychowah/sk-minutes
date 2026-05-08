- Purpose: Explain execution plan usage in this repository
- Scope: When to create a plan, where plans belong, and how plans relate to other docs; excludes task content itself
- Status: Active
- Last validated: 2026-05-08
- Source of truth for: Execution plan lifecycle and usage rules

# Execution Plans

Execution plans are temporary, task-scoped documents for work that spans multiple sessions or commits.

## When To Create A Plan

- Create a plan for feature work, bug fixes, migrations, refactors, or investigations that need handoff across sessions or commits.
- Do not create a plan for every small change.
- Do not use a plan as repo-global truth by default.

## Where Plans Live

- Use `docs/plans/` for plan templates and plan files.
- An active scoped plan currently exists at [active/workflow-contract-and-interface-coherence.md](active/workflow-contract-and-interface-coherence.md).
- No completed scoped plan files are currently retained.
- Active plans live under `docs/plans/active/`.
- If completed plan folders are added later, completed plans should move to `docs/plans/completed/`.

## Relationship To Other Docs

- Plans do not replace [DEVNOTES.md](../../DEVNOTES.md) for repo-wide recent truth.
- Plans do not replace [INDEX.md](../../INDEX.md) for repository map and authority rules.
- Plans should link to stable owner docs instead of copying them.
- Completed plan files may be deleted once stable facts have been moved into the owner documents.
