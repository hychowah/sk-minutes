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


def _modelscope_cache_root() -> Path:
    return Path.home() / ".cache" / "modelscope" / "hub" / "models"


class SenseVoiceTranscriber:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = None
        self._ensure_ffmpeg_on_path()

    def transcribe_file(self, audio_path: Path | str, language: str | None = None) -> TranscriptionResult:
        source = Path(audio_path)
        if not source.exists():
            raise FileNotFoundError(source)

        return self._transcribe_input(str(source), language=language)

    def transcribe_waveform(self, waveform: Any, language: str | None = None) -> TranscriptionResult:
        return self._transcribe_input(waveform, language=language)

    def _transcribe_input(self, input_value: Any, language: str | None = None) -> TranscriptionResult:
        result = self._generate(input_value, language=language)
        return self._build_result(result, language=language)

    def _generate(self, input_value: Any, language: str | None = None) -> list[dict[str, Any]]:
        model = self._get_model()
        selected_language = language or self.settings.transcription_language

        try:
            result = model.generate(
                input=input_value,
                cache={},
                language=selected_language,
                use_itn=self.settings.transcription_use_itn,
                batch_size_s=self.settings.transcription_batch_size_s,
                merge_vad=self.settings.transcription_merge_vad,
                merge_length_s=self.settings.transcription_merge_length_s,
            )
        except Exception as exc:  # pragma: no cover - upstream exception types vary
            raise SenseVoiceError(str(exc)) from exc

        return result

    def _build_result(self, result: list[dict[str, Any]], language: str | None = None) -> TranscriptionResult:
        selected_language = language or self.settings.transcription_language
        processed_text = self._rich_postprocess(result[0]["text"] if result else "")

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
            self._model = AutoModel(**self._model_kwargs())
        except Exception as exc:  # pragma: no cover - model bootstrap failures vary by environment
            raise SenseVoiceError(str(exc)) from exc

        return self._model

    def _model_kwargs(self) -> dict[str, Any]:
        return {
            "model": self._resolve_model_reference(self.settings.sensevoice_model),
            "vad_model": self._resolve_model_reference(self.settings.sensevoice_vad_model),
            "vad_kwargs": {"max_single_segment_time": self.settings.transcription_max_single_segment_ms},
            "device": self._resolve_device(),
            "disable_update": True,
        }

    def _resolve_model_reference(self, model_name: str) -> str:
        model_path = Path(model_name)
        if model_path.exists():
            return str(model_path)

        try:
            from funasr.download.name_maps_from_hub import name_maps_ms
        except Exception:
            return model_name

        mapped_name = name_maps_ms.get(model_name, model_name)
        cached_path = _modelscope_cache_root() / Path(mapped_name)
        if cached_path.exists():
            return str(cached_path)

        return model_name

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