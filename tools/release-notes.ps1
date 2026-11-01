#Requires -Version 5.1
<#
.SYNOPSIS
    Prints one version's notes from CHANGELOG.md: what goes on its GitHub release page.
.DESCRIPTION
    A version's notes are everything under its heading ("## 0.21.0", optionally followed by a date,
    "## 0.21.0 (2026-11-02)") up to the next "## " heading, trimmed. It fails when the version has no
    heading or nothing under it, so a release can't go out without notes.

    release.ps1 checks the notes before it tags; the Release workflow puts them on the release.
.PARAMETER Version
    The version, such as 0.21.0 or 0.21.0-beta.1. A leading 'v' is ignored.
.PARAMETER Changelog
    The changelog to read. Default: CHANGELOG.md at the repository's root.
.PARAMETER Text
    The changelog's text, instead of reading a file (release.ps1 checks what it's about to write).
.PARAMETER Out
    Writes the notes to this file (UTF-8, no BOM) instead of printing them.
.EXAMPLE
    .\tools\release-notes.ps1 0.21.0
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [string] $Version,
    [string] $Changelog = (Join-Path $PSScriptRoot '..\CHANGELOG.md'),
    [string] $Text,
    [string] $Out
)

$ErrorActionPreference = 'Stop'
$Version = $Version.Trim() -replace '^v', ''
if (-not $PSBoundParameters.ContainsKey('Text')) {
    if (-not (Test-Path $Changelog)) { throw "No changelog at $Changelog." }
    $Text = [System.IO.File]::ReadAllText((Resolve-Path $Changelog))
}

$lines = $Text -replace "`r`n", "`n" -split "`n"
$notes = $null
foreach ($line in $lines) {
    if ($line -match '^##\s+v?(?<version>\S+)') {
        if ($null -ne $notes) { break }
        if ($Matches['version'] -eq $Version) { $notes = New-Object System.Collections.Generic.List[string] }
        continue
    }

    if ($null -ne $notes) { $notes.Add($line) }
}

if ($null -eq $notes) { throw "CHANGELOG.md has no '## $Version' section: add the release's notes there (or under '## Unreleased', which release.ps1 names)." }
$body = ($notes -join "`n").Trim()
if ($body.Length -eq 0) { throw "CHANGELOG.md's '## $Version' section is empty." }

if ($Out) {
    $folder = Split-Path -Parent $Out
    if ($folder) { New-Item -ItemType Directory -Force $folder | Out-Null }
    [System.IO.File]::WriteAllText($Out, $body + "`n", (New-Object System.Text.UTF8Encoding $false))
}
else {
    $body
}
