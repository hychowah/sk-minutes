from __future__ import annotations

import argparse
import json
import subprocess
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from minutes.config import Settings
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import ArtifactRecord, CreateJobRequest, JobRecord, JobStatus


CLI_IMPORT_PROBE = """
import json
import sys
import time
from pathlib import Path

repo_root = Path(sys.argv[1])
src_root = repo_root / \"src\"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

cli_started = time.perf_counter()
import minutes.cli
cli_import_ms = (time.perf_counter() - cli_started) * 1000

print(json.dumps({
    \"cli_import_ms\": round(cli_import_ms, 3),
    \"loaded_modules\": {
        \"config\": \"minutes.config\" in sys.modules,
        \"uvicorn\": \"uvicorn\" in sys.modules,
        \"api_app\": \"minutes.api.app\" in sys.modules,
        \"ffmpeg\": \"minutes.adapters.ffmpeg\" in sys.modules,
        \"transcriber\": \"minutes.adapters.transcriber_sensevoice\" in sys.modules,
        \"diarizer\": \"minutes.adapters.diarizer_pyannote\" in sys.modules,
        \"summarizer\": \"minutes.adapters.summarizer_openai_compatible\" in sys.modules,
    },
}))
"""


CONFIG_IMPORT_PROBE = """
import json
import sys
import time
from pathlib import Path

repo_root = Path(sys.argv[1])
src_root = repo_root / \"src\"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

config_started = time.perf_counter()
import minutes.config
config_import_ms = (time.perf_counter() - config_started) * 1000

print(json.dumps({
    \"config_import_ms\": round(config_import_ms, 3),
}))
"""


SETTINGS_INIT_PROBE = """
import json
import sys
import time
from pathlib import Path

repo_root = Path(sys.argv[1])
state_root = Path(sys.argv[2])
src_root = repo_root / \"src\"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from minutes.config import get_settings

started = time.perf_counter()
settings = get_settings.__wrapped__()
settings = settings.model_copy(update={\"state_root\": state_root})
settings.ensure_state_dirs()
settings_init_ms = (time.perf_counter() - started) * 1000

print(json.dumps({
    \"settings_init_ms\": round(settings_init_ms, 3),
    \"state_root_exists\": state_root.exists(),
}))
"""


ORCHESTRATOR_IMPORT_PROBE = """
import json
import sys
import time
from pathlib import Path

repo_root = Path(sys.argv[1])
src_root = repo_root / \"src\"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

orchestrator_started = time.perf_counter()
from minutes.orchestrator import JobOrchestrator
orchestrator_import_ms = (time.perf_counter() - orchestrator_started) * 1000

print(json.dumps({
    \"orchestrator_import_ms\": round(orchestrator_import_ms, 3),
}))
"""


