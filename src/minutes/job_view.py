from __future__ import annotations

from minutes.config import Settings
from minutes.pipeline import next_pending_stage
from minutes.storage.models import JobRecord, JobResponse


def to_job_response(job: JobRecord, settings: Settings) -> JobResponse:
    pending_stage = next_pending_stage(job, settings)
    return JobResponse(**job.model_dump(), next_stage=pending_stage)


def to_job_response_list(jobs: list[JobRecord], settings: Settings) -> list[JobResponse]:
    return [to_job_response(job, settings) for job in jobs]