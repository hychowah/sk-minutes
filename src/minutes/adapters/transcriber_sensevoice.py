from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

from minutes.config import Settings, get_settings


class SenseVoiceError(RuntimeError):
    """Raised when SenseVoice/FunASR transcription fails."""


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    raw_segments: list[dict[str, Any]]
    model_name: str
    device: str
    language: str


class SenseVoiceTranscriber:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = None
        self._ensure_ffmpeg_on_path()

    def transcribe_file(self, audio_path: Path | str, language: str | None = None) -> TranscriptionResult:
        source = Path(audio_path)
        if not source.exists():
            raise FileNotFoundError(source)

        model = self._get_model()
        selected_language = language or self.settings.transcription_language

        try:
            result = model.generate(
                input=str(source),
                cache={},
                language=selected_language,
                use_itn=self.settings.transcription_use_itn,
                batch_size_s=self.settings.transcription_batch_size_s,
                merge_vad=self.settings.transcription_merge_vad,
                merge_length_s=self.settings.transcription_merge_length_s,
            )
            processed_text = self._rich_postprocess(result[0]["text"] if result else "")
        except Exception as exc:  # pragma: no cover - upstream exception types vary
            raise SenseVoiceError(str(exc)) from exc

        return TranscriptionResult(
            text=processed_text,
            raw_segments=result,
            model_name=self.settings.sensevoice_model,
            device=self._resolve_device(),
            language=selected_language,
        )

    def _get_model(self):
        if self._model is not None:
            return self._model

        try:
            from funasr import AutoModel
        except Exception as exc:  # pragma: no cover - import failures depend on environment
            raise SenseVoiceError("FunASR is not available in the current environment.") from exc

        try:
            self._model = AutoModel(
                model=self.settings.sensevoice_model,
                vad_model=self.settings.sensevoice_vad_model,
                vad_kwargs={"max_single_segment_time": self.settings.transcription_max_single_segment_ms},
                device=self._resolve_device(),
            )
        except Exception as exc:  # pragma: no cover - model bootstrap failures vary by environment
            raise SenseVoiceError(str(exc)) from exc

        return self._model

    @staticmethod
    def _rich_postprocess(text: str) -> str:
        try:
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
        except Exception as exc:  # pragma: no cover - import failures depend on environment
            raise SenseVoiceError("FunASR post-processing utilities are not available.") from exc
        return rich_transcription_postprocess(text)

    def _resolve_device(self) -> str:
        configured = self.settings.transcription_device
        if configured != "auto":
            return configured

        try:
            import torch
        except Exception:
            return "cpu"

        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def _ensure_ffmpeg_on_path(self) -> None:
        ffmpeg_dir = str(self.settings.ffmpeg_bin.parent)
        current_path = os.environ.get("PATH", "")
        path_parts = current_path.split(os.pathsep) if current_path else []
        if ffmpeg_dir not in path_parts:
            os.environ["PATH"] = os.pathsep.join([ffmpeg_dir, *path_parts]) if path_parts else ffmpeg_dir