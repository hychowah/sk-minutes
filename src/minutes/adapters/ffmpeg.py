from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from minutes.config import Settings, get_settings


class FfmpegError(RuntimeError):
    """Raised when an ffmpeg or ffprobe command fails."""


@dataclass(slots=True)
class MediaProbeResult:
    format_name: str | None
    duration_seconds: float | None
    streams: list[dict[str, Any]]
    raw: dict[str, Any]


class FfmpegAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.ffmpeg_bin = self.settings.ffmpeg_bin
        self.ffprobe_bin = self.ffmpeg_bin.with_name("ffprobe.exe")

    def ensure_available(self) -> None:
        if not self.ffmpeg_bin.exists():
            raise FfmpegError(f"ffmpeg binary not found at {self.ffmpeg_bin}")
        if not self.ffprobe_bin.exists():
            raise FfmpegError(f"ffprobe binary not found at {self.ffprobe_bin}")

    def version(self) -> str:
        self.ensure_available()
        completed = self._run_command([str(self.ffmpeg_bin), "-version"])
        return completed.stdout.splitlines()[0]

    def probe(self, source_path: Path | str) -> MediaProbeResult:
        self.ensure_available()
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(source)

        completed = self._run_command(
            [
                str(self.ffprobe_bin),
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(source),
            ]
        )
        payload = json.loads(completed.stdout)
        format_payload = payload.get("format", {})
        duration_raw = format_payload.get("duration")
        duration_seconds = float(duration_raw) if duration_raw is not None else None
        return MediaProbeResult(
            format_name=format_payload.get("format_name"),
            duration_seconds=duration_seconds,
            streams=payload.get("streams", []),
            raw=payload,
        )

    def normalize_to_wav(self, source_path: Path | str, output_path: Path | str) -> Path:
        self.ensure_available()
        source = Path(source_path)
        output = Path(output_path)
        if not source.exists():
            raise FileNotFoundError(source)

        output.parent.mkdir(parents=True, exist_ok=True)
        self._run_command(
            [
                str(self.ffmpeg_bin),
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(output),
            ]
        )
        return output

    @staticmethod
    def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise FfmpegError(completed.stderr.strip() or completed.stdout.strip() or "ffmpeg command failed")
        return completed