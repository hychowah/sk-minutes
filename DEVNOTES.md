- Purpose: Rolling recent verified work log
- Scope: Recent verified changes, validations, and handoff notes; excludes evergreen knowledge, stable architecture, and long-term debt ownership
- Status: Active
- Last validated: 2026-05-09
- Source of truth for: Most recent verified repository state, recent changes, next-session handoff notes

# Development Notes

## 2026-05-09 - FunASR Cached Model Reuse

### What Changed

- Updated [src/minutes/adapters/transcriber_sensevoice.py](src/minutes/adapters/transcriber_sensevoice.py) so the transcriber now prefers existing ModelScope cache directories for the configured SenseVoice and VAD models before handing values to FunASR.
- The same change now passes `disable_update=True` to `AutoModel`, which suppresses FunASR's version-update check during model bootstrap.

### What Was Tried

- Kept the change local to the transcriber adapter instead of adding new config surface first.
- Reused FunASR's own ModelScope name map for aliases like `fsmn-vad`, so cached-path resolution stays aligned with the installed package rather than a repo-local duplicate table.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "transcriber_model_kwargs_prefer_cached_modelscope_paths or show_config_includes_summary_retry_settings or list_jobs_cli_prints_jobs_as_json or show_job_cli_prints_job_json"` passed with 4 selected tests.
- Runtime inspection confirmed that the expected cached model directories already exist under `%USERPROFILE%\.cache\modelscope\hub\models\iic\SenseVoiceSmall` and `%USERPROFILE%\.cache\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch`.

### Next Session Should Know

- The first cold run still needs the hub download, but once those directories exist the transcriber should pass their local paths into FunASR instead of raw hub identifiers.
- If startup still feels slow after this, the remaining time is more likely model load time, ffmpeg normalization, or deeper eager imports rather than repeated hub download resolution.

## 2026-05-09 - CLI Serve-Only Import Deferral

### What Changed

- Updated [src/minutes/cli.py](src/minutes/cli.py) so `uvicorn` and `create_app` are imported only inside the `serve` command branch instead of at module import time.
- Kept the rest of the CLI command routing unchanged, so non-serve commands like `process-file`, `show-config`, `list-jobs`, and `show-job` still execute through the same command branches after settings load.

### What Was Tried

- Chose the smallest startup-cost slice first: remove web-server and API-stack imports from the default CLI import path before touching deeper orchestration imports.
- Verified the import boundary directly rather than inferring it from timings alone.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "show_config_includes_summary_retry_settings or list_jobs_cli_prints_jobs_as_json or show_job_cli_prints_job_json"` passed with 3 selected tests.
- Running a direct Python snippet in the workspace showed that importing `minutes.cli` no longer loads `minutes.api.app` or `uvicorn` into `sys.modules`.

### Next Session Should Know

- Non-serve CLI startup is now narrower than before, but `process-file` still imports `JobOrchestrator`, which currently imports all adapter modules up front.
- The next startup-reduction slice, if needed, is to defer heavy adapter-module imports in [src/minutes/orchestrator.py](src/minutes/orchestrator.py) until their stage is actually reached.

## 2026-05-09 - Workflow Contract Plan Closeout

### What Changed

- Updated [src/minutes/storage/models.py](src/minutes/storage/models.py) and [src/minutes/storage/file_store.py](src/minutes/storage/file_store.py) so stored jobs no longer persist the now-obsolete `current_stage` field.
- Updated [src/minutes/orchestrator.py](src/minutes/orchestrator.py) so the raw stored job record now keeps one `workflow_stage` marker plus `status`, and summary generation now reuses the shared [src/minutes/pipeline/__init__.py](src/minutes/pipeline/__init__.py) `summary_source_artifact` owner instead of a duplicate private helper.
- Updated [tests/test_normalization_flow.py](tests/test_normalization_flow.py) so internal workflow assertions now use `workflow_stage` and `next_pending_stage` rather than the removed `current_stage` field.
- Moved the finished scoped plan to [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md) and updated [INDEX.md](INDEX.md), [docs/README.md](docs/README.md), [docs/plans/README.md](docs/plans/README.md), [docs/progress-tracker.md](docs/progress-tracker.md), and [docs/master-plan.md](docs/master-plan.md) so the repository no longer claims there is active scoped work when there is not.

### What Was Tried

- Removed `current_stage` from storage instead of keeping it as a persistence-only compatibility field, because the only remaining implementation users were orchestrator writes and test assertions.
- Kept the public transport contract and the raw stored workflow marker separate: public job payloads still derive canonical progress from shared artifact rules, while stored jobs keep only the raw stage/status needed by the worker and orchestrator.
- Closed the scoped workflow/interface plan rather than stretching it into performance work, so MP-004 can become the next explicit active slice without mixing owner docs.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "test_orchestrator_normalizes_job or test_summarize_job_waits_for_speaker_transcript_when_diarization_enabled or test_worker_run_once_picks_up_job_missing_summary_artifact or test_process_job_summarizes_plain_transcript_when_configured or test_summarize_job_prefers_existing_speaker_transcript_even_when_diarization_disabled"` passed with 5 selected tests.
- `python -m pytest tests/test_normalization_flow.py` passed with 39 tests after removing `current_stage` from persistence and closing the scoped plan.

