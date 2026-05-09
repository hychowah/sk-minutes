# Minutes

This repository now contains a local transcription and summary workspace.

## Purpose

Minutes is a local transcription project for turning recorded media into reviewable text outputs on a Windows workstation, with the current main language focus on Cantonese and English.

The application can:

- Normalize audio from a media file.
- Generate a plain transcript.
- Optionally generate a speaker-attributed transcript when diarization is enabled.
- Optionally generate a persisted summary when a compatible summary backend is configured.

## Result Showcase

The repository includes a committed example output set under [sample/test1](sample/test1) so you can inspect the artifact shape without running the full pipeline first.

The committed sample set includes:

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

3. Optionally copy `.env.example` to `.env` and override runtime settings, including the summary backend if you want automatic summarization.
4. Run the local doctor script:

```powershell
.\scripts\doctor.ps1
```

The default local runtime state root is `.minutes-data` in the repository root. Keep that directory user-writable and ignored by git.

## Configuration

- Set `MINUTES_FFMPEG_BIN` if `ffmpeg` is not already available on `PATH`.
- Set `MINUTES_DIARIZATION_ENABLED=1` and `MINUTES_PYANNOTE_AUTH_TOKEN` to enable speaker diarization.
- Set `MINUTES_SUMMARY_BASE_URL` and `MINUTES_SUMMARY_MODEL` to enable summary generation.
- Set `MINUTES_SUMMARY_API_KEY` when the configured summary backend requires authentication.

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

To inspect persisted jobs from the CLI:

```powershell
python -m minutes list-jobs
python -m minutes show-job <job_id>
```

To create a job for one media file and process it through normalization plus transcription:

```powershell
python -m minutes process-file C:\path\to\audio.wav
```

The first SenseVoice transcription run may download the FunASR speech and VAD models into your user ModelScope cache. Later runs should reuse the cached local model directories instead of treating them as fresh hub downloads.

If `MINUTES_DIARIZATION_ENABLED=1` is set and `MINUTES_PYANNOTE_AUTH_TOKEN` is configured, the same command will continue into pyannote 3.1 diarization and speaker-attributed transcript assembly. The run will write diarization artifacts plus `speaker_transcript.json` and `speaker_transcript.txt` beside the plain transcript artifacts.

If `MINUTES_SUMMARY_BASE_URL` and `MINUTES_SUMMARY_MODEL` are configured, the same command will continue into summary generation and write `summary.json` plus `summary.txt` beside the transcript artifacts. Use `--summary-language <code>` on `process-file` when you need the summary output language to differ from the transcript language.

To print the transcript text for an existing processed job:

```powershell
python -m minutes show-transcript <job_id>
```

To print the speaker-attributed transcript text for an existing processed job:

```powershell
python -m minutes show-transcript <job_id> --speaker-attributed
```

The API route `GET /api/jobs/{job_id}/transcript` also accepts `?speaker_attributed=true` to return the assembled speaker-labeled text instead of the plain transcript.

To print the summary text for an existing processed job:

```powershell
python -m minutes show-summary <job_id>
```

To inspect summary metadata and freshness details for an existing processed job:

```powershell
python -m minutes show-summary <job_id> --json
```

To run or rerun summary generation for an existing job after configuring the summary backend:

```powershell
python -m minutes summarize-job <job_id>
```

The API route `GET /api/jobs/{job_id}/summary` returns the persisted summary text plus summary metadata. When a current summary source is selected, the JSON response also exposes `source_current`, `current_source_artifact_kind`, and `current_source_artifact_path`. `POST /api/jobs/{job_id}/summarize` runs or reruns the summary stage for one job.

## Test

Run the local regression suite with:

```powershell
python -m pytest tests/test_normalization_flow.py
```

To run the opt-in real-audio integration test:

```powershell
$env:MINUTES_RUN_REAL_AUDIO_TESTS='1'; python -m pytest tests/test_real_audio_integration.py -m integration
```

## Sample Output

- Runtime artifacts such as normalized audio, segment scratch output, and generated summaries stay under the gitignored `.minutes-data` state root.
