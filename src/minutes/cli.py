from __future__ import annotations

import argparse
import json
from typing import Sequence

import uvicorn

from minutes.api.app import create_app
from minutes.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="minutes", description="Minutes local application tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show-config", help="Print resolved runtime configuration.")
    subparsers.add_parser("run-once", help="Process the next queued job once.")

    process_parser = subparsers.add_parser("process-file", help="Create a job for a media file and process it end-to-end.")
    process_parser.add_argument("source_path", help="Path to the audio or video file.")
    process_parser.add_argument("--language", default=None, help="Optional transcription language override.")

    transcript_parser = subparsers.add_parser("show-transcript", help="Print the transcript text for a processed job.")
    transcript_parser.add_argument("job_id", help="Job identifier.")
    transcript_parser.add_argument("--json", action="store_true", help="Print transcript metadata as JSON instead of plain text.")
    transcript_parser.add_argument(
        "--speaker-attributed",
        action="store_true",
        help="Print the speaker-attributed transcript when it exists.",
    )

    serve_parser = subparsers.add_parser("serve", help="Run the local web application.")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = get_settings()

    if args.command == "show-config":
        payload = {
            "app_name": settings.app_name,
            "app_env": settings.app_env,
            "host": settings.host,
            "port": settings.port,
            "state_root": str(settings.state_root),
            "cache_root": str(settings.cache_root),
            "data_root": str(settings.data_root),
            "logs_root": str(settings.logs_root),
            "ffmpeg_bin": str(settings.ffmpeg_bin),
            "ffmpeg_available": settings.ffmpeg_available,
            "diarization_enabled": settings.diarization_enabled,
            "pyannote_model": settings.pyannote_model,
            "diarization_device": settings.diarization_device,
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "run-once":
        from minutes.worker import JobWorker

        job = JobWorker().run_once()
        if job is None:
            print("No queued jobs available.")
            return 0

        print(json.dumps(job.model_dump(mode="json"), indent=2))
        return 0

    if args.command == "process-file":
        from minutes.orchestrator import JobOrchestrator
        from minutes.storage.file_store import FileStateStore
        from minutes.storage.models import CreateJobRequest

        store = FileStateStore(settings)
        job = store.create_job(CreateJobRequest(source_path=args.source_path, language=args.language))
        processed = JobOrchestrator(store=store).process_job(job.job_id)
        print(json.dumps(processed.model_dump(mode="json"), indent=2))
        return 0 if processed.status != "failed" else 1

    if args.command == "show-transcript":
        from pathlib import Path

        from minutes.storage.file_store import FileStateStore
        from minutes.storage.models import TranscriptResponse

        store = FileStateStore(settings)
        artifact_kind = "speaker_transcript_text" if args.speaker_attributed else "transcript_text"
        artifact = store.get_artifact(args.job_id, artifact_kind)
        if artifact is None:
            label = "Speaker-attributed transcript" if args.speaker_attributed else "Transcript"
            print(f"{label} artifact not found for job {args.job_id}.")
            return 1

        payload = TranscriptResponse(
            job_id=args.job_id,
            text=Path(artifact.path).read_text(encoding="utf-8"),
            artifact_path=artifact.path,
            metadata=artifact.metadata,
        )
        if args.json:
            print(json.dumps(payload.model_dump(mode="json"), indent=2, ensure_ascii=False))
        else:
            print(payload.text)
        return 0

    if args.command == "serve":
        uvicorn.run(
            create_app(),
            host=settings.host,
            port=settings.port,
            reload=args.reload,
        )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())