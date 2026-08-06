param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('SessionStart', 'PreToolUse')]
    [string]$Event
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($env:PLUGIN_ROOT)) {
    [Console]::Error.WriteLine('CodeOps hook plugin root is unavailable.')
    exit 1
}

$declaredRoot = [System.IO.Path]::GetFullPath($env:PLUGIN_ROOT)
$launcherRoot = [System.IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
if (-not [string]::Equals(
    $declaredRoot,
    $launcherRoot,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    [Console]::Error.WriteLine('CodeOps hook plugin identity is invalid.')
    exit 1
}

$payload = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($payload)) {
    [Console]::Error.WriteLine('CodeOps hook input is invalid.')
    exit 1
}

$bootstrap = Join-Path $PSScriptRoot 'codeops-windows-preflight.ps1'
$hookEntry = Join-Path $PSScriptRoot 'codeops_hooks.py'
$python = & $bootstrap -ResolvePython
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$payload | & $python $hookEntry --event $Event
exit $LASTEXITCODE
