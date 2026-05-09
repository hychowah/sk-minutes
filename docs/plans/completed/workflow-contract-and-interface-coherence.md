- Purpose: Historical scoped execution plan for the completed workflow and interface cleanup slice
- Scope: Cross-session implementation plan for workflow semantics, interface coherence, and the first measurement-prep tasks; excludes repo-wide truth ownership
- Status: Completed
- Last validated: 2026-05-09
- Source of truth for: Historical record of the completed MP-002 and MP-003 workflow/interface cleanup slice

# Execution Plan

Historical document. This file records a completed scoped workstream and must not replace stable owner docs.

## Title

Workflow Contract And Interface Coherence

## Status

Completed

## Created Date

2026-05-08

## Last Updated Date

2026-05-09

## Branch

main

## Scope Type

Refactor

## Goal

Finish the current cleanup of workflow ownership and operator-facing interface coherence without broadening the stack beyond the repository's local-first target shape.

## Success Criteria

- Workflow stage readiness and job eligibility are controlled from one shared owner instead of duplicated heuristics.
- `status` versus workflow-progress semantics are explicit enough that CLI, API, worker, and tests no longer need to infer meaning from mixed stage strings alone.
- Operator-facing CLI, API, README, and diagnostics expose coherent job discovery, state-root guidance, and artifact retrieval behavior.
- The next performance slice is unblocked by a stable workflow contract and clear interface surfaces.

## Non-Goals

- Replacing FastAPI, the CLI, or the local file store.
- Adding multi-worker or service-oriented infrastructure.
- Solving every performance issue before measurement exists.
- Converting the pipeline into a generic framework unless the current linear shape proves insufficient.

## Current Checkpoint

- Shared stage-selection ownership now exists in [src/minutes/pipeline/__init__.py](../../../src/minutes/pipeline/__init__.py).
- The worker and orchestrator already consume that shared stage-selection helper.
- CLI job discovery and doctor state-root alignment have been implemented.
- `workflow_stage` now records workflow progress separately from execution `status`, and successful stage transitions now resolve to `queued` or `completed` based on remaining pending work.
- Transcript and summary retrieval now flow through a shared query owner instead of duplicated CLI and API transport logic.
- The public API create-job surface now requires `source_path`, while the internal store path still permits seeded artifact workflows for manual and test usage.
- A first local measurement path now exists in [scripts/measure_local.py](../../../scripts/measure_local.py), with the synthetic control-plane benchmark already validated.
- A real transcription benchmark has now been validated on the committed [file/test1.mp3](../../../file/test1.mp3) fixture, exposing a large cold-versus-warm latency gap.
- Real speaker-assembly and summary benchmarks have now also been validated against the persisted artifacts for the committed `file/test1.mp3` job.
- The API now reuses an app-scoped store and orchestrator, and the new API benchmark shows a first-versus-second request drop from `19.504s` to `2.841s` on `file/test1.mp3`.
- Speaker assembly now prefers in-memory waveform transcription with a fallback to temp-file transcription, cutting the measured benchmark from about `62.5s` to about `27.0s` on the same real artifacts while preserving the simpler per-clip path.
- Follow-on experiments with batched transcription and more aggressive same-speaker merging were intentionally dropped because they either regressed the end-to-end benchmark or looked too specific to one fixture.
- `current_stage` no longer mirrors `workflow_stage` on queued jobs; it now exposes the next pending stage while `workflow_stage` remains the owner of last completed workflow progress.
- CLI and API job payloads now also expose `next_stage` explicitly through a shared transport-facing job view instead of forcing downstream callers to infer it from `current_stage`.
- Persisted summary artifacts now record `summary_elapsed_ms` and `summary_timeout_seconds`, giving normal job outputs their first built-in summary latency context.
- Summary retries are now explicit and bounded through `summary_max_retries`, and persisted summary artifacts now record that retry configuration alongside timeout and elapsed-time metadata.
- Summary stage readiness now invalidates stale summaries by comparing persisted summary provenance to the currently selected transcript source artifact.
- The summary-aware control-plane benchmark now shows only a small worker-scan delta from provenance checks at 250 synthetic jobs, and summary retrieval now exposes freshness through shared API and CLI JSON response fields.
- Public job payloads now use an explicit shared job view, expose `summary_state`, and no longer leak `current_stage` through CLI or API payloads.
- Public `workflow_stage` is now derived from canonical artifact-backed workflow progress, so out-of-order stage execution no longer produces incoherent transport payloads.
- The last remaining closeout work has landed: `current_stage` has been removed from stored job records, and summary generation now reuses the shared summary-source owner.

