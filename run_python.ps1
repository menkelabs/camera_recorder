# Python launcher that uses explicit paths to avoid path issues

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Script,
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$currentDir = Get-Location
$pythonExe = Join-Path $currentDir ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run setup_env.ps1 first to create it." -ForegroundColor Yellow
    exit 1
}

$scriptPath = Join-Path $currentDir $Script

if (-not (Test-Path $scriptPath)) {
    Write-Host "Error: Script not found: $Script" -ForegroundColor Red
    exit 1
}

# Run Python with explicit path
& $pythonExe $scriptPath @Arguments

