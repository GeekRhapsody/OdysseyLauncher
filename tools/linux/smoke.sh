#!/usr/bin/env bash
# Checks an AppImage (or a Linux export's binary) headless, on Linux: a smoke run that prints the Launcher.Core line,
# and tools/launch-smoke.ps1, run with PowerShell 7 against it (a --launch of the fake emulator, built here for
# Linux, in an isolated user folder). Run tools/linux/setup.sh first.
#
#   bash tools/linux/smoke.sh <AppImage or binary>
#
# The AppImage is mounted read-only, as on a desktop (WSL 2.7's root has FUSE). Where there's no FUSE, set
# APPIMAGE_EXTRACT_AND_RUN=1: the runtime then unpacks it into /tmp and runs it from there.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$here/common.sh"
repo="$(cd "$here/../.." && pwd)"
if [[ $# -ne 1 ]]; then
    echo "usage: smoke.sh <AppImage or binary>" >&2
    exit 2
fi

program="$(readlink -f "$1")"
work="$ODYSSEY_LINUX_CACHE/repo"
echo "==> The fake emulator, built for Linux in $work"
sync_tree "$repo" "$work"
dotnet build "$work/tests/FakeEmulator" --nologo -v quiet

echo "==> Smoke run (headless)"
if ! output="$("$program" --headless --quit-after 10 2>&1)" || ! grep -q 'Launcher.Core' <<< "$output"; then
    echo "$output"
    echo "error: the smoke run failed, or printed no Launcher.Core line" >&2
    exit 1
fi

grep 'Launcher.Core' <<< "$output" | sed 's/^/    /'
echo "==> Launch smoke run (headless)"
"$PWSH" -NoProfile -File "$work/tools/launch-smoke.ps1" -Executable "$program"