## Context To Read First

- [INDEX.md](../../../INDEX.md)
- [AGENTS.md](../../../AGENTS.md)
- [KNOWLEDGE.md](../../../KNOWLEDGE.md)
- [DEVNOTES.md](../../../DEVNOTES.md)
- [README.md](../../README.md)
- [tech-debt.md](../../tech-debt.md)

## Constraints

- Keep the repository local-first and single-user biased unless product scope changes explicitly.
- Do not move recent verified truth out of [DEVNOTES.md](../../../DEVNOTES.md).
- Keep docs ownership clear: this plan is temporary and task-scoped.
- Prefer focused regression coverage after each slice rather than broad speculative refactors.
- Avoid changing unrelated provider integrations while cleaning up workflow semantics.

## Affected Areas

- [src/minutes/pipeline/__init__.py](../../../src/minutes/pipeline/__init__.py)
- [src/minutes/orchestrator.py](../../../src/minutes/orchestrator.py)
- [src/minutes/worker.py](../../../src/minutes/worker.py)
- [src/minutes/storage/models.py](../../../src/minutes/storage/models.py)
- [src/minutes/storage/file_store.py](../../../src/minutes/storage/file_store.py)
- [src/minutes/cli.py](../../../src/minutes/cli.py)
- [src/minutes/api/routes_jobs.py](../../../src/minutes/api/routes_jobs.py)
- [README.md](../../../README.md)
- [scripts/doctor.ps1](../../../scripts/doctor.ps1)
- [tests/test_normalization_flow.py](../../../tests/test_normalization_flow.py)

## Workstreams

### Workstream 1

- Normalize the workflow contract after the first shared-owner slice.
- Separate execution status from workflow-progress meaning in the job model and downstream surfaces.
- Decide whether source-less jobs are a supported advanced workflow or should be rejected at creation time.

### Workstream 2

- Finish the current operator interface coherence pass.
- Reduce duplication between CLI and API retrieval behavior through a shared query or service layer.
- Keep README and diagnostics aligned with the actual runtime and job-discovery flows.

### Workstream 3

- Prepare the first performance measurement slice without taking on large architecture changes yet.
- Define the smallest useful measurement path for model warm-up, speaker assembly, summary size pressure, and job-scan behavior.

## Milestones

1. Land the semantics cleanup for `status` and workflow progress with focused regression coverage.
2. Land a shared retrieval/query layer used by both CLI and API for transcript and summary lookups.
3. Add the first lightweight measurement path or documented benchmark procedure for the known local hotspots.

## Validation Plan

- Extend [tests/test_normalization_flow.py](../../../tests/test_normalization_flow.py) for status semantics, job eligibility, and retrieval parity.
- Re-run narrow pytest selections after each slice before widening scope.
- Keep the doctor script and README aligned with the validated runtime defaults.
- Use the opt-in real-audio path only when a slice changes real execution behavior rather than just control-plane semantics.

## Commit Strategy

- Keep commits scoped by slice: workflow semantics, retrieval/query cleanup, and measurement prep should land separately when possible.
- Update [DEVNOTES.md](../../../DEVNOTES.md) after each verified slice.
- Move durable outcomes from this plan into stable owner docs as they become real.

## Progress Log

