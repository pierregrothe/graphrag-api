# PowerShell script to run security checks locally
# This simulates the GitHub Actions security workflow

param(
    [ValidateSet("fast", "pr", "comprehensive")]
    [string]$Mode = "fast",

    [switch]$Fix = $false,

    [switch]$Verbose = $false,

    [switch]$SkipPreCommit = $false
)

# Colors for output
$Host.UI.RawUI.ForegroundColor = "White"

function Write-Header {
    param([string]$Message)
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 60) -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue -BackgroundColor Black
    Write-Host ("=" * 60) -ForegroundColor Blue
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "[PASS] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "[FAIL] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Cyan -NoNewline
    Write-Host $Message
}

# Main execution
Write-Header "LOCAL SECURITY WORKFLOW TEST"

Write-Info "Mode: $Mode"
Write-Info "Auto-fix: $($Fix ? 'Enabled' : 'Disabled')"
Write-Info "Verbose: $($Verbose ? 'Enabled' : 'Disabled')"

# Build command arguments
$args = @("scripts/test_security_workflow.py", "--mode", $Mode)

if ($Fix) {
    $args += "--fix"
}

if ($Verbose) {
    $args += "--verbose"
}

# Run the security workflow test
Write-Info "Starting security checks..."
$result = python @args
$exitCode = $LASTEXITCODE

# Display result
if ($exitCode -eq 0) {
    Write-Success "Security checks passed!"

    if (-not $SkipPreCommit) {
        Write-Info "Running pre-commit hooks to ensure everything is ready..."
        pre-commit run --all-files

        if ($LASTEXITCODE -eq 0) {
            Write-Success "All checks passed! Ready to commit."
        } else {
            Write-Warning "Pre-commit hooks found issues. Run with --fix to auto-fix."
        }
    }
} else {
    Write-Error "Security checks failed!"
    Write-Info "Exit code: $exitCode"

    if ($Mode -eq "fast") {
        Write-Info "Tip: Run with -Mode pr for more comprehensive checks"
    }

    if (-not $Fix) {
        Write-Info "Tip: Run with -Fix to auto-fix some issues"
    }
}

# Provide quick commands
Write-Host "`nQuick Commands:" -ForegroundColor Cyan
Write-Host "  Fast check:         .\scripts\security-check.ps1 -Mode fast"
Write-Host "  PR simulation:      .\scripts\security-check.ps1 -Mode pr"
Write-Host "  Full analysis:      .\scripts\security-check.ps1 -Mode comprehensive"
Write-Host "  Auto-fix issues:    .\scripts\security-check.ps1 -Fix"
Write-Host "  Skip pre-commit:    .\scripts\security-check.ps1 -SkipPreCommit"

exit $exitCode
