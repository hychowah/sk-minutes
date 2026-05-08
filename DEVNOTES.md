- Purpose: Rolling recent verified work log
- Scope: Recent verified changes, validations, and handoff notes; excludes evergreen knowledge, stable architecture, and long-term debt ownership
- Status: Active
- Last validated: 2026-05-08
- Source of truth for: Most recent verified repository state, recent changes, next-session handoff notes

# Development Notes

## 2026-05-07 - Summary Stage Implementation

### What Changed

- Added [src/minutes/adapters/summarizer_openai_compatible.py](src/minutes/adapters/summarizer_openai_compatible.py) with a narrow OpenAI-compatible summary adapter that requests structured JSON and renders a persisted text summary.
- Switched the summary adapter to the official OpenAI Python client so remote OpenAI-compatible backends can be used directly instead of relying on a hand-rolled HTTP layer.
- Extended [src/minutes/config.py](src/minutes/config.py), [.env.example](.env.example), and [src/minutes/cli.py](src/minutes/cli.py) with summary backend settings, summary-aware job creation, `show-summary`, and `summarize-job` surfaces.
- Extended [src/minutes/storage/models.py](src/minutes/storage/models.py) and [src/minutes/storage/file_store.py](src/minutes/storage/file_store.py) so job-owned transcription and summary language fields persist through job creation.
- Extended [src/minutes/orchestrator.py](src/minutes/orchestrator.py), [src/minutes/worker.py](src/minutes/worker.py), and [src/minutes/api/routes_jobs.py](src/minutes/api/routes_jobs.py) with a persisted summary stage that prefers the speaker-attributed transcript when it exists and writes `summary.json` plus `summary.txt`.
- Hardened the worker so source-less jobs are no longer treated as actionable by summary or diarization stages.
- Hardened transcript and summary retrieval so missing artifact files return controlled not-found responses instead of tracebacks.
- Aligned the checked-in default runtime state root with the documented workspace-local `.minutes-data` path.
- Changed [.env.example](.env.example) to use a generic OpenAI-compatible summary base URL placeholder instead of a localhost-specific example.
- Created a temporary summary-slice plan during implementation and later removed the completed plan file after stable owner docs were updated.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with focused summary-stage coverage for source selection, worker pickup, API retrieval, CLI retrieval, and explicit summarize triggering.

### What Was Tried

