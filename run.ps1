$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

$projectRoot = $PSScriptRoot
$venvPythonCandidates = @(
    Join-Path $projectRoot '.venv\Scripts\python.exe'
    Join-Path $projectRoot '.venv313\Scripts\python.exe'
    Join-Path $projectRoot 'venv\Scripts\python.exe'
)

$pythonExe = $venvPythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $pythonExe) {
    $venvDir = Join-Path $projectRoot '.venv'

    if (-not (Test-Path $venvDir)) {
        Write-Host 'Creating virtual environment...'

        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv $venvDir
        }
        elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv $venvDir
        }
        else {
            throw 'Python was not found. Install Python 3 and try again.'
        }
    }

    $pythonExe = Join-Path $venvDir 'Scripts\python.exe'
}

if (-not (Test-Path $pythonExe)) {
    throw 'Could not find a usable Python interpreter in the project environment.'
}

$requirementsFile = Join-Path $projectRoot 'requirements.txt'

if (Test-Path $requirementsFile) {
    Write-Host 'Installing dependencies...'
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r $requirementsFile
}

Write-Host ''
Write-Host 'Starting RAG Studio on http://localhost:8000'
Write-Host 'Make sure Ollama is running on http://localhost:11434'
Write-Host ''

& $pythonExe (Join-Path $projectRoot 'main.py')