#!/usr/bin/env bash
# Builds the solution and runs its tests on Linux (docs/ARCHITECTURE.md decisions log, 2026-11-02), from a copy of the
# working tree in ~/.cache/odyssey-linux/repo: the checkout's own bin/ and obj/ are restored for Windows, so they're
# left alone. Leaves out the scan benchmarks, as release.yml does (their budgets were set on the Deck). Arguments go to
# dotnet test, e.g. --filter-class '*PlatformPathsTests'. Run tools/linux/setup.sh first.
#
#   bash tools/linux/test.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$here/common.sh"
repo="$(cd "$here/../.." && pwd)"
work="$ODYSSEY_LINUX_CACHE/repo"

echo "==> Copying the working tree to $work"
sync_tree "$repo" "$work"
cd "$work"
echo "==> dotnet build"
dotnet build --nologo

# The native libraries the AppImage carries, where the tests load them from (beside Launcher.Core), with the struct
# offsets FfmpegAbiTests compares with the bindings'.
tests_out="$work/tests/Launcher.Core.Tests/bin/Debug/net10.0"
native=("${FFMPEG_LIBS[@]/#/$FFMPEG_DIR/lib/}" "$FFMPEG_DIR/ffmpeg-abi.txt" "$PDFIUM_DIR/lib/libpdfium.so")
for file in "${native[@]}"; do
    if [[ ! -f $file ]]; then
        echo "error: there's no $file: run tools/linux/setup.sh" >&2
        exit 1
    fi
done

cp "${native[@]}" "$tests_out/"
echo "==> dotnet test"
dotnet test --no-build --filter-not-trait "Category=Benchmark" "$@"
