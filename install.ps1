<#
.SYNOPSIS
    Install sfcs-mdp after cloning the repository.
.DESCRIPTION
    Installs the sfcs-mdp package in the current Python environment so that
    both ``sfcs-mdp`` and ``python -m sfcs_mdp`` work from any shell.
    Run this script from the repository root:

        .\install.ps1

    To include development tools (pytest, ruff, mypy) pass -Dev:

        .\install.ps1 -Dev
#>
param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"

# Locate python
$python = Get-Command python -ErrorAction SilentlyContinue |
          Select-Object -ExpandProperty Source -First 1
if (-not $python) {
    Write-Error "Python was not found on your PATH. Install Python 3.11+ from https://www.python.org and try again."
    exit 1
}

# Verify minimum version
$ver = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
$parts = $ver -split '\.'
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
    Write-Error "Python 3.11 or newer is required (found $ver)."
    exit 1
}

Write-Host "Using Python $ver ($python)" -ForegroundColor Cyan

if ($Dev) {
    Write-Host "Installing sfcs-mdp with dev dependencies..." -ForegroundColor Cyan
    & $python -m pip install -e ".[dev]"
} else {
    Write-Host "Installing sfcs-mdp..." -ForegroundColor Cyan
    & $python -m pip install -e .
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed."
    exit 1
}

Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
Write-Host "You can now run the CLI with either:" -ForegroundColor Green
Write-Host "  sfcs-mdp <command> [options]" -ForegroundColor Yellow
Write-Host "  python -m sfcs_mdp <command> [options]" -ForegroundColor Yellow
Write-Host ""
Write-Host "Quick start:" -ForegroundColor Cyan
Write-Host "  python -m sfcs_mdp validate" -ForegroundColor White
Write-Host "  python -m sfcs_mdp simulate --build-id BUILD_0001 --rev-tag REV_A" -ForegroundColor White
