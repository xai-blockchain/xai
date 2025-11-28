[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$NodeArgs
)

$NodeArgs = $NodeArgs
if (-not $NodeArgs) {
    $NodeArgs = @()
}
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $scriptDir "run-python.ps1"

& $runner -m xai.core.node @NodeArgs