### Next Session Should Know

- There is no active scoped execution plan currently; the finished workflow/interface plan is now historical at [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md).
- `current_stage` is gone from both public transport and stored job records; internal code should use `status`, raw `workflow_stage`, and shared helpers like `next_pending_stage` instead.
- The clearest next active slice is MP-004 performance follow-up, using the existing validated measurements rather than reopening workflow-contract cleanup.

## 2026-05-09 - Public Job Contract Canonicalization

### What Changed

- Updated [src/minutes/storage/models.py](src/minutes/storage/models.py) so `JobResponse` is now an explicit public transport model instead of inheriting every persisted `JobRecord` field by default.
- Updated [src/minutes/job_view.py](src/minutes/job_view.py) so CLI and API job payloads are assembled intentionally from shared workflow helpers instead of passing through `job.model_dump()`.
- Updated [src/minutes/pipeline/__init__.py](src/minutes/pipeline/__init__.py) with shared `summary_state` and canonical `workflow_progress_stage` helpers so public job payloads expose summary freshness and artifact-backed workflow progress from one owner.
- Removed `current_stage` from public CLI and API job payloads while keeping the stored job record permissive for existing on-disk compatibility.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) and [tests/test_real_audio_integration.py](tests/test_real_audio_integration.py) so transport-facing coverage now asserts the new public payload contract and the out-of-order diarization edge case.

### What Was Tried

- Kept the storage model intact for now and changed only the public transport assembly first, so the compatibility cut stays local to CLI and API payloads instead of forcing a storage migration immediately.
- Reused the shared pipeline owner for both `summary_state` and public `workflow_stage` derivation instead of teaching the serializer a second set of artifact rules.
- Treated stale summaries as falling back to the last current non-summary workflow stage in public payloads, so `workflow_stage` and `next_stage` stay coherent even when old summary artifacts still exist.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "test_list_jobs_cli_prints_jobs_as_json or test_show_job_cli_prints_job_json or test_get_job_route_reports_stale_summary_state or test_get_job_route_canonicalizes_workflow_stage_after_out_of_order_diarization or test_summarize_job_route_runs_summary_stage"` passed with 5 selected tests across the transport-contract slice.
- `python -m pytest tests/test_normalization_flow.py` passed with 39 tests after the public job contract canonicalization slice.

### Next Session Should Know

- Public job payloads no longer expose `current_stage`; downstream CLI and API consumers should use `workflow_stage`, `next_stage`, and `summary_state` instead.
- Public `workflow_stage` is now derived from canonical artifact-backed progress rather than the raw persisted field, so out-of-order stage execution no longer leaks confusing workflow history into transport payloads.
- The remaining cleanup question is whether `current_stage` should stay persisted internally for compatibility or be retired from storage as well once on-disk migration expectations are clearer.

## 2026-05-09 - Summary Freshness Visibility

### What Changed

- Updated [src/minutes/queries.py](src/minutes/queries.py) so summary retrieval now derives freshness from the shared pipeline owner and returns whether the persisted summary still matches the currently selected source artifact.
- Extended [src/minutes/storage/models.py](src/minutes/storage/models.py) `SummaryResponse` with `source_current`, `current_source_artifact_kind`, and `current_source_artifact_path` so API responses and CLI JSON can expose summary freshness without changing the plain-text path.
- Promoted the shared summary source helpers in [src/minutes/pipeline/__init__.py](src/minutes/pipeline/__init__.py) into the public pipeline surface so retrieval and workflow gating use the same staleness rule.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with focused API and CLI coverage for fresh and intentionally stale summary retrieval.

### What Was Tried

- Kept the change in the shared query layer rather than adding separate CLI and API logic so both surfaces derive freshness from the same owner.
- Exposed current-source details only in JSON response fields instead of changing plain-text summary output, keeping the default operator path compact.
- Treated summary freshness as unknown when no current source artifact is selected under the active settings, instead of forcing a misleading `true` or `false` value.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "test_summary_route_returns_text or test_summary_route_reports_stale_summary_source_state or test_show_summary_cli_json_includes_source_status"` passed with 3 selected tests.
- `python -m pytest tests/test_normalization_flow.py` passed with 37 tests after the summary freshness visibility slice.

### Next Session Should Know

- API summary retrieval and CLI `show-summary --json` now expose whether the summary still matches the currently selected source artifact, plus the current source kind and path when one is available.
- The plain-text summary output intentionally stays unchanged; operators who need freshness details should use the JSON path.
- The next likely summary-facing slice is whether job-level transport should surface similar freshness hints, or whether `current_stage` retirement is now the higher-value cleanup.

