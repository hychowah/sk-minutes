- Purpose: Temporary scoped execution plan for the summary-stage implementation slice
- Scope: Add a persisted summary stage, summary retrieval surfaces, and validation for the existing local pipeline; excludes packaging and provider-specific deployment work
- Status: Complete
- Last validated: 2026-05-07
- Source of truth for: The current summary-stage implementation effort only

# Title

Summary Stage Implementation

## Status

Complete

## Created Date

2026-05-07

## Last Updated Date

2026-05-07

## Branch

No git repository detected.

## Scope Type

Feature

## Goal

Add a persisted summary stage on top of the validated transcript artifacts using one OpenAI-compatible backend seam and minimal architecture churn.

## Success Criteria

- A configured job can progress from transcript artifacts to persisted `summary.json` and `summary.txt` artifacts.
- Summary input selection is deterministic and validated.
- Summary retrieval works through both the CLI and the API.
- Job-owned request language fields persist through job creation and are usable by downstream stages.

## Non-Goals

- Multi-provider backend abstraction beyond one OpenAI-compatible adapter.
- Automatic invalidation or recomputation when upstream transcript artifacts change later.
- Packaging or installer work.

## Current Checkpoint

Summary-stage code is implemented, hardened, and validated with focused fake-adapter coverage plus a successful live DeepSeek OpenAI-compatible summary run. No active scoped execution plan remains for this slice.

## Context To Read First

- [INDEX.md](../../INDEX.md)
- [AGENTS.md](../../AGENTS.md)
- [KNOWLEDGE.md](../../KNOWLEDGE.md)
- [DEVNOTES.md](../../DEVNOTES.md)

## Constraints

- Keep the current monolith and artifact-driven worker/orchestrator flow.
- Prefer the speaker-attributed transcript as summary input when it exists.
- Persist provenance metadata so summary artifacts are inspectable.
- Keep live-provider validation opt-in.

## Affected Areas

- [README.md](../../README.md)
- [.env.example](../../.env.example)
- [DEVNOTES.md](../../DEVNOTES.md)
- [KNOWLEDGE.md](../../KNOWLEDGE.md)
- [src/minutes/config.py](../../src/minutes/config.py)
- [src/minutes/orchestrator.py](../../src/minutes/orchestrator.py)
- [src/minutes/worker.py](../../src/minutes/worker.py)
- [src/minutes/cli.py](../../src/minutes/cli.py)
- [src/minutes/api/routes_jobs.py](../../src/minutes/api/routes_jobs.py)
- [src/minutes/storage/models.py](../../src/minutes/storage/models.py)
- [src/minutes/storage/file_store.py](../../src/minutes/storage/file_store.py)
- [src/minutes/adapters/summarizer_openai_compatible.py](../../src/minutes/adapters/summarizer_openai_compatible.py)
- [tests/test_normalization_flow.py](../../tests/test_normalization_flow.py)

## Workstreams

### Workstream 1

- Persist job-owned request language fields needed by downstream stages.

### Workstream 2

- Add a provider-agnostic OpenAI-compatible summary adapter and runtime settings.

### Workstream 3

- Extend orchestrator, worker, CLI, and API surfaces with summary-stage behavior.

### Workstream 4

- Validate source selection, retrieval, and scheduling with focused tests.

## Milestones

1. Job-owned request language persistence lands.
2. Summary adapter and settings land.
3. Summary stage and retrieval surfaces land.
4. Focused regression tests pass.

## Validation Plan

- Run `python -m pytest tests/test_normalization_flow.py`.
- Keep any live provider smoke test opt-in and backend-dependent.

## Commit Strategy

- Keep the provider abstraction narrow.
- Validate the narrow regression file before updating owner docs.

## Progress Log

- 2026-05-07: Created a dedicated summary-slice plan after the foundation plan became historical.
- 2026-05-07: Persisted job-owned transcription and summary language fields.
- 2026-05-07: Added the OpenAI-compatible summary adapter, summary stage, CLI/API summary retrieval, and focused regression tests.
- 2026-05-07: Hardened worker gating, missing-artifact retrieval behavior, and the default state-root configuration after a review pass.
- 2026-05-07: Validated a live summary run against a reachable DeepSeek OpenAI-compatible backend and persisted summary artifacts successfully.

## Decision Log

- 2026-05-07: Keep summary inside the existing monolith as another persisted artifact-driven stage.
- 2026-05-07: Prefer `speaker_transcript_text` over `transcript_text` when both exist.
- 2026-05-07: Persist both `summary.json` and `summary.txt` instead of making summary generation ephemeral.

## Open Questions

- No open questions remain inside this completed plan.

## Risks

- Summary artifacts currently record provenance but do not automatically invalidate when upstream transcript artifacts change later.

## Handoff Notes

- `MINUTES_SUMMARY_BASE_URL` and `MINUTES_SUMMARY_MODEL` are the minimum configuration needed to activate automatic summarization.
- `MINUTES_SUMMARY_API_KEY` remains optional because some local OpenAI-compatible backends do not require it.
- A live summary run is now validated against at least one DeepSeek OpenAI-compatible backend path using the official OpenAI client.
- Focus future validation on a text-artifact-based smoke path rather than rerunning the full audio stack unless a provider contract specifically requires it.

## Done Bar

- The repository can generate and retrieve persisted summary artifacts through the existing local pipeline surfaces.

## Archive Note

- This file is now historical summary-stage context. Do not treat it as an active execution plan unless follow-on scoped work is reopened.