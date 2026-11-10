#!/usr/bin/env bash
# Installs what the Linux build needs (docs/ARCHITECTURE.md decisions log, 2026-11-02), as root in WSL's distro, or as a
# user with sudo for apt (the Release workflow's runner: decisions log, 2026-11-05):
#
#   ~/.dotnet                                     the .NET SDK global.json names (its major.minor, the newest patch),
#                                                 with the runtime the tests and the fake emulator run on, by
#                                                 Microsoft's dotnet-install.sh
#   ~/.cache/odyssey-linux/tools/powershell-<v>/  PowerShell 7, for the repo's .ps1 scripts (tools/launch-smoke.ps1)
#   ~/.cache/odyssey-linux/tools/appimagetool-<v>-x86_64.AppImage, runtime-<v>-x86_64
#                                                 appimagetool, and the static AppImage runtime it's given, so the
#                                                 AppImage needs no libfuse2 (tools/linux/make-appimage.sh)
#   gcc, make, nasm, pkg-config, binutils,        Ubuntu's packages, by apt, those missing: the C tools for FFmpeg,
#   zsync, appstream, fuse3                       objdump for the glibc floor check, zsyncmake for the AppImage's
#                                                 .zsync file, appstreamcli for its AppStream metadata, and
#                                                 fusermount3 to mount it in smoke.sh as a user
#   ~/.cache/odyssey-linux/native/ffmpeg-<v>/     FFmpeg for videos (L4): its libraries (lib/), headers, licence,
#                                                 how it was configured (recipe.txt), and ffmpeg-abi.txt, the struct
#                                                 offsets FfmpegAbiTests checks; built from its source tarball, in
#                                                 about a minute and a half, only when the recipe changes
#   ~/.cache/odyssey-linux/native/pdfium-<build>/ PDFium for manuals (L4): pdfium-binaries' libpdfium.so (lib/),
#                                                 its licences and its VERSION
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

echo "==> The C and packaging tools (Ubuntu's packages)"
# Each tool, and the package that has it.
packages=()
for pair in gcc:gcc make:make nasm:nasm pkg-config:pkg-config objdump:binutils zsyncmake:zsync appstreamcli:appstream     fusermount3:fuse3; do
    command -v "${pair%%:*}" > /dev/null || packages+=("${pair#*:}")
done

if (( ${#packages[@]} )); then
    as_root=()
    (( EUID == 0 )) || as_root=(sudo)
    "${as_root[@]}" env DEBIAN_FRONTEND=noninteractive apt-get update -qq
    "${as_root[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends libc6-dev "${packages[@]}" > /dev/null
fi

echo "==> FFmpeg $FFMPEG_VERSION (LGPL, decoders only) into $FFMPEG_DIR"
recipe="$(ffmpeg_recipe)"
if [[ ! -f $FFMPEG_DIR/recipe.txt || $(< "$FFMPEG_DIR/recipe.txt") != "$recipe" ]]; then
    # Fetched only for a build, so a cached build (release.yml) downloads nothing.
    tarball="$TOOLS_DIR/ffmpeg-$FFMPEG_VERSION.tar.xz"
    fetch "https://ffmpeg.org/releases/ffmpeg-$FFMPEG_VERSION.tar.xz" "$FFMPEG_SHA256" "$tarball"
    build="$ODYSSEY_LINUX_CACHE/build/ffmpeg-$FFMPEG_VERSION"
    rm -rf "$build" "$FFMPEG_DIR"
    mkdir -p "$build" "$FFMPEG_DIR/lib"
    tar -xJf "$tarball" -C "$build" --strip-components=1
    # The header by a relative name, so no path of this machine's ends up in the libraries' configuration string.
    cp "$here/glibc-floor.h" "$build/"
    (
        cd "$build"
        ./configure --prefix="$build/install" "${FFMPEG_CONFIGURE[@]}" --extra-cflags="-include glibc-floor.h" > configure.log 2>&1 \
            || { tail -n 30 configure.log; exit 1; }
        make -j"$(nproc)" > make.log 2>&1 || { tail -n 30 make.log; exit 1; }
        make install > /dev/null
    )
    for lib in "${FFMPEG_LIBS[@]}"; do
        cp -L "$build/install/lib/$lib" "$FFMPEG_DIR/lib/"
    done

    cp -r "$build/install/include" "$FFMPEG_DIR/"
    cp "$build/COPYING.LGPLv2.1" "$FFMPEG_DIR/"
    echo "$recipe" > "$FFMPEG_DIR/recipe.txt"
fi

check_glibc_floor "$FFMPEG_DIR"/lib/*
mkdir -p "$ODYSSEY_LINUX_CACHE/build"
gcc -Wall -Werror -I"$FFMPEG_DIR/include" "$here/ffmpeg-abi.c" -o "$ODYSSEY_LINUX_CACHE/build/ffmpeg-abi"
"$ODYSSEY_LINUX_CACHE/build/ffmpeg-abi" > "$FFMPEG_DIR/ffmpeg-abi.txt"

echo "==> PDFium $PDFIUM_BUILD into $PDFIUM_DIR"
tarball="$TOOLS_DIR/pdfium-$PDFIUM_BUILD-linux-x64.tgz"
fetch "https://github.com/bblanchon/pdfium-binaries/releases/download/chromium%2F$PDFIUM_BUILD/pdfium-linux-x64.tgz"     "$PDFIUM_SHA256" "$tarball"
if [[ ! -f $PDFIUM_DIR/lib/libpdfium.so ]]; then
    rm -rf "$PDFIUM_DIR"
    mkdir -p "$PDFIUM_DIR"
    tar -xzf "$tarball" -C "$PDFIUM_DIR" lib/libpdfium.so LICENSE licenses VERSION
fi

check_glibc_floor "$PDFIUM_DIR/lib/libpdfium.so"

dotnet --list-sdks
dotnet --list-runtimes | grep Microsoft.NETCore.App
"$PWSH" -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
echo "Linux tools ready."
