from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactRecord(BaseModel):
    kind: str
    path: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class JobRecord(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    workflow_stage: str | None = None
    current_stage: str | None = None
    source_path: str | None = None
    transcription_language: str | None = None
    summary_language: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    error_message: str | None = None


class JobResponse(JobRecord):
    next_stage: str | None = None


class CreateJobRequest(BaseModel):
    source_path: str | None = None
    language: str | None = None
    summary_language: str | None = None


class TranscriptResponse(BaseModel):
    job_id: str
    text: str
    artifact_path: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class SummaryResponse(BaseModel):
    job_id: str
    text: str
    artifact_path: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    source_current: bool | None = None
    current_source_artifact_kind: str | None = None
    current_source_artifact_path: str | None = None