## 2026-05-09 - Summary Provenance Benchmark Follow-Up

### What Changed

- Extended [scripts/measure_local.py](scripts/measure_local.py) `control-plane` with synthetic `summary-current` and `summary-stale` scenarios so worker pickup can measure the new summary provenance gate directly instead of inferring from the old created-job baseline.
- Pinned that synthetic control-plane benchmark to `diarization_enabled=False` so transcript-based summary eligibility is measured consistently regardless of local `.env` overrides.
- Kept the benchmark slice read-only with respect to runtime behavior: no pipeline logic changed after the provenance invalidation implementation.

### What Was Tried

- Reused the existing control-plane benchmark instead of adding a separate summary benchmark command, so scan comparisons stay in one place.
- Seeded current-summary jobs as non-actionable and stale-summary jobs as actionable to measure the exact `next_pending_stage` comparison path introduced by summary provenance invalidation.
- Fixed an initial false-negative benchmark shape after confirming the synthetic settings were inheriting local diarization config and suppressing transcript-based summary readiness.

### What Was Validated

- `python scripts/measure_local.py control-plane --job-count 25 --iterations 3 --scenario summary-stale` passed after pinning the synthetic settings.
- `python scripts/measure_local.py control-plane --job-count 250 --iterations 5 --scenario created` reported `next_actionable_job_ms` median `34.847`.
- `python scripts/measure_local.py control-plane --job-count 250 --iterations 5 --scenario summary-current` reported `next_actionable_job_ms` median `37.640`.
- `python scripts/measure_local.py control-plane --job-count 250 --iterations 5 --scenario summary-stale` reported `next_actionable_job_ms` median `36.935`.

### Next Session Should Know

- The provenance-aware summary gate adds only a small synthetic worker-scan cost at the current 250-job benchmark scale, so it does not currently justify further control-plane optimization on its own.
- The more useful next summary slice is likely operator-facing visibility or cache policy refinement rather than more micro-optimization around the stale-summary predicate.
- The summary-aware benchmark now lives in the existing control-plane helper, so future workflow-gate comparisons can reuse it without inventing another measurement script.

## 2026-05-08 - Summary Provenance Invalidation

### What Changed

- Updated [src/minutes/pipeline/__init__.py](src/minutes/pipeline/__init__.py) so summary stage readiness now checks whether an existing `summary_text` artifact still matches the current transcript or speaker-transcript source provenance.
- Kept the invalidation logic in the shared pipeline owner so worker pickup and normal `process_job` flow use the same stale-summary rule.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with a focused regression that proves the worker regenerates a stale summary when the transcript source changes.

### What Was Tried

- Reused the existing summary artifact provenance metadata (`source_artifact_kind`, `source_artifact_path`, `source_artifact_created_at`) instead of inventing a new invalidation marker.
- Limited the change to stage gating only, so explicit `summarize-job` behavior remains a direct rerun path and does not need special-case handling.
- Treated summaries as current only when their stored provenance exactly matches the current selected summary source artifact.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "worker_run_once_regenerates_stale_summary_when_transcript_changes or worker_run_once_summarizes_source_less_job_with_existing_transcript or process_job_summarizes_plain_transcript_when_configured"` passed with 3 selected tests.
- `python -m pytest tests/test_normalization_flow.py` passed with 35 tests after the summary provenance invalidation slice.

### Next Session Should Know

- Summary artifacts are no longer treated as valid solely because `summary_text` exists; they must also match the currently selected transcript source provenance.
- This change closes the simplest stale-summary gap without changing explicit rerun behavior or introducing broader cache invalidation rules.
- The next summary-focused slice can decide whether user-facing outputs should surface stale-summary regeneration more explicitly or whether deeper summary cache policy is still needed.

## 2026-05-08 - Summary Retry Configuration And Metadata

### What Changed

- Updated [src/minutes/adapters/summarizer_openai_compatible.py](src/minutes/adapters/summarizer_openai_compatible.py) so transient summary request timeouts and connection failures now use a bounded retry loop instead of failing immediately.
- Added `summary_max_retries` to [src/minutes/config.py](src/minutes/config.py), surfaced it through [src/minutes/cli.py](src/minutes/cli.py) `show-config`, and documented it in [.env.example](.env.example).
- Updated [src/minutes/orchestrator.py](src/minutes/orchestrator.py) so persisted summary artifacts now also record `summary_max_retries` alongside the existing timeout and elapsed-time metadata.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with a focused adapter retry test plus a `show-config` regression for the new summary retry setting.

### What Was Tried

- Kept retries limited to transient timeout and connection failures instead of retrying HTTP status failures or invalid response content.
- Reused the existing summary adapter boundary rather than adding retry logic in the orchestrator, so transport failures remain owned where the provider call is made.
- Kept the retry count configurable and bounded instead of hardcoding a magic retry loop.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "show_config_includes_summary_retry_settings or summary_adapter_retries_timeout_once or process_job_summarizes_plain_transcript_when_configured or summarize_job_route_runs_summary_stage"` passed with 4 selected tests.
- `python -m pytest tests/test_normalization_flow.py` passed with 34 tests after the summary retry slice.

