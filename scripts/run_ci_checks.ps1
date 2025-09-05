# PowerShell script to run CI checks locally
# Matches GitHub Actions workflow

Write-Host "`n=====================================" -ForegroundColor Blue
Write-Host "Running Local CI Checks" -ForegroundColor Blue
Write-Host "=====================================`n" -ForegroundColor Blue

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

Write-Host "`n===== CODE QUALITY CHECKS =====" -ForegroundColor Blue

# Black formatting check
if (-not (Run-Check "poetry run black --check src/ tests/" "Black formatting check")) {
    $failed = $true
    Write-Host "Run 'poetry run black src/ tests/' to fix formatting" -ForegroundColor Yellow
}

# Ruff linting
if (-not (Run-Check "poetry run ruff check src/ tests/" "Ruff linting")) {
    $failed = $true
    Write-Host "Run 'poetry run ruff check --fix src/ tests/' to fix issues" -ForegroundColor Yellow
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
    Write-Host "`n[FAILED] Some checks failed. Please fix the issues before pushing." -ForegroundColor Red
    Write-Host "Tip: Run 'poetry run black src/ tests/' and 'poetry run ruff check --fix src/ tests/' to auto-fix many issues" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "`n[SUCCESS] All CI checks passed! Ready to commit and push." -ForegroundColor Green
    exit 0
}