- 2026-05-08: Created the scoped plan after the first shared workflow-owner and CLI discovery slices were already validated.
- 2026-05-08: Landed the first status-semantics cleanup by adding `workflow_stage` and making successful stages resolve `queued` versus `completed` from remaining workflow.
- 2026-05-08: Landed a shared retrieval/query layer for transcript and summary lookups used by both CLI and API surfaces.
- 2026-05-08: Rejected source-less jobs at the public API create surface while keeping the internal seeded-artifact path intact.
- 2026-05-08: Added the first lightweight measurement script and validated the synthetic control-plane benchmark path.
- 2026-05-08: Validated the transcription benchmark against `file/test1.mp3` and captured the first cold-versus-warm baseline.
- 2026-05-08: Validated speaker-assembly and summary benchmarks against the persisted real-job artifacts from `file/test1.mp3`.
- 2026-05-08: Reused the API store and orchestrator through `app.state` and validated the API transcription benchmark on one app instance.
- 2026-05-08: Optimized speaker assembly to prefer in-memory transcription and cut the measured speaker-assembly benchmark by more than half on the same real artifacts.
- 2026-05-08: Rejected batched speaker retranscription and wider same-speaker merge tuning after the full benchmark showed they were not worth keeping.
- 2026-05-08: Narrowed `current_stage` so queued jobs now expose the next pending stage instead of duplicating `workflow_stage`.
- 2026-05-08: Added a shared job view so CLI and API job payloads now expose `next_stage` explicitly.
- 2026-05-08: Added persisted summary timing metadata so normal job artifacts now record summary latency and timeout context.
- 2026-05-08: Added bounded summary retries for transient timeout and connection failures and surfaced the retry setting through config and artifacts.
- 2026-05-08: Taught the shared pipeline gate to regenerate stale summaries when stored summary provenance no longer matches the current transcript source.
- 2026-05-09: Extended the control-plane benchmark to measure current-versus-stale summary provenance scenarios and confirmed only a small worker-scan delta at 250 synthetic jobs.
- 2026-05-09: Exposed summary freshness through shared retrieval responses so API consumers and CLI JSON can tell whether a summary still matches the current source artifact.
- 2026-05-09: Split the public job transport model from the stored job record, removed `current_stage` from public payloads, and added `summary_state` to the shared job view.
- 2026-05-09: Canonicalized public `workflow_stage` from artifact-backed workflow progress so job payloads stay coherent even after out-of-order stage execution.
- 2026-05-09: Removed `current_stage` from stored job records, switched internal tests to the shared `next_pending_stage` owner, and retired the duplicate orchestrator summary-source helper.
- 2026-05-09: Moved this file from `docs/plans/active/` to `docs/plans/completed/` after the done bar was validated.

## Decision Log

- 2026-05-08: Keep the current local-first stack and defer broad infrastructure changes until measurement or product scope justifies them.
- 2026-05-08: Treat workflow semantics cleanup as the blocking slice before wider performance work.
- 2026-05-08: Keep `current_stage` temporarily as the compatibility field while `workflow_stage` becomes the explicit owner of workflow progress.
- 2026-05-08: Keep `current_stage` as a compatibility field for now, but narrow queued jobs to the next pending stage so it stops duplicating `workflow_stage`.
- 2026-05-08: Expose `next_stage` in transport payloads rather than persisting more derived workflow fields into stored job records.
- 2026-05-08: Use a small shared query module for retrieval instead of introducing a larger service layer before more artifact types exist.
- 2026-05-08: Treat source-less jobs as an internal/manual seeded-artifact workflow only, not a public API create-job shape.
- 2026-05-08: Put the first measurement path in a script rather than tests so local benchmarking stays opt-in and does not slow the regression suite.
- 2026-05-09: Remove `current_stage` from public transport now that no external compatibility requirement exists, while keeping storage permissive until any persistence migration is justified.
- 2026-05-09: Derive public `workflow_stage` from canonical artifact-backed progress instead of exposing the raw persisted field directly.
- 2026-05-09: Remove `current_stage` from stored job records as well, because the shared workflow owner and public transport split made the field redundant.
- 2026-05-09: Close the scoped workflow/interface plan after the remaining duplicate helper paths were retired and the full normalization suite revalidated.

## Open Questions

- None. Closed on 2026-05-09 after removing `current_stage` from storage and deduplicating the remaining summary-source helper path.

## Risks

- Changing `status` semantics could break tests or interface assumptions that currently rely on the existing overloaded meaning.
- Tightening source-less job rules too early could remove a workflow that is currently useful for manual artifact seeding.
- Over-designing the retrieval layer too soon could create framework-like indirection without enough current value.

## Handoff Notes

- Start with [DEVNOTES.md](../../../DEVNOTES.md) to confirm the latest verified baseline before acting on any follow-on work.
- Treat this file as historical only; it no longer owns live scoped progress.
- Use [INDEX.md](../../../INDEX.md), [DEVNOTES.md](../../../DEVNOTES.md), and [tech-debt.md](../../tech-debt.md) to confirm whether any follow-on work should be reopened.

## Done Bar

- Workflow semantics are explicit and covered by focused tests.
- CLI and API retrieval behavior share a common owner or query layer where intended.
- The next performance slice has a concrete measurement path and no longer depends on unclear workflow or interface semantics.

## Archive Note

- Completed and moved to `docs/plans/completed/` on 2026-05-09 after the done bar was met and final validation was recorded.