from __future__ import annotations

from minutes.config import Settings
from minutes.pipeline import next_pending_stage, summary_state, workflow_progress_stage
from minutes.storage.models import JobRecord, JobResponse


def to_job_response(job: JobRecord, settings: Settings) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        workflow_stage=workflow_progress_stage(job, settings),
        summary_state=summary_state(job, settings),
        source_path=job.source_path,
        transcription_language=job.transcription_language,
        summary_language=job.summary_language,
        created_at=job.created_at,
        updated_at=job.updated_at,
        artifacts=job.artifacts,
        error_message=job.error_message,
        next_stage=next_pending_stage(job, settings),
    )


def to_job_response_list(jobs: list[JobRecord], settings: Settings) -> list[JobResponse]:
    return [to_job_response(job, settings) for job in jobs]