from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from minutes.config import Settings, get_settings
from minutes.job_view import to_job_response, to_job_response_list
from minutes.orchestrator import JobOrchestrator
from minutes.queries import ArtifactLookupError, JobLookupError, get_summary_response, get_transcript_response
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import CreateJobRequest, JobRecord, JobResponse, SummaryResponse, TranscriptResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _settings(request: Request | None = None) -> Settings:
    if request is not None and hasattr(request.app.state, "settings"):
        return request.app.state.settings
    return get_settings()


def _store(request: Request | None = None) -> FileStateStore:
    if request is not None and hasattr(request.app.state, "store"):
        return request.app.state.store
    return FileStateStore(_settings(request))


def _orchestrator(request: Request | None = None) -> JobOrchestrator:
    if request is not None and hasattr(request.app.state, "orchestrator"):
        return request.app.state.orchestrator
    return JobOrchestrator(store=_store(request))


@router.get("", response_model=list[JobResponse])
def list_jobs(request: Request) -> list[JobResponse]:
    settings = _settings(request)
    return to_job_response_list(_store(request).list_jobs(), settings)


@router.post("", response_model=JobResponse, status_code=201)
def create_job(request: Request, payload: CreateJobRequest) -> JobResponse:
    if payload.source_path is None or not payload.source_path.strip():
        raise HTTPException(status_code=400, detail="source_path is required when creating a job through the API")
    job = _store(request).create_job(payload)
    return to_job_response(job, _settings(request))


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, request: Request) -> JobResponse:
    try:
        job = _store(request).get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return to_job_response(job, _settings(request))


@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
def get_transcript(job_id: str, request: Request, speaker_attributed: bool = False) -> TranscriptResponse:
    try:
        return get_transcript_response(_store(request), job_id, speaker_attributed=speaker_attributed)
    except JobLookupError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except ArtifactLookupError as exc:
        raise HTTPException(status_code=404, detail=exc.api_detail) from exc


@router.get("/{job_id}/summary", response_model=SummaryResponse)
def get_summary(job_id: str, request: Request) -> SummaryResponse:
    try:
        return get_summary_response(_store(request), job_id)
    except JobLookupError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except ArtifactLookupError as exc:
        raise HTTPException(status_code=404, detail=exc.api_detail) from exc


@router.post("/{job_id}/normalize", response_model=JobResponse)
def normalize_job(job_id: str, request: Request) -> JobResponse:
    try:
        job = _orchestrator(request).normalize_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job or source file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_job_response(job, _settings(request))


@router.post("/{job_id}/transcribe", response_model=JobResponse)
def transcribe_job(job_id: str, request: Request) -> JobResponse:
    try:
        job = _orchestrator(request).transcribe_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job or source file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_job_response(job, _settings(request))


@router.post("/{job_id}/summarize", response_model=JobResponse)
def summarize_job(job_id: str, request: Request) -> JobResponse:
    try:
        job = _orchestrator(request).summarize_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job or source file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_job_response(job, _settings(request))


@router.post("/{job_id}/process", response_model=JobResponse)
def process_job(job_id: str, request: Request) -> JobResponse:
    try:
        job = _orchestrator(request).process_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job or source file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_job_response(job, _settings(request))