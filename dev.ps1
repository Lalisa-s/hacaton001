param(
    [ValidateSet('all', 'backend', 'frontend')]
    [string]$Component = 'all'
)
$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create backend/.venv and install backend/requirements.txt first. See README.md.'
}
& $pythonPath (Join-Path $PSScriptRoot 'tools\dev.py') $Component
exit $LASTEXITCODE
