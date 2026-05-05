from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from minutes.api.app import create_app
from minutes.adapters.diarizer_pyannote import DiarizationResult, DiarizationSegment
from minutes.adapters.transcriber_sensevoice import TranscriptionResult
from minutes.config import Settings
from minutes.orchestrator import JobOrchestrator
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import CreateJobRequest
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


def _settings(tmp_path: Path, diarization_enabled: bool = False) -> Settings:
    settings = Settings(
        state_root=tmp_path / "state",
        ffmpeg_bin=Path(r"C:\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe"),
        diarization_enabled=diarization_enabled,
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