### Next Session Should Know

- Summary timeouts and connection failures no longer fail on the first transient attempt by default; the adapter now retries up to the configured `summary_max_retries` bound.
- Persisted summary artifacts now expose timeout, retry, and elapsed-time context together, so post-run inspection has better operational signal.
- The next summary-focused slice can decide whether failures after all retries should produce richer user-facing guidance or whether summary caching/invalidation is the higher-value next step.

## 2026-05-08 - Summary Artifact Timing Metadata

### What Changed

- Updated [src/minutes/orchestrator.py](src/minutes/orchestrator.py) so persisted `summary_json` and `summary_text` artifacts now record `summary_elapsed_ms` and `summary_timeout_seconds` in their metadata.
- Kept the timing capture at the orchestration boundary so the recorded latency reflects the full provider call used by the summary stage without changing the summary adapter contract.
- Updated [tests/test_normalization_flow.py](tests/test_normalization_flow.py) so summary-stage coverage now asserts the new persisted timing metadata.

### What Was Tried

- Anchored the instrumentation at `summarize_job` instead of the adapter so the metadata is captured exactly where artifacts are persisted.
- Limited the slice to derived metadata rather than changing summary job control flow or retry behavior.
- Reused the existing summary artifact metadata surface so the new latency context becomes visible without introducing a new artifact type or benchmark-only path.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "process_job_summarizes_plain_transcript_when_configured or process_job_summarizes_speaker_transcript_when_available or summarize_job_prefers_existing_speaker_transcript_even_when_diarization_disabled or summarize_job_route_runs_summary_stage"` passed with 4 selected tests.

### Next Session Should Know

- Persisted summary artifacts now include both the observed summary-call latency and the configured timeout, so summary behavior is easier to inspect from normal job outputs.
- This is instrumentation only; summary stage retry, cancellation, and caching behavior are still unchanged.
- The next summary-focused slice can build on this metadata if summary retry or timeout handling needs to become more explicit.

## 2026-05-08 - Shared Job View And next_stage Exposure

### What Changed

- Added [src/minutes/job_view.py](src/minutes/job_view.py) as the shared transport-facing job serializer for CLI and API job payloads.
- Added `next_stage` to [src/minutes/storage/models.py](src/minutes/storage/models.py) `JobResponse` so operator-facing job payloads expose the next actionable stage explicitly.
- Updated [src/minutes/cli.py](src/minutes/cli.py) so `list-jobs`, `show-job`, `run-once`, `process-file`, and `summarize-job` now print the shared job view instead of dumping the raw stored model directly.
- Updated [src/minutes/api/routes_jobs.py](src/minutes/api/routes_jobs.py) so job routes now return the shared `JobResponse` payload with `next_stage` included.
- Updated [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with focused assertions for the new `next_stage` field in CLI and API job outputs.

### What Was Tried

- Reused the existing shared [src/minutes/pipeline/__init__.py](src/minutes/pipeline/__init__.py) `next_pending_stage` helper so the new payload field is derived from the same workflow owner the worker already uses.
- Kept `next_stage` transport-only instead of persisting it in the stored job record, because it is derived state that depends on the current settings and artifacts.
- Kept `current_stage` and `workflow_stage` intact so this slice improves interface clarity without widening into a storage or schema migration.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "orchestrator_normalizes_job or normalize_route_processes_job or list_jobs_cli_prints_jobs_as_json or show_job_cli_prints_job_json or worker_run_once_picks_up_job_missing_summary_artifact"` passed with 5 selected tests.
- `python -m pytest tests/test_normalization_flow.py` passed with 32 tests after the shared job view and `next_stage` transport change.

### Next Session Should Know

- CLI and API job payloads now expose `next_stage` explicitly, so downstream operators no longer need to infer the next actionable work from `current_stage` alone.
- `workflow_stage` still owns the last completed workflow point, `current_stage` still reflects the active/current compatibility view, and `next_stage` now exposes the next pending work for transport consumers.
- The next useful slice is summary handling or deciding whether downstream interfaces can rely enough on `workflow_stage` plus `next_stage` to retire `current_stage` eventually.

## 2026-05-08 - current_stage Pending-Stage Cleanup

### What Changed

- Updated [src/minutes/orchestrator.py](src/minutes/orchestrator.py) so queued jobs now expose the next pending workflow stage in `current_stage` instead of mirroring the last completed point already stored in `workflow_stage`.
- Kept the existing running and failed behavior intact so `current_stage` still shows the active or failed stage while work is in progress or when a stage fails.
- Updated [tests/test_normalization_flow.py](tests/test_normalization_flow.py) so queued-stage assertions now reflect the narrower `current_stage` meaning.

### What Was Tried

