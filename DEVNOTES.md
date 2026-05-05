- Purpose: Rolling recent verified work log
- Scope: Recent verified changes, validations, and handoff notes; excludes evergreen knowledge, stable architecture, and long-term debt ownership
- Status: Active
- Last validated: 2026-05-05
- Source of truth for: Most recent verified repository state, recent changes, next-session handoff notes

# Development Notes

## 2026-05-05 - Sample Output Folder And Commit Alignment

### What Changed

- Added a curated committed sample output set under [sample/test1](sample/test1) using artifacts from the validated `file/test1.mp3` real run.
- Added [sample/README.md](sample/README.md), [sample/test1/metadata.json](sample/test1/metadata.json), [sample/test1/transcript.txt](sample/test1/transcript.txt), and [sample/test1/speaker_transcript.txt](sample/test1/speaker_transcript.txt).
- Updated [.gitignore](.gitignore) so bulky copied artifacts such as normalized WAV files and per-speaker scratch folders remain untracked even if future examples are staged under `sample/`.
- Updated [README.md](README.md), [INDEX.md](INDEX.md), [KNOWLEDGE.md](KNOWLEDGE.md), [docs/plans/README.md](docs/plans/README.md), and [docs/plans/2026-05-05-local-minutes-implementation.md](docs/plans/2026-05-05-local-minutes-implementation.md) to match the current repository state for commit.

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
- `python -m minutes process-file C:\Users\user\OneDrive\Documents\Minutes\file\test1.mp3` completed successfully with `current_stage: speaker_attributed`.
- The successful real run wrote `speaker_transcript.json` and `speaker_transcript.txt` under the workspace-local `.minutes-data` state root.

### Next Session Should Know

- Speaker attribution is currently assembled by retranscribing diarization windows, not by aligning timestamps from the base transcript.
- Very short diarization windows are padded before retranscription to keep SenseVoice stable on real media.
- The existing transcript retrieval surfaces now support speaker-attributed output through `--speaker-attributed` in the CLI and `?speaker_attributed=true` in the API.

## 2026-05-05 - Documentation Wording Cleanup

### What Changed

- Updated [README.md](README.md) to remove machine-specific wording from setup and test guidance.
- Updated [README.md](README.md) and [docs/plans/2026-05-05-local-minutes-implementation.md](docs/plans/2026-05-05-local-minutes-implementation.md) to replace `*-first` wording with more neutral phrasing.

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
- Replaced the CPU-only `torch` and `torchaudio` wheels with CUDA-enabled Windows wheels and verified GPU execution on the local RTX 4070.
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
- `python -m minutes process-file C:\Users\user\OneDrive\Documents\Minutes\file\test1.mp3` now completes successfully with transcription and diarization artifacts written under the workspace-local `.minutes-data` state root.
- The successful real run recorded `device: cuda:0` for both SenseVoice transcription and pyannote diarization.

### Next Session Should Know

- The repository now has a working foundation scaffold and minimal persisted job state.
- The repository now has a working normalization path from queued job to canonical WAV artifact.
- The repository now has a working end-to-end normalization plus transcription path for a single audio file.
- The repository now has an opt-in diarization stage that writes `diarization.json` and `diarization.rttm` artifacts when enabled.
- The repository now has a repeatable opt-in integration test for the committed `file/test1.mp3` fixture.
- Live Windows diarization is now working in this environment with the in-memory audio path and CUDA-enabled `torch` / `torchaudio` wheels.
- The next implementation slice can build summarization on top of the validated speaker-attributed transcript artifacts.
- `ffmpeg` is available through explicit configuration and no longer blocks media normalization work.
