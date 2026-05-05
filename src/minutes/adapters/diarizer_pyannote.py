from __future__ import annotations

from dataclasses import dataclass as std_dataclass
from dataclasses import dataclass
import inspect
import os
from pathlib import Path

import numpy as np

from minutes.config import Settings, get_settings


class PyannoteDiarizationError(RuntimeError):
    """Raised when pyannote diarization fails or is unavailable."""


@dataclass(slots=True)
class DiarizationSegment:
    start_seconds: float
    end_seconds: float
    speaker: str


@dataclass(slots=True)
class DiarizationResult:
    segments: list[DiarizationSegment]
    model_name: str
    device: str


class PyannoteDiarizer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._pipeline = None
        if not self.settings.pyannote_metrics_enabled:
            os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")

    def diarize_file(self, audio_path: Path | str) -> DiarizationResult:
        source = Path(audio_path)
        if not source.exists():
            raise FileNotFoundError(source)
        if not self.settings.pyannote_auth_token:
            raise PyannoteDiarizationError(
                "MINUTES_PYANNOTE_AUTH_TOKEN is required before diarization can run. "
                "Accept the pyannote model conditions on Hugging Face first."
            )

        pipeline = self._get_pipeline()
        diarization_kwargs: dict[str, int] = {}
        if self.settings.diarization_num_speakers is not None:
            diarization_kwargs["num_speakers"] = self.settings.diarization_num_speakers
        if self.settings.diarization_min_speakers is not None:
            diarization_kwargs["min_speakers"] = self.settings.diarization_min_speakers
        if self.settings.diarization_max_speakers is not None:
            diarization_kwargs["max_speakers"] = self.settings.diarization_max_speakers

        try:
            diarization = pipeline(self._load_audio_payload(source), **diarization_kwargs)
        except Exception as exc:  # pragma: no cover - upstream exception types vary
            raise PyannoteDiarizationError(str(exc)) from exc

        segments = [
            DiarizationSegment(
                start_seconds=float(turn.start),
                end_seconds=float(turn.end),
                speaker=str(speaker),
            )
            for turn, _, speaker in diarization.itertracks(yield_label=True)
        ]
        segments.sort(key=lambda item: (item.start_seconds, item.end_seconds, item.speaker))
        return DiarizationResult(
            segments=segments,
            model_name=self.settings.pyannote_model,
            device=self._resolve_device(),
        )

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        try:
            self._ensure_huggingface_hub_compat()
            self._ensure_speechbrain_compat()
            self._ensure_torchaudio_compat()
            self._ensure_torch_serialization_compat()
            import torch
            from pyannote.audio import Pipeline
        except Exception as exc:  # pragma: no cover - import failures depend on environment
            raise PyannoteDiarizationError("pyannote.audio is not available in the current environment.") from exc

        try:
            self._pipeline = Pipeline.from_pretrained(
                self.settings.pyannote_model,
                use_auth_token=self.settings.pyannote_auth_token,
            )
            self._pipeline.to(torch.device(self._resolve_device()))
        except Exception as exc:  # pragma: no cover - model bootstrap failures vary by environment
            raise PyannoteDiarizationError(str(exc)) from exc

        return self._pipeline

    @staticmethod
    def _load_audio_payload(source: Path) -> dict[str, object]:
        try:
            import soundfile
            import torch
        except Exception as exc:  # pragma: no cover - dependency availability varies by environment
            raise PyannoteDiarizationError("soundfile and torch are required for diarization audio loading.") from exc

        waveform, sample_rate = soundfile.read(str(source), always_2d=True)
        if waveform.size == 0:
            raise PyannoteDiarizationError(f"Audio file is empty: {source}")

        waveform = np.asarray(waveform, dtype=np.float32).T
        return {
            "waveform": torch.from_numpy(waveform),
            "sample_rate": int(sample_rate),
        }

    @staticmethod
    def _ensure_huggingface_hub_compat() -> None:
        try:
            import huggingface_hub
            import inspect
        except Exception:
            return

        hf_hub_download = getattr(huggingface_hub, "hf_hub_download", None)
        if hf_hub_download is None:
            return

        if "use_auth_token" in inspect.signature(hf_hub_download).parameters:
            return

        if getattr(hf_hub_download, "_minutes_compat_wrapped", False):
            return

        def _compat_hf_hub_download(*args, **kwargs):
            if "use_auth_token" in kwargs and "token" not in kwargs:
                kwargs["token"] = kwargs.pop("use_auth_token")
            else:
                kwargs.pop("use_auth_token", None)
            return hf_hub_download(*args, **kwargs)

        _compat_hf_hub_download._minutes_compat_wrapped = True
        huggingface_hub.hf_hub_download = _compat_hf_hub_download

    @staticmethod
    def _ensure_speechbrain_compat() -> None:
        try:
            import os as _os
            from speechbrain.utils.importutils import LazyModule
        except Exception:
            return

        ensure_module = getattr(LazyModule, "ensure_module", None)
        if ensure_module is None or getattr(ensure_module, "_minutes_compat_wrapped", False):
            return

        def _compat_ensure_module(self, stacklevel: int):
            importer_frame = None
            try:
                importer_frame = inspect.getframeinfo(__import__("sys")._getframe(stacklevel + 1))
            except AttributeError:
                importer_frame = None

            if importer_frame is not None and _os.path.basename(importer_frame.filename) == "inspect.py":
                raise AttributeError()

            return ensure_module(self, stacklevel)

        _compat_ensure_module._minutes_compat_wrapped = True
        LazyModule.ensure_module = _compat_ensure_module

    @staticmethod
    def _ensure_torch_serialization_compat() -> None:
        try:
            import torch
        except Exception:
            return

        add_safe_globals = getattr(torch.serialization, "add_safe_globals", None)
        torch_version_class = getattr(torch, "torch_version", None)
        torch_version_class = getattr(torch_version_class, "TorchVersion", None)
        if add_safe_globals is None or torch_version_class is None:
            pass
        else:
            add_safe_globals([torch_version_class])

        torch_load = getattr(torch, "load", None)
        if torch_load is None:
            return
        if getattr(torch_load, "_minutes_compat_wrapped", False):
            return
        if "weights_only" not in inspect.signature(torch_load).parameters:
            return

        def _compat_torch_load(*args, **kwargs):
            if kwargs.get("weights_only") is None:
                kwargs["weights_only"] = False
            return torch_load(*args, **kwargs)

        _compat_torch_load._minutes_compat_wrapped = True
        torch.load = _compat_torch_load

    @staticmethod
    def _ensure_torchaudio_compat() -> None:
        try:
            import soundfile
            import torchaudio
        except Exception:
            return

        if not hasattr(torchaudio, "AudioMetaData"):
            @std_dataclass(slots=True)
            class AudioMetaDataCompat:
                sample_rate: int
                num_frames: int
                num_channels: int
                bits_per_sample: int
                encoding: str

            torchaudio.AudioMetaData = AudioMetaDataCompat

        if not hasattr(torchaudio, "list_audio_backends"):
            torchaudio.list_audio_backends = lambda: ["soundfile"]

        if not hasattr(torchaudio, "info"):
            def _compat_info(uri, backend: str | None = None):
                info = soundfile.info(uri)
                return torchaudio.AudioMetaData(
                    sample_rate=int(info.samplerate),
                    num_frames=int(info.frames),
                    num_channels=int(info.channels),
                    bits_per_sample=int(info.subtype_info.split("-")[0]) if info.subtype_info and info.subtype_info.split("-")[0].isdigit() else 0,
                    encoding=info.subtype or "UNKNOWN",
                )

            torchaudio.info = _compat_info

    def _resolve_device(self) -> str:
        configured = self.settings.diarization_device
        if configured != "auto":
            return configured

        try:
            import torch
        except Exception:
            return "cpu"

        return "cuda:0" if torch.cuda.is_available() else "cpu"