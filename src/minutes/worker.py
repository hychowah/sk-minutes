from __future__ import annotations

from minutes.orchestrator import JobOrchestrator
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import ArtifactRecord, JobRecord, JobStatus


class JobWorker:
    def __init__(
        self,
        store: FileStateStore | None = None,
        orchestrator: JobOrchestrator | None = None,
    ) -> None:
        self.store = store or FileStateStore()
        self.orchestrator = orchestrator or JobOrchestrator(store=self.store)

    def next_actionable_job(self) -> JobRecord | None:
        for job in self.store.list_jobs():
            if job.status in {JobStatus.FAILED, JobStatus.CANCELLED}:
                continue
            if job.source_path and self._artifact(job, "transcript_text") is None:
                return job
            if self.store.settings.diarization_enabled and self._artifact(job, "diarization_json") is None:
                return job
            if self.store.settings.diarization_enabled and self._artifact(job, "speaker_transcript_text") is None:
                return job
        return None

    def run_once(self) -> JobRecord | None:
        next_job = self.next_actionable_job()
        if next_job is None:
            return None
        return self.orchestrator.process_job(next_job.job_id)

    @staticmethod
    def _artifact(job: JobRecord, kind: str) -> ArtifactRecord | None:
        for artifact in job.artifacts:
            if artifact.kind == kind:
                return artifact
        return None