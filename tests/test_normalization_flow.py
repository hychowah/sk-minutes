from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from minutes.api.app import create_app
from minutes.adapters.diarizer_pyannote import DiarizationResult, DiarizationSegment
from minutes.adapters.summarizer_openai_compatible import OpenAICompatibleSummarizer
from minutes.adapters.summarizer_openai_compatible import SummaryResult
from minutes.adapters.transcriber_sensevoice import TranscriptionResult
from minutes.config import Settings
from minutes.orchestrator import JobOrchestrator
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import ArtifactRecord, CreateJobRequest
from minutes.worker import JobWorker


class FakeTranscriber:
    def transcribe_file(self, audio_path: Path | str, language: str | None = None) -> TranscriptionResult:
        return TranscriptionResult(
            text="hello from fake transcriber",
            raw_segments=[{"text": "hello from fake transcriber"}],
            model_name="fake-sensevoice",
            device="cpu",
            language=language or "auto",
        )


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
        ffmpeg_bin=Path(r"C:\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe"),
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


def test_orchestrator_normalizes_job(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "input.wav"
    _make_source_audio(settings, source)

    job = store.create_job(CreateJobRequest(source_path=str(source)))
    updated = JobOrchestrator(store=store).normalize_job(job.job_id)

    artifact_kinds = [artifact.kind for artifact in updated.artifacts]
    assert updated.status == "queued"
    assert updated.current_stage == "normalized"
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
    assert updated.current_stage == "transcribed"
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
    assert updated.current_stage == "summarized"
    assert summarizer.calls == [("hello from fake transcriber", "yue")]
    summary_artifact = store.get_artifact(job.job_id, "summary_text")
    assert summary_artifact is not None
    assert summary_artifact.metadata["source_artifact_kind"] == "transcript_text"
    assert summary_artifact.metadata["summary_language"] == "yue"


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

    assert updated.current_stage == "summarized"
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
    assert updated.current_stage == "summarized"
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

    assert partially_processed.current_stage == "diarized"
    assert store.get_artifact(job.job_id, "speaker_transcript_text") is None

    summarized = JobOrchestrator(
        store=store,
        transcriber=FakeTranscriber(),
        diarizer=FakeDiarizer(),
        summarizer=summarizer,
    ).summarize_job(job.job_id)

    assert summarized.current_stage == "summarized"
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

    assert transcribed.current_stage == "transcribed"
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
    assert updated.current_stage == "summarized"
    assert len(summarizer.calls) == 1


def test_worker_skips_source_less_job_when_summary_enabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    store.create_job(CreateJobRequest())

    worker = JobWorker(store=store)

    assert worker.next_actionable_job() is None


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
    assert [artifact["kind"] for artifact in payload["artifacts"]] == ["probe", "normalized_audio"]


def test_process_job_runs_both_stages_with_fake_transcriber(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = FileStateStore(settings)
    source = tmp_path / "process-input.wav"
    _make_source_audio(settings, source)
    job = store.create_job(CreateJobRequest(source_path=str(source)))

    updated = JobOrchestrator(store=store, transcriber=FakeTranscriber()).process_job(job.job_id)

    assert updated.status == "completed"
    assert updated.current_stage == "transcribed"
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
            str(Path.cwd() / ".venv" / "Scripts" / "python.exe"),
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
            str(Path.cwd() / ".venv" / "Scripts" / "python.exe"),
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
    result = subprocess.run(
        [
            str(Path.cwd() / ".venv" / "Scripts" / "python.exe"),
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
            str(Path.cwd() / ".venv" / "Scripts" / "python.exe"),
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
            str(Path.cwd() / ".venv" / "Scripts" / "python.exe"),
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
    assert updated.current_stage == "speaker_attributed"
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


def test_summarize_job_route_runs_summary_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, summary_enabled=True)
    store = FileStateStore(settings)
    source = tmp_path / "route-summarize-action.wav"
    _make_source_audio(settings, source)
    job = store.create_job(CreateJobRequest(source_path=str(source)))
    JobOrchestrator(store=store, transcriber=FakeTranscriber()).transcribe_job(job.job_id)

    def _fake_summary(self: OpenAICompatibleSummarizer, text: str, summary_language: str) -> SummaryResult:
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

    monkeypatch.setattr(OpenAICompatibleSummarizer, "summarize_text", _fake_summary)

    app = create_app(settings)
    client = TestClient(app)

    response = client.post(f"/api/jobs/{job.job_id}/summarize")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_stage"] == "summarized"


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

    assert summarized.current_stage == "summarized"
    assert summarizer.calls == [("speaker transcript text", "en")]