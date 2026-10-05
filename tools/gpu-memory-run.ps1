#Requires -Version 5.1
<#
.SYNOPSIS
    Runs an export for a fixed time while sampling its GPU memory as Windows sees it, once a second.
.DESCRIPTION
    Spike tool (docs/perf/spike-direct-images.md). Starts -Executable with --memory-log (the app's own view: Godot's
    video, texture and buffer memory, and what it's doing) and the given -AppArgs, and samples the process's
    "GPU Process Memory" counters (dedicated, shared, total committed) and its working set into gpu.csv beside the
    app's memory.csv. After -Seconds it closes the window. Not for frame-time runs: polling performance counters
    adds hitches (ARCHITECTURE.md A3).
.EXAMPLE
    .\tools\gpu-memory-run.ps1 -Executable artifacts/export-poc/windows/OdysseyLauncher.exe -Out artifacts/poc-bench/mem-poc `
        -AppArgs "--user-dir=$PWD\artifacts\poc-bench\user", '--start-system=megadrive', '--nav-script=pagedown,accept'
#>
param(
    [Parameter(Mandatory)] [string] $Executable,
    [Parameter(Mandatory)] [string] $Out,
    [string[]] $AppArgs = @(),
    [string[]] $EngineArgs = @('--resolution', '1280x800'),
    [ValidateRange(5, 3600)] [int] $Seconds = 90
)
$ErrorActionPreference = 'Stop'
$exe = [IO.Path]::GetFullPath($Executable)
$Out = [IO.Path]::GetFullPath($Out)
New-Item -ItemType Directory -Force $Out | Out-Null
$memoryLog = Join-Path $Out 'memory.csv'
$gpuLog = Join-Path $Out 'gpu.csv'

$arguments = $EngineArgs + @('--') + @(('"--memory-log={0}"' -f $memoryLog)) + ($AppArgs | ForEach-Object { '"{0}"' -f $_ })
$process = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru
$null = $process.Handle
$id = $process.Id
$counters = @('Dedicated Usage', 'Shared Usage', 'Total Committed') | ForEach-Object { "\GPU Process Memory(pid_${id}_*)\$_" }
$lines = [Collections.Generic.List[string]]::new()
$lines.Add('utc,dedicated_mb,shared_mb,committed_mb,working_set_mb')
$end = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $end -and -not $process.HasExited) {
    $at = [DateTime]::UtcNow.ToString('O')
    $values = @{ 'dedicated usage' = 0.0; 'shared usage' = 0.0; 'total committed' = 0.0 }
    try {
        # One instance per adapter and memory segment set; the process's figures are their sum.
        foreach ($s in (Get-Counter $counters -ErrorAction SilentlyContinue).CounterSamples) {
            $name = ($s.Path -split '\\')[-1]
            $values[$name] += $s.CookedValue
        }
    }
    catch { }
    $process.Refresh()
    $lines.Add([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0},{1:0.0},{2:0.0},{3:0.0},{4:0.0}', $at,
        $values['dedicated usage'] / 1MB, $values['shared usage'] / 1MB, $values['total committed'] / 1MB, $process.WorkingSet64 / 1MB))
    Start-Sleep -Milliseconds 1000
}

if (-not $process.HasExited) {
    $null = $process.CloseMainWindow()
    if (-not $process.WaitForExit(10000)) { Stop-Process -Id $id -Force }
}
[IO.File]::WriteAllLines($gpuLog, $lines)
Write-Host "Samples: $($lines.Count - 1) -> $gpuLog; app log: $memoryLog"
