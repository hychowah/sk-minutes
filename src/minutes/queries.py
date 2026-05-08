from __future__ import annotations

from pathlib import Path

from minutes.pipeline import summary_is_current, summary_source_artifact
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import SummaryResponse, TranscriptResponse


class JobLookupError(FileNotFoundError):
    def __init__(self, job_id: str) -> None:
        super().__init__(job_id)
        self.job_id = job_id


class ArtifactLookupError(FileNotFoundError):
    def __init__(self, api_detail: str, cli_message: str) -> None:
        super().__init__(cli_message)
        self.api_detail = api_detail
        self.cli_message = cli_message


def get_transcript_response(
    store: FileStateStore,
    job_id: str,
    *,
    speaker_attributed: bool = False,
) -> TranscriptResponse:
    artifact_kind = "speaker_transcript_text" if speaker_attributed else "transcript_text"
    label = "Speaker-attributed transcript" if speaker_attributed else "Transcript"

    artifact = _get_artifact(store, job_id, artifact_kind)
    text = _read_artifact_text(artifact.path, api_detail=f"{label} not found", cli_message=f"{label} artifact not found for job {job_id}.")

    return TranscriptResponse(
        job_id=job_id,
        text=text,
        artifact_path=artifact.path,
        metadata=artifact.metadata,
    )


def get_summary_response(store: FileStateStore, job_id: str) -> SummaryResponse:
    try:
        job = store.get_job(job_id)
    except FileNotFoundError as exc:
        raise JobLookupError(job_id) from exc

    artifact = _get_artifact(store, job_id, "summary_text")
    text = _read_artifact_text(
        artifact.path,
        api_detail="Summary not found",
        cli_message=f"Summary artifact not found for job {job_id}.",
    )
    current_source = summary_source_artifact(job, store.settings)

    return SummaryResponse(
        job_id=job_id,
        text=text,
        artifact_path=artifact.path,
        metadata=artifact.metadata,
        source_current=None if current_source is None else summary_is_current(job, store.settings),
        current_source_artifact_kind=None if current_source is None else current_source.kind,
        current_source_artifact_path=None if current_source is None else current_source.path,
    )


def _get_artifact(store: FileStateStore, job_id: str, kind: str):
    try:
        artifact = store.get_artifact(job_id, kind)
    except FileNotFoundError as exc:
        raise JobLookupError(job_id) from exc

    if artifact is None:
        if kind == "summary_text":
            raise ArtifactLookupError(
                api_detail="Summary not found",
                cli_message=f"Summary artifact not found for job {job_id}.",
            )

        label = "Speaker-attributed transcript" if kind == "speaker_transcript_text" else "Transcript"
        raise ArtifactLookupError(
            api_detail=f"{label} not found",
            cli_message=f"{label} artifact not found for job {job_id}.",
        )

    return artifact


def _read_artifact_text(path: str, *, api_detail: str, cli_message: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactLookupError(api_detail=api_detail, cli_message=cli_message) from exc