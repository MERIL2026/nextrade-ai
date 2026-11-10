[CmdletBinding()]
param(
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    Write-Host "==> $Label" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed ($LASTEXITCODE): $Label"
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $apiPython = Join-Path $repoRoot "services/api/.venv/Scripts/python.exe"
    $workerPython = Join-Path $repoRoot "services/worker/.venv/Scripts/python.exe"

    if (-not (Test-Path $apiPython)) {
        throw "API virtual environment missing at $apiPython"
    }
    if (-not (Test-Path $workerPython)) {
        throw "Worker virtual environment missing at $workerPython"
    }

    Invoke-Checked "Verify documents/ directory (26 PDFs) is local and Git-ignored" {
        $pdfCount = (Get-ChildItem -Path "documents" -Filter "*.pdf" -File).Count
        if ($pdfCount -ne 26) {
            throw "Expected 26 PDFs in documents/, found $pdfCount"
        }
        & git check-ignore -q documents
    }

    Invoke-Checked "Verify .env is Git-ignored and .env.example is valid" {
        & git check-ignore -q .env
        & docker compose --env-file .env.example config --quiet
    }

    Invoke-Checked "Ruff lint & format check (services/api, services/worker, tests)" {
        & $apiPython -m ruff check services/api services/worker tests
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $apiPython -m ruff format --check services/api services/worker tests
    }

    Invoke-Checked "Strict mypy typecheck (services/api & services/worker)" {
        & $apiPython -m mypy --config-file services/api/pyproject.toml services/api/app services/api/alembic/env.py services/api/tests
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $workerPython -m mypy --config-file services/worker/pyproject.toml services/worker/worker_app services/worker/tests
    }

    Invoke-Checked "Pytest unit suite (services/api)" {
        Push-Location "services/api"
        try {
            & $apiPython -m pytest -m unit
        }
        finally {
            Pop-Location
        }
    }

    Invoke-Checked "Pytest unit suite (services/worker)" {
        Push-Location "services/worker"
        try {
            & $workerPython -m pytest -m unit
        }
        finally {
            Pop-Location
        }
    }

    Invoke-Checked "Frontend verification (apps/web)" {
        Push-Location "apps/web"
        try {
            & pnpm peers check
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            & pnpm exec next typegen
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            & pnpm typecheck
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            & pnpm lint
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            & pnpm test
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            if (-not $SkipFrontendBuild) {
                $env:NEXT_PUBLIC_APP_NAME = "NEXTRADE AI"
                $env:NEXT_PUBLIC_APP_ENV = "local"
                $env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8001"
                & pnpm build
            }
        }
        finally {
            Pop-Location
        }
    }

    Write-Host "NEXTRADE AI Phase 1 static & unit verification passed." -ForegroundColor Green
}
finally {
    Pop-Location
}

