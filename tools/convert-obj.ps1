<#
.SYNOPSIS
  Converts Wavefront OBJ models to launcher-ready GLBs in bulk, then checks each with odyssey-scrape.

.DESCRIPTION
  For every .obj under -Path (or the one file given), runs Blender headless (tools/convert-obj/obj_to_glb.py)
  to import it, put the origin at the bottom centre, apply transforms and export a GLB with the settings in
  docs/THEMING.md section 9. It then runs `odyssey-scrape inspect-model --kind=<Kind>` on the GLB. The MTL and
  textures are found next to the OBJ. Needs `dotnet build` first, for the inspector.

.EXAMPLE
  .\tools\convert-obj.ps1 -Path D:\models -Kind system
  .\tools\convert-obj.ps1 -Path D:\models -OutDir D:\glb -Kind game -Height 1 -Force
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Path,
    [string]$OutDir,                                   # default: the GLB goes next to its OBJ
    [ValidateSet('game', 'template', 'system')][string]$Kind = 'game',
    [double]$Height = 0,                               # scale to this many metres tall; 0 leaves the size alone
    [string]$Blender,                                  # default: newest under Program Files\Blender Foundation
    [switch]$Force,                                    # overwrite existing GLBs
    [switch]$NoInspect
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$script = Join-Path $PSScriptRoot 'convert-obj\obj_to_glb.py'
$inspector = Join-Path $repo 'tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe'

if (-not $Blender) {
    $Blender = Get-ChildItem 'C:\Program Files\Blender Foundation\Blender *\blender.exe' -ErrorAction SilentlyContinue |
        Sort-Object { [version]($_.Directory.Name -replace '^Blender ', '') } -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $Blender -or -not (Test-Path $Blender)) { throw 'Blender not found. Pass -Blender <path to blender.exe>.' }
if (-not $NoInspect -and -not (Test-Path $inspector)) { throw "Inspector not built: run 'dotnet build' first, or pass -NoInspect." }

$root = (Resolve-Path $Path).Path
$files = if (Test-Path $root -PathType Leaf) { Get-Item $root } else { Get-ChildItem $root -Recurse -Filter *.obj }
if (-not $files) { throw "No .obj files under $root." }
$base = if (Test-Path $root -PathType Leaf) { Split-Path $root -Parent } else { $root }

$results = foreach ($f in $files) {
    $rel = $f.FullName.Substring($base.TrimEnd('\').Length).TrimStart('\')
    $glb = if ($OutDir) { Join-Path $OutDir ([IO.Path]::ChangeExtension($rel, '.glb')) } else { [IO.Path]::ChangeExtension($f.FullName, '.glb') }
    New-Item -ItemType Directory -Force (Split-Path $glb -Parent) | Out-Null

    $status = 'OK'; $detail = ''
    if ((Test-Path $glb) -and -not $Force) {
        $status = 'SKIPPED'; $detail = 'exists (use -Force)'
    }
    else {
        $blenderArgs = @('--background', '--factory-startup', '--python', $script, '--', $f.FullName, $glb)
        if ($Height -gt 0) { $blenderArgs += "--height=$Height" }
        $out = & $Blender @blenderArgs 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $glb)) {
            $status = 'FAILED'; $detail = 'Blender: ' + (($out -split "`n" | Where-Object { $_ -match 'Error|obj_to_glb' } | Select-Object -Last 2) -join ' ').Trim()
        }
        elseif (-not $NoInspect) {
            $report = & $inspector "inspect-model" "--kind=$Kind" $glb 2>&1 | Out-String
            if ($LASTEXITCODE -ne 0) { $status = 'REJECTED' }
            $detail = (($report -split "`n" | Where-Object { $_ -match 'error|warn|triangles|reject' } | ForEach-Object { $_.Trim() }) -join '; ')
        }
    }
    Write-Host ('{0,-9} {1}  {2}' -f $status, $rel, $detail)
    [pscustomobject]@{ Status = $status; Source = $rel; Glb = $glb; Detail = $detail }
}

Write-Host ''
$results | Group-Object Status | ForEach-Object { Write-Host ('{0}: {1}' -f $_.Name, $_.Count) }
if ($results | Where-Object { $_.Status -in 'FAILED', 'REJECTED' }) { exit 1 }
