from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from httpx import Request
from fastapi.testclient import TestClient
from openai import APITimeoutError

from minutes.api.app import create_app
from minutes.adapters.diarizer_pyannote import DiarizationResult, DiarizationSegment
from minutes.adapters.summarizer_openai_compatible import OpenAICompatibleSummarizer
from minutes.adapters.summarizer_openai_compatible import SummaryResult
from minutes.adapters.transcriber_sensevoice import SenseVoiceTranscriber
from minutes.adapters.transcriber_sensevoice import TranscriptionResult
import minutes.adapters.transcriber_sensevoice as transcriber_module
from minutes.config import Settings
from minutes.orchestrator import JobOrchestrator
from minutes.pipeline import next_pending_stage
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import ArtifactRecord, CreateJobRequest
from minutes.worker import JobWorker


def _python_executable() -> str:
    return sys.executable


def _ffmpeg_bin() -> Path:
    configured = os.environ.get("MINUTES_FFMPEG_BIN")
    if configured:
        return Path(configured)

    ffmpeg_on_path = shutil.which("ffmpeg")
    if ffmpeg_on_path:
        return Path(ffmpeg_on_path)

    return Path(r"C:\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe")


class FakeTranscriber:
    def transcribe_file(self, audio_path: Path | str, language: str | None = None) -> TranscriptionResult:
        return TranscriptionResult(
            text="hello from fake transcriber",
            raw_segments=[{"text": "hello from fake transcriber"}],
            model_name="fake-sensevoice",
            device="cpu",
            language=language or "auto",
        )

    def transcribe_waveform(self, waveform, language: str | None = None) -> TranscriptionResult:
        return self.transcribe_file("waveform", language=language)


class FakeDiarizer:
    def diarize_file(self, audio_path: Path | str) -> DiarizationResult:
        return DiarizationResult(
            segments=[
                DiarizationSegment(start_seconds=0.0, end_seconds=0.4, speaker="SPEAKER_00"),
                DiarizationSegment(start_seconds=0.4, end_seconds=1.0, speaker="SPEAKER_01"),
            ],
            model_name="fake-pyannote",
            device="cpu",
        )


class FakeSummarizer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def summarize_text(self, text: str, summary_language: str) -> SummaryResult:
        self.calls.append((text, summary_language))
        return SummaryResult(
            text="Summary\n\nSynthetic summary body",
            structured_data={
                "summary": "Synthetic summary body",
                "key_points": ["Key point 1"],
                "decisions": ["Decision 1"],
                "action_items": ["Action 1"],
                "risks": ["Risk 1"],
            },
            model_name="fake-summary-model",
            base_url="http://summary.test/v1",
            prompt_version="v1",
            summary_language=summary_language,
        )


def _settings(tmp_path: Path, diarization_enabled: bool = False, summary_enabled: bool = False) -> Settings:
    settings = Settings(
        state_root=tmp_path / "state",
        ffmpeg_bin=_ffmpeg_bin(),
        diarization_enabled=diarization_enabled,
        summary_base_url="http://summary.test/v1" if summary_enabled else None,
        summary_model="fake-summary-model" if summary_enabled else None,
    )
    settings.ensure_state_dirs()
    return settings


