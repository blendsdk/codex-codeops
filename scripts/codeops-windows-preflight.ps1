param(
    [switch]$ResolvePython
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

function Find-CodeOpsPython {
    $candidates = @(
        @{ Name = 'py'; Prefix = @('-3') },
        @{ Name = 'python'; Prefix = @() }
    )

    foreach ($candidate in $candidates) {
        $command = Get-Command -Name $candidate.Name -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -eq $command) {
            continue
        }

        $probeArguments = @($candidate.Prefix) + @(
            '-c',
            'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
        )
        $probeArguments[-1] = (
            'import sys; print(sys.executable); ' +
            'raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
        )
        try {
            $probeOutput = @(& $command.Source @probeArguments 2>$null)
        }
        catch {
            continue
        }
        if ($LASTEXITCODE -eq 0 -and $probeOutput.Count -gt 0) {
            $executable = [string]$probeOutput[-1]
            if ([System.IO.Path]::IsPathRooted($executable) -and (Test-Path -LiteralPath $executable)) {
                return @{ Path = [System.IO.Path]::GetFullPath($executable) }
            }
        }
    }

    return $null
}

$python = Find-CodeOpsPython
if ($null -eq $python) {
    [Console]::Error.WriteLine(
        'CodeOps requires Python 3.10 or newer. Install it and make py -3 or python available.'
    )
    exit 2
}

if ($ResolvePython) {
    Write-Output $python.Path
    exit 0
}

$preflight = Join-Path $PSScriptRoot 'codeops_windows_preflight.py'
& $python.Path $preflight @args
exit $LASTEXITCODE
