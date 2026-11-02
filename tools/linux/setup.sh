#!/usr/bin/env bash
# Installs what the Linux build needs, with no sudo (docs/ARCHITECTURE.md decisions log, 2026-11-02):
#
#   ~/.dotnet                                     the .NET SDK global.json names (its major.minor, the newest patch)
#                                                 and the .NET 8 runtime the tests and the fake emulator run on, by
#                                                 Microsoft's dotnet-install.sh
#   ~/.cache/odyssey-linux/tools/powershell-<v>/  PowerShell 7, for the repo's .ps1 scripts (tools/launch-smoke.ps1)
#   ~/.cache/odyssey-linux/tools/appimagetool-<v>-x86_64.AppImage, runtime-<v>-x86_64
#                                                 appimagetool, and the static AppImage runtime it's given, so the
#                                                 AppImage needs no libfuse2 (tools/linux/make-appimage.sh)
#
# The downloads are pinned in tools/linux/common.sh. What's already there is kept, so run it again at any time.
#
#   bash tools/linux/setup.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$here/common.sh"
repo="$(cd "$here/../.." && pwd)"

echo "==> .NET into $DOTNET_ROOT"
installer="$TOOLS_DIR/dotnet-install.sh"
mkdir -p "$TOOLS_DIR"
curl --fail --location --silent --show-error --output "$installer" https://dot.net/v1/dotnet-install.sh
sdk_channel="$(sed -n 's/.*"version": *"\([0-9]*\.[0-9]*\)\..*/\1/p' "$repo/global.json" | head -n 1)"
bash "$installer" --channel "$sdk_channel" --install-dir "$DOTNET_ROOT" --no-path
bash "$installer" --channel 8.0 --runtime dotnet --install-dir "$DOTNET_ROOT" --no-path

echo "==> PowerShell $POWERSHELL_VERSION"
tarball="$TOOLS_DIR/powershell-$POWERSHELL_VERSION-linux-x64.tar.gz"
fetch "https://github.com/PowerShell/PowerShell/releases/download/v$POWERSHELL_VERSION/powershell-$POWERSHELL_VERSION-linux-x64.tar.gz" \
    "$POWERSHELL_SHA256" "$tarball"
if [[ ! -x $PWSH ]]; then
    rm -rf "$(dirname "$PWSH")"
    mkdir -p "$(dirname "$PWSH")"
    tar -xzf "$tarball" -C "$(dirname "$PWSH")"
    chmod +x "$PWSH"
fi

echo "==> appimagetool $APPIMAGETOOL_VERSION and the runtime $RUNTIME_VERSION"
fetch "https://github.com/AppImage/appimagetool/releases/download/$APPIMAGETOOL_VERSION/appimagetool-x86_64.AppImage" \
    "$APPIMAGETOOL_SHA256" "$APPIMAGETOOL"
chmod +x "$APPIMAGETOOL"
fetch "https://github.com/AppImage/type2-runtime/releases/download/$RUNTIME_VERSION/runtime-x86_64" \
    "$RUNTIME_SHA256" "$APPIMAGE_RUNTIME"

dotnet --list-sdks
dotnet --list-runtimes | grep Microsoft.NETCore.App
"$PWSH" -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
echo "Linux tools ready."