def _make_source_audio(settings: Settings, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(settings.ffmpeg_bin),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_show_config_includes_summary_retry_settings(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(tmp_path / "state")
    env["MINUTES_SUMMARY_BASE_URL"] = "http://summary.test/v1"
    env["MINUTES_SUMMARY_MODEL"] = "fake-summary-model"
    env["MINUTES_SUMMARY_TIMEOUT_SECONDS"] = "45"
    env["MINUTES_SUMMARY_MAX_RETRIES"] = "2"

    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-config",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)

    assert payload["summary_timeout_seconds"] == 45
    assert payload["summary_max_retries"] == 2


def test_transcriber_model_kwargs_prefer_cached_modelscope_paths(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    cache_root = tmp_path / "modelscope-cache"
    sensevoice_cache = cache_root / "iic" / "SenseVoiceSmall"
    vad_cache = cache_root / "iic" / "speech_fsmn_vad_zh-cn-16k-common-pytorch"
    sensevoice_cache.mkdir(parents=True)
    vad_cache.mkdir(parents=True)
    monkeypatch.setattr(transcriber_module, "_modelscope_cache_root", lambda: cache_root)

    kwargs = SenseVoiceTranscriber(settings)._model_kwargs()

    assert kwargs["model"] == str(sensevoice_cache)
    assert kwargs["vad_model"] == str(vad_cache)
    assert kwargs["disable_update"] is True


def test_orchestrator_import_leaves_optional_adapters_unloaded(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(tmp_path / "state")
    env["PYTHONPATH"] = str(Path.cwd() / "src") + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [
            _python_executable(),
            "-c",
            (
                "import json, sys;"
                "from minutes.config import Settings;"
                "from minutes.storage.file_store import FileStateStore;"
                "from minutes.orchestrator import JobOrchestrator;"
                "settings = Settings(state_root=sys.argv[1]);"
                "settings.ensure_state_dirs();"
                "JobOrchestrator(store=FileStateStore(settings));"
                "print(json.dumps({"
                "'diarizer': 'minutes.adapters.diarizer_pyannote' in sys.modules,"
                "'summarizer': 'minutes.adapters.summarizer_openai_compatible' in sys.modules,"
                "'transcriber': 'minutes.adapters.transcriber_sensevoice' in sys.modules"
                "}))"
            ),
            str(tmp_path / "state"),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)

    assert payload == {
        "diarizer": False,
        "summarizer": False,
        "transcriber": False,
    }


def test_measure_local_startup_path_reports_import_boundary(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            _python_executable(),
            str(Path.cwd() / "scripts" / "measure_local.py"),
            "startup-path",
            "--iterations",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["command"] == "startup-path"
    assert payload["iterations"] == 1
    assert payload["config_import_ms"]["min"] >= 0.0
    assert payload["cli_import_ms"]["min"] >= 0.0
    assert payload["settings_init_ms"]["min"] >= 0.0
    assert payload["orchestrator_import_ms"]["min"] >= 0.0
    assert payload["orchestrator_construct_ms"]["min"] >= 0.0
    assert payload["loaded_modules"] == {
        "config": True,
        "uvicorn": False,
        "api_app": False,
        "ffmpeg": False,
        "transcriber": False,
        "diarizer": False,
        "summarizer": False,
    }


def test_orchestrator_normalizes_job(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "input.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    updated = JobOrchestrator(store=store).normalize_job(job.job_id)

    artifact_kinds = [artifact.kind for artifact in updated.artifacts]
    assert updated.status == "queued"
    assert updated.workflow_stage == "normalized"
    assert next_pending_stage(updated, settings) == "transcribe"
    assert artifact_kinds == ["probe", "normalized_audio"]
    assert Path(updated.artifacts[-1].path).exists()


def test_create_job_persists_requested_languages(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)

    created = store.create_job(
        CreateJobRequest(
            source_path="C:/media/example.wav",
            language="yue",
            summary_language="en",
        )
    )

    reloaded = store.get_job(created.job_id)

    assert reloaded.source_path == "C:/media/example.wav"
    assert reloaded.transcription_language == "yue"
    assert reloaded.summary_language == "en"


def test_worker_run_once_processes_job_to_transcribed(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "worker-input.wav"
    _make_source_audio(settings, source)
    job = store.create_job(CreateJobRequest(source_path=str(source)))

    orchestrator = JobOrchestrator(store=store, transcriber=FakeTranscriber())
    updated = JobWorker(store=store, orchestrator=orchestrator).run_once()

    assert updated is not None
    assert updated.job_id == job.job_id
    assert updated.status == "completed"
    assert updated.workflow_stage == "transcribed"
    assert next_pending_stage(updated, settings) is None
    assert [artifact.kind for artifact in updated.artifacts] == ["probe", "normalized_audio", "transcript_json", "transcript_text"]


def test_process_job_summarizes_plain_transcript_when_configured(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "summary-input.wav"
    _make_source_audio(settings, source)
    summarizer = FakeSummarizer()
    job = store.create_job(CreateJobRequest(source_path=str(source), language="yue"))

    updated = JobOrchestrator(
        store=store,
        transcriber=FakeTranscriber(),
        summarizer=summarizer,
    ).process_job(job.job_id)

    assert updated.status == "completed"
    assert updated.workflow_stage == "summarized"
    assert next_pending_stage(updated, settings) is None
    assert summarizer.calls == [("hello from fake transcriber", "yue")]
    summary_artifact = store.get_artifact(job.job_id, "summary_text")
    assert summary_artifact is not None
    assert summary_artifact.metadata["source_artifact_kind"] == "transcript_text"
    assert summary_artifact.metadata["summary_language"] == "yue"
    assert summary_artifact.metadata["summary_timeout_seconds"] == settings.summary_timeout_seconds
    assert summary_artifact.metadata["summary_max_retries"] == settings.summary_max_retries
    assert float(summary_artifact.metadata["summary_elapsed_ms"]) >= 0.0


def test_summary_adapter_retries_timeout_once(tmp_path: Path) -> None:
    settings = Settings(
        state_root=tmp_path / "state",
        ffmpeg_bin=_ffmpeg_bin(),
        summary_base_url="http://summary.test/v1",
        summary_model="fake-summary-model",
        summary_max_retries=1,
    )
    settings.ensure_state_dirs()

    summarizer = OpenAICompatibleSummarizer(settings)
    request = Request("POST", "http://summary.test/v1/chat/completions")

    class FakeResponse:
        def model_dump(self, mode: str = "json"):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Retried summary body",
                                    "key_points": [],
                                    "decisions": [],
                                    "action_items": [],
                                    "risks": [],
                                }
                            )
                        }
                    }
                ]
            }

    class FakeCompletions:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **payload):
            self.calls += 1
            if self.calls == 1:
                raise APITimeoutError(request=request)
            return FakeResponse()

    fake_completions = FakeCompletions()
    summarizer._client = type(
        "FakeClient",
        (),
        {"chat": type("FakeChat", (), {"completions": fake_completions})()},
    )()

    result = summarizer.summarize_text("Meeting notes text", summary_language="en")

    assert fake_completions.calls == 2
    assert result.summary_language == "en"
    assert result.structured_data["summary"] == "Retried summary body"


def test_process_job_uses_match_transcript_language_when_none_is_resolved(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "summary-auto-language.wav"
    _make_source_audio(settings, source)
    summarizer = FakeSummarizer()
    job = store.create_job(CreateJobRequest(source_path=str(source)))

    updated = JobOrchestrator(
        store=store,
        transcriber=FakeTranscriber(),
        summarizer=summarizer,
    ).process_job(job.job_id)

    assert updated.workflow_stage == "summarized"
    assert next_pending_stage(updated, settings) is None
    assert summarizer.calls == [("hello from fake transcriber", "match-transcript")]


def test_process_job_summarizes_speaker_transcript_when_available(tmp_path: Path) -> None:
    settings = _settings(tmp_path, diarization_enabled=True, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "summary-speaker-input.wav"
    _make_source_audio(settings, source)
    summarizer = FakeSummarizer()
    job = store.create_job(CreateJobRequest(source_path=str(source), summary_language="en"))

    updated = JobOrchestrator(
        store=store,
        transcriber=FakeTranscriber(),
        diarizer=FakeDiarizer(),
        summarizer=summarizer,
    ).process_job(job.job_id)

    assert updated.status == "completed"
    assert updated.workflow_stage == "summarized"
    assert next_pending_stage(updated, settings) is None
    assert len(summarizer.calls) == 1
    assert "SPEAKER_00" in summarizer.calls[0][0]
    assert summarizer.calls[0][1] == "en"
    summary_artifact = store.get_artifact(job.job_id, "summary_text")
    assert summary_artifact is not None
    assert summary_artifact.metadata["source_artifact_kind"] == "speaker_transcript_text"


def test_summarize_job_waits_for_speaker_transcript_when_diarization_enabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, diarization_enabled=True, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "summary-gating.wav"
    _make_source_audio(settings, source)
    summarizer = FakeSummarizer()
    job = store.create_job(CreateJobRequest(source_path=str(source)))

    partially_processed = JobOrchestrator(
        store=store,
        transcriber=FakeTranscriber(),
        diarizer=FakeDiarizer(),
    ).diarize_job(job.job_id)

    assert partially_processed.status == "queued"
    assert partially_processed.workflow_stage == "diarized"
    assert next_pending_stage(partially_processed, settings) == "transcribe"
    assert store.get_artifact(job.job_id, "speaker_transcript_text") is None

    summarized = JobOrchestrator(
        store=store,
        transcriber=FakeTranscriber(),
        diarizer=FakeDiarizer(),
        summarizer=summarizer,
    ).summarize_job(job.job_id)

    assert summarized.status == "completed"
    assert summarized.workflow_stage == "summarized"
    assert next_pending_stage(summarized, settings) is None
    assert len(summarizer.calls) == 1
    assert "SPEAKER_00" in summarizer.calls[0][0]


def test_worker_run_once_picks_up_job_missing_summary_artifact(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "worker-summary-input.wav"
    _make_source_audio(settings, source)
    summarizer = FakeSummarizer()
    job = store.create_job(CreateJobRequest(source_path=str(source)))
    orchestrator = JobOrchestrator(store=store, transcriber=FakeTranscriber())
    transcribed = orchestrator.transcribe_job(job.job_id)

    assert transcribed.status == "queued"
    assert transcribed.workflow_stage == "transcribed"
    assert next_pending_stage(transcribed, settings) == "summarize"
    assert store.get_artifact(job.job_id, "summary_text") is None

    worker = JobWorker(
        store=store,
        orchestrator=JobOrchestrator(
            store=store,
            transcriber=FakeTranscriber(),
            summarizer=summarizer,
        ),
    )
    next_job = worker.next_actionable_job()
    updated = worker.run_once()

    assert next_job is not None
    assert next_job.job_id == job.job_id
    assert updated is not None
    assert updated.workflow_stage == "summarized"
    assert len(summarizer.calls) == 1


def test_worker_skips_source_less_job_when_summary_enabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    store.create_job(CreateJobRequest())

    worker = JobWorker(store=store)

    assert worker.next_actionable_job() is None


def test_worker_run_once_summarizes_source_less_job_with_existing_transcript(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    job = store.create_job(CreateJobRequest())
    transcript_path = store.artifacts_root(job.job_id) / "transcript.txt"
    transcript_path.write_text("manual transcript text", encoding="utf-8")
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="transcript_text",
            path=str(transcript_path),
            metadata={"language": "en"},
        ),
    )
    store.save_job(job)

    summarizer = FakeSummarizer()
    worker = JobWorker(
        store=store,
        orchestrator=JobOrchestrator(store=store, summarizer=summarizer),
    )

    updated = worker.run_once()

    assert updated is not None
    assert updated.status == "completed"
    assert updated.workflow_stage == "summarized"
    assert updated.status == "completed"
    assert updated.workflow_stage == "summarized"
    assert next_pending_stage(updated, settings) is None
    assert summarizer.calls == [("manual transcript text", "en")]
    summary_artifact = store.get_artifact(job.job_id, "summary_text")
    assert summary_artifact is not None
    assert summary_artifact.metadata["source_artifact_kind"] == "transcript_text"


def test_worker_run_once_regenerates_stale_summary_when_transcript_changes(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    job = store.create_job(CreateJobRequest())
    artifacts_root = store.artifacts_root(job.job_id)

    transcript_path = artifacts_root / "transcript-new.txt"
    transcript_path.write_text("fresh transcript text", encoding="utf-8")
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="transcript_text",
            path=str(transcript_path),
            metadata={"language": "en"},
        ),
    )

    stale_summary_path = artifacts_root / "summary.txt"
    stale_summary_path.write_text("stale summary text", encoding="utf-8")
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="summary_text",
            path=str(stale_summary_path),
            metadata={
                "source_artifact_kind": "transcript_text",
                "source_artifact_path": str(artifacts_root / "transcript-old.txt"),
                "source_artifact_created_at": "2000-01-01T00:00:00+00:00",
                "summary_language": "en",
            },
        ),
    )
    store.save_job(job)

    summarizer = FakeSummarizer()
    updated = JobWorker(
        store=store,
        orchestrator=JobOrchestrator(store=store, summarizer=summarizer),
    ).run_once()

    assert updated is not None
    assert updated.status == "completed"
    assert updated.workflow_stage == "summarized"
    assert next_pending_stage(updated, settings) is None
    assert summarizer.calls == [("fresh transcript text", "en")]
    summary_artifact = store.get_artifact(job.job_id, "summary_text")
    assert summary_artifact is not None
    assert summary_artifact.metadata["source_artifact_path"] == str(transcript_path)


