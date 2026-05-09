- Purpose: Historical scoped plan for the completed MP-004 startup-performance investigation slice
- Scope: Cross-session record of the measured startup-boundary investigation and the first mitigation for avoidable `process-file` startup overhead; excludes live repository truth ownership
- Status: Completed
- Last validated: 2026-05-09
- Source of truth for: Historical record of the completed MP-004 startup slice

# Execution Plan

Historical document. This file records a completed scoped workstream and must not replace stable owner docs.

## Title

MP-004 Startup Hotspot Investigation

## Status

Completed

## Created Date

2026-05-09

## Last Updated Date

2026-05-09

## Branch

main

## Scope Type

Investigation

## Goal

Choose and validate the first measured mitigation for avoidable `process-file` startup overhead on the local-first pipeline path.

## Success Criteria

- The repo has one trustworthy way to inspect or measure the startup/import portion of the `process-file` path instead of only full transcription timings.
- The dominant avoidable startup hotspot is confirmed from current code and measurement evidence.
- The first mitigation lands in a narrow slice with focused regression coverage and before/after validation.
- Stable owner docs reflect the verified result without turning this plan into a second source of truth.

## Non-Goals

- Folding TD-002 pyannote and torchaudio compatibility hardening into this plan.
- Replacing the local file store, CLI, FastAPI app, or single-user execution model.
- Broad performance bundling across summary, control-plane, and speaker-assembly paths before the startup boundary is measured.
- Introducing framework-like indirection unless the measured hotspot requires it.

## Current Checkpoint

- [src/minutes/orchestrator.py](../../../src/minutes/orchestrator.py) now lazy-resolves default adapters instead of importing and constructing them all at module import and orchestrator construction time.
- [tests/test_normalization_flow.py](../../../tests/test_normalization_flow.py) contains subprocess regressions proving importing and constructing `JobOrchestrator` leaves optional adapter modules unloaded until a stage actually needs them, and that the `startup-path` benchmark returns the expected JSON contract.
- [scripts/measure_local.py](../../../scripts/measure_local.py) now has a validated `startup-path` probe with separate fresh-process measurements for config import, CLI import, settings initialization, orchestrator import, and orchestrator construction.
- The final measured baseline showed `config_import_ms` median `244.550`, `cli_import_ms` median `230.501`, `settings_init_ms` median `4.777`, `orchestrator_import_ms` median `236.673`, and `orchestrator_construct_ms` median `0.256`.
- That evidence showed the remaining fresh-process startup cost is primarily the configuration-framework import path in [src/minutes/config.py](../../../src/minutes/config.py), not default adapter construction or first settings initialization.
- The slice closed with the decision not to replace `pydantic-settings` for startup alone, because the likely win did not justify the framework churn and compatibility risk under the current local-first stack.

## Context To Read First

- [INDEX.md](../../../INDEX.md)
- [AGENTS.md](../../../AGENTS.md)
- [KNOWLEDGE.md](../../../KNOWLEDGE.md)
- [DEVNOTES.md](../../../DEVNOTES.md)
- [README.md](../../README.md)
- [tech-debt.md](../../tech-debt.md)

## Constraints

- Keep the repository local-first and single-user biased unless product scope changes explicitly.
- Keep recent verified truth in [DEVNOTES.md](../../../DEVNOTES.md), not in this plan.
- Do not widen this slice into TD-002 until the torch stack is pinned.
- Prefer focused validation and measured comparisons over speculative refactors.

## Affected Areas

- [src/minutes/cli.py](../../../src/minutes/cli.py)
- [src/minutes/config.py](../../../src/minutes/config.py)
- [src/minutes/orchestrator.py](../../../src/minutes/orchestrator.py)
- [scripts/measure_local.py](../../../scripts/measure_local.py)
- [tests/test_normalization_flow.py](../../../tests/test_normalization_flow.py)
- [docs/tech-debt.md](../../tech-debt.md)

## Workstreams

### Workstream 1

- Added a startup-specific probe that isolates import and constructor overhead from later model bootstrap and full pipeline work.
- Used that probe to confirm the orchestrator import boundary was only the first cheap slice, not the remaining dominant startup cost.

### Workstream 2

- Kept default adapter creation lazy in [src/minutes/orchestrator.py](../../../src/minutes/orchestrator.py) while preserving injected test seams.
- Added focused regressions for import boundaries and the startup benchmark contract.

### Workstream 3

- Recorded verified findings in [DEVNOTES.md](../../../DEVNOTES.md) and updated [tech-debt.md](../../tech-debt.md) after the startup decision was complete.

