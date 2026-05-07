- Purpose: Reusable technical lessons and constraints for future contributors and sessions
- Scope: Stable patterns, documentation conventions, and reusable gotchas; excludes chronological work logs and task-local status
- Status: Active
- Last validated: 2026-05-07
- Source of truth for: Reusable repository lessons, constraints, and anti-patterns

# Reusable Knowledge

## Current Constraints

- The repository has only an initial implementation foundation so far.
- Summary integration is validated against at least one OpenAI-compatible backend, but activation still depends on configuring the summary base URL and model.
- pyannote diarization requires a Hugging Face token with accepted model conditions before live runs can succeed.
- The validated local setup in this repository keeps runtime state under `.minutes-data` in the workspace root and ignores it through git.

## Patterns To Reuse

- Keep one owner per type of truth.
- Prefer linking to the owner document over copying live status.
- Separate stable reference docs from temporary task docs.
- Validate each new implementation slice with the narrowest executable check available before widening scope.
- Commit only curated example outputs under `sample/`; keep full runtime artifacts in the gitignored `.minutes-data` state root.
- Prefer a normal user-owned state root over `%LOCALAPPDATA%` when external binaries need to read and write the same files on this Windows setup.
- Add a focused regression test as soon as a new execution path becomes real, especially for file and process orchestration.
- Persist job-owned request fields in the stored job record as soon as downstream stages depend on them, or later feature flags and language overrides will be lost across worker boundaries.
- Treat downstream LLM stages as artifact-driven text derivations and record source-artifact provenance in their output metadata.
- On this Windows setup, FunASR may call `ffmpeg` by name during audio loading even when the app already knows the explicit binary path, so the configured ffmpeg directory must also be injected into `PATH` before transcription.
- Keep heavyweight real-model audio tests opt-in and fixture-based so they are reproducible without slowing every normal test run.
- When pyannote is used with the current torch and torchaudio stack in this repo, compatibility shims may be required because pyannote 3.x still expects older torchaudio top-level APIs.
- On Windows, SpeechBrain lazy imports can also be tripped accidentally by Python's `inspect` path handling, so guard patches may be needed before pyannote model loading succeeds.
- On Windows, feeding pyannote an in-memory waveform from `soundfile` is a practical way to bypass fragile `torchcodec` file-loading requirements.
- When speaker-attributed transcript assembly retranscribes diarization windows, pad very short windows before sending them through SenseVoice or the model can fail on degenerate feature shapes.

## Anti-Patterns To Avoid

- Duplicating current status across README, plans, and notes.
- Treating temporary plan files as canonical repository truth.
- Writing speculative commands or architecture before implementation exists.
- Committing raw runtime artifacts from `.minutes-data` when a smaller curated example under `sample/` would do.
- Storing large model caches inside the synced repository tree.
- Assuming a path is usable by external tools just because Python can see it.