- Anchored the new `current_stage` value to the existing shared [src/minutes/pipeline/__init__.py](src/minutes/pipeline/__init__.py) `next_pending_stage` helper instead of inventing a second stage-transition rule.
- Kept terminal completed jobs unchanged so fully completed jobs still expose their last completed stage in both `workflow_stage` and `current_stage` for compatibility.
- Used the smallest semantics change that stops `current_stage` from duplicating `workflow_stage` on queued jobs without widening the slice into transport or storage refactors.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "orchestrator_normalizes_job or summarize_job_waits_for_speaker_transcript_when_diarization_enabled or worker_run_once_picks_up_job_missing_summary_artifact or worker_run_once_processes_job_to_transcribed"` passed with 4 selected tests.
- `python -m pytest tests/test_normalization_flow.py` passed with 32 tests after the `current_stage` cleanup.

### Next Session Should Know

- `workflow_stage` remains the explicit owner of last completed workflow progress.
- `current_stage` is now narrower: queued jobs show the next pending stage, running jobs show the active stage, failed jobs show the failed stage, and terminal completed jobs still expose the completed stage for compatibility.
- The next useful slice is summary handling or deciding whether `current_stage` should eventually be retired once downstream interfaces rely on `workflow_stage` directly.

## 2026-05-08 - Speaker Assembly In-Memory Transcription

### What Changed

- Updated [src/minutes/adapters/transcriber_sensevoice.py](src/minutes/adapters/transcriber_sensevoice.py) with a shared internal transcription path plus a new `transcribe_waveform` entrypoint for in-memory audio.
- Updated [src/minutes/orchestrator.py](src/minutes/orchestrator.py) so speaker transcript assembly now prefers in-memory waveform transcription and falls back to the previous temp-WAV path only when the in-memory path fails.
- Updated [tests/test_normalization_flow.py](tests/test_normalization_flow.py) so the fake transcriber supports the waveform entrypoint and the speaker-segment merge behavior used by speaker assembly.

### What Was Tried

- First confirmed with direct runtime checks that FunASR could accept a longer in-memory waveform clip, while still observing that very short clips can fail in the frontend path.
- Chose a safe hybrid approach: use in-memory transcription by default for speaker clips, but preserve the temp-file path as a fallback for short or incompatible clips.
- Re-ran the same real speaker-assembly benchmark against the same persisted artifacts after the change so the before-versus-after comparison stayed meaningful.
- Tried a batched in-memory transcription path and a more aggressive same-speaker merge threshold, then dropped both because they either regressed the full benchmark or pushed the code toward tuning for one fixture.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "merge_diarization_segments_merges_same_speaker_across_short_gap or process_job_runs_diarization_when_enabled or process_job_summarizes_speaker_transcript_when_available or summarize_job_waits_for_speaker_transcript_when_diarization_enabled"` passed with 4 selected tests.
- `python scripts/measure_local.py speaker-assembly .minutes-data/data/jobs/<job_id>/artifacts/normalized.wav .minutes-data/data/jobs/<job_id>/artifacts/diarization.json --transcript-path .minutes-data/data/jobs/<job_id>/artifacts/transcript.txt` completed successfully after the change and reported a best rerun of `speaker_assembly_ms: 27042.537`.
- The previous baseline for the same benchmark input was `speaker_assembly_ms: 62478.602`, so the in-memory path reduced the measured speaker-assembly time by more than half while the code stayed on the simpler non-batched path.

### Next Session Should Know

- Speaker assembly no longer depends exclusively on per-segment temp WAV files; it now prefers in-memory waveform transcription and only falls back when needed.
- The measured speaker-assembly hotspot is materially smaller now, but it is still slower than the warm API transcription path and slower than the summary stage.
- Additional local tuning passes for batching or more aggressive segment merging were intentionally rejected because they did not improve the full benchmark enough to justify the complexity or the fixture-specific risk.
- The next useful slice should shift to summary handling or `current_stage` cleanup rather than more speaker-assembly tuning.

## 2026-05-08 - API Reuse Wiring And API-Path Benchmark

### What Changed

- Updated [src/minutes/api/app.py](src/minutes/api/app.py) so the FastAPI app now creates and stores a shared `FileStateStore` plus `JobOrchestrator` on `app.state`.
- Updated [src/minutes/api/routes_jobs.py](src/minutes/api/routes_jobs.py) so route helpers prefer the app-scoped store and orchestrator instead of constructing fresh instances per request.
- Updated [tests/test_normalization_flow.py](tests/test_normalization_flow.py) so the summarize route test now proves the route uses the app-scoped orchestrator path.
- Extended [scripts/measure_local.py](scripts/measure_local.py) with an `api-transcription` benchmark that measures first and second transcription requests against one app instance.

### What Was Tried

