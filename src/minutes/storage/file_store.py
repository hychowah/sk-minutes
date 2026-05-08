from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from minutes.config import Settings, get_settings
from minutes.storage.models import ArtifactRecord, CreateJobRequest, JobRecord, utc_now


class FileStateStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.jobs_root = self.settings.data_root / "jobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)

    def job_root(self, job_id: str) -> Path:
        return self.jobs_root / job_id

    def artifacts_root(self, job_id: str) -> Path:
        root = self.job_root(job_id) / "artifacts"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def list_jobs(self) -> list[JobRecord]:
        jobs = [self._read_job(job_file) for job_file in self.jobs_root.glob("*/job.json")]
        jobs.sort(key=lambda job: (job.updated_at, job.created_at, job.job_id), reverse=True)
        return jobs

    def create_job(self, request: CreateJobRequest | None = None) -> JobRecord:
        payload = request or CreateJobRequest()
        job = JobRecord(
            job_id=uuid4().hex,
            workflow_stage="created",
            source_path=payload.source_path,
            transcription_language=payload.language,
            summary_language=payload.summary_language,
            current_stage="created",
        )
        return self.save_job(job)

    def get_job(self, job_id: str) -> JobRecord:
        return self._read_job(self._job_file(job_id))

    def save_job(self, job: JobRecord) -> JobRecord:
        stored_job = job.model_copy(update={"updated_at": utc_now()})
        job_file = self._job_file(stored_job.job_id)
        job_file.parent.mkdir(parents=True, exist_ok=True)
        job_file.write_text(stored_job.model_dump_json(indent=2), encoding="utf-8")
        return stored_job

    def replace_artifact(self, job: JobRecord, artifact: ArtifactRecord) -> JobRecord:
        artifacts = [existing for existing in job.artifacts if existing.kind != artifact.kind]
        artifacts.append(artifact)
        return job.model_copy(update={"artifacts": artifacts})

    def get_artifact(self, job_id: str, kind: str) -> ArtifactRecord | None:
        job = self.get_job(job_id)
        for artifact in job.artifacts:
            if artifact.kind == kind:
                return artifact
        return None

    def _job_file(self, job_id: str) -> Path:
        return self.job_root(job_id) / "job.json"

    @staticmethod
    def _read_job(path: Path) -> JobRecord:
        return JobRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))