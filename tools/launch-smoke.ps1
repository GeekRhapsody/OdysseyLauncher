#Requires -Version 5.1
<#
.SYNOPSIS
    End-to-end launch check: runs the app with --launch against tests/FakeEmulator, in an isolated user folder.
.DESCRIPTION
    Run `dotnet build` first (it builds the fake emulator). The script recreates -UserDir (default
    artifacts/launch-smoke) with a settings.toml, systems.toml and emulators.toml that point the Mega Drive at the
    fake emulator, installed in a folder with spaces and non-ASCII characters, and one ROM. Then it runs

        godot --path godot [--headless] -- --user-dir=<UserDir> --launch=megadrive/<rom> --quit-after-launch

    and checks the exit code and the arguments the fake received. Nothing outside -UserDir is touched.

    -Windowed shows the window, so you can watch the launcher show its running screen and come back; -SleepMs sets
    how long the fake "plays". -Executable runs another build, e.g. the export, instead of `godot --path godot`.
    It runs under PowerShell 7 on Linux too: tools/linux/make-appimage.ps1 runs it against the AppImage there.
.EXAMPLE
    .\tools\launch-smoke.ps1
.EXAMPLE
    .\tools\launch-smoke.ps1 -Windowed -SleepMs 5000 -Executable artifacts/export/windows/OdysseyLauncher.exe
#>
param(
    [string] $UserDir = '',
    [int] $SleepMs = 1500,
    [switch] $Windowed,
    [string] $Executable = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
# Paths are built a part at a time, so they have the OS's separators (Windows PowerShell's Join-Path takes one child).
if (-not $UserDir) { $UserDir = [IO.Path]::Combine($root, 'artifacts', 'launch-smoke') }
$UserDir = [IO.Path]::GetFullPath($UserDir)

$fakeBuild = [IO.Path]::Combine($root, 'tests', 'FakeEmulator', 'bin', 'Debug', 'net8.0')
$fakeName = if ([IO.Path]::DirectorySeparatorChar -eq '\') { 'FakeEmulator.exe' } else { 'FakeEmulator' }
if (-not (Test-Path ([IO.Path]::Combine($fakeBuild, $fakeName)))) { throw "Build the fake emulator first (dotnet build): $fakeBuild" }

function Write-Utf8([string] $Path, [string] $Text) {
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($Path)) | Out-Null
    [IO.File]::WriteAllText($Path, $Text, (New-Object Text.UTF8Encoding $false))
}

# Non-ASCII from code points, because Windows PowerShell reads a script without a BOM as ANSI.
$accented = "$([char]0x00FC)$([char]0x00E9)"            # u-umlaut, e-acute
$japanese = "$([char]0x65E5)$([char]0x672C)"            # "Japan"

if (Test-Path $UserDir) { Remove-Item -Recurse -Force $UserDir }
$emuDir = [IO.Path]::Combine($UserDir, "Emulators $accented $japanese", 'Fake Emu')
New-Item -ItemType Directory -Force $emuDir | Out-Null
Copy-Item ([IO.Path]::Combine($fakeBuild, '*')) $emuDir
$exe = [IO.Path]::Combine($emuDir, $fakeName)
$romRoot = [IO.Path]::Combine($UserDir, "ROMs $accented")
$romName = 'Smoke Test (World).md'
$rom = [IO.Path]::Combine($romRoot, 'megadrive', $romName)
Write-Utf8 $rom 'rom'
$log = [IO.Path]::Combine($UserDir, 'fake-log.json')

Write-Utf8 ([IO.Path]::Combine($UserDir, 'settings.toml')) "[paths]`nrom_root = '$romRoot'`n"
Write-Utf8 ([IO.Path]::Combine($UserDir, 'systems.toml')) "[systems.megadrive]`nemulator = `"fake`"`n"
Write-Utf8 ([IO.Path]::Combine($UserDir, 'emulators.toml')) @"
[emulators.fake]
name = "Fake Emulator"
executable = '$exe'
args = ['--fake-log=$log', '--fake-sleep=$SleepMs', '{rom}', '--stem={rom_stem}']
"@

$appArgs = @('--', "--user-dir=$UserDir", "--launch=megadrive/$romName", '--quit-after-launch')
$engineArgs = @()
if (-not $Windowed) { $engineArgs += '--headless' }

Write-Host "==> Launching megadrive/$romName through the fake emulator ($SleepMs ms)" -ForegroundColor Cyan
$previous = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    if ($Executable) {
        $output = @(& (Resolve-Path $Executable).ProviderPath @engineArgs @appArgs 2>&1 | ForEach-Object { "$_" })
    }
    else {
        $output = @(& godot @engineArgs --path ([IO.Path]::Combine($root, 'godot')) @appArgs 2>&1 | ForEach-Object { "$_" })
    }
    $code = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previous
}

# Config warnings about the built-in profiles' default paths are expected here; only the launch is shown.
$output | Where-Object { $_ -match '^Launch|error' } | ForEach-Object { Write-Host "    $_" }
if ($code -ne 0) {
    $output | ForEach-Object { Write-Host "    $_" }
    throw "The app exited with code $code."
}

if (-not (Test-Path $log)) { throw "The fake emulator didn't run: no $log." }
$seen = [IO.File]::ReadAllText($log, [Text.Encoding]::UTF8) | ConvertFrom-Json
$expected = @("--fake-log=$log", "--fake-sleep=$SleepMs", $rom, '--stem=Smoke Test (World)')
if (Compare-Object $expected @($seen.args) -SyncWindow 0 -CaseSensitive) {
    throw "The fake emulator got the wrong arguments.`n  expected: $($expected -join ' | ')`n  got:      $($seen.args -join ' | ')"
}

if ($seen.cwd -ne $emuDir) { throw "The working folder was '$($seen.cwd)', not '$emuDir'." }
Write-Host 'Launch smoke passed.' -ForegroundColor Green
