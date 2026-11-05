#Requires -Version 5.1
<#
.SYNOPSIS
    Makes the Linux AppImage on Windows (docs/ARCHITECTURE.md decisions log, 2026-11-02): the Linux export here, then
    the AppImage and its checks in a WSL distro.
.DESCRIPTION
    Run `dotnet build` first, as for any export.
    1. Exports the "Linux" preset into artifacts/export/linux, windowed, so the shader baker has a rendering device (it
       bakes Vulkan's shaders). -SkipExport uses the export that's there.
    2. In the WSL distro -Distro (default OdysseyLinux), as root: tools/linux/setup.sh (the pinned tools, once),
       tools/linux/make-appimage.sh (artifacts/linux/OdysseyLauncher-<version>-linux-x86_64.AppImage, its .sha256 and .zsync),
       and tools/linux/smoke.sh against the AppImage, headless. Nothing else in the distro is changed.
.EXAMPLE
    .\tools\linux\make-appimage.ps1
.EXAMPLE
    .\tools\linux\make-appimage.ps1 -SkipExport
#>
param(
    [switch] $SkipExport,
    [string] $Distro = 'OdysseyLinux'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$export = [IO.Path]::Combine($root, 'artifacts', 'export', 'linux')
$version = [regex]::Match([IO.File]::ReadAllText([IO.Path]::Combine($root, 'Directory.Build.props')), '<Version>([^<]+)</Version>').Groups[1].Value
$name = "OdysseyLauncher-$version-linux-x86_64.AppImage"

if (-not $SkipExport) {
    Write-Host '==> Godot export (Linux)' -ForegroundColor Cyan
    New-Item -ItemType Directory -Force $export | Out-Null
    # Native tools write progress to stderr: judge the export by its exit code (as tools/verify.ps1 does).
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = @(& godot --path ([IO.Path]::Combine($root, 'godot')) --export-release 'Linux' ([IO.Path]::Combine($export, 'OdysseyLauncher.x86_64')) 2>&1 | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }

    if ($code -ne 0) {
        $output | ForEach-Object { Write-Host "    $_" }
        throw "The export failed with exit code $code."
    }

    # Baked, the PCK is about 1.2 MB (Vulkan's SPIR-V); an export that baked nothing (a headless one) is about 50 KB.
    $pck = Get-Item ([IO.Path]::Combine($export, 'OdysseyLauncher.pck'))
    if ($pck.Length -lt 512KB) { throw "The PCK is only $($pck.Length) bytes: the shader baker didn't run." }
    Write-Host ("    PCK {0:N2} MB" -f ($pck.Length / 1MB))
}

function Invoke-Linux([string] $Script, [string[]] $Arguments) {
    & wsl.exe -d $Distro -u root --exec bash "$linuxRoot/tools/linux/$Script" @Arguments
    if ($LASTEXITCODE -ne 0) { throw "tools/linux/$Script failed in WSL ($Distro) with exit code $LASTEXITCODE." }
}

# The repo as the distro sees it (/mnt/c/...).
$linuxRoot = (& wsl.exe -d $Distro -u root --exec wslpath -a ($root -replace '\\', '/') | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxRoot) { throw "WSL's $Distro isn't there: install it (wsl --install Ubuntu-24.04 --name $Distro) or pass -Distro." }

Write-Host "==> Linux tools ($Distro)" -ForegroundColor Cyan
Invoke-Linux 'setup.sh' @()
Write-Host "==> AppImage" -ForegroundColor Cyan
Invoke-Linux 'make-appimage.sh' @("$linuxRoot/artifacts/export/linux", "$linuxRoot/artifacts/linux")
Write-Host "==> Checks" -ForegroundColor Cyan
Invoke-Linux 'smoke.sh' @("$linuxRoot/artifacts/linux/$name")
Write-Host "AppImage ready: $([IO.Path]::Combine($root, 'artifacts', 'linux', $name))" -ForegroundColor Green
