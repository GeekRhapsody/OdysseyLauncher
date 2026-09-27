#Requires -Version 5.1
<#
.SYNOPSIS
    Exports an ExportRelease build and benchmarks it: one warm-up run, then several measured runs.
.DESCRIPTION
    Each run starts the exported app with --bench, waits for it to quit and reads its JSON report.
    Reports land in artifacts/bench/<timestamp>/ (gitignored). Windowed only: every run shows the
    app for its startup plus Frames / refresh-rate seconds.
.EXAMPLE
    .\tools\bench-export.ps1
.EXAMPLE
    .\tools\bench-export.ps1 -SkipExport -Fullscreen -Frames 600
.EXAMPLE
    .\tools\bench-export.ps1 -SkipExport -Label vulkan -EngineArgs '--rendering-driver', 'vulkan'
#>
param(
    [ValidateRange(1, 50)] [int] $Runs = 5,
    [ValidateRange(1, 1000000)] [int] $Frames = 120,
    [ValidatePattern('^\d+x\d+$')] [string] $Resolution = '1280x800',
    [switch] $Fullscreen,
    [switch] $SkipExport,
    # Extra engine arguments, placed before the user arguments (e.g. --rendering-method mobile).
    [string[]] $EngineArgs = @(),
    # Appended to the report folder name, to tell experiments apart.
    [ValidatePattern('^[A-Za-z0-9_-]*$')] [string] $Label = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $root 'artifacts\export\windows\OdysseyLauncher.exe'

if (-not $SkipExport) {
    New-Item -ItemType Directory -Force (Split-Path -Parent $exe) | Out-Null
    Write-Host '==> Exporting ExportRelease build' -ForegroundColor Cyan
    # Godot writes progress to stderr, so judge the export by its exit code (as verify.ps1 does).
    $ErrorActionPreference = 'Continue'
    $output = @(godot --headless --path (Join-Path $root 'godot') --export-release 'Windows Desktop' $exe 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($code -ne 0) {
        $output | ForEach-Object { Write-Host "    $_" }
        throw "Export failed with exit code $code."
    }
}

if (-not (Test-Path $exe)) {
    throw "No export at $exe. Run without -SkipExport first."
}

$folder = Get-Date -Format 'yyyyMMdd-HHmmss'
if ($Label) {
    $folder += "-$Label"
}

$reports = Join-Path $root "artifacts\bench\$folder"
New-Item -ItemType Directory -Force $reports | Out-Null
$display = if ($Fullscreen) { @('--fullscreen') } else { @('--resolution', $Resolution) }
$display += $EngineArgs

$rows = @()
for ($run = 0; $run -le $Runs; $run++) {
    $phase = if ($run -eq 0) { 'warm-up' } else { "run $run of $Runs" }
    Write-Host "==> Bench $phase" -ForegroundColor Cyan
    $json = Join-Path $reports ('run-{0}.json' -f $run)
    $arguments = $display + @('--', ('"--bench={0}"' -f $json), "--bench-frames=$Frames")
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "The app exited with code $($process.ExitCode). See the log in %APPDATA%\Godot\app_userdata\Odyssey Launcher\logs."
    }

    if ($run -eq 0) {
        continue
    }

    $report = Get-Content $json -Raw | ConvertFrom-Json
    if ($null -eq $report.app_startup_ms) {
        throw "Run $run has no app_startup_ms: the interactive mark was never recorded."
    }

    $rows += [pscustomobject]@{
        Run             = $run
        # The 1 s target covers our code only: first autoload's _EnterTree -> interactive.
        OurCodeMs       = [math]::Round($report.app_startup_ms, 1)
        BeforeOurCodeMs = [math]::Round($report.startup_ms.autoload_enter_tree, 1)
        TotalMs         = [math]::Round($report.startup_ms.interactive, 1)
        MeanMs          = [math]::Round($report.frames.mean_ms, 2)
        P99Ms           = [math]::Round($report.frames.p99_ms, 2)
        MaxMs           = [math]::Round($report.frames.max_ms, 2)
        Hitches         = $report.frames.hitch_count
        GpuMs           = [math]::Round($report.render_ms.gpu_mean_ms, 2)
    }
}

$rows | Format-Table -AutoSize | Out-String | Write-Host

function Get-Median([double[]] $values) {
    $sorted = @($values | Sort-Object)
    $middle = [int][math]::Floor($sorted.Count / 2)
    if ($sorted.Count % 2 -eq 1) { return $sorted[$middle] }
    return ($sorted[$middle - 1] + $sorted[$middle]) / 2
}

$ourCode = Get-Median @($rows | ForEach-Object { $_.OurCodeMs })
$beforeOurCode = Get-Median @($rows | ForEach-Object { $_.BeforeOurCodeMs })
$total = Get-Median @($rows | ForEach-Object { $_.TotalMs })
$first = Get-Content (Join-Path $reports 'run-1.json') -Raw | ConvertFrom-Json
$verdict = if ($ourCode -lt 1000) { 'within' } else { 'OVER' }
Write-Host ('Median start-up of our code (first autoload -> interactive): {0} ms, {1} the 1000 ms target.' -f $ourCode, $verdict) -ForegroundColor Green
Write-Host ('Median engine and .NET start-up before our code: {0} ms; process start -> interactive: {1} ms.' -f $beforeOurCode, $total)
Write-Host ('{0} warm runs, {1}/{2}, {3}x{4}, {5:N2} Hz, {6}, {7}.' -f $Runs, $first.machine.rendering_method, `
    $first.machine.rendering_driver, $first.display.window_width, $first.display.window_height, $first.display.refresh_hz, `
    $first.dotnet_version, $first.app_version)
Write-Host "Reports: $reports"
