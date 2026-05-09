- Purpose: Rolling recent verified work log
- Scope: Recent verified changes, validations, and handoff notes; excludes evergreen knowledge, stable architecture, and long-term debt ownership
- Status: Active
- Last validated: 2026-05-09
- Source of truth for: Most recent verified repository state, recent changes, next-session handoff notes

# Development Notes

## Maintenance Rule

- Keep this file at or below 500 lines.
- When a new verified entry would push it over 500 lines, move the oldest complete dated entries into the archive files listed in [docs/devnotes/README.md](docs/devnotes/README.md).
- Keep archive files at or below 500 lines too; split them by date or date range before they grow past that cap.

## 2026-05-09 - README Audience Guardrail

### What Changed

- Removed developer-facing test and CI guidance from [README.md](README.md) so the repository README stays end-user-facing.
- Updated [AGENTS.md](AGENTS.md) to explicitly forbid adding developer workflow, testing, CI, planning, or contributor-process content to the README.

### What Was Tried

- Corrected the README directly instead of leaving the audience boundary implicit.
- Tightened the repository agent rules at the same time so future edits have an explicit guardrail.

### What Was Validated

- Targeted README search confirmed the removed developer-facing terms and sections are no longer present.
- [README.md](README.md) and [AGENTS.md](AGENTS.md) reported no editor-detected errors after the change.

### Next Session Should Know

- Treat [README.md](README.md) as end-user documentation only.
- Put developer-facing workflow or maintenance guidance in owner docs other than the README.

## 2026-05-09 - DEVNOTES Archive Rollover

### What Changed

- Added [docs/devnotes/README.md](docs/devnotes/README.md) as the archive index and rollover owner for historical development notes.
- Moved the 2026-05-08 entries into [docs/devnotes/archive-2026-05-08.md](docs/devnotes/archive-2026-05-08.md) and the 2026-05-05 through 2026-05-07 entries into [docs/devnotes/archive-2026-05-05-to-2026-05-07.md](docs/devnotes/archive-2026-05-05-to-2026-05-07.md).
- Updated [INDEX.md](INDEX.md), [docs/README.md](docs/README.md), and [AGENTS.md](AGENTS.md) so the repository now points to the archive owner and carries an explicit 500-line cap rule for DEVNOTES and each archive file.

### What Was Tried

- Kept the recent 2026-05-09 verified log entries in [DEVNOTES.md](DEVNOTES.md) and archived only older complete dated entries.
- Split the historical notes into two archive files by date range so neither archive becomes another oversized history file immediately.

### What Was Validated

- `DEVNOTES.md` now measures 321 lines.
- `docs/devnotes/archive-2026-05-08.md` now measures 362 lines.
- `docs/devnotes/archive-2026-05-05-to-2026-05-07.md` now measures 223 lines.
- The edited markdown files reported no editor-detected errors after the rollover.

### Next Session Should Know

- Start with [DEVNOTES.md](DEVNOTES.md) for recent verified truth and use [docs/devnotes/README.md](docs/devnotes/README.md) only when older history is needed.
- Future rollover should move the oldest complete dated entries, not partial sections, and should keep every devnotes file under the same 500-line cap.

## 2026-05-09 - Real-Audio Test Isolation Follow-Up

### What Changed

- Updated [tests/test_real_audio_integration.py](tests/test_real_audio_integration.py) so the opt-in real-audio integration test now uses the active Python interpreter instead of assuming a repo-local `.venv\Scripts\python.exe` path.
- The same test now sets a temporary `MINUTES_STATE_ROOT` under `.pytest-tmp` so it no longer writes into the default repository `.minutes-data` runtime state during validation.
- Updated [README.md](README.md) so the opt-in integration-test guidance now reflects the isolated temporary state-root behavior.

### What Was Tried

- Kept the integration path opt-in and manual instead of widening required CI, but removed the remaining workstation-specific test harness assumptions from that path.

