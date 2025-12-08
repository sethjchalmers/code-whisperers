# Code Whisperers - PowerShell Install Script
# Usage: iwr -useb https://raw.githubusercontent.com/sethjchalmers/code-whisperers/master/scripts/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "🎭 Installing Code Whisperers..." -ForegroundColor Cyan

# Check for Python
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -notmatch "Python 3\.(\d+)") {
        throw "Python 3.10+ required"
    }
    $minorVersion = [int]$Matches[1]
    if ($minorVersion -lt 10) {
        throw "Python 3.10+ required (found $pythonVersion)"
    }
} catch {
    Write-Host "❌ Python 3.10+ is required but not found." -ForegroundColor Red
    Write-Host "   Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Install location
$InstallDir = Join-Path $env:USERPROFILE ".code-whisperers"

# Clone or update
if (Test-Path $InstallDir) {
    Write-Host "📦 Updating existing installation..." -ForegroundColor Green
    Push-Location $InstallDir
    git pull --quiet
} else {
    Write-Host "📦 Cloning repository..." -ForegroundColor Green
    git clone --quiet https://github.com/sethjchalmers/code-whisperers.git $InstallDir
    Push-Location $InstallDir
}

# Create virtual environment
Write-Host "🐍 Setting up Python environment..." -ForegroundColor Green
python -m venv .venv
& .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install --quiet --upgrade pip
pip install --quiet -e .

Pop-Location

# Create wrapper script
$BinDir = Join-Path $env:USERPROFILE ".local\bin"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$WrapperScript = Join-Path $BinDir "code-whisperers.ps1"
@"
`$env:VIRTUAL_ENV = "`$env:USERPROFILE\.code-whisperers\.venv"
& "`$env:USERPROFILE\.code-whisperers\.venv\Scripts\python.exe" -m cli.main `$args
"@ | Out-File -FilePath $WrapperScript -Encoding UTF8

# Create batch file wrapper for cmd.exe
$BatchWrapper = Join-Path $BinDir "code-whisperers.cmd"
@"
@echo off
powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\.local\bin\code-whisperers.ps1" %*
"@ | Out-File -FilePath $BatchWrapper -Encoding ASCII

Write-Host ""
Write-Host "✅ Code Whisperers installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Quick Start:" -ForegroundColor Cyan
Write-Host "   code-whisperers review --diff HEAD~1  # Review last commit"
Write-Host "   code-whisperers review --base main     # Review changes vs main"
Write-Host "   code-whisperers review --help          # Show all options"
Write-Host ""
Write-Host "🔑 Set your GitHub token for free AI access:" -ForegroundColor Yellow
Write-Host "   `$env:GITHUB_TOKEN = 'ghp_your_token_here'"
Write-Host ""
Write-Host "📝 Add to your PowerShell profile:" -ForegroundColor Yellow
Write-Host "   `$env:Path += `";`$env:USERPROFILE\.local\bin`""
Write-Host "   `$env:GITHUB_TOKEN = 'ghp_your_token_here'"
