[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PythonArgs
)

if (-not $PythonArgs -or $PythonArgs.Count -eq 0) {
    Write-Host "Usage: .\run-python.ps1 <module or script> [args]"
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$projectSrc = Join-Path $repoRoot "src"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$projectSrc;$env:PYTHONPATH"
}
else {
    $env:PYTHONPATH = $projectSrc
}

function Invoke-PythonCommand {
    param (
        [string]$Command,
        [string[]]$Arguments
    )

    if ($Command -eq "py -3") {
        & py -3 @Arguments
    }
    else {
        & $Command @Arguments
    }
}

$pythonCandidates = @()
if ($env:PYTHON_CMD) {
    $pythonCandidates += $env:PYTHON_CMD
}
$pythonCandidates += @("python", "python3", "py -3")

$pythonFound = $false
foreach ($candidate in $pythonCandidates) {
    if ($candidate -eq "py -3") {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            Invoke-PythonCommand -Command $candidate -Arguments $PythonArgs
            $pythonFound = $true
            break
        }
    }
    elseif (Get-Command $candidate -ErrorAction SilentlyContinue) {
        Invoke-PythonCommand -Command $candidate -Arguments $PythonArgs
        $pythonFound = $true
        break
    }
}

if (-not $pythonFound) {
    Write-Error "Python interpreter not found. Install Python 3.10+ or set PYTHON_CMD."
    exit 1
}
