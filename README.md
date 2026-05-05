# Minutes

This repository now contains the implementation foundation for a local transcription workspace.

## Purpose

Minutes is a local transcription project for turning recorded media into reviewable text outputs on a Windows workstation.

The current implementation is aimed at these outcomes:

- Accept a real media file and normalize it into a stable audio artifact for downstream processing.
- Produce a plain transcript with SenseVoice through FunASR.
- Optionally run pyannote diarization and assemble a speaker-attributed transcript that is easier to inspect and refine.
- Keep the pipeline local, file-backed, and inspectable so later summary generation can build on known transcript artifacts instead of opaque model responses.

In practice, this project is the foundation for a workflow like this: input audio or video, extract or normalize audio, transcribe it, separate speakers when enabled, and then use the resulting text as the source for later minutes or summary generation.

## What This Repo Is

- A Python local application scaffold for transcription, opt-in diarization, and later summarization work.
- A documentation control plane for human onboarding and multi-session LLM work.
- A committed sample output set under [sample/test1](sample/test1) generated from the validated [file/test1.mp3](file/test1.mp3) fixture.

## Result Showcase

The repository includes a committed example output set under [sample/test1](sample/test1) so you can inspect the current quality and artifact shape without running the full pipeline first.

The sample set shows the current end-to-end output from the validated [file/test1.mp3](file/test1.mp3) run:

- Source media: [file/test1.mp3](file/test1.mp3)
- Plain transcript: [sample/test1/transcript.txt](sample/test1/transcript.txt)
- Speaker-attributed transcript: [sample/test1/speaker_transcript.txt](sample/test1/speaker_transcript.txt)
- Sample metadata: [sample/test1/metadata.json](sample/test1/metadata.json)

## Setup

1. Create or activate the repository virtual environment.
2. Install the project in editable mode:

```powershell
python -m pip install -e .
```

3. Optionally copy `.env.example` to `.env` and override runtime settings.
4. Run the local doctor script:

```powershell
.\scripts\doctor.ps1
```

The local workspace setup can point `MINUTES_STATE_ROOT` at `.minutes-data` in the repository root. Keep that directory user-writable and ignored by git.

## Run

Use the local launch script:

```powershell
.\scripts\run-local.ps1
```

Or run the package directly after installation:

```powershell
python -m minutes serve --reload
```

To process the next queued job once from the CLI:

```powershell
python -m minutes run-once
```

To create a job for one media file and process it through normalization plus transcription:

```powershell
python -m minutes process-file C:\path\to\audio.wav
```

If `MINUTES_DIARIZATION_ENABLED=1` is set and `MINUTES_PYANNOTE_AUTH_TOKEN` is configured, the same command will continue into pyannote 3.1 diarization and speaker-attributed transcript assembly. The run will write diarization artifacts plus `speaker_transcript.json` and `speaker_transcript.txt` beside the plain transcript artifacts.

To print the transcript text for an existing processed job:

```powershell
python -m minutes show-transcript <job_id>
```

To print the speaker-attributed transcript text for an existing processed job:

```powershell
python -m minutes show-transcript <job_id> --speaker-attributed
```

The API route `GET /api/jobs/{job_id}/transcript` also accepts `?speaker_attributed=true` to return the assembled speaker-labeled text instead of the plain transcript.

## Test

Current narrow validation commands:

```powershell
python -m compileall src
python -m minutes show-config
python -m pytest tests/test_normalization_flow.py
$env:MINUTES_RUN_REAL_AUDIO_TESTS='1'; python -m pytest tests/test_real_audio_integration.py -m integration
```

The scaffold resolves `ffmpeg` from `MINUTES_FFMPEG_BIN` when it is set.
SenseVoice/FunASR transcription is wired into the CLI pipeline.
The repository-local fixture at [file/test1.mp3](file/test1.mp3) is covered by an opt-in real-audio integration test.
pyannote diarization and speaker-attributed transcript assembly are available as opt-in stages. Real runs require a Hugging Face access token that has accepted the `pyannote/speaker-diarization-3.1` conditions.
On this machine, the current local `.env` pins transcription and diarization to `cuda:0`.

## Sample Output

- A curated example output set from the validated `file/test1.mp3` run lives under [sample/test1](sample/test1).
- The committed sample set keeps only reviewable artifacts: [sample/test1/metadata.json](sample/test1/metadata.json), [sample/test1/transcript.txt](sample/test1/transcript.txt), and [sample/test1/speaker_transcript.txt](sample/test1/speaker_transcript.txt).
- Large runtime artifacts such as normalized WAV files and per-segment scratch output stay under the gitignored `.minutes-data` state root.

## Windows Notes

- The validated local setup in this repository writes runtime state to `.minutes-data` under the workspace root; keep it gitignored.
- Keep the configured `ffmpeg` directory on `PATH` because downstream audio libraries may still invoke `ffmpeg` by name.
- The current Windows diarization stack in this repo relies on local compatibility shims for `torchaudio`, `huggingface_hub`, PyTorch serialization defaults, and SpeechBrain lazy imports.
- The current Windows implementation avoids pyannote's `torchcodec` file loader by passing in-memory waveforms from the normalized WAV artifact.
- Speaker-attributed assembly retranscribes diarization windows and pads very short windows before sending them back through SenseVoice.
- GPU execution on Windows is now validated in this workspace with CUDA-enabled `torch` and `torchaudio` wheels.

## Where To Look Next

- Start with [INDEX.md](INDEX.md) for reading order and authority rules.
- Read [AGENTS.md](AGENTS.md) for LLM operating rules.
- Read [DEVNOTES.md](DEVNOTES.md) for the most recent verified repository state.
- Read [docs/plans/2026-05-05-local-minutes-implementation.md](docs/plans/2026-05-05-local-minutes-implementation.md) for the active scoped implementation plan.