- Chose app-scoped reuse as the smallest code change that could turn the measured warm-model advantage into an API-visible improvement.
- Kept the fallback helper behavior intact so routes still work outside the normal app factory path when needed.
- Validated the route wiring first with focused tests, then measured the actual API path with the new benchmark subcommand.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "summarize_job_route_runs_summary_stage or normalize_route_processes_job or transcript_route_returns_text or summary_route_returns_text"` passed with 4 selected tests.
- `python scripts/measure_local.py api-transcription file/test1.mp3` completed successfully and reported `first_request_seconds: 19.504`, `second_request_seconds: 2.841`, with both requests ending at `workflow_stage: transcribed` on one app instance.

### Next Session Should Know

- The API now reuses an app-scoped orchestrator and store, so repeated requests on one app instance can benefit from warmed adapters.
- The measured API-path gap is now much smaller than the original direct cold-start benchmark, which confirms the reuse change is paying off where it was intended.
- Speaker assembly remains the largest measured local heavy path at about `62.5s`, so it is a strong candidate for the next direct optimization slice.

## 2026-05-08 - Source-Less API Decision And First Measurement Path

### What Changed

- Updated [src/minutes/api/routes_jobs.py](src/minutes/api/routes_jobs.py) so the public `POST /api/jobs` surface now rejects requests that omit `source_path`.
- Kept the internal store path permissive so manual and test-only seeded-artifact workflows can still create source-less jobs when artifacts are injected out-of-band.
- Added [scripts/measure_local.py](scripts/measure_local.py) as the first lightweight local measurement script with subcommands for synthetic control-plane timings plus opt-in transcription, summary, and speaker-assembly measurements.
- Updated [INDEX.md](INDEX.md), [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md), and [docs/progress-tracker.md](docs/progress-tracker.md) so the source-less job decision and measurement-path milestone are reflected in the current planning docs.

### What Was Tried

- Tightened only the public API create surface instead of the underlying `CreateJobRequest` model so internal seeded-artifact tests and manual workflows remain available.
- Put the first benchmark path in a standalone script rather than in pytest so control-plane and heavy-model measurements stay opt-in.
- Validated the script first against a synthetic control-plane scenario before treating it as the repo's first real measurement surface.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "create_job_route_rejects_missing_source_path or normalize_route_processes_job or worker_skips_source_less_job_when_summary_enabled or worker_run_once_summarizes_source_less_job_with_existing_transcript or summarize_job_prefers_existing_speaker_transcript_even_when_diarization_disabled"` passed with 5 selected tests.
- `python scripts/measure_local.py control-plane --job-count 50 --iterations 3` completed successfully and reported list-jobs plus next-actionable-job timings for a synthetic 50-job state root.
- `python scripts/measure_local.py transcription file/test1.mp3` completed successfully after model bootstrap and reported `cold_seconds: 82.553`, `warm_seconds: 6.401`, `device: cuda:0`, and `model_name: iic/SenseVoiceSmall`.
- `python scripts/measure_local.py speaker-assembly .minutes-data/data/jobs/<job_id>/artifacts/normalized.wav .minutes-data/data/jobs/<job_id>/artifacts/diarization.json --transcript-path .minutes-data/data/jobs/<job_id>/artifacts/transcript.txt` completed successfully and reported `speaker_assembly_ms: 62478.602` with `workflow_stage: speaker_attributed`.
- `python scripts/measure_local.py summary .minutes-data/data/jobs/<job_id>/artifacts/speaker_transcript.txt --iterations 2` completed successfully and reported `summary_ms` min/median/max of `12098.171 / 13280.762 / 14463.353` against the configured `deepseek-v4-flash` backend.

### Next Session Should Know

- Source-less jobs are no longer a supported public API create shape, but they remain available internally for seeded-artifact workflows.
- The first measurement path now exists in [scripts/measure_local.py](scripts/measure_local.py); the synthetic control-plane subcommand and the real transcription benchmark have both been validated.
- The first real heavy-path baseline now shows a large cold-versus-warm transcription gap on [file/test1.mp3](file/test1.mp3), so model reuse should remain a primary performance focus.
- The measured heavy-path baselines now show three distinct costs: transcription cold start at `82.553s` versus warm at `6.401s`, speaker assembly at `62.479s`, and summary latency around `12.1s` to `14.5s`.
- The next performance step should choose one of those measured hotspots for direct optimization rather than doing more speculative benchmarking first.

## 2026-05-08 - Shared Retrieval Query Layer

### What Changed

- Added [src/minutes/queries.py](src/minutes/queries.py) as the shared owner for transcript and summary artifact lookup, file reads, and user-facing not-found messages.
- Updated [src/minutes/cli.py](src/minutes/cli.py) so `show-transcript` and `show-summary` now use the shared retrieval helpers instead of duplicating lookup and file-read logic.
- Updated [src/minutes/api/routes_jobs.py](src/minutes/api/routes_jobs.py) so the transcript and summary routes now use the same shared retrieval helpers as the CLI.

### What Was Tried