ORCHESTRATOR_CONSTRUCT_PROBE = """
import json
import sys
import time
from pathlib import Path

repo_root = Path(sys.argv[1])
state_root = Path(sys.argv[2])
src_root = repo_root / \"src\"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from minutes.config import Settings
from minutes.storage.file_store import FileStateStore
from minutes.orchestrator import JobOrchestrator

settings = Settings(state_root=state_root)
settings.ensure_state_dirs()

construct_started = time.perf_counter()
JobOrchestrator(store=FileStateStore(settings))
orchestrator_construct_ms = (time.perf_counter() - construct_started) * 1000

print(json.dumps({
    \"orchestrator_construct_ms\": round(orchestrator_construct_ms, 3),
}))
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local measurement helpers for Minutes.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    control_plane = subparsers.add_parser("control-plane", help="Measure job listing and worker pickup over synthetic jobs.")
    control_plane.add_argument("--job-count", type=int, default=250, help="Synthetic job count to seed.")
    control_plane.add_argument("--iterations", type=int, default=5, help="Number of repeated timing iterations.")
    control_plane.add_argument(
        "--scenario",
        choices=("created", "summary-current", "summary-stale"),
        default="created",
        help="Synthetic job shape to seed for next_actionable_job measurements.",
    )

    transcription = subparsers.add_parser("transcription", help="Measure cold and warm transcription against one audio file.")
    transcription.add_argument("audio_path", help="Path to the input audio file.")
    transcription.add_argument("--language", default=None, help="Optional transcription language override.")

    api_transcription = subparsers.add_parser("api-transcription", help="Measure first and second API transcription requests on one app instance.")
    api_transcription.add_argument("audio_path", help="Path to the input audio file.")
    api_transcription.add_argument("--language", default=None, help="Optional transcription language override.")

    startup_path = subparsers.add_parser(
        "startup-path",
        help="Measure fresh-process CLI and orchestrator startup on the process-file path.",
    )
    startup_path.add_argument("--iterations", type=int, default=5, help="Number of fresh-process samples to collect.")

    summary = subparsers.add_parser("summary", help="Measure summary latency against one transcript file.")
    summary.add_argument("transcript_path", help="Path to the transcript text file.")
    summary.add_argument("--summary-language", default="match-transcript", help="Summary output language.")
    summary.add_argument("--iterations", type=int, default=1, help="Number of repeated summary calls.")

    assembly = subparsers.add_parser("speaker-assembly", help="Measure speaker transcript assembly against prepared artifacts.")
    assembly.add_argument("normalized_audio_path", help="Path to normalized WAV audio.")
    assembly.add_argument("diarization_json_path", help="Path to diarization.json.")
    assembly.add_argument("--transcript-path", default=None, help="Optional transcript text artifact path to seed.")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "control-plane":
        payload = measure_control_plane(job_count=args.job_count, iterations=args.iterations, scenario=args.scenario)
    elif args.command == "transcription":
        payload = measure_transcription(Path(args.audio_path), language=args.language)
    elif args.command == "api-transcription":
        payload = measure_api_transcription(Path(args.audio_path), language=args.language)
    elif args.command == "startup-path":
        payload = measure_startup_path(iterations=args.iterations)
    elif args.command == "summary":
        payload = measure_summary(Path(args.transcript_path), summary_language=args.summary_language, iterations=args.iterations)
    elif args.command == "speaker-assembly":
        payload = measure_speaker_assembly(
            normalized_audio_path=Path(args.normalized_audio_path),
            diarization_json_path=Path(args.diarization_json_path),
            transcript_path=Path(args.transcript_path) if args.transcript_path else None,
        )
    else:
        parser.error(f"Unsupported command: {args.command}")
        return 2

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def measure_control_plane(*, job_count: int, iterations: int, scenario: str) -> dict[str, Any]:
    from minutes.worker import JobWorker

    with tempfile.TemporaryDirectory(prefix="minutes-measure-") as temp_dir:
        settings = Settings(
            state_root=Path(temp_dir) / "state",
            diarization_enabled=False,
            summary_base_url="http://benchmark.invalid" if scenario != "created" else None,
            summary_model="benchmark-summary" if scenario != "created" else None,
        )
        settings.ensure_state_dirs()
        store = FileStateStore(settings)

        expected_job_id = _seed_control_plane_jobs(store, job_count=job_count, scenario=scenario)

        list_jobs_samples: list[float] = []
        next_actionable_samples: list[float] = []

        for _ in range(iterations):
            list_jobs_start = time.perf_counter()
            jobs = store.list_jobs()
            list_jobs_samples.append((time.perf_counter() - list_jobs_start) * 1000)

            worker = JobWorker(store=store)
            next_actionable_start = time.perf_counter()
            next_job = worker.next_actionable_job()
            next_actionable_samples.append((time.perf_counter() - next_actionable_start) * 1000)

            actual_job_id = None if next_job is None else next_job.job_id
            if actual_job_id != expected_job_id:
                raise RuntimeError(
                    "Synthetic control-plane benchmark did not find the expected actionable job "
                    f"for scenario {scenario!r}."
                )

    return {
        "command": "control-plane",
        "job_count": job_count,
        "iterations": iterations,
        "scenario": scenario,
        "list_jobs_ms": _stats(list_jobs_samples),
        "next_actionable_job_ms": _stats(next_actionable_samples),
    }


def measure_startup_path(*, iterations: int) -> dict[str, Any]:
    config_import_samples: list[float] = []
    cli_import_samples: list[float] = []
    settings_init_samples: list[float] = []
    orchestrator_import_samples: list[float] = []
    orchestrator_construct_samples: list[float] = []
    loaded_modules: dict[str, bool] | None = None

    with tempfile.TemporaryDirectory(prefix="minutes-startup-measure-") as temp_dir:
        for index in range(iterations):
            state_root = Path(temp_dir) / f"state-{index}"
            config_payload = _run_startup_probe(CONFIG_IMPORT_PROBE, str(REPO_ROOT))
            cli_payload = _run_startup_probe(CLI_IMPORT_PROBE, str(REPO_ROOT))
            settings_payload = _run_startup_probe(SETTINGS_INIT_PROBE, str(REPO_ROOT), str(state_root))
            orchestrator_import_payload = _run_startup_probe(ORCHESTRATOR_IMPORT_PROBE, str(REPO_ROOT))
            orchestrator_construct_payload = _run_startup_probe(ORCHESTRATOR_CONSTRUCT_PROBE, str(REPO_ROOT), str(state_root))

            config_import_samples.append(float(config_payload["config_import_ms"]))
            cli_import_samples.append(float(cli_payload["cli_import_ms"]))
            settings_init_samples.append(float(settings_payload["settings_init_ms"]))
            orchestrator_import_samples.append(float(orchestrator_import_payload["orchestrator_import_ms"]))
            orchestrator_construct_samples.append(float(orchestrator_construct_payload["orchestrator_construct_ms"]))
            loaded_modules = dict(cli_payload["loaded_modules"])

    return {
        "command": "startup-path",
        "iterations": iterations,
        "config_import_ms": _stats(config_import_samples),
        "cli_import_ms": _stats(cli_import_samples),
        "settings_init_ms": _stats(settings_init_samples),
        "orchestrator_import_ms": _stats(orchestrator_import_samples),
        "orchestrator_construct_ms": _stats(orchestrator_construct_samples),
        "loaded_modules": loaded_modules,
    }


def _run_startup_probe(probe: str, *probe_args: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-c", probe, *probe_args],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return json.loads(result.stdout)


def _seed_control_plane_jobs(store: FileStateStore, *, job_count: int, scenario: str) -> str | None:
    if scenario == "created":
        actionable_job = store.create_job(CreateJobRequest(source_path="C:/media/actionable.wav"))
        for _ in range(max(job_count - 1, 0)):
            store.create_job(CreateJobRequest())
        return actionable_job.job_id

    actionable_job = _create_summary_control_plane_job(store, stale=scenario == "summary-stale")
    for _ in range(max(job_count - 1, 0)):
        _create_summary_control_plane_job(store, stale=False)

    if scenario == "summary-current":
        return None
    return actionable_job.job_id


def _create_summary_control_plane_job(store: FileStateStore, *, stale: bool) -> JobRecord:
    job = store.create_job(CreateJobRequest())
    artifacts_root = store.artifacts_root(job.job_id)
    transcript_artifact = ArtifactRecord(
        kind="transcript_text",
        path=str(artifacts_root / "transcript.txt"),
        metadata={"language": "en"},
    )
    job = store.replace_artifact(job, transcript_artifact)

    summary_metadata: dict[str, str] = {
        "source_artifact_kind": transcript_artifact.kind,
        "summary_language": "en",
    }
    if stale:
        summary_metadata["source_artifact_path"] = str(artifacts_root / "transcript-stale.txt")
        summary_metadata["source_artifact_created_at"] = "2000-01-01T00:00:00+00:00"
    else:
        summary_metadata["source_artifact_path"] = transcript_artifact.path
        summary_metadata["source_artifact_created_at"] = transcript_artifact.created_at.isoformat()

    job = store.replace_artifact(
        job,
        ArtifactRecord(
            kind="summary_text",
            path=str(artifacts_root / "summary.txt"),
            metadata=summary_metadata,
        ),
    )
    return store.save_job(job)


def measure_transcription(audio_path: Path, *, language: str | None) -> dict[str, Any]:
    from minutes.adapters.transcriber_sensevoice import SenseVoiceTranscriber

    settings = Settings()
    settings.ensure_state_dirs()
    transcriber = SenseVoiceTranscriber(settings)

    cold_start = time.perf_counter()
    cold_result = transcriber.transcribe_file(audio_path, language=language)
    cold_seconds = time.perf_counter() - cold_start

    warm_start = time.perf_counter()
    warm_result = transcriber.transcribe_file(audio_path, language=language)
    warm_seconds = time.perf_counter() - warm_start

    return {
        "command": "transcription",
        "audio_path": str(audio_path),
        "language": cold_result.language,
        "cold_seconds": round(cold_seconds, 3),
        "warm_seconds": round(warm_seconds, 3),
        "cold_text_length": len(cold_result.text),
        "warm_text_length": len(warm_result.text),
        "device": cold_result.device,
        "model_name": cold_result.model_name,
    }


def measure_api_transcription(audio_path: Path, *, language: str | None) -> dict[str, Any]:
    from minutes.api.app import create_app

    with tempfile.TemporaryDirectory(prefix="minutes-api-measure-") as temp_dir:
        settings = Settings(state_root=Path(temp_dir) / "state")
        settings.ensure_state_dirs()
        app = create_app(settings)
        client = TestClient(app)

        first_job_id = _create_job_via_api(client, audio_path, language=language)
        first_started_at = time.perf_counter()
        first_response = client.post(f"/api/jobs/{first_job_id}/transcribe")
        first_seconds = time.perf_counter() - first_started_at
        first_payload = _ensure_ok(first_response)

        second_job_id = _create_job_via_api(client, audio_path, language=language)
        second_started_at = time.perf_counter()
        second_response = client.post(f"/api/jobs/{second_job_id}/transcribe")
        second_seconds = time.perf_counter() - second_started_at
        second_payload = _ensure_ok(second_response)

    return {
        "command": "api-transcription",
        "audio_path": str(audio_path),
        "language": language or "auto",
        "first_request_seconds": round(first_seconds, 3),
        "second_request_seconds": round(second_seconds, 3),
        "first_status": first_payload["status"],
        "second_status": second_payload["status"],
        "first_workflow_stage": first_payload.get("workflow_stage"),
        "second_workflow_stage": second_payload.get("workflow_stage"),
    }


def measure_summary(transcript_path: Path, *, summary_language: str, iterations: int) -> dict[str, Any]:
    from minutes.adapters.summarizer_openai_compatible import OpenAICompatibleSummarizer

    settings = Settings()
    settings.ensure_state_dirs()
    summarizer = OpenAICompatibleSummarizer(settings)
    transcript_text = transcript_path.read_text(encoding="utf-8")
    samples: list[float] = []
    last_result = None

    for _ in range(iterations):
        started_at = time.perf_counter()
        last_result = summarizer.summarize_text(transcript_text, summary_language=summary_language)
        samples.append((time.perf_counter() - started_at) * 1000)

    if last_result is None:
        raise RuntimeError("Summary benchmark did not produce a result.")

    return {
        "command": "summary",
        "transcript_path": str(transcript_path),
        "iterations": iterations,
        "summary_language": last_result.summary_language,
        "summary_ms": _stats(samples),
        "summary_length": len(last_result.text),
        "model_name": last_result.model_name,
        "base_url": last_result.base_url,
    }


def measure_speaker_assembly(
    *,
    normalized_audio_path: Path,
    diarization_json_path: Path,
    transcript_path: Path | None,
) -> dict[str, Any]:
    from minutes.orchestrator import JobOrchestrator

    with tempfile.TemporaryDirectory(prefix="minutes-assembly-") as temp_dir:
        settings = Settings(state_root=Path(temp_dir) / "state", diarization_enabled=True)
        settings.ensure_state_dirs()
        store = FileStateStore(settings)
        job = store.create_job(CreateJobRequest(source_path=str(normalized_audio_path)))

        transcript_artifact_path = transcript_path or (store.artifacts_root(job.job_id) / "transcript.txt")
        if transcript_path is None:
            transcript_artifact_path.write_text("benchmark transcript seed", encoding="utf-8")

        job = store.replace_artifact(
            job,
            ArtifactRecord(kind="normalized_audio", path=str(normalized_audio_path), metadata={}),
        )
        job = store.replace_artifact(
            job,
            ArtifactRecord(kind="diarization_json", path=str(diarization_json_path), metadata={}),
        )
        job = store.replace_artifact(
            job,
            ArtifactRecord(kind="transcript_text", path=str(transcript_artifact_path), metadata={"language": "auto"}),
        )
        job = store.save_job(job.model_copy(update={"status": JobStatus.QUEUED}))

        orchestrator = JobOrchestrator(store=store)
        started_at = time.perf_counter()
        assembled = orchestrator.assemble_speaker_transcript_job(job.job_id)
        elapsed_ms = (time.perf_counter() - started_at) * 1000

        speaker_artifact = store.get_artifact(job.job_id, "speaker_transcript_text")
        if speaker_artifact is None:
            raise RuntimeError("Speaker assembly benchmark did not produce a speaker transcript artifact.")

        return {
            "command": "speaker-assembly",
            "normalized_audio_path": str(normalized_audio_path),
            "diarization_json_path": str(diarization_json_path),
            "status": assembled.status,
            "workflow_stage": assembled.workflow_stage,
            "speaker_assembly_ms": round(elapsed_ms, 3),
            "speaker_transcript_path": speaker_artifact.path,
        }


def _stats(samples: list[float]) -> dict[str, float]:
    return {
        "min": round(min(samples), 3),
        "median": round(statistics.median(samples), 3),
        "mean": round(statistics.fmean(samples), 3),
        "max": round(max(samples), 3),
    }


def _create_job_via_api(client: TestClient, audio_path: Path, *, language: str | None) -> str:
    payload: dict[str, str] = {"source_path": str(audio_path)}
    if language is not None:
        payload["language"] = language

    response = client.post("/api/jobs", json=payload)
    data = _ensure_ok(response)
    return str(data["job_id"])


def _ensure_ok(response) -> dict[str, Any]:
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    raise SystemExit(main())