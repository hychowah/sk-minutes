from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

from minutes.adapters.diarizer_pyannote import PyannoteDiarizationError, PyannoteDiarizer
from minutes.adapters.ffmpeg import FfmpegAdapter, FfmpegError
from minutes.adapters.summarizer_openai_compatible import OpenAICompatibleSummarizer, OpenAICompatibleSummaryError
from minutes.adapters.transcriber_sensevoice import SenseVoiceError, SenseVoiceTranscriber
from minutes.pipeline import StageName, next_pending_stage
from minutes.storage.file_store import FileStateStore
from minutes.storage.models import ArtifactRecord, JobRecord, JobStatus


class JobOrchestrator:
    def __init__(
        self,
        store: FileStateStore | None = None,
        ffmpeg: FfmpegAdapter | None = None,
        transcriber: SenseVoiceTranscriber | None = None,
        diarizer: PyannoteDiarizer | None = None,
        summarizer: OpenAICompatibleSummarizer | None = None,
    ) -> None:
        self.store = store or FileStateStore()
        self.ffmpeg = ffmpeg or FfmpegAdapter(self.store.settings)
        self.transcriber = transcriber or SenseVoiceTranscriber(self.store.settings)
        self.diarizer = diarizer or PyannoteDiarizer(self.store.settings)
        self.summarizer = summarizer or OpenAICompatibleSummarizer(self.store.settings)

    def process_job(self, job_id: str) -> JobRecord:
        job = self.store.get_job(job_id)
        while True:
            pending_stage = next_pending_stage(job, self.store.settings)
            if pending_stage is None:
                return job
            if pending_stage == StageName.NORMALIZE:
                job = self.normalize_job(job_id)
            elif pending_stage == StageName.TRANSCRIBE:
                job = self.transcribe_job(job_id)
            elif pending_stage == StageName.DIARIZE:
                job = self.diarize_job(job_id)
            elif pending_stage == StageName.ASSEMBLE_SPEAKERS:
                job = self.assemble_speaker_transcript_job(job_id)
            elif pending_stage == StageName.SUMMARIZE:
                job = self.summarize_job(job_id)
            else:
                return job

            if job.status == JobStatus.FAILED:
                return job
        return job

    def normalize_job(self, job_id: str) -> JobRecord:
        job = self.store.get_job(job_id)
        if not job.source_path:
            raise ValueError("Job source_path is required before normalization.")

        source_path = Path(job.source_path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)

        running_job = self._mark_running(job, StageName.NORMALIZE)

        try:
            artifacts_root = self.store.artifacts_root(job_id)
            probe_result = self.ffmpeg.probe(source_path)
            probe_path = artifacts_root / "probe.json"
            probe_path.write_text(json.dumps(probe_result.raw, indent=2), encoding="utf-8")

            normalized_path = artifacts_root / "normalized.wav"
            self.ffmpeg.normalize_to_wav(source_path, normalized_path)

            staged_job = self.store.replace_artifact(
                running_job,
                ArtifactRecord(
                    kind="probe",
                    path=str(probe_path),
                    metadata={
                        "format_name": probe_result.format_name,
                        "duration_seconds": probe_result.duration_seconds,
                    },
                ),
            )
            staged_job = self.store.replace_artifact(
                staged_job,
                ArtifactRecord(
                    kind="normalized_audio",
                    path=str(normalized_path),
                    metadata={
                        "sample_rate": 16000,
                        "channels": 1,
                        "codec": "pcm_s16le",
                    },
                ),
            )

            return self._complete_stage(staged_job, StageName.NORMALIZED)
        except (FfmpegError, OSError, json.JSONDecodeError) as exc:
            return self._fail_stage(running_job, StageName.NORMALIZE, exc)

    def transcribe_job(self, job_id: str) -> JobRecord:
        job = self.store.get_job(job_id)
        normalized_audio = self._artifact(job, "normalized_audio")
        if normalized_audio is None:
            job = self.normalize_job(job_id)
            if job.status == JobStatus.FAILED:
                return job
            normalized_audio = self._artifact(job, "normalized_audio")
        if normalized_audio is None:
            raise ValueError("Normalized audio artifact is required before transcription.")

        running_job = self._mark_running(job, StageName.TRANSCRIBE)

        try:
            artifacts_root = self.store.artifacts_root(job_id)
            result = self.transcriber.transcribe_file(
                normalized_audio.path,
                language=job.transcription_language,
            )
            transcript_json_path = artifacts_root / "transcript.json"
            transcript_json_path.write_text(
                json.dumps(result.raw_segments, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            transcript_text_path = artifacts_root / "transcript.txt"
            transcript_text_path.write_text(result.text, encoding="utf-8")

            staged_job = self.store.replace_artifact(
                running_job,
                ArtifactRecord(
                    kind="transcript_json",
                    path=str(transcript_json_path),
                    metadata={
                        "model_name": result.model_name,
                        "device": result.device,
                        "language": result.language,
                    },
                ),
            )
            staged_job = self.store.replace_artifact(
                staged_job,
                ArtifactRecord(
                    kind="transcript_text",
                    path=str(transcript_text_path),
                    metadata={
                        "model_name": result.model_name,
                        "device": result.device,
                        "language": result.language,
                    },
                ),
            )

            return self._complete_stage(staged_job, StageName.TRANSCRIBED)
        except (SenseVoiceError, OSError) as exc:
            return self._fail_stage(running_job, StageName.TRANSCRIBE, exc)

    def diarize_job(self, job_id: str) -> JobRecord:
        if not self.store.settings.diarization_enabled:
            raise ValueError("Diarization is disabled. Set MINUTES_DIARIZATION_ENABLED=1 to enable it.")

        job = self.store.get_job(job_id)
        normalized_audio = self._artifact(job, "normalized_audio")
        if normalized_audio is None:
            job = self.normalize_job(job_id)
            if job.status == JobStatus.FAILED:
                return job
            normalized_audio = self._artifact(job, "normalized_audio")
        if normalized_audio is None:
            raise ValueError("Normalized audio artifact is required before diarization.")

        running_job = self._mark_running(job, StageName.DIARIZE)

        try:
            artifacts_root = self.store.artifacts_root(job_id)
            result = self.diarizer.diarize_file(normalized_audio.path)
            diarization_json_path = artifacts_root / "diarization.json"
            diarization_payload = [
                {
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "speaker": segment.speaker,
                }
                for segment in result.segments
            ]
            diarization_json_path.write_text(
                json.dumps(diarization_payload, indent=2),
                encoding="utf-8",
            )

            diarization_rttm_path = artifacts_root / "diarization.rttm"
            rttm_lines = [
                "SPEAKER {job_id} 1 {start:.3f} {duration:.3f} <NA> <NA> {speaker} <NA> <NA>".format(
                    job_id=job_id,
                    start=segment.start_seconds,
                    duration=max(segment.end_seconds - segment.start_seconds, 0.0),
                    speaker=segment.speaker,
                )
                for segment in result.segments
            ]
            diarization_rttm_path.write_text("\n".join(rttm_lines) + ("\n" if rttm_lines else ""), encoding="utf-8")

            staged_job = self.store.replace_artifact(
                running_job,
                ArtifactRecord(
                    kind="diarization_json",
                    path=str(diarization_json_path),
                    metadata={
                        "model_name": result.model_name,
                        "device": result.device,
                        "segment_count": len(result.segments),
                    },
                ),
            )
            staged_job = self.store.replace_artifact(
                staged_job,
                ArtifactRecord(
                    kind="diarization_rttm",
                    path=str(diarization_rttm_path),
                    metadata={
                        "model_name": result.model_name,
                        "device": result.device,
                        "segment_count": len(result.segments),
                    },
                ),
            )

            return self._complete_stage(staged_job, StageName.DIARIZED)
        except (PyannoteDiarizationError, OSError) as exc:
            return self._fail_stage(running_job, StageName.DIARIZE, exc)

    def assemble_speaker_transcript_job(self, job_id: str) -> JobRecord:
        if not self.store.settings.diarization_enabled:
            raise ValueError("Speaker transcript assembly requires diarization to be enabled.")

        job = self.store.get_job(job_id)
        normalized_audio = self._artifact(job, "normalized_audio")
        transcript_text = self._artifact(job, "transcript_text")
        diarization_json = self._artifact(job, "diarization_json")
        if normalized_audio is None:
            job = self.normalize_job(job_id)
            if job.status == JobStatus.FAILED:
                return job
            normalized_audio = self._artifact(job, "normalized_audio")
        if transcript_text is None:
            job = self.transcribe_job(job_id)
            if job.status == JobStatus.FAILED:
                return job
            transcript_text = self._artifact(job, "transcript_text")
        if diarization_json is None:
            job = self.diarize_job(job_id)
            if job.status == JobStatus.FAILED:
                return job
            diarization_json = self._artifact(job, "diarization_json")

        if normalized_audio is None or transcript_text is None or diarization_json is None:
            raise ValueError("Normalized audio, transcript, and diarization artifacts are required before speaker transcript assembly.")

        running_job = self._mark_running(job, StageName.ASSEMBLE_SPEAKERS)

        try:
            artifacts_root = self.store.artifacts_root(job_id)
            assembly_payload = self._build_speaker_transcript_payload(
                normalized_audio_path=Path(normalized_audio.path),
                diarization_json_path=Path(diarization_json.path),
                temp_root=artifacts_root / "speaker_segments",
            )
            speaker_transcript_json_path = artifacts_root / "speaker_transcript.json"
            speaker_transcript_json_path.write_text(
                json.dumps(assembly_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            speaker_transcript_text_path = artifacts_root / "speaker_transcript.txt"
            speaker_transcript_text_path.write_text(
                self._render_speaker_transcript(assembly_payload),
                encoding="utf-8",
            )

            speaker_count = len({entry["speaker"] for entry in assembly_payload})
            transcription_model_name = getattr(
                getattr(self.transcriber, "settings", None),
                "sensevoice_model",
                "unknown",
            )
            diarization_model_name = getattr(
                getattr(self.diarizer, "settings", None),
                "pyannote_model",
                "unknown",
            )
            staged_job = self.store.replace_artifact(
                running_job,
                ArtifactRecord(
                    kind="speaker_transcript_json",
                    path=str(speaker_transcript_json_path),
                    metadata={
                        "transcription_model": transcription_model_name,
                        "diarization_model": diarization_model_name,
                        "segment_count": len(assembly_payload),
                        "speaker_count": speaker_count,
                    },
                ),
            )
            staged_job = self.store.replace_artifact(
                staged_job,
                ArtifactRecord(
                    kind="speaker_transcript_text",
                    path=str(speaker_transcript_text_path),
                    metadata={
                        "transcription_model": transcription_model_name,
                        "diarization_model": diarization_model_name,
                        "segment_count": len(assembly_payload),
                        "speaker_count": speaker_count,
                    },
                ),
            )

            return self._complete_stage(staged_job, StageName.SPEAKER_ATTRIBUTED)
        except (OSError, ValueError, json.JSONDecodeError, SenseVoiceError) as exc:
            return self._fail_stage(running_job, StageName.ASSEMBLE_SPEAKERS, exc)

    def summarize_job(self, job_id: str) -> JobRecord:
        if not self.store.settings.summary_configured:
            raise ValueError("Summary backend is not configured.")

        job = self.store.get_job(job_id)
        if self.store.settings.diarization_enabled and self._artifact(job, "speaker_transcript_text") is None:
            job = self.assemble_speaker_transcript_job(job_id)
            if job.status == JobStatus.FAILED:
                return job
        if self._artifact(job, "transcript_text") is None:
            job = self.transcribe_job(job_id)
            if job.status == JobStatus.FAILED:
                return job

        source_artifact = self._summary_source_artifact(job)
        if source_artifact is None:
            raise ValueError("Transcript artifact is required before summarization.")

        running_job = self._mark_running(job, StageName.SUMMARIZE)

        try:
            source_text = Path(source_artifact.path).read_text(encoding="utf-8")
            summary_language = self._resolve_summary_language(running_job)
            started_at = perf_counter()
            result = self.summarizer.summarize_text(source_text, summary_language=summary_language)
            summary_elapsed_ms = round((perf_counter() - started_at) * 1000, 3)

            artifacts_root = self.store.artifacts_root(job_id)
            summary_json_path = artifacts_root / "summary.json"
            summary_payload = {
                "summary": result.structured_data["summary"],
                "key_points": result.structured_data["key_points"],
                "decisions": result.structured_data["decisions"],
                "action_items": result.structured_data["action_items"],
                "risks": result.structured_data["risks"],
            }
            summary_json_path.write_text(
                json.dumps(summary_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            summary_text_path = artifacts_root / "summary.txt"
            summary_text_path.write_text(result.text, encoding="utf-8")

            metadata = {
                "source_artifact_kind": source_artifact.kind,
                "source_artifact_path": source_artifact.path,
                "source_artifact_created_at": source_artifact.created_at.isoformat(),
                "provider_base_url": result.base_url,
                "model_name": result.model_name,
                "prompt_version": result.prompt_version,
                "summary_language": result.summary_language,
                "summary_elapsed_ms": summary_elapsed_ms,
                "summary_timeout_seconds": self.store.settings.summary_timeout_seconds,
                "summary_max_retries": self.store.settings.summary_max_retries,
            }
            staged_job = self.store.replace_artifact(
                running_job,
                ArtifactRecord(
                    kind="summary_json",
                    path=str(summary_json_path),
                    metadata=metadata,
                ),
            )
            staged_job = self.store.replace_artifact(
                staged_job,
                ArtifactRecord(
                    kind="summary_text",
                    path=str(summary_text_path),
                    metadata=metadata,
                ),
            )

            return self._complete_stage(staged_job, StageName.SUMMARIZED)
        except (OpenAICompatibleSummaryError, OSError, ValueError) as exc:
            return self._fail_stage(running_job, StageName.SUMMARIZE, exc)

    def _mark_running(self, job: JobRecord, active_stage: StageName) -> JobRecord:
        running_job = job.model_copy(
            update={
                "status": JobStatus.RUNNING,
                "workflow_stage": self._workflow_stage(job),
                "current_stage": active_stage,
                "error_message": None,
            }
        )
        return self.store.save_job(running_job)

    def _complete_stage(self, job: JobRecord, completed_stage: StageName) -> JobRecord:
        completed_job = job.model_copy(
            update={
                "workflow_stage": completed_stage,
                "error_message": None,
            }
        )
        pending_stage = next_pending_stage(completed_job, self.store.settings)
        completed_job = completed_job.model_copy(
            update={
                "status": JobStatus.COMPLETED if pending_stage is None else JobStatus.QUEUED,
                "current_stage": completed_stage if pending_stage is None else pending_stage,
            }
        )
        return self.store.save_job(completed_job)

    def _fail_stage(self, job: JobRecord, failed_stage: StageName, exc: Exception) -> JobRecord:
        failed_job = job.model_copy(
            update={
                "status": JobStatus.FAILED,
                "workflow_stage": self._workflow_stage(job),
                "current_stage": failed_stage,
                "error_message": str(exc),
            }
        )
        return self.store.save_job(failed_job)

    @staticmethod
    def _workflow_stage(job: JobRecord) -> str | None:
        return job.workflow_stage or job.current_stage

    def _build_speaker_transcript_payload(
        self,
        normalized_audio_path: Path,
        diarization_json_path: Path,
        temp_root: Path,
    ) -> list[dict[str, object]]:
        diarization_segments = json.loads(diarization_json_path.read_text(encoding="utf-8"))
        merged_segments = self._merge_diarization_segments(diarization_segments)
        if not merged_segments:
            return []

        try:
            import numpy as np
            import soundfile
        except Exception as exc:  # pragma: no cover - dependency availability varies by environment
            raise ValueError("soundfile and numpy are required for speaker transcript assembly.") from exc

        waveform, sample_rate = soundfile.read(str(normalized_audio_path), always_2d=True)
        if waveform.size == 0:
            return []

        waveform = np.asarray(waveform, dtype=np.float32)
        temp_root.mkdir(parents=True, exist_ok=True)

        payload: list[dict[str, object]] = []
        for index, segment in enumerate(merged_segments, start=1):
            clip_start_seconds, clip_end_seconds = self._clip_bounds_for_transcription(
                start_seconds=float(segment["start_seconds"]),
                end_seconds=float(segment["end_seconds"]),
                max_seconds=len(waveform) / sample_rate,
            )
            start_frame = max(int(clip_start_seconds * sample_rate), 0)
            end_frame = min(int(clip_end_seconds * sample_rate), len(waveform))
            if end_frame <= start_frame:
                continue

            clip = waveform[start_frame:end_frame]
            if clip.size == 0:
                continue

            transcription = self._transcribe_speaker_clip(
                clip=clip,
                sample_rate=sample_rate,
                temp_root=temp_root,
                index=index,
                speaker=str(segment["speaker"]),
            )

            text = transcription.text.strip()
            if not text:
                continue

            payload.append(
                {
                    "speaker": segment["speaker"],
                    "start_seconds": segment["start_seconds"],
                    "end_seconds": segment["end_seconds"],
                    "source_segment_count": segment["source_segment_count"],
                    "text": text,
                }
            )

        return payload

    @staticmethod
    def _clip_input(clip):
        if clip.ndim == 2 and clip.shape[1] == 1:
            return clip[:, 0]
        return clip

    def _transcribe_speaker_clip(
        self,
        *,
        clip,
        sample_rate: int,
        temp_root: Path,
        index: int,
        speaker: str,
    ):
        try:
            clip_input = self._clip_input(clip)
            return self.transcriber.transcribe_waveform(clip_input)
        except (AttributeError, SenseVoiceError, ValueError, RuntimeError):
            temp_root.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=temp_root, prefix=f"{index:03d}_{speaker}_", suffix=".wav", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            try:
                import soundfile

                soundfile.write(str(temp_path), clip, sample_rate)
                return self.transcriber.transcribe_file(temp_path)
            finally:
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def _clip_bounds_for_transcription(
        start_seconds: float,
        end_seconds: float,
        max_seconds: float,
        min_duration_seconds: float = 1.0,
    ) -> tuple[float, float]:
        clip_start_seconds = max(start_seconds, 0.0)
        clip_end_seconds = min(end_seconds, max_seconds)
        clip_duration = clip_end_seconds - clip_start_seconds
        if clip_duration >= min_duration_seconds:
            return clip_start_seconds, clip_end_seconds

        padding = (min_duration_seconds - clip_duration) / 2
        clip_start_seconds = max(clip_start_seconds - padding, 0.0)
        clip_end_seconds = min(clip_end_seconds + padding, max_seconds)

        if clip_end_seconds - clip_start_seconds < min_duration_seconds:
            clip_start_seconds = max(clip_end_seconds - min_duration_seconds, 0.0)
            clip_end_seconds = min(clip_start_seconds + min_duration_seconds, max_seconds)

        return clip_start_seconds, clip_end_seconds

    @staticmethod
    def _merge_diarization_segments(
        diarization_segments: list[dict[str, object]],
        max_gap_seconds: float = 0.35,
    ) -> list[dict[str, object]]:
        merged: list[dict[str, object]] = []
        ordered_segments = sorted(
            diarization_segments,
            key=lambda segment: (float(segment["start_seconds"]), float(segment["end_seconds"])),
        )

        for segment in ordered_segments:
            start_seconds = float(segment["start_seconds"])
            end_seconds = float(segment["end_seconds"])
            speaker = str(segment["speaker"])
            if end_seconds <= start_seconds:
                continue

            if (
                merged
                and merged[-1]["speaker"] == speaker
                and start_seconds - float(merged[-1]["end_seconds"]) <= max_gap_seconds
            ):
                merged[-1]["end_seconds"] = max(float(merged[-1]["end_seconds"]), end_seconds)
                merged[-1]["source_segment_count"] = int(merged[-1]["source_segment_count"]) + 1
                continue

            merged.append(
                {
                    "speaker": speaker,
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "source_segment_count": 1,
                }
            )

        return merged

    @classmethod
    def _render_speaker_transcript(cls, payload: list[dict[str, object]]) -> str:
        blocks: list[str] = []
        for entry in payload:
            header = "[{speaker} | {start} -> {end}]".format(
                speaker=entry["speaker"],
                start=cls._format_timestamp(float(entry["start_seconds"])),
                end=cls._format_timestamp(float(entry["end_seconds"])),
            )
            blocks.append(f"{header}\n{entry['text']}")
        return "\n\n".join(blocks)

    @staticmethod
    def _format_timestamp(total_seconds: float) -> str:
        whole_seconds = max(int(total_seconds), 0)
        hours, remainder = divmod(whole_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _artifact(job: JobRecord, kind: str) -> ArtifactRecord | None:
        for artifact in job.artifacts:
            if artifact.kind == kind:
                return artifact
        return None

    def _summary_source_artifact(self, job: JobRecord) -> ArtifactRecord | None:
        speaker_transcript = self._artifact(job, "speaker_transcript_text")
        if speaker_transcript is not None:
            return speaker_transcript
        return self._artifact(job, "transcript_text")

    def _resolve_summary_language(self, job: JobRecord) -> str:
        if job.summary_language:
            return job.summary_language

        transcript_artifact = self._artifact(job, "transcript_text")
        if transcript_artifact is not None:
            language = transcript_artifact.metadata.get("language")
            if isinstance(language, str) and language.strip() and language != "auto":
                return language

        if job.transcription_language and job.transcription_language != "auto":
            return job.transcription_language
        if self.store.settings.transcription_language != "auto":
            return self.store.settings.transcription_language
        return "match-transcript"