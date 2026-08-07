param(
    [ValidateSet('list', 'all', 'validate', 'docs', 'migration', 'roadmap', 'compact')]
    [string]$Command = 'all',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ForwardedArguments
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$preflight = Join-Path $PSScriptRoot 'codeops-windows-preflight.ps1'
$reserved = @($ForwardedArguments | Where-Object { $_ -eq '--root' -or $_ -like '--root=*' })
if ($reserved.Count -gt 0) {
    [Console]::Error.WriteLine('codeops-verify: --root is fixed by the trusted launcher.')
    exit 2
}
$python = & $preflight -ResolvePython
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($python)) {
    exit 2
}

$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$verifier = Join-Path $PSScriptRoot 'codeops_verify.py'
$nativeErrorActionPreference = $ErrorActionPreference
try {
    # Windows PowerShell converts native stderr into error records. Verification children may
    # legitimately write diagnostics to stderr even when their aggregate result succeeds, so the
    # native exit code remains the authority for this invocation.
    $ErrorActionPreference = 'Continue'
    & $python $verifier $Command --root $root @ForwardedArguments
    $nativeExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $nativeErrorActionPreference
}
exit $nativeExitCode