## Milestones

1. Land the first lazy-loading mitigation with a focused regression and keep the narrow pytest slice green.
2. Add and validate a startup-specific measurement path, then capture baseline evidence.
3. Decide whether TD-004 should continue or close after the measured startup investigation.

## Validation Plan

- `python -m pytest tests/test_normalization_flow.py -k "orchestrator_import_leaves_optional_adapters_unloaded or orchestrator_normalizes_job or process_job_summarizes_plain_transcript_when_configured or list_jobs_cli_prints_jobs_as_json or show_job_cli_prints_job_json"`
- `python -m pytest tests/test_normalization_flow.py -k "measure_local_startup_path_reports_import_boundary or orchestrator_import_leaves_optional_adapters_unloaded"`
- `python scripts/measure_local.py startup-path --iterations 3`
- `python -m pytest tests/test_normalization_flow.py`

## Commit Strategy

- Keep startup slices narrow and sequential: lazy adapter resolution, startup measurement, then either one more hotspot follow-up or explicit closeout.
- Update [DEVNOTES.md](../../../DEVNOTES.md) after each verified slice.
- Move this file to `docs/plans/completed/` only after the done bar is met and final validation is recorded.

## Progress Log

- 2026-05-09: Created the scoped MP-004 startup plan after the completed workflow/interface plan was archived and MP-004 became the next explicit workstream.
- 2026-05-09: Updated [src/minutes/orchestrator.py](../../../src/minutes/orchestrator.py) so default adapters are imported and constructed lazily instead of at module import and constructor time.
- 2026-05-09: Added subprocess regressions in [tests/test_normalization_flow.py](../../../tests/test_normalization_flow.py) proving optional adapter modules remain unloaded after importing and constructing `JobOrchestrator`, and that the startup benchmark reports the expected import-boundary contract.
- 2026-05-09: Added the `startup-path` command in [scripts/measure_local.py](../../../scripts/measure_local.py), validated its JSON contract, and captured fresh-process startup baselines.
- 2026-05-09: Split the `startup-path` probe into separate measurements for config import, CLI import, settings initialization, orchestrator import, and orchestrator construction, which showed [src/minutes/config.py](../../../src/minutes/config.py) import now dominates the measured startup boundary.
- 2026-05-09: Closed the plan after the full normalization suite passed and the repo accepted the remaining config-framework import cost as not worth replacement for startup alone.

## Decision Log

- 2026-05-09: Start MP-004 with an investigation-first startup slice instead of a broader performance bundle.
- 2026-05-09: Exclude TD-002 from this plan until the target torch stack is pinned.
- 2026-05-09: Treat eager adapter import and construction in [src/minutes/orchestrator.py](../../../src/minutes/orchestrator.py) as the first measured mitigation target.
- 2026-05-09: Keep the startup-specific probe inside [scripts/measure_local.py](../../../scripts/measure_local.py), but run the actual measurement in a child interpreter so the parent benchmark runner does not warm the imports under test.
- 2026-05-09: Treat the current startup bottleneck as primarily a configuration-framework import cost question, because the split probe shows first settings initialization and orchestrator construction are both small compared with importing [src/minutes/config.py](../../../src/minutes/config.py).
- 2026-05-09: Do not replace `pydantic-settings` for startup alone; the likely win does not justify the behavioral risk and framework churn under the current stack.

## Open Questions

- None. Closed on 2026-05-09 after the benchmarked startup slice showed the remaining cost is accepted under the current configuration framework.

## Risks

- A startup probe that reuses the current benchmark script without fixing its own eager imports could produce misleading numbers.
- Pushing laziness too far into stage execution could make error boundaries or dependency requirements less obvious.
- Treating contextual cold-vs-warm transcription timings as pure startup evidence would overstate what this slice actually improved.

## Handoff Notes

- Start from [DEVNOTES.md](../../../DEVNOTES.md) for the latest verified baseline before reopening any performance follow-up.
- Treat this file as historical only; it no longer owns live scoped progress.
- Reopen MP-004 only if a broader configuration simplification effort or another measured hotspot justifies more work.

## Done Bar

- The repo has one validated startup-specific measurement path for the `process-file` import boundary.
- The dominant avoidable startup hotspot has at least one verified mitigation.
- Stable owner docs capture the verified outcome, and TD-004 is updated accordingly.

## Archive Note

- Completed and moved to `docs/plans/completed/` on 2026-05-09 after the done bar was met and final validation was recorded.