- Chose a small query module instead of a broader service abstraction because only transcript and summary retrieval currently need shared transport-independent behavior.
- Preserved the existing API 404 details and CLI error messages so the refactor changes ownership without changing the current user-facing contract.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "transcript_route_returns_text or transcript_route_returns_speaker_attributed_text or summary_route_returns_text or summary_route_returns_not_found_when_missing or transcript_route_returns_not_found_when_file_missing or summary_route_returns_not_found_when_file_missing or show_transcript_cli_prints_text or show_transcript_cli_prints_speaker_attributed_text or show_summary_cli_prints_text or show_summary_cli_returns_error_when_file_missing or show_transcript_cli_returns_error_when_file_missing"` passed with 11 selected tests.

### Next Session Should Know

- Transcript and summary retrieval are now shared across CLI and API through [src/minutes/queries.py](src/minutes/queries.py).
- The next interface decision is whether source-less jobs remain a supported workflow and how that should be reflected in create-job surfaces.
- The next planned implementation slice after that is the first lightweight performance measurement path.

## 2026-05-08 - Status And Workflow Stage Separation

### What Changed

- Added `workflow_stage` to [src/minutes/storage/models.py](src/minutes/storage/models.py) so workflow progress is now stored explicitly instead of being inferred only from `status` and `current_stage`.
- Updated [src/minutes/storage/file_store.py](src/minutes/storage/file_store.py) so new jobs persist both the initial created workflow stage and the visible current stage.
- Updated [src/minutes/orchestrator.py](src/minutes/orchestrator.py) so successful stage transitions now compute `queued` versus `completed` from remaining pending work, while `workflow_stage` records the completed workflow point.
- Kept `current_stage` as the compatibility field for the visible stage name while the codebase begins using `workflow_stage` as the explicit progress owner.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) and [tests/test_real_audio_integration.py](tests/test_real_audio_integration.py) with focused assertions for `workflow_stage` and the updated queued-versus-completed semantics.

### What Was Tried

- Chose the smallest schema change that could separate workflow progress from execution lifecycle without rewriting every user-facing surface in one pass.
- Preserved `current_stage` temporarily so the visible API and CLI payloads remain readable while the repository transitions to the new explicit workflow-progress field.
- Made successful stage completion resolve terminality from the shared `next_pending_stage` helper instead of hard-coding `completed` on every successful stage.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "orchestrator_normalizes_job or worker_run_once_processes_job_to_transcribed or process_job_summarizes_plain_transcript_when_configured or process_job_uses_match_transcript_language_when_none_is_resolved or process_job_summarizes_speaker_transcript_when_available or summarize_job_waits_for_speaker_transcript_when_diarization_enabled or worker_run_once_picks_up_job_missing_summary_artifact or worker_run_once_summarizes_source_less_job_with_existing_transcript or normalize_route_processes_job or process_job_runs_both_stages_with_fake_transcriber or process_job_runs_diarization_when_enabled or summarize_job_route_runs_summary_stage or summarize_job_prefers_existing_speaker_transcript_even_when_diarization_disabled"` passed with 13 selected tests.

### Next Session Should Know

- `workflow_stage` is now the explicit owner of workflow progress, while `current_stage` remains as a compatibility field that still mirrors the visible stage name.
- Successful non-terminal stage calls now return `queued` instead of `completed`, which makes worker pickup semantics and direct stage-call semantics align better.
- The next cleanup slice should decide whether source-less jobs remain supported and should start moving shared retrieval behavior out of the CLI and API transport layers.

## 2026-05-08 - First Active Scoped Execution Plan

### What Changed

- Added [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md) as the historical record of the first scoped workflow and interface cleanup execution plan.
- Updated [docs/plans/README.md](docs/plans/README.md), [docs/README.md](docs/README.md), [docs/progress-tracker.md](docs/progress-tracker.md), and [INDEX.md](INDEX.md) so the repository documentation reflects the finished scoped plan state.

### What Was Tried

- Reused the existing temporary-plan template and session planning work to avoid inventing a new planning format.
- Kept the plan explicitly task-scoped and temporary so it supports handoff without replacing the stable owner docs.

### What Was Validated

- The new active plan and updated markdown owner docs reported no editor-detected errors.

### Next Session Should Know

- The finished scoped workflow/interface plan is retained historically at [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md).
- `INDEX.md` and the docs map now treat that plan as the active scoped work source until the workstream is complete.

## 2026-05-08 - Docs Landing Page

### What Changed

- Added [docs/README.md](docs/README.md) as a stable landing page for the `docs/` folder.
- Updated [INDEX.md](INDEX.md) so the new docs landing page is part of the documented repository map and stable-doc inventory.

### What Was Tried

- Kept the landing page focused on navigation and ownership guidance so it does not compete with [DEVNOTES.md](DEVNOTES.md), [README.md](README.md), or the new planning docs.

### What Was Validated

- The new markdown file and updated owner docs reported no editor-detected errors.

### Next Session Should Know

- [docs/README.md](docs/README.md) is now the entry point for stable documentation under `docs/`.

