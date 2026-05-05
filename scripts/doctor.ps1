Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python virtual environment not found at $PythonExe"
}

$StateRoot = if ($env:MINUTES_STATE_ROOT) {
    $env:MINUTES_STATE_ROOT
} else {
    Join-Path $env:USERPROFILE 'MinutesData'
}

$ConfiguredFfmpeg = if ($env:MINUTES_FFMPEG_BIN) {
    $env:MINUTES_FFMPEG_BIN
} else {
    'C:\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe'
}

$ResolvedFfmpeg = if (Test-Path $ConfiguredFfmpeg) {
    $ConfiguredFfmpeg
} else {
    $FfmpegCommand = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($FfmpegCommand) {
        $FfmpegCommand.Source
    } else {
        $null
    }
}

Write-Output "Repo root: $RepoRoot"
Write-Output "Python: $PythonExe"
Write-Output "State root: $StateRoot"
Write-Output "Configured ffmpeg: $ConfiguredFfmpeg"

if ($ResolvedFfmpeg) {
    Write-Output "ffmpeg: $ResolvedFfmpeg"
} else {
    Write-Warning 'ffmpeg was not found at the configured path or on PATH.'
}