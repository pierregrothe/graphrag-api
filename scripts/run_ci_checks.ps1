# PowerShell script to run CI checks locally
# Matches GitHub Actions workflow

param(
    [switch]$NoFix = $false,
    [switch]$Fix = $true
)

# If NoFix is specified, disable Fix
if ($NoFix) {
    $Fix = $false
}

Write-Host "`n=====================================" -ForegroundColor Blue
Write-Host "Running Local CI Checks" -ForegroundColor Blue
Write-Host "=====================================`n" -ForegroundColor Blue

if ($Fix) {
    Write-Host "[INFO] Auto-fix mode: ENABLED (use -NoFix to disable)" -ForegroundColor Cyan
} else {
    Write-Host "[INFO] Auto-fix mode: DISABLED (use -Fix to enable)" -ForegroundColor Cyan
}

# Set environment variables
$env:JWT_SECRET_KEY = "test-secret-key-for-ci-only-12345678"
$env:DEBUG = "true"
$env:GRAPHRAG_LLM_PROVIDER = "ollama"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
$env:OLLAMA_LLM_MODEL = "llama2"
$env:OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"

$failed = $false

# Function to run a command and check result
function Run-Check {
    param(
        [string]$Command,
        [string]$Description
    )

    Write-Host "`nRunning: $Description" -ForegroundColor Cyan
    Write-Host "Command: $Command" -ForegroundColor Gray

    Invoke-Expression $Command

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] $Description passed" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[ERROR] $Description failed" -ForegroundColor Red
        return $false
    }
}

# Auto-fix issues if enabled
if ($Fix) {
    Write-Host "`n===== AUTO-FIXING ISSUES =====" -ForegroundColor Blue

    Write-Host "[INFO] Running Black to auto-format code..." -ForegroundColor Cyan
    Run-Check "poetry run black src/ tests/" "Black auto-formatting" | Out-Null
    Write-Host "[SUCCESS] Black formatting applied successfully" -ForegroundColor Green

    Write-Host "[INFO] Running Ruff to auto-fix linting issues..." -ForegroundColor Cyan
    Run-Check "poetry run ruff check --fix src/ tests/" "Ruff auto-fix" | Out-Null
    Write-Host "[SUCCESS] Ruff fixes applied successfully" -ForegroundColor Green

    Write-Host "[INFO] Running isort to fix import ordering..." -ForegroundColor Cyan
    Run-Check "poetry run isort src/ tests/ --profile black" "Import sorting" | Out-Null
    Write-Host "[SUCCESS] Import ordering fixed successfully" -ForegroundColor Green

    Write-Host "[INFO] Auto-fix complete. Now running validation checks..." -ForegroundColor Cyan
}

Write-Host "`n===== CODE QUALITY CHECKS =====" -ForegroundColor Blue

# Black formatting check
if (-not (Run-Check "poetry run black --check src/ tests/" "Black formatting check")) {
    $failed = $true
    if (-not $Fix) {
        Write-Host "Run 'poetry run black src/ tests/' to fix formatting" -ForegroundColor Yellow
    }
}

# Ruff linting
if (-not (Run-Check "poetry run ruff check src/ tests/" "Ruff linting")) {
    $failed = $true
    if (-not $Fix) {
        Write-Host "Run 'poetry run ruff check --fix src/ tests/' to fix issues" -ForegroundColor Yellow
    }
}

# MyPy type checking
if (-not (Run-Check "poetry run mypy src/graphrag_api_service" "MyPy type checking")) {
    $failed = $true
}

# Bandit security check
if (-not (Run-Check "poetry run bandit -r src/ -ll -q" "Bandit security check")) {
    $failed = $true
}

Write-Host "`n===== UNIT TESTS =====" -ForegroundColor Blue

# Run unit tests with coverage
if (-not (Run-Check "poetry run pytest tests/unit/ --cov=src/graphrag_api_service --cov-report=term-missing -v" "Unit tests with coverage")) {
    $failed = $true
}

Write-Host "`n===== ADDITIONAL LOCAL CHECKS =====" -ForegroundColor Blue

# Pre-commit hooks
if (-not (Run-Check "pre-commit run --all-files" "Pre-commit hooks")) {
    Write-Host "Some pre-commit hooks may have auto-fixed issues" -ForegroundColor Yellow
}

Write-Host "`n===== SUMMARY =====" -ForegroundColor Blue

if ($failed) {
    Write-Host "`n[FAILED] Some checks failed." -ForegroundColor Red
    if (-not $Fix) {
        Write-Host "Tip: Run this script with -Fix flag to auto-fix many issues" -ForegroundColor Yellow
        Write-Host "Example: .\scripts\run_ci_checks.ps1 -Fix" -ForegroundColor Yellow
    } else {
        Write-Host "Some issues could not be auto-fixed. Manual intervention required." -ForegroundColor Yellow
    }
    exit 1
} else {
    Write-Host "`n[SUCCESS] All CI checks passed! Ready to commit and push." -ForegroundColor Green
    exit 0
}