- Started with the smallest prerequisite fix by persisting job-owned request language fields before adding summary behavior.
- Kept summary inside the existing artifact-driven monolith instead of activating the placeholder pipeline package or adding a separate service.
- Made summary generation automatic only when `MINUTES_SUMMARY_BASE_URL` and `MINUTES_SUMMARY_MODEL` are configured.
- Reused the existing transcript retrieval pattern for summary retrieval rather than introducing a generic retrieval framework.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py::test_create_job_persists_requested_languages` passed.
- `python -m pytest tests/test_normalization_flow.py -k "summarize or summary_route or show_summary or missing_summary_artifact"` passed with 8 selected tests.
- `python -m pytest tests/test_normalization_flow.py` passed with 26 tests after the summary-stage changes and hardening fixes.
- `python -m pytest tests/test_normalization_flow.py -k "summarize or summary_route or show_summary or missing_summary_artifact"` passed again after switching the adapter to the OpenAI client.
- `python -m minutes show-config` resolved successfully with the workspace-local `.minutes-data` state root.
- `python -m compileall src` succeeded after the final review-driven fixes.
- `python -m minutes summarize-job 37faa46a38cb4670a7d46d3d9ffc816e` completed successfully after the summary backend was pointed at a reachable OpenAI-compatible endpoint.
- `python -m minutes show-summary 37faa46a38cb4670a7d46d3d9ffc816e` returned persisted summary text generated from the existing speaker-attributed transcript artifact.

### Next Session Should Know

- Automatic summarization stays inactive until `MINUTES_SUMMARY_BASE_URL` and `MINUTES_SUMMARY_MODEL` are configured.
- `MINUTES_SUMMARY_API_KEY` remains optional so local OpenAI-compatible gateways can work without a bearer token.
- Summary artifacts persist source-artifact provenance metadata, but the repository does not yet auto-invalidate summaries if upstream transcript artifacts change later.
- Live-provider summary generation is now validated against at least one real OpenAI-compatible backend path using the official OpenAI client.

## 2026-05-05 - Sample Output Folder And Commit Alignment

### What Changed

- Added a curated committed sample output set under [sample/test1](sample/test1) using artifacts from the validated `file/test1.mp3` real run.
- Added [sample/README.md](sample/README.md), [sample/test1/metadata.json](sample/test1/metadata.json), [sample/test1/transcript.txt](sample/test1/transcript.txt), and [sample/test1/speaker_transcript.txt](sample/test1/speaker_transcript.txt).
- Updated [.gitignore](.gitignore) so bulky copied artifacts such as normalized WAV files and per-speaker scratch folders remain untracked even if future examples are staged under `sample/`.
- Updated [README.md](README.md), [INDEX.md](INDEX.md), [KNOWLEDGE.md](KNOWLEDGE.md), and [docs/plans/README.md](docs/plans/README.md) to match the current repository state for commit.

### What Was Tried

- Reviewed the owner docs and plan docs against the actual workspace state before adding new files.
- Chose a curated sample set rather than copying the full `.minutes-data` job directory into the repository.
- Kept the committed example focused on reviewable outputs and left bulky runtime artifacts in the gitignored runtime state root.

### What Was Validated

- The sample files were copied from the successful `file/test1.mp3` run that completed at `speaker_attributed`.
- The updated markdown and ignore files reported no editor-detected errors.

### Next Session Should Know

- The committed example outputs now live under `sample/test1` and can be used for documentation, UI mocks, or summary-stage development without browsing `.minutes-data`.
- The runtime state root remains `.minutes-data`; `sample/` is only for curated examples that are intentionally committed.

## 2026-05-05 - Speaker-Attributed Transcript Assembly

### What Changed

- Extended [src/minutes/orchestrator.py](src/minutes/orchestrator.py) with a speaker-attributed assembly stage that runs after diarization and writes `speaker_transcript.json` plus `speaker_transcript.txt`.
- Added short-window padding during segment retranscription so tiny diarization windows do not fail SenseVoice feature extraction on real audio.
- Extended [src/minutes/worker.py](src/minutes/worker.py) so diarization-enabled jobs continue until the `speaker_attributed` stage is complete.
- Extended [src/minutes/api/routes_jobs.py](src/minutes/api/routes_jobs.py) and [src/minutes/cli.py](src/minutes/cli.py) so the existing transcript retrieval surfaces can return the speaker-attributed text.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with coverage for speaker-attributed pipeline completion and transcript retrieval.

### What Was Tried

- Reused diarization timing windows as the only reliable alignment source because the current SenseVoice transcript artifact does not expose word or segment timestamps.
- Built speaker-attributed text by retranscribing merged diarization windows from the normalized WAV artifact.
- Reproduced a real failure on `file/test1.mp3` caused by very short diarization windows and then fixed it locally by padding retranscribed clips to a minimum duration.
- Reused the existing transcript API and CLI entrypoints instead of adding separate speaker-transcript commands or routes.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py` passed with 9 tests after the speaker-attributed stage and retrieval updates.
- `python -m minutes process-file <repo-root>\file\test1.mp3` completed successfully with `current_stage: speaker_attributed`.
- The successful real run wrote `speaker_transcript.json` and `speaker_transcript.txt` under the workspace-local `.minutes-data` state root.

### Next Session Should Know

- Speaker attribution is currently assembled by retranscribing diarization windows, not by aligning timestamps from the base transcript.
- Very short diarization windows are padded before retranscription to keep SenseVoice stable on real media.
- The existing transcript retrieval surfaces now support speaker-attributed output through `--speaker-attributed` in the CLI and `?speaker_attributed=true` in the API.

## 2026-05-05 - Documentation Wording Cleanup

### What Changed

- Updated [README.md](README.md) to remove machine-specific wording from setup and test guidance.
- Updated [README.md](README.md) and the temporary plan docs that existed at the time to replace `*-first` wording with more neutral phrasing.

### What Was Tried

- Replaced environment-specific path references in the user-facing docs with configuration-based guidance.
- Searched markdown docs for remaining `*-first` phrasing after the edits.

