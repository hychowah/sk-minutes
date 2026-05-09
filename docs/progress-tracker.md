- Purpose: High-level repository progress view across master-plan workstreams
- Scope: Current workstream state, evidence links, and next gates; excludes detailed task logs, recent verified implementation notes, and unresolved debt details
- Status: Active
- Last validated: 2026-05-09
- Source of truth for: High-level workstream progress tracking

# Progress Tracker

This tracker is a coordination view, not the owner of live implementation detail.

Use these linked owner docs for the actual details:

- Recent verified repository truth: [DEVNOTES.md](../DEVNOTES.md)
- Long-lived workstream direction: [master-plan.md](master-plan.md)
- Unresolved debt and cleanup priorities: [tech-debt.md](tech-debt.md)
- Temporary scoped execution plans: [plans/README.md](plans/README.md)

## State Meanings

- `Established`: The workstream foundation exists and is already part of the working baseline.
- `Active`: Verified work is currently moving the workstream forward.
- `Planned`: The workstream is accepted but not yet in active implementation.
- `Conditional`: The workstream should only proceed if a trigger is met.

## Workstream Status

| Workstream | State | Evidence Owner | Last Verified | Next Gate |
| --- | --- | --- | --- | --- |
| MP-001 Core Local Pipeline | Established | [DEVNOTES.md](../DEVNOTES.md) | 2026-05-08 | Preserve end-to-end local correctness while other workstreams change surrounding workflow and interfaces. |
| MP-002 Workflow Contract Cleanup | Established | [DEVNOTES.md](../DEVNOTES.md) | 2026-05-09 | Preserve the shared workflow owner and reopen only if a new stage or transport surface starts drifting again. |
| MP-003 Operator Interface Coherence | Established | [DEVNOTES.md](../DEVNOTES.md) | 2026-05-09 | Keep CLI, API, README, and diagnostics aligned as new operator-facing fields or commands land. |
| MP-004 Performance Measurement And Hotspot Removal | Active | [master-plan.md](master-plan.md), [DEVNOTES.md](../DEVNOTES.md) | 2026-05-09 | Use the existing validated measurements to choose the first real hotspot follow-up, with transcription cold-start reuse and remaining local heavy paths now better bounded than the summary gate. |
| MP-005 Retrieval And Query Layer Cleanup | Established | [DEVNOTES.md](../DEVNOTES.md) | 2026-05-09 | Extend the shared retrieval and freshness owners only when new artifact types or transport rules would otherwise duplicate logic again. |
| MP-006 Storage And Execution Model Hardening | Conditional | [master-plan.md](master-plan.md), [AGENTS.md](../AGENTS.md) | 2026-05-08 | Reassess only if the repo target changes beyond a single-user local workstation flow or measurement shows the current control plane is blocking growth. |

## Review Rules

- Update this document when a workstream changes state or its next gate changes materially.
- Update [DEVNOTES.md](../DEVNOTES.md) for verified implementation changes before updating this tracker.
- Link to the owning doc instead of copying detailed status or long task lists here.