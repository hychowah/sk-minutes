- Purpose: Stable landing page for repository documentation under docs/
- Scope: Document map and ownership guidance for stable docs in this folder; excludes live implementation status, setup instructions, and temporary task handoff
- Status: Active
- Last validated: 2026-05-09
- Source of truth for: docs/ folder navigation and document ownership overview

# Docs Overview

This folder holds stable repository documents.

These documents should point to their owner surfaces instead of duplicating live implementation details.

## Read This Folder In Context

1. Start with [../INDEX.md](../INDEX.md) for repository-wide authority rules.
2. Use this page to find the right stable document under `docs/`.
3. Follow links to the owner document for the type of information you need.

## Documents In This Folder

- [tech-debt.md](tech-debt.md): unresolved debt inventory and cleanup priorities.
- [plans/README.md](plans/README.md): rules for temporary scoped execution plans.
- [plans/completed/mp-004-startup-hotspot-investigation.md](plans/completed/mp-004-startup-hotspot-investigation.md): historical record of the completed MP-004 startup investigation plan.
- [plans/completed/workflow-contract-and-interface-coherence.md](plans/completed/workflow-contract-and-interface-coherence.md): historical record of the completed workflow and interface cleanup plan.
- [plans/_EXEC_PLAN_TEMPLATE.md](plans/_EXEC_PLAN_TEMPLATE.md): template for scoped plan files when they are needed.

## Ownership Rules

- Use [../DEVNOTES.md](../DEVNOTES.md) for recent verified repository truth.
- Use [../INDEX.md](../INDEX.md) for repository map and current maintenance posture.
- Use [tech-debt.md](tech-debt.md) for unresolved debt items.
- Use documents under [plans/](plans) only for temporary scoped work that needs handoff across sessions or commits.

## What Does Not Belong Here

- Setup and usage instructions that belong in [../README.md](../README.md).
- Recent verified implementation logs that belong in [../DEVNOTES.md](../DEVNOTES.md).
- Task-local scratch notes or temporary status documents outside the scoped plan workflow.