# scripts/create-release.ps1
# PowerShell script to create a new release tag
# Author: Pierre Grothé
# Creation Date: 2025-09-05

param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern("^\d+\.\d+\.\d+$")]
    [string]$Version,

    [string]$Message = "Release version",

    [switch]$Push = $false
)

# Colors for output
function Write-Info { Write-Host "[INFO]" -ForegroundColor Cyan -NoNewline; Write-Host " $args" }
function Write-Success { Write-Host "[SUCCESS]" -ForegroundColor Green -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[ERROR]" -ForegroundColor Red -NoNewline; Write-Host " $args" }

Write-Info "Creating release tag v$Version"

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
Write-Info "Creating tag v$Version with message: $Message v$Version"
git tag -a "v$Version" -m "$Message v$Version"

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

            # Extract major and minor for additional tags
            $parts = $Version.Split('.')
            if ($parts.Count -eq 3) {
                $major = $parts[0]
                $minor = "$($parts[0]).$($parts[1])"
                Write-Info "  - ghcr.io/pierregrothe/graphrag-api:$major"
                Write-Info "  - ghcr.io/pierregrothe/graphrag-api:$minor"
            }
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