### What Was Validated

- `$env:MINUTES_RUN_REAL_AUDIO_TESTS='1'; .\.venv\Scripts\python.exe -m pytest tests/test_real_audio_integration.py -m integration` passed after isolating the test from local state, summary, and diarization overrides.
- `python -m pytest tests/test_normalization_flow.py` passed after the integration-test isolation follow-up.

### Next Session Should Know

- The default regression suite remains the required CI gate, while the real-audio integration path is still manual but now better isolated from local runtime state and local summary/diarization environment overrides.

## 2026-05-09 - Minimal Windows CI Baseline

### What Changed

- Added [.github/workflows/ci.yml](.github/workflows/ci.yml) as the first required GitHub Actions workflow for this repository.
- Kept the workflow intentionally narrow: one `windows-latest` job that installs `ffmpeg`, installs the project with the `dev` extra, and runs the documented default regression suite `python -m pytest tests/test_normalization_flow.py`.
- Updated [tests/test_normalization_flow.py](tests/test_normalization_flow.py) so subprocess-based regression tests now use the active Python interpreter and resolve `ffmpeg` from `MINUTES_FFMPEG_BIN` or `PATH` before falling back to the existing Windows default path.
- Updated [README.md](README.md) so the documented setup path now covers the `dev` extra needed for tests and explains the new required CI gate.

### What Was Tried

- Chose a Windows-only CI lane instead of a cross-platform matrix because the validated workflow, default ffmpeg path handling, and several repository scripts are still Windows-shaped.
- Kept the heavy real-audio integration path out of required CI rather than turning a manual validation lane into a merge gate.
- Fixed the main regression harness first instead of making CI emulate one local `.venv\Scripts\python.exe` layout.

### What Was Validated

- `.\.venv\Scripts\python.exe -m pytest tests/test_normalization_flow.py -k "show_config_includes_summary_retry_settings or orchestrator_import_leaves_optional_adapters_unloaded or measure_local_startup_path_reports_import_boundary or show_transcript_cli_prints_text or list_jobs_cli_prints_jobs_as_json or show_job_cli_prints_job_json or show_summary_cli_prints_text or show_summary_cli_json_includes_source_status"` passed with 8 selected tests after the test-harness portability change.

### Next Session Should Know

- The repository now has a minimal required Windows CI workflow, but the opt-in real-audio integration path is still manual and non-blocking.
- The default regression suite no longer depends on hardcoded `.venv\Scripts\python.exe` test subprocess paths, which lowers CI friction and makes local non-`.venv` runs more honest.

## 2026-05-09 - Roadmap Doc Removal

### What Changed

- Removed the former roadmap coordination docs `docs/master-plan.md` and `docs/progress-tracker.md`.
- Updated [INDEX.md](INDEX.md), [docs/README.md](docs/README.md), [docs/tech-debt.md](docs/tech-debt.md), [docs/plans/completed/mp-004-startup-hotspot-investigation.md](docs/plans/completed/mp-004-startup-hotspot-investigation.md), [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md), and the affected history entries in [DEVNOTES.md](DEVNOTES.md) so the repository no longer links to deleted roadmap files.

### What Was Tried

- Kept the existing ownership model instead of inventing replacement roadmap docs: [INDEX.md](INDEX.md) now carries the current maintenance posture, [DEVNOTES.md](DEVNOTES.md) remains the recent verified truth, and [docs/tech-debt.md](docs/tech-debt.md) continues to own unresolved maintenance debt.

### What Was Validated

- Targeted search confirmed the deleted roadmap files are no longer referenced as live documentation links in the stable docs.

### Next Session Should Know

- The repository no longer has separate roadmap coordination docs under `docs/`; use [INDEX.md](INDEX.md), [DEVNOTES.md](DEVNOTES.md), [docs/README.md](docs/README.md), and [docs/tech-debt.md](docs/tech-debt.md) instead.

