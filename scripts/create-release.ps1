# scripts/create-release.ps1
# PowerShell script to create a new release tag with calendar-based versioning
# Author: Pierre Grothé
# Creation Date: 2025-09-05
# Version Format: YYYY.WW.ET.NNN where:
#   YYYY = Year
#   WW = Week number (1-52)
#   ET = Environment Type (10=dev, 20=prod)
#   NNN = Sequential number (1-999)

param(
    [Parameter(Mandatory=$false)]
    [ValidatePattern("^\d{4}\.\d{1,2}\.(10|20)\.\d{1,3}$")]
    [string]$Version,

    [ValidateSet("dev", "prod")]
    [string]$Type = "dev",

    [string]$Message = "Release",

    [switch]$Push = $false,

    [switch]$AutoVersion = $false
)

# Colors for output
function Write-Info { Write-Host "[INFO]" -ForegroundColor Cyan -NoNewline; Write-Host " $args" }
function Write-Success { Write-Host "[SUCCESS]" -ForegroundColor Green -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[ERROR]" -ForegroundColor Red -NoNewline; Write-Host " $args" }

# Function to get current week number
function Get-WeekNumber {
    param([datetime]$Date = (Get-Date))
    $culture = [System.Globalization.CultureInfo]::CurrentCulture
    $calendar = $culture.Calendar
    $calendarWeekRule = $culture.DateTimeFormat.CalendarWeekRule
    $firstDayOfWeek = $culture.DateTimeFormat.FirstDayOfWeek
    return $calendar.GetWeekOfYear($Date, $calendarWeekRule, $firstDayOfWeek)
}

# Function to get next sequential number
function Get-NextSequentialNumber {
    param(
        [string]$Year,
        [string]$Week,
        [string]$EnvType
    )

    # Get all existing tags matching the pattern
    $pattern = "v$Year.$Week.$EnvType.*"
    $existingTags = git tag -l $pattern 2>$null

    if (-not $existingTags) {
        return 1
    }

    # Extract the highest sequential number
    $maxNumber = 0
    foreach ($tag in $existingTags) {
        if ($tag -match "v\d{4}\.\d{1,2}\.(10|20)\.(\d{1,3})") {
            $num = [int]$matches[2]
            if ($num -gt $maxNumber) {
                $maxNumber = $num
            }
        }
    }

    return $maxNumber + 1
}

# Generate version if not provided or if AutoVersion is set
if ($AutoVersion -or -not $Version) {
    $year = (Get-Date).Year
    $week = Get-WeekNumber
    $envType = if ($Type -eq "prod") { "20" } else { "10" }
    $seqNumber = Get-NextSequentialNumber -Year $year -Week $week -EnvType $envType

    $Version = "$year.$week.$envType.$seqNumber"
    Write-Info "Auto-generated version: $Version"
}

# Validate version format
if ($Version -notmatch "^\d{4}\.\d{1,2}\.(10|20)\.\d{1,3}$") {
    Write-Error "Invalid version format. Expected: YYYY.WW.ET.NNN (e.g., 2025.36.10.1)"
    Write-Error "  YYYY = Year (4 digits)"
    Write-Error "  WW = Week number (1-52)"
    Write-Error "  ET = Environment Type (10=dev, 20=prod)"
    Write-Error "  NNN = Sequential number (1-999)"
    exit 1
}

# Extract version components
$versionParts = $Version.Split('.')
$year = $versionParts[0]
$week = $versionParts[1]
$envType = $versionParts[2]
$seqNum = $versionParts[3]

$envName = if ($envType -eq "20") { "production" } else { "development" }

Write-Info "Creating $envName release tag v$Version"

# Check if we're in a git repository
if (!(Test-Path .git)) {
    Write-Error "Not in a git repository"
    exit 1
}

# Check if tag already exists
$existingTag = git tag -l "v$Version" 2>$null
if ($existingTag) {
    Write-Error "Tag v$Version already exists"
    exit 1
}

# Get current branch
$currentBranch = git branch --show-current
Write-Info "Current branch: $currentBranch"

# Check for uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Error "You have uncommitted changes. Please commit or stash them first."
    exit 1
}

# Create the tag
$fullMessage = "$Message - $envName release v$Version"
Write-Info "Creating tag v$Version with message: $fullMessage"
git tag -a "v$Version" -m "$fullMessage"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Tag v$Version created successfully"

    # Show the tag
    git show "v$Version" --no-patch

    if ($Push) {
        Write-Info "Pushing tag to origin..."
        git push origin "v$Version"

        if ($LASTEXITCODE -eq 0) {
            Write-Success "Tag pushed to origin"
            Write-Info "Docker image will be built automatically by GitHub Actions"
            Write-Info "Image tags will be:"
            Write-Info "  - ghcr.io/pierregrothe/graphrag-api:latest"
            Write-Info "  - ghcr.io/pierregrothe/graphrag-api:v$Version"
            Write-Info "  - ghcr.io/pierregrothe/graphrag-api:$Version"

            # For production releases, also create major version tags
            if ($envType -eq "20") {
                Write-Info "  - ghcr.io/pierregrothe/graphrag-api:$year"
                Write-Info "  - ghcr.io/pierregrothe/graphrag-api:$year.$week"
            }

            Write-Info ""
            Write-Info "Pull the image with:"
            Write-Info "  docker pull ghcr.io/pierregrothe/graphrag-api:$Version"
        } else {
            Write-Error "Failed to push tag to origin"
            exit 1
        }
    } else {
        Write-Info "Tag created locally. Use -Push to push to origin"
        Write-Info "Or manually: git push origin v$Version"
    }
} else {
    Write-Error "Failed to create tag"
    exit 1
}

# Show next suggested version
$nextSeqNum = [int]$seqNum + 1
$nextVersion = "$year.$week.$envType.$nextSeqNum"
Write-Info ""
Write-Info "Next suggested version: $nextVersion"
Write-Info "Usage: .\scripts\create-release.ps1 -Version $nextVersion -Push"
Write-Info "Or use -AutoVersion for automatic version generation"
