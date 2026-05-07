- Purpose: Temporary scoped execution plan for initial implementation work
- Scope: Establish the first code foundation, bootstrap runtime, and near-term implementation sequence; excludes repo-wide truth ownership
- Status: Active
- Last validated: 2026-05-05
- Source of truth for: This implementation effort only

# Title

Initial Local Minutes Implementation

## Status

Complete

## Created Date

2026-05-05

## Last Updated Date

2026-05-07

## Branch

No git repository detected.

## Scope Type

Feature

## Goal

Create the first runnable Python foundation for a local transcription pipeline based on SenseVoice and pyannote 3.1.

## Success Criteria

- The repository contains a Python project manifest and importable package.
- A minimal FastAPI app can be created successfully.
- Runtime configuration resolves to a local app-state root and keeps generated state gitignored.
- The implementation path for the next slices is documented without replacing owner documents.
- A real audio file can be processed through the current runnable slice.

## Non-Goals

- Final summary generation integration inside this foundation plan.
- Final packaging or installer work.

## Current Checkpoint

Foundation scaffold, local scripts, file-backed job state, normalization orchestration, transcription orchestration, transcript retrieval, opt-in diarization plus speaker-attributed assembly orchestration, worker execution, real-audio CLI plus fixture-based integration tests, and a committed example output set under `sample/test1` are validated. Follow-on summary work now lives in [docs/plans/2026-05-07-summary-stage-implementation.md](2026-05-07-summary-stage-implementation.md).

## Context To Read First

- [INDEX.md](../../INDEX.md)
- [AGENTS.md](../../AGENTS.md)
- [KNOWLEDGE.md](../../KNOWLEDGE.md)
- [DEVNOTES.md](../../DEVNOTES.md)

## Constraints

- Keep implementation local and Python-based.
- Keep large model caches outside the synced repository when practical, but keep the validated workspace-local `.minutes-data` runtime state root gitignored.
- Keep v1 architecture simple: one web/backend process plus one worker process later.
- Do not hard-code exact resource caps that Windows and CUDA cannot guarantee.

## Affected Areas

- [README.md](../../README.md)
- [sample/](../../sample/)
- [pyproject.toml](../../pyproject.toml)
- [src/minutes/](../../src/minutes/)
- [scripts/](../../scripts/)

## Workstreams

### Workstream 1

- Establish Python packaging and runtime configuration.

### Workstream 2

- Create minimal FastAPI application bootstrap and CLI entrypoint.

### Workstream 3

- Add first-run validation and documentation updates after verified work.

## Milestones

1. Foundation scaffold committed to the working tree.
2. Basic app bootstrap validated.
3. Owner documents updated after verification.

## Validation Plan

- Run a narrow Python validation against the new package.
- Check new files for syntax or import errors.

## Commit Strategy

- Keep early changes small and foundation-focused.
- Validate each scaffold slice before widening scope.

## Progress Log

- 2026-05-05: Created active execution plan and began foundation scaffold.
- 2026-05-05: Added Python packaging, runtime configuration, FastAPI bootstrap, local scripts, and a file-backed job store.
- 2026-05-05: Added ffmpeg path configuration, resolved the state-root path issue, and validated media probing plus normalization.
- 2026-05-05: Added job normalization orchestration, a run-once worker path, and passing normalization regression tests.
- 2026-05-05: Added SenseVoice/FunASR transcription, fixed the ffmpeg PATH issue for FunASR loading, and validated end-to-end transcription on a generated spoken WAV.
- 2026-05-05: Added transcript retrieval surfaces and validated the committed `file/test1.mp3` fixture with an opt-in integration test.
- 2026-05-05: Added an opt-in pyannote diarization stage, validated the fake-diarizer pipeline path, and confirmed pyannote import works with a torchaudio compatibility shim.
- 2026-05-05: Added speaker-attributed transcript assembly, hardened it against very short diarization windows, and validated retrieval through the existing CLI and API surfaces.
- 2026-05-05: Added a curated committed sample output set under `sample/test1` based on the validated real run of `file/test1.mp3`.
- 2026-05-07: Closed this foundation plan and split ongoing summary work into [docs/plans/2026-05-07-summary-stage-implementation.md](2026-05-07-summary-stage-implementation.md).

## Decision Log

- 2026-05-05: Start with a Python monolith and local web bootstrap instead of a frontend-heavy or multi-service design.

## Open Questions

- No open questions remain inside this foundation plan. Summary-stage questions moved to [docs/plans/2026-05-07-summary-stage-implementation.md](2026-05-07-summary-stage-implementation.md).

## Risks

- OpenAI-compatible summary backend selection and prompt design remain a later integration risk.
- pyannote currently relies on a local torchaudio compatibility shim in this repo because the installed torchaudio removed top-level APIs that pyannote still imports.

## Handoff Notes

- The validated runtime state root for this repository is now the workspace-local `.minutes-data` directory, which remains gitignored.
- Normalization, transcription, diarization, and speaker-attributed transcript assembly are now live pipeline stages.
- The current `process-file` CLI path works on real audio with GPU-backed transcription and diarization in this environment.
- The existing transcript retrieval surfaces can now return speaker-attributed text without direct artifact browsing.
- The repository-local `file/test1.mp3` fixture remains the safest repeatable path for real-audio validation.
- A curated example output set from that validated real run now lives under `sample/test1` for commit-safe inspection and downstream development.
- Summary implementation continues in [docs/plans/2026-05-07-summary-stage-implementation.md](2026-05-07-summary-stage-implementation.md).

## Done Bar

- The Python package exists, imports cleanly, and exposes a minimal app bootstrap path.

## Archive Note

- This file is now historical foundation context. Do not treat it as the active plan for new implementation slices.