## 2026-05-09 - Roadmap Maintenance Transition

### What Changed

- Updated the then-current roadmap coordination docs, together with [INDEX.md](INDEX.md), [docs/README.md](docs/README.md), and [docs/tech-debt.md](docs/tech-debt.md), so the stable docs described maintenance posture and reopen triggers instead of implying an unfinished forward roadmap.
- Updated the historical handoff note in [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md) so it no longer assumes there must be a next active workstream.

### What Was Tried

- Kept the stable owner documents themselves `Active`, because in this repo that status describes the document lifecycle rather than whether the roadmap is finished.
- Left TD-002 open in [docs/tech-debt.md](docs/tech-debt.md) as maintenance debt instead of forcing the roadmap itself to stay artificially incomplete.

### What Was Validated

- Cross-checked the then-current roadmap docs together with [INDEX.md](INDEX.md), [docs/README.md](docs/README.md), [docs/tech-debt.md](docs/tech-debt.md), and [DEVNOTES.md](DEVNOTES.md) so the roadmap completion language stayed consistent with the no-active-plan state and the remaining open debt signal.

### Next Session Should Know

- The roadmap baseline is now documented as complete for the current scope, and the repository should be treated as maintained rather than mid-roadmap.
- Remaining work should reopen a workstream only when a regression, dependency break, measured hotspot, or explicit scope change justifies it.

## 2026-05-09 - MP-004 Startup Plan Closeout

### What Changed

- Moved the finished scoped startup plan to [docs/plans/completed/mp-004-startup-hotspot-investigation.md](docs/plans/completed/mp-004-startup-hotspot-investigation.md) and updated [INDEX.md](INDEX.md), [docs/README.md](docs/README.md), [docs/plans/README.md](docs/plans/README.md), and the then-current roadmap coordination docs so the repository no longer claims there is active scoped work when there is not.
- Updated [docs/tech-debt.md](docs/tech-debt.md) so TD-004 is now resolved: the repo has a startup-specific measurement path, one verified mitigation, and an explicit decision not to replace `pydantic-settings` for startup alone.

### What Was Tried

- Treated the split `startup-path` benchmark as the decision point rather than pushing one more speculative startup refactor into the configuration layer.
- Chose to keep the current configuration framework because the remaining measured cost is import-time framework overhead, while first settings initialization and orchestrator construction are both already cheap.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py` passed with 42 tests before closing the scoped startup plan.

### Next Session Should Know

- There is no active scoped execution plan currently; the finished startup plan is now historical at [docs/plans/completed/mp-004-startup-hotspot-investigation.md](docs/plans/completed/mp-004-startup-hotspot-investigation.md).
- Reopen MP-004 only if a broader configuration simplification effort or another measured hotspot justifies more performance work.

## 2026-05-09 - Startup Path Benchmark Baseline

### What Changed

- Updated [scripts/measure_local.py](scripts/measure_local.py) with a new `startup-path` command that launches a fresh Python child process and measures the `process-file` startup boundary around `minutes.cli` import, `minutes.orchestrator` import, and `JobOrchestrator` construction.
- Kept the startup probe subprocess-based so its reported timings are not polluted by the benchmark runner process already importing the code under test.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with a focused regression that asserts the new benchmark command returns the expected JSON shape and still reports the optional adapter modules as unloaded after importing the CLI and constructing `JobOrchestrator`.

### What Was Tried

- Moved the heavier benchmark-only imports in [scripts/measure_local.py](scripts/measure_local.py) into the functions that use them so the script can dispatch the new startup probe without eagerly importing every benchmark dependency first.
- Measured the startup boundary in a child interpreter instead of trying to reuse the parent `measure_local.py` process, because the parent process would otherwise warm the imports being measured.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "measure_local_startup_path_reports_import_boundary or orchestrator_import_leaves_optional_adapters_unloaded"` passed with 2 selected tests.
- `python scripts/measure_local.py startup-path --iterations 3` reported `cli_import_ms` median `235.830`, `orchestrator_import_ms` median `8.865`, and `orchestrator_construct_ms` median `0.321`, with `uvicorn`, `minutes.api.app`, `minutes.adapters.ffmpeg`, `minutes.adapters.transcriber_sensevoice`, `minutes.adapters.diarizer_pyannote`, and `minutes.adapters.summarizer_openai_compatible` all still absent from `sys.modules` after the probe.
- After splitting that probe further, `python scripts/measure_local.py startup-path --iterations 3` reported `config_import_ms` median `244.550`, `cli_import_ms` median `230.501`, `settings_init_ms` median `4.777`, `orchestrator_import_ms` median `236.673`, and `orchestrator_construct_ms` median `0.256`, showing that importing [src/minutes/config.py](src/minutes/config.py) now dominates the measured startup boundary while first settings construction and orchestrator construction are both small.

