from __future__ import annotations

from enum import StrEnum

from minutes.config import Settings
from minutes.storage.models import ArtifactRecord, JobRecord


class StageName(StrEnum):
	CREATED = "created"
	NORMALIZE = "normalize"
	NORMALIZED = "normalized"
	TRANSCRIBE = "transcribe"
	TRANSCRIBED = "transcribed"
	DIARIZE = "diarize"
	DIARIZED = "diarized"
	ASSEMBLE_SPEAKERS = "assemble_speakers"
	SPEAKER_ATTRIBUTED = "speaker_attributed"
	SUMMARIZE = "summarize"
	SUMMARIZED = "summarized"


def next_pending_stage(job: JobRecord, settings: Settings) -> StageName | None:
	if job.source_path and artifact(job, "normalized_audio") is None:
		return StageName.NORMALIZE
	if artifact(job, "normalized_audio") is not None and artifact(job, "transcript_text") is None:
		return StageName.TRANSCRIBE
	if settings.diarization_enabled and artifact(job, "normalized_audio") is not None and artifact(job, "diarization_json") is None:
		return StageName.DIARIZE
	if (
		settings.diarization_enabled
		and artifact(job, "normalized_audio") is not None
		and artifact(job, "transcript_text") is not None
		and artifact(job, "diarization_json") is not None
		and artifact(job, "speaker_transcript_text") is None
	):
		return StageName.ASSEMBLE_SPEAKERS
	if settings.summary_configured and _has_summary_source(job, settings) and not summary_is_current(job, settings):
		return StageName.SUMMARIZE
	return None


def artifact(job: JobRecord, kind: str) -> ArtifactRecord | None:
	for existing in job.artifacts:
		if existing.kind == kind:
			return existing
	return None


def _has_summary_source(job: JobRecord, settings: Settings) -> bool:
	return summary_source_artifact(job, settings) is not None


def summary_source_artifact(job: JobRecord, settings: Settings) -> ArtifactRecord | None:
	if artifact(job, "speaker_transcript_text") is not None:
		return artifact(job, "speaker_transcript_text")
	if settings.diarization_enabled:
		return None
	return artifact(job, "transcript_text")


def summary_is_current(job: JobRecord, settings: Settings) -> bool:
	summary_artifact = artifact(job, "summary_text")
	if summary_artifact is None:
		return False

	current_source = summary_source_artifact(job, settings)
	if current_source is None:
		return True

	metadata = summary_artifact.metadata
	return (
		metadata.get("source_artifact_kind") == current_source.kind
		and metadata.get("source_artifact_path") == current_source.path
		and metadata.get("source_artifact_created_at") == current_source.created_at.isoformat()
	)


__all__ = ["StageName", "artifact", "next_pending_stage", "summary_is_current", "summary_source_artifact"]
"""Pipeline stages for the Minutes application."""