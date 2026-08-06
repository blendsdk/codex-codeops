param(
    [ValidateSet('list', 'all', 'validate', 'docs', 'migration', 'roadmap', 'compact')]
    [string]$Command = 'all',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ForwardedArguments
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$preflight = Join-Path $PSScriptRoot 'codeops-windows-preflight.ps1'
$python = & $preflight -ResolvePython
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($python)) {
    exit 2
}

$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$verifier = Join-Path $PSScriptRoot 'codeops_verify.py'
& $python $verifier $Command --root $root @ForwardedArguments
exit $LASTEXITCODE