def test_worker_skips_source_less_job_when_diarization_enabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, diarization_enabled=True)
    store = FileStateStore(settings)
    store.create_job(CreateJobRequest())

    worker = JobWorker(store=store)

    assert worker.next_actionable_job() is None


def test_normalize_route_processes_job(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    source = tmp_path / "api-input.wav"
    _make_source_audio(settings, source)
    client = TestClient(create_app(settings))

    created = client.post("/api/jobs", json={"source_path": str(source)})
    assert created.status_code == 201

    job_id = created.json()["job_id"]
    normalized = client.post(f"/api/jobs/{job_id}/normalize")

    assert normalized.status_code == 200
    payload = normalized.json()
    assert payload["status"] == "queued"
    assert payload["workflow_stage"] == "normalized"
    assert payload["next_stage"] == "transcribe"
    assert [artifact["kind"] for artifact in payload["artifacts"]] == ["probe", "normalized_audio"]


def test_create_job_route_rejects_missing_source_path(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    client = TestClient(create_app(settings))

    response = client.post("/api/jobs", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "source_path is required when creating a job through the API"


def test_process_job_runs_both_stages_with_fake_transcriber(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "process-input.wav"
    _make_source_audio(settings, source)
    job = store.create_job(CreateJobRequest(source_path=str(source)))

    updated = JobOrchestrator(store=store, transcriber=FakeTranscriber()).process_job(job.job_id)

    assert updated.status == "completed"
    assert updated.workflow_stage == "transcribed"
    assert next_pending_stage(updated, settings) is None
    assert [artifact.kind for artifact in updated.artifacts] == ["probe", "normalized_audio", "transcript_json", "transcript_text"]


def test_transcript_route_returns_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "route-transcript.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber()).process_job(job.job_id)

    client = TestClient(create_app(settings))
    response = client.get(f"/api/jobs/{job.job_id}/transcript")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job.job_id
    assert payload["text"] == "hello from fake transcriber"


def test_transcript_route_returns_speaker_attributed_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path, diarization_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "route-speaker-transcript.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber(), diarizer=FakeDiarizer()).process_job(job.job_id)

    client = TestClient(create_app(settings))
    response = client.get(f"/api/jobs/{job.job_id}/transcript?speaker_attributed=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job.job_id
    assert "SPEAKER_00" in payload["text"]
    assert "hello from fake transcriber" in payload["text"]


def test_summary_route_returns_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "route-summary.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber(), summarizer=FakeSummarizer()).process_job(job.job_id)

    client = TestClient(create_app(settings))
    response = client.get(f"/api/jobs/{job.job_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job.job_id
    assert "Synthetic summary body" in payload["text"]
    assert payload["source_current"] is True
    assert payload["current_source_artifact_kind"] == "transcript_text"
    assert payload["current_source_artifact_path"].endswith("transcript.txt")


def test_summary_route_reports_stale_summary_source_state(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    job = store.create_job(CreateJobRequest())
    artifacts_root = store.artifacts_root(job.job_id)

    transcript_path = artifacts_root / "transcript.txt"
    transcript_path.write_text("fresh transcript text", encoding="utf-8")
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="transcript_text",
            path=str(transcript_path),
            metadata={"language": "en"},
        ),
    )

    summary_path = artifacts_root / "summary.txt"
    summary_path.write_text("stale summary text", encoding="utf-8")
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="summary_text",
            path=str(summary_path),
            metadata={
                "source_artifact_kind": "transcript_text",
                "source_artifact_path": str(artifacts_root / "transcript-old.txt"),
                "source_artifact_created_at": "2000-01-01T00:00:00+00:00",
                "summary_language": "en",
            },
        ),
    )
    store.save_job(job)

    client = TestClient(create_app(settings))
    response = client.get(f"/api/jobs/{job.job_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job.job_id
    assert payload["source_current"] is False
    assert payload["current_source_artifact_kind"] == "transcript_text"
    assert payload["current_source_artifact_path"] == str(transcript_path)


def test_summary_route_returns_not_found_when_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "route-summary-missing.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber()).transcribe_job(job.job_id)

    client = TestClient(create_app(settings))
    response = client.get(f"/api/jobs/{job.job_id}/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "Summary not found"


def test_transcript_route_returns_not_found_when_file_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "route-transcript-deleted.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber()).process_job(job.job_id)
    transcript_artifact = store.get_artifact(job.job_id, "transcript_text")
    assert transcript_artifact is not None
    Path(transcript_artifact.path).unlink()

    client = TestClient(create_app(settings))
    response = client.get(f"/api/jobs/{job.job_id}/transcript")

    assert response.status_code == 404
    assert response.json()["detail"] == "Transcript not found"


def test_summary_route_returns_not_found_when_file_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "route-summary-deleted.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber(), summarizer=FakeSummarizer()).process_job(job.job_id)
    summary_artifact = store.get_artifact(job.job_id, "summary_text")
    assert summary_artifact is not None
    Path(summary_artifact.path).unlink()

    client = TestClient(create_app(settings))
    response = client.get(f"/api/jobs/{job.job_id}/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "Summary not found"


def test_show_transcript_cli_prints_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "cli-transcript.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber()).process_job(job.job_id)

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-transcript",
            job.job_id,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.stdout.strip() == "hello from fake transcriber"


def test_list_jobs_cli_prints_jobs_as_json(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    first = store.create_job(CreateJobRequest(source_path="C:/media/first.wav"))
    second = store.create_job(CreateJobRequest(source_path="C:/media/second.wav"))

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    env["MINUTES_SUMMARY_BASE_URL"] = ""
    env["MINUTES_SUMMARY_MODEL"] = ""
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "list-jobs",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)

    assert [job["job_id"] for job in payload] == [second.job_id, first.job_id]
    assert payload[0]["next_stage"] == "normalize"
    assert payload[1]["next_stage"] == "normalize"
    assert "current_stage" not in payload[0]
    assert "current_stage" not in payload[1]


def test_show_job_cli_prints_job_json(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    job = store.create_job(CreateJobRequest(source_path="C:/media/example.wav", language="yue", summary_language="en"))

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    env["MINUTES_SUMMARY_BASE_URL"] = ""
    env["MINUTES_SUMMARY_MODEL"] = ""
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-job",
            job.job_id,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)

    assert payload["job_id"] == job.job_id
    assert payload["source_path"] == "C:/media/example.wav"
    assert payload["transcription_language"] == "yue"
    assert payload["summary_language"] == "en"
    assert payload["summary_state"] is None
    assert payload["next_stage"] == "normalize"
    assert "current_stage" not in payload


def test_get_job_route_reports_stale_summary_state(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    job = store.create_job(CreateJobRequest())
    artifacts_root = store.artifacts_root(job.job_id)

    transcript_path = artifacts_root / "transcript.txt"
    transcript_path.write_text("fresh transcript text", encoding="utf-8")
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="transcript_text",
            path=str(transcript_path),
            metadata={"language": "en"},
        ),
    )

    summary_path = artifacts_root / "summary.txt"
    summary_path.write_text("stale summary text", encoding="utf-8")
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="summary_text",
            path=str(summary_path),
            metadata={
                "source_artifact_kind": "transcript_text",
                "source_artifact_path": str(artifacts_root / "transcript-old.txt"),
                "source_artifact_created_at": "2000-01-01T00:00:00+00:00",
                "summary_language": "en",
            },
        ),
    )
    store.save_job(job)

    app = create_app(settings)
    app.state.store = store
    client = TestClient(app)

    response = client.get(f"/api/jobs/{job.job_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_stage"] == "transcribed"
    assert payload["summary_state"] == "stale"
    assert payload["next_stage"] == "summarize"
    assert "current_stage" not in payload


def test_get_job_route_canonicalizes_workflow_stage_after_out_of_order_diarization(tmp_path: Path) -> None:
    settings = _settings(tmp_path, diarization_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "route-diarize-out-of-order.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber(), diarizer=FakeDiarizer()).diarize_job(job.job_id)

    app = create_app(settings)
    app.state.store = store
    client = TestClient(app)

    response = client.get(f"/api/jobs/{job.job_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_stage"] == "normalized"
    assert payload["next_stage"] == "transcribe"
    assert "current_stage" not in payload


def test_show_job_cli_returns_error_when_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-job",
            "missing-job",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 1
    assert "Job not found: missing-job" in result.stdout


def test_show_transcript_cli_prints_speaker_attributed_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path, diarization_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "cli-speaker-transcript.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber(), diarizer=FakeDiarizer()).process_job(job.job_id)

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-transcript",
            job.job_id,
            "--speaker-attributed",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "SPEAKER_00" in result.stdout
    assert "hello from fake transcriber" in result.stdout


def test_show_summary_cli_prints_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "cli-summary.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber(), summarizer=FakeSummarizer()).process_job(job.job_id)

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    env["MINUTES_SUMMARY_BASE_URL"] = settings.summary_base_url or ""
    env["MINUTES_SUMMARY_MODEL"] = settings.summary_model or ""
    env["MINUTES_DIARIZATION_ENABLED"] = "false"
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-summary",
            job.job_id,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "Synthetic summary body" in result.stdout


def test_show_summary_cli_json_includes_source_status(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "cli-summary-json.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber(), summarizer=FakeSummarizer()).process_job(job.job_id)

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    env["MINUTES_SUMMARY_BASE_URL"] = settings.summary_base_url or ""
    env["MINUTES_SUMMARY_MODEL"] = settings.summary_model or ""
    env["MINUTES_DIARIZATION_ENABLED"] = "false"
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-summary",
            job.job_id,
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["job_id"] == job.job_id
    assert payload["source_current"] is True
    assert payload["current_source_artifact_kind"] == "transcript_text"
    assert payload["current_source_artifact_path"].endswith("transcript.txt")


def test_show_summary_cli_returns_error_when_file_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "cli-summary-deleted.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber(), summarizer=FakeSummarizer()).process_job(job.job_id)
    summary_artifact = store.get_artifact(job.job_id, "summary_text")
    assert summary_artifact is not None
    Path(summary_artifact.path).unlink()

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    env["MINUTES_SUMMARY_BASE_URL"] = settings.summary_base_url or ""
    env["MINUTES_SUMMARY_MODEL"] = settings.summary_model or ""
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-summary",
            job.job_id,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 1
    assert "Summary artifact not found" in result.stdout


def test_show_transcript_cli_returns_error_when_file_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "cli-transcript-deleted.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber()).process_job(job.job_id)
    transcript_artifact = store.get_artifact(job.job_id, "transcript_text")
    assert transcript_artifact is not None
    Path(transcript_artifact.path).unlink()

    env = os.environ.copy()
    env["MINUTES_STATE_ROOT"] = str(settings.state_root)
    result = subprocess.run(
        [
            _python_executable(),
            "-m",
            "minutes",
            "show-transcript",
            job.job_id,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 1
    assert "Transcript artifact not found" in result.stdout


def test_process_job_runs_diarization_when_enabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, diarization_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "diarize-input.wav"
    _make_source_audio(settings, source)
    job = store.create_job(CreateJobRequest(source_path=str(source)))

    updated = JobOrchestrator(
        store=store,
        transcriber=FakeTranscriber(),
        diarizer=FakeDiarizer(),
    ).process_job(job.job_id)

    assert updated.status == "completed"
    assert updated.workflow_stage == "speaker_attributed"
    assert next_pending_stage(updated, settings) is None
    assert [artifact.kind for artifact in updated.artifacts] == [
        "probe",
        "normalized_audio",
        "transcript_json",
        "transcript_text",
        "diarization_json",
        "diarization_rttm",
        "speaker_transcript_json",
        "speaker_transcript_text",
    ]
    assert Path(store.get_artifact(job.job_id, "diarization_json").path).exists()
    assert Path(store.get_artifact(job.job_id, "diarization_rttm").path).exists()
    speaker_text = Path(store.get_artifact(job.job_id, "speaker_transcript_text").path).read_text(encoding="utf-8")
    assert "SPEAKER_00" in speaker_text
    assert "hello from fake transcriber" in speaker_text


def test_merge_diarization_segments_merges_same_speaker_across_short_gap() -> None:
    merged = JobOrchestrator._merge_diarization_segments(
        [
            {"start_seconds": 0.0, "end_seconds": 2.0, "speaker": "SPEAKER_00"},
            {"start_seconds": 2.3, "end_seconds": 4.0, "speaker": "SPEAKER_00"},
            {"start_seconds": 4.2, "end_seconds": 5.0, "speaker": "SPEAKER_01"},
        ]
    )

    assert merged == [
        {
            "speaker": "SPEAKER_00",
            "start_seconds": 0.0,
            "end_seconds": 4.0,
            "source_segment_count": 2,
        },
        {
            "speaker": "SPEAKER_01",
            "start_seconds": 4.2,
            "end_seconds": 5.0,
            "source_segment_count": 1,
        },
    ]


def test_summarize_job_route_runs_summary_stage(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "route-summarize-action.wav"
    _make_source_audio(settings, source)
    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber()).transcribe_job(job.job_id)

    app = create_app(settings)
    app.state.store = store
    app.state.orchestrator = JobOrchestrator(
        store=store,
        transcriber=FakeTranscriber(),
        summarizer=FakeSummarizer(),
    )
    client = TestClient(app)

    response = client.post(f"/api/jobs/{job.job_id}/summarize")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["workflow_stage"] == "summarized"
    assert payload["summary_state"] == "current"
    assert "current_stage" not in payload


def test_summarize_job_prefers_existing_speaker_transcript_even_when_diarization_disabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    artifacts_root = store.artifacts_root("manual")
    transcript_path = artifacts_root / "transcript.txt"
    transcript_path.write_text("plain transcript text", encoding="utf-8")
    speaker_path = artifacts_root / "speaker_transcript.txt"
    speaker_path.write_text("speaker transcript text", encoding="utf-8")

    job = store.create_job(CreateJobRequest())
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="transcript_text",
            path=str(transcript_path),
            metadata={"language": "en"},
        ),
    )
    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="speaker_transcript_text",
            path=str(speaker_path),
            metadata={},
        ),
    )
    store.save_job(job)

    summarizer = FakeSummarizer()
    summarized = JobOrchestrator(store=store, summarizer=summarizer).summarize_job(job.job_id)

    assert summarized.status == "completed"
    assert summarized.workflow_stage == "summarized"
    assert next_pending_stage(summarized, settings) is None
    assert summarizer.calls == [("speaker transcript text", "en")]