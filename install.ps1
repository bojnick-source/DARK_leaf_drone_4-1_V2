<#
.SYNOPSIS
    Install DARK leaf Drone — Vibe Engineering Studio.
.DESCRIPTION
    Installs the sfcs-mdp package in the current Python environment so that
    both ``sfcs-mdp`` and ``python -m sfcs_mdp`` work from any shell.
    Run this script from the repository root:

        .\install.ps1

    To include development tools (pytest, ruff, mypy) pass -Dev:

        .\install.ps1 -Dev

    To build a standalone .exe (no Python install needed to run it):

        .\install.ps1 -Exe

    To also build the C++ v2 engine (requires CMake and a C++20 compiler):

        .\install.ps1 -Cpp

    To create a desktop shortcut after installation:

        .\install.ps1 -Shortcut
#>
param(
    [switch]$Dev,
    [switch]$Exe,
    [switch]$Cpp,
    [switch]$Shortcut
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

if ($Exe) {
    Write-Host ""
    Write-Host "Building standalone .exe ..." -ForegroundColor Cyan
    & $python -m pip install ".[exe]"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install PyInstaller."
        exit 1
    }
    & $python build_exe.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "EXE build failed."
        exit 1
    }
    Write-Host ""
    Write-Host "Standalone executable created in dist/sfcs-mdp.exe" -ForegroundColor Green
    Write-Host "You can copy dist\sfcs-mdp.exe anywhere and run it without Python." -ForegroundColor Green
}

if ($Cpp) {
    Write-Host ""
    Write-Host "Building C++ v2 engine ..." -ForegroundColor Cyan
    $cmake = Get-Command cmake -ErrorAction SilentlyContinue |
             Select-Object -ExpandProperty Source -First 1
    if (-not $cmake) {
        Write-Error "CMake was not found on your PATH. Install CMake 3.20+ from https://cmake.org and try again."
        exit 1
    }
    & $cmake -S . -B build -DENABLE_V2_ENGINE=ON
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake configure failed."
        exit 1
    }
    & $cmake --build build --config Release
    if ($LASTEXITCODE -ne 0) {
        Write-Error "C++ build failed."
        exit 1
    }
    Write-Host ""
    Write-Host "C++ v2 engine built successfully." -ForegroundColor Green
    Write-Host "Use the integrated workflow:" -ForegroundColor Cyan
    Write-Host "  python -m sfcs_mdp simulate --build-id BUILD_0001 --rev-tag REV_A --engine-cli build/v2/engine/v2_engine_cli" -ForegroundColor White
}

# ── Desktop shortcut ──────────────────────────────────────────────────
if ($Shortcut) {
    Write-Host ""
    Write-Host "Creating desktop shortcut..." -ForegroundColor Cyan
    $repoRoot   = (Get-Location).Path
    $launcherHtml = Join-Path $repoRoot "ui" "launcher.html"
    $iconPath    = Join-Path $repoRoot "ui" "icon.svg"

    if (-not (Test-Path $launcherHtml)) {
        Write-Warning "ui/launcher.html not found — skipping shortcut."
    } else {
        $desktop = [Environment]::GetFolderPath("Desktop")
        $lnkPath = Join-Path $desktop "DARK leaf Drone.url"

        # Create a .url shortcut (works for browser-based apps)
        @"
[InternetShortcut]
URL=file:///$($launcherHtml -replace '\\','/')
IconIndex=0
"@ | Out-File -FilePath $lnkPath -Encoding ASCII

        Write-Host "Desktop shortcut created: $lnkPath" -ForegroundColor Green
        Write-Host "Double-click 'DARK leaf Drone' on your desktop to launch the studio." -ForegroundColor Green
    }
}

# ── Final summary ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== DARK leaf Drone — Vibe Engineering Studio ===" -ForegroundColor Cyan
Write-Host "Launch the studio:  open ui/launcher.html in your browser" -ForegroundColor White
Write-Host "  or run:  cd ui && python -m http.server" -ForegroundColor White
Write-Host "  then open:  http://localhost:8000/launcher.html" -ForegroundColor White