### What Was Validated

- A markdown search found no remaining `*-first` phrasing in repository docs.
- The edited documentation files reported no editor-detected errors.

### Next Session Should Know

- Keep stable docs generic and configuration-driven unless a machine-specific detail is required for correctness.

## 2026-05-05 - Documentation Bootstrap

### What Changed

- Created the minimum documentation control plane for an empty repository.
- Added [README.md](README.md), [INDEX.md](INDEX.md), [AGENTS.md](AGENTS.md), [KNOWLEDGE.md](KNOWLEDGE.md), [DEVNOTES.md](DEVNOTES.md), [docs/tech-debt.md](docs/tech-debt.md), [docs/plans/README.md](docs/plans/README.md), and [docs/plans/_EXEC_PLAN_TEMPLATE.md](docs/plans/_EXEC_PLAN_TEMPLATE.md).

### What Was Tried

- Inspected the repository and confirmed it was empty before creating any documentation.
- Chose the minimum required file set only.

### What Was Validated

- No repository files existed before bootstrap.
- No optional documentation files were justified by the current repository state.
- Unknown operational details remained explicitly marked as Unknown yet.

### Next Session Should Know

- The repository has no implementation yet.
- Create the first active execution plan only when real scoped work begins.
- If code is added later, update the owner document instead of spreading the same live status across multiple files.

## 2026-05-05 - Implementation Foundation

### What Changed

- Created an active scoped execution plan for the first implementation effort.
- Added the Python project manifest at [pyproject.toml](pyproject.toml).
- Added the initial application package under [src/minutes](src/minutes) with runtime configuration, CLI entrypoint, FastAPI bootstrap, and a minimal file-backed job store.
- Added [scripts/doctor.ps1](scripts/doctor.ps1) and [scripts/run-local.ps1](scripts/run-local.ps1) for local validation and launch.
- Added [.gitignore](.gitignore) and [.env.example](.env.example) for local development hygiene.
- Added the first ffmpeg adapter at [src/minutes/adapters/ffmpeg.py](src/minutes/adapters/ffmpeg.py).
- Changed the default runtime state root from `%LOCALAPPDATA%` to a user-writable path outside the repository because external tools could not reliably access the AppData-backed path.
- Added [src/minutes/orchestrator.py](src/minutes/orchestrator.py) to execute the normalization stage for a persisted job.
- Added [src/minutes/worker.py](src/minutes/worker.py) and the `python -m minutes run-once` CLI path to process the next queued job.
- Added [tests/test_normalization_flow.py](tests/test_normalization_flow.py) for targeted normalization regressions.
- Added [src/minutes/adapters/transcriber_sensevoice.py](src/minutes/adapters/transcriber_sensevoice.py) to transcribe normalized audio with SenseVoice through FunASR.
- Extended the orchestrator, worker, routes, and CLI so a job can proceed from normalization to transcription, including the `python -m minutes process-file` path.
- Updated [pyproject.toml](pyproject.toml) to declare the speech stack dependencies used by the new transcription stage.
- Added transcript retrieval through the API and the `python -m minutes show-transcript` CLI path.
- Added [tests/test_real_audio_integration.py](tests/test_real_audio_integration.py) to exercise the repository-local [file/test1.mp3](file/test1.mp3) fixture as an opt-in real-audio integration test.
- Added [src/minutes/adapters/diarizer_pyannote.py](src/minutes/adapters/diarizer_pyannote.py) and an opt-in pyannote 3.1 diarization stage in the orchestrator.
- Moved the validated local runtime state root to the workspace-local `.minutes-data` directory and ignored it through [.gitignore](.gitignore).

### What Was Tried