## 2026-05-08 - Master Plan And Progress Tracker

### What Changed

- Added [docs/master-plan.md](docs/master-plan.md) as the stable repository-level workstream direction and sequencing document.
- Added [docs/progress-tracker.md](docs/progress-tracker.md) as the high-level progress view across the master-plan workstreams.
- Updated [INDEX.md](INDEX.md) so the new stable planning docs are part of the documented repository map and status-source ownership.

### What Was Tried

- Kept the new docs explicitly subordinate to [DEVNOTES.md](DEVNOTES.md), [docs/tech-debt.md](docs/tech-debt.md), and scoped execution plans so they do not become duplicated live-status owners.
- Limited the tracker to high-level workstream states and next gates rather than copying detailed task status into a second log.

### What Was Validated

- The new planning docs were checked against the repository's existing authority and documentation-ownership rules in [AGENTS.md](AGENTS.md), [INDEX.md](INDEX.md), and [docs/plans/README.md](docs/plans/README.md).
- The edited markdown files reported no editor-detected errors.

### Next Session Should Know

- [docs/master-plan.md](docs/master-plan.md) is now the stable owner for repository-level sequencing.
- [docs/progress-tracker.md](docs/progress-tracker.md) is now the high-level coordination view, but recent verified work must still be recorded first in [DEVNOTES.md](DEVNOTES.md).

## 2026-05-08 - Workflow Contract And CLI Discovery Cleanup

### What Changed

- Gave the workflow a first real shared owner in [src/minutes/pipeline/__init__.py](src/minutes/pipeline/__init__.py) by adding authoritative stage names plus a shared `next_pending_stage` helper.
- Updated [src/minutes/orchestrator.py](src/minutes/orchestrator.py) so `process_job` now follows the shared stage-selection helper instead of duplicating artifact checks inline.
- Updated [src/minutes/worker.py](src/minutes/worker.py) so queue pickup uses the same shared stage-selection contract as the orchestrator.
- This shared stage flow now allows source-less jobs with an existing transcript artifact to be summarized through the worker path when summary generation is configured.
- Added CLI job discovery commands in [src/minutes/cli.py](src/minutes/cli.py): `list-jobs` and `show-job`.
- Updated [src/minutes/storage/file_store.py](src/minutes/storage/file_store.py) so job listing order is based on persisted timestamps instead of reverse UUID path order.
- Updated [scripts/doctor.ps1](scripts/doctor.ps1) so its default reported state root matches the application runtime default of the repository-local `.minutes-data` directory.
- Updated [README.md](README.md) with the new CLI job-discovery commands.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with CLI discovery coverage and a worker regression test for artifact-backed summary pickup.

### What Was Tried

- Started with the smallest structural slice by centralizing stage readiness without changing the artifact model or public job schema.
- Reused the existing `src/minutes/pipeline` package as the owner for stage names and stage-selection rules instead of creating another coordination module.
- Let the new CLI discovery tests drive one follow-up correction by replacing reverse-UUID job ordering with timestamp-based ordering in the file store.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "worker_run_once_processes_job_to_transcribed or worker_run_once_picks_up_job_missing_summary_artifact or worker_skips_source_less_job_when_summary_enabled or worker_skips_source_less_job_when_diarization_enabled or process_job_runs_both_stages_with_fake_transcriber or process_job_runs_diarization_when_enabled or process_job_summarizes_plain_transcript_when_configured or summarize_job_prefers_existing_speaker_transcript_even_when_diarization_disabled"` passed with 8 selected tests.
- `python -m pytest tests/test_normalization_flow.py -k "list_jobs_cli_prints_jobs_as_json or show_job_cli_prints_job_json or show_job_cli_returns_error_when_missing or show_transcript_cli_prints_text or worker_run_once_processes_job_to_transcribed or worker_run_once_picks_up_job_missing_summary_artifact or worker_skips_source_less_job_when_summary_enabled or worker_skips_source_less_job_when_diarization_enabled"` passed with 8 selected tests after the timestamp-ordering fix.
- `python -m pytest tests/test_normalization_flow.py -k "worker_run_once_summarizes_source_less_job_with_existing_transcript or worker_run_once_picks_up_job_missing_summary_artifact or summarize_job_prefers_existing_speaker_transcript_even_when_diarization_disabled or worker_skips_source_less_job_when_summary_enabled"` passed with 4 selected tests.
- `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned; .\scripts\doctor.ps1` reported the repository-local `.minutes-data` state root and resolved the configured `ffmpeg` binary.

### Next Session Should Know

- Stage selection is now shared between the worker and orchestrator, but `status` versus `current_stage` semantics are still overloaded and should be cleaned up in a later slice.
- Source-less jobs are still allowed at creation time; the new shared stage helper only makes the existing artifact-backed summary path workable when a transcript artifact is already present.
- CLI users can now discover job ids without using the API, but artifact retrieval still has dedicated commands only for transcript and summary.

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
