from __future__ import annotations

from minutes.orchestrator import JobOrchestrator
from minutes.pipeline import next_pending_stage
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import JobRecord, JobStatus


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
            if next_pending_stage(job, self.store.settings) is not None:
                return job
        return None

    def run_once(self) -> JobRecord | None:
        next_job = self.next_actionable_job()
        if next_job is None:
            return None
        return self.orchestrator.process_job(next_job.job_id)