### Next Session Should Know

- The repo now has a validated startup-specific benchmark path for the `process-file` import boundary.
- After the lazy-loading slice, the remaining measured cost in this probe is no longer default adapter construction or first `get_settings()` work; the next likely startup follow-up is the [src/minutes/config.py](src/minutes/config.py) import path itself, which currently pulls in `pydantic` and `pydantic-settings` on every fresh process start.

## 2026-05-09 - Orchestrator Adapter Lazy Loading

### What Changed

- Updated [src/minutes/orchestrator.py](src/minutes/orchestrator.py) so default ffmpeg, transcriber, diarizer, and summarizer adapters are now imported and constructed lazily instead of at module import and `JobOrchestrator` construction time.
- Extended [tests/test_normalization_flow.py](tests/test_normalization_flow.py) with a subprocess regression that proves importing and constructing `JobOrchestrator` leaves the diarizer, summarizer, and transcriber adapter modules unloaded until a stage actually needs them.
- Created the active MP-004 startup plan at [docs/plans/active/mp-004-startup-hotspot-investigation.md](docs/plans/active/mp-004-startup-hotspot-investigation.md) and updated [INDEX.md](INDEX.md) plus [docs/plans/README.md](docs/plans/README.md) so the repository now points to the active scoped work correctly.

### What Was Tried

- Kept the orchestrator constructor signature and injected test seams intact, then changed only the default adapter path behind property accessors.
- Left measurement work for the next adjacent slice because [scripts/measure_local.py](scripts/measure_local.py) still imports heavy modules at script load and is not yet a clean startup-only benchmark.

### What Was Validated

- `python -m pytest tests/test_normalization_flow.py -k "orchestrator_import_leaves_optional_adapters_unloaded or orchestrator_normalizes_job or process_job_summarizes_plain_transcript_when_configured or list_jobs_cli_prints_jobs_as_json or show_job_cli_prints_job_json"` passed with 5 selected tests.

### Next Session Should Know

- The first startup-cost mitigation for TD-004 is now in place, and the new startup-path benchmark now covers the remaining import-boundary evidence gap.
- The active scoped work now lives at [docs/plans/active/mp-004-startup-hotspot-investigation.md](docs/plans/active/mp-004-startup-hotspot-investigation.md).

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
- Moved the finished scoped plan to [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md) and updated [INDEX.md](INDEX.md), [docs/README.md](docs/README.md), [docs/plans/README.md](docs/plans/README.md), and the then-current roadmap coordination docs so the repository no longer claims there is active scoped work when there is not.

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

## Older History

- Older verified entries now live under [docs/devnotes/README.md](docs/devnotes/README.md).
- Use [docs/devnotes/archive-2026-05-08.md](docs/devnotes/archive-2026-05-08.md) for archived 2026-05-08 notes.
- Use [docs/devnotes/archive-2026-05-05-to-2026-05-07.md](docs/devnotes/archive-2026-05-05-to-2026-05-07.md) for archived 2026-05-05 through 2026-05-07 notes.
