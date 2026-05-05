Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python virtual environment not found at $PythonExe"
}

$existingPythonPath = $env:PYTHONPATH
if ([string]::IsNullOrWhiteSpace($existingPythonPath)) {
    $env:PYTHONPATH = Join-Path $RepoRoot 'src'
} else {
    $env:PYTHONPATH = "$(Join-Path $RepoRoot 'src');$existingPythonPath"
}

& $PythonExe -m minutes serve --reload