- Scaffolded the application foundation before touching pipeline-specific integrations.
- Installed the project into the existing local virtual environment in editable mode.
- Exercised the file-backed job store by creating, reloading, and then removing a dummy validation job under the external state root.
- Verified a local ffmpeg installation and wired it into runtime configuration and the doctor script.
- Added and exercised ffmpeg-backed media probing and normalization against a synthetic sample.
- Wired the existing file-backed jobs model to a real normalization execution path.
- Exercised normalization directly, through the FastAPI route, and through the CLI worker path.
- Installed `torch`, `torchaudio`, `funasr`, `modelscope`, and `huggingface_hub` into the repository environment.
- Ran a real spoken WAV generated with Windows `System.Speech` through the public `python -m minutes process-file` path.
- Reproduced the first transcription failure directly and traced it to FunASR invoking `ffmpeg` by name after torchaudio fell back from missing `torchcodec`.
- Fixed that by prepending the configured ffmpeg directory to `PATH` inside the SenseVoice adapter and then reran transcription successfully.
- Fixed the API settings propagation bug so route handlers use the app's configured state root instead of a default global store.
- Exercised the repository-local `file/test1.mp3` fixture through an opt-in pytest integration test.
- Installed `pyannote.audio`, found that its import path breaks against the current `torchaudio` top-level API, and added a narrow compatibility shim in the adapter so pyannote can import.
- Added fake-diarizer coverage so the staged pipeline can validate normalization, transcription, and opt-in diarization without requiring a Hugging Face token.
- Exercised a real pyannote-backed run with a configured Hugging Face token and advanced past token access, hub auth, torchaudio API, PyTorch serialization, and SpeechBrain lazy-import issues.
- Switched pyannote audio input to an in-memory waveform payload so the Windows runtime no longer depends on `torchcodec` file loading.
- Replaced the CPU-only `torch` and `torchaudio` wheels with CUDA-enabled Windows wheels and verified GPU execution in the local environment.
- Fixed Windows subprocess decoding in the ffmpeg adapter by forcing UTF-8 with replacement during command capture.

### What Was Validated

- No editor-detected errors were present in the new Python modules or `pyproject.toml`.
- `python -m compileall src` succeeded.
- `python -m minutes show-config` resolved the expected runtime settings.
- Importing `minutes.api.app:create_app` at runtime succeeded and returned the expected app title and version.
- The new job store persisted and reloaded a job record successfully.
- `scripts/doctor.ps1` now succeeds and resolves `ffmpeg` from the configured binary path.
- The ffmpeg adapter successfully reported version information, probed generated media, and normalized a sample to mono 16 kHz WAV using the new default state root.
- `python -m pytest tests/test_normalization_flow.py` passed with coverage for orchestrator, worker, and API normalization paths.
- The staged job tests still pass after the transcription-stage refactor.
- A direct transcription retry against the previously failed normalized WAV succeeded after the ffmpeg `PATH` fix.
- `python -m minutes process-file <path-to-audio>` completed successfully and produced transcript artifacts.
- The transcript text from the spoken test WAV was: `Hello, this is a test recording for the minutess application.`
- `python -m pytest tests/test_normalization_flow.py` now passes with transcript retrieval coverage included.
- `$env:MINUTES_RUN_REAL_AUDIO_TESTS='1'; python -m pytest tests/test_real_audio_integration.py -m integration` passed against [file/test1.mp3](file/test1.mp3).
- `python -m pytest tests/test_normalization_flow.py` passes with 7 tests after adding diarization-stage coverage.
- `python -c "from minutes.adapters.diarizer_pyannote import PyannoteDiarizer; PyannoteDiarizer._ensure_torchaudio_compat(); import pyannote.audio; print(pyannote.audio.__version__)"` succeeded and reported `3.4.0`.
- `python -m minutes process-file <repo-root>\file\test1.mp3` now completes successfully with transcription and diarization artifacts written under the workspace-local `.minutes-data` state root.
- The successful real run used GPU-backed transcription and diarization in a validated local environment.

### Next Session Should Know

- The repository now has a working foundation scaffold and minimal persisted job state.
- The repository now has a working normalization path from queued job to canonical WAV artifact.
- The repository now has a working end-to-end normalization plus transcription path for a single audio file.
- The repository now has an opt-in diarization stage that writes `diarization.json` and `diarization.rttm` artifacts when enabled.
- The repository now has a repeatable opt-in integration test for the committed `file/test1.mp3` fixture.
- Live Windows diarization is now working in this environment with the in-memory audio path and CUDA-enabled `torch` / `torchaudio` wheels.
- The next implementation slice can build summarization on top of the validated speaker-attributed transcript artifacts.
- `ffmpeg` is available through explicit configuration and no longer blocks media normalization work.
