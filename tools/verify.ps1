#Requires -Version 5.1
<#
.SYNOPSIS
    Full local check: build, unit tests, Godot's headless C# build and import, and a headless smoke run.
.DESCRIPTION
    Run from anywhere:  .\tools\verify.ps1
    Needs `godot` (the Godot 4.7.2 .NET console build) on PATH.
    The windowed checks (--capture, --bench) are separate; see CLAUDE.md.
#>
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    function Invoke-Step([string] $Name, [scriptblock] $Command, [string] $MustContain = '') {
        Write-Host "==> $Name" -ForegroundColor Cyan
        # Native tools write progress to stderr. Under 'Stop', Windows PowerShell 5.1 would turn
        # that into terminating errors, so relax it and judge the step by its exit code instead.
        $previous = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $output = @(& $Command 2>&1 | ForEach-Object { "$_" })
            $code = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previous
        }

        $missing = $MustContain -and -not ($output | Where-Object { $_.Contains($MustContain) })
        if ($code -ne 0 -or $missing) {
            $output | ForEach-Object { Write-Host "    $_" }
            if ($code -ne 0) { throw "$Name failed with exit code $code." }
            throw "$Name didn't print '$MustContain'."
        }

        $output | Select-Object -Last 3 | ForEach-Object { Write-Host "    $_" }
    }

    Invoke-Step 'dotnet build' { dotnet build --nologo }
    Invoke-Step 'dotnet test' { dotnet test --no-build }
    Invoke-Step 'Godot C# build (headless)' { godot --headless --path godot --build-solutions --quit }
    Invoke-Step 'Godot import (headless)' { godot --headless --path godot --import }
    Invoke-Step 'Godot smoke run (headless)' { godot --headless --path godot --quit-after 10 } -MustContain 'Launcher.Core'

    Write-Host 'All checks passed.' -ForegroundColor Green
}
finally {
    Pop-Location
}
