$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = $root
$frontendDir = Join-Path $root 'frontend'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Error "Python interpreter not found at $venvPython. Create or activate the .venv environment first."
    exit 1
}

if (-not (Test-Path $frontendDir)) {
    Write-Error "Frontend folder not found at $frontendDir."
    exit 1
}

Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$backendDir'; & '$venvPython' -m uvicorn api:app --reload --port 8000"
) -WindowStyle Normal

Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$frontendDir'; npm run dev"
) -WindowStyle Normal

Write-Host 'Started backend on http://127.0.0.1:8000 and frontend on the Vite dev URL shown in the frontend window.'