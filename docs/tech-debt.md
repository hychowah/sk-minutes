- Purpose: Living debt register
- Scope: Unresolved implementation and documentation debt items plus their status; excludes recent work log and architecture ownership
- Status: Active
- Last validated: 2026-05-05
- Source of truth for: Current debt inventory and cleanup priorities

# Tech Debt

## Active Debt

| ID | Title | Priority | Why It Matters | What To Do | Affected Area | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TD-002 | pyannote depends on removed torchaudio top-level APIs | High | Live diarization currently needs a local compatibility shim for `AudioMetaData`, `list_audio_backends`, and `info`, which is fragile across future package upgrades. | Replace the shim with a verified package version set or a cleaner upstream-compatible integration once the target torch stack is pinned. | [src/minutes/adapters/diarizer_pyannote.py](src/minutes/adapters/diarizer_pyannote.py) | Open |

## Resolved Debt

| ID | Title | Priority | Why It Mattered | What Was Done | Affected Area | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TD-001 | Setup and execution workflow not established | Medium | Future contributors did not have canonical setup, run, or test steps. | Added verified setup, run, and test instructions to [README.md](README.md). | Repository-wide onboarding | Resolved |
| TD-003 | Windows diarization stack still needs torchcodec | High | Real pyannote diarization reached audio loading but failed on `torchcodec` in the Windows pip environment. | Bypassed file-based loading by passing pyannote an in-memory waveform from the normalized WAV artifact instead. | [src/minutes/adapters/diarizer_pyannote.py](src/minutes/adapters/diarizer_pyannote.py) | Resolved |
