from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_state_root() -> Path:
    return Path.cwd() / ".minutes-data"


def _default_ffmpeg_bin() -> Path:
    preferred_path = Path(r"C:\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe")
    return preferred_path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MINUTES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Minutes"
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8765
    state_root: Path = Field(default_factory=_default_state_root)
    ffmpeg_bin: Path = Field(default_factory=_default_ffmpeg_bin)
    sensevoice_model: str = "iic/SenseVoiceSmall"
    sensevoice_vad_model: str = "fsmn-vad"
    transcription_device: str = "auto"
    transcription_language: str = "auto"
    transcription_use_itn: bool = True
    transcription_batch_size_s: int = 30
    transcription_merge_vad: bool = True
    transcription_merge_length_s: int = 15
    transcription_max_single_segment_ms: int = 30000
    summary_base_url: str | None = None
    summary_api_key: str | None = None
    summary_model: str | None = None
    summary_prompt_version: str = "v1"
    summary_timeout_seconds: int = 120
    summary_temperature: float = 0.1
    diarization_enabled: bool = False
    pyannote_model: str = "pyannote/speaker-diarization-3.1"
    pyannote_auth_token: str | None = None
    diarization_device: str = "auto"
    diarization_num_speakers: int | None = None
    diarization_min_speakers: int | None = None
    diarization_max_speakers: int | None = None
    pyannote_metrics_enabled: bool = False

    @property
    def cache_root(self) -> Path:
        return self.state_root / "cache"

    @property
    def data_root(self) -> Path:
        return self.state_root / "data"

    @property
    def logs_root(self) -> Path:
        return self.state_root / "logs"

    @property
    def ffmpeg_available(self) -> bool:
        return self.ffmpeg_bin.exists()

    @property
    def summary_configured(self) -> bool:
        return bool(self.summary_base_url and self.summary_model)

    def ensure_state_dirs(self) -> None:
        for directory in (self.state_root, self.cache_root, self.data_root, self.logs_root):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_state_dirs()
    return settings