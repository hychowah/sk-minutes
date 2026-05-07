from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pathlib import Path

from minutes.config import Settings, get_settings
from minutes.orchestrator import JobOrchestrator
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import CreateJobRequest, JobRecord, SummaryResponse, TranscriptResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _settings(request: Request | None = None) -> Settings:
    if request is not None and hasattr(request.app.state, "settings"):
        return request.app.state.settings
    return get_settings()


def _store(request: Request | None = None) -> FileStateStore:
    return FileStateStore(_settings(request))


def _orchestrator(request: Request | None = None) -> JobOrchestrator:
    return JobOrchestrator(store=_store(request))


@router.get("", response_model=list[JobRecord])
def list_jobs(request: Request) -> list[JobRecord]:
    return _store(request).list_jobs()


@router.post("", response_model=JobRecord, status_code=201)
def create_job(request: Request, payload: CreateJobRequest) -> JobRecord:
    return _store(request).create_job(payload)


@router.get("/{job_id}", response_model=JobRecord)
def get_job(job_id: str, request: Request) -> JobRecord:
    try:
        return _store(request).get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
def get_transcript(job_id: str, request: Request, speaker_attributed: bool = False) -> TranscriptResponse:
    artifact_kind = "speaker_transcript_text" if speaker_attributed else "transcript_text"
    try:
        artifact = _store(request).get_artifact(job_id, artifact_kind)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if artifact is None:
        detail = "Speaker-attributed transcript not found" if speaker_attributed else "Transcript not found"
        raise HTTPException(status_code=404, detail=detail)

    try:
        text = Path(artifact.path).read_text(encoding="utf-8")
    except OSError as exc:
        detail = "Speaker-attributed transcript not found" if speaker_attributed else "Transcript not found"
        raise HTTPException(status_code=404, detail=detail) from exc

    return TranscriptResponse(
        job_id=job_id,
        text=text,
        artifact_path=artifact.path,
        metadata=artifact.metadata,
    )


@router.get("/{job_id}/summary", response_model=SummaryResponse)
def get_summary(job_id: str, request: Request) -> SummaryResponse:
    try:
        artifact = _store(request).get_artifact(job_id, "summary_text")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if artifact is None:
        raise HTTPException(status_code=404, detail="Summary not found")

    try:
        text = Path(artifact.path).read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=404, detail="Summary not found") from exc

    return SummaryResponse(
        job_id=job_id,
        text=text,
        artifact_path=artifact.path,
        metadata=artifact.metadata,
    )


@router.post("/{job_id}/normalize", response_model=JobRecord)
def normalize_job(job_id: str, request: Request) -> JobRecord:
    try:
        return _orchestrator(request).normalize_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job or source file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/transcribe", response_model=JobRecord)
def transcribe_job(job_id: str, request: Request) -> JobRecord:
    try:
        return _orchestrator(request).transcribe_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job or source file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/summarize", response_model=JobRecord)
def summarize_job(job_id: str, request: Request) -> JobRecord:
    try:
        return _orchestrator(request).summarize_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job or source file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/process", response_model=JobRecord)
def process_job(job_id: str, request: Request) -> JobRecord:
    try:
        return _orchestrator(request).process_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job or source file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc