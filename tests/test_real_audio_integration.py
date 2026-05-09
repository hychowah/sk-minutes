from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "file" / "test1.mp3"


@pytest.mark.integration
def test_process_file_fixture_mp3() -> None:
    if not FIXTURE_PATH.exists():
        pytest.skip("Real audio fixture is not available.")

    if os.environ.get("MINUTES_RUN_REAL_AUDIO_TESTS") != "1":
        pytest.skip("Set MINUTES_RUN_REAL_AUDIO_TESTS=1 to run the real audio integration test.")

    python_exe = Path.cwd() / ".venv" / "Scripts" / "python.exe"
    result = subprocess.run(
        [str(python_exe), "-m", "minutes", "process-file", str(FIXTURE_PATH)],
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
    )

    payload = json.loads(result.stdout[result.stdout.index("{") :])
    transcript_artifact = next(artifact for artifact in payload["artifacts"] if artifact["kind"] == "transcript_text")
    transcript_text = Path(transcript_artifact["path"]).read_text(encoding="utf-8").strip()

    assert payload["status"] == "completed"
    assert payload["workflow_stage"] == "transcribed"
    assert "current_stage" not in payload
    assert transcript_text