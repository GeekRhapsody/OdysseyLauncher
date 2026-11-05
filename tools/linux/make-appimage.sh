#!/usr/bin/env bash
# Packages a Linux export into an AppImage (docs/ARCHITECTURE.md decisions log, 2026-11-02): the export's binary, PCK,
# .NET data folder and themes in usr/bin, the FFmpeg setup.sh builds and PDFium in usr/lib (L4), with FFmpeg's licence
# and how to get its source in usr/share/licenses/ffmpeg and PDFium's licences in usr/share/licenses/pdfium, with AppRun,
# the desktop entry, the icon and the AppStream metadata (APP_ID in common.sh, checked by appstreamcli), squashed by
# appimagetool with the static type2 runtime, so the AppImage needs no libfuse2, and with zsync's update information,
# for AppImageUpdate and the like (decisions log, 2026-11-05). Every ELF file in it is checked against the glibc floor
# (GLIBC_FLOOR in common.sh). Run tools/linux/setup.sh first. On Windows, tools/linux/make-appimage.ps1 does the
# export, then this and the smoke test through WSL.
#
#   bash tools/linux/make-appimage.sh <export folder> <out folder>
#
# Writes <out folder>/OdysseyLauncher-<version>-linux-x86_64.AppImage, the version from Directory.Build.props, its
# .sha256 as release.yml writes the zip's, and its .zsync, which the release carries beside it. The AppDir is built in ~/.cache/odyssey-linux, on Linux's own filesystem:
# an export on /mnt/c has no file modes, and squashing from it is slow.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$here/common.sh"
repo="$(cd "$here/../.." && pwd)"
if [[ $# -ne 2 ]]; then
    echo "usage: make-appimage.sh <export folder> <out folder>" >&2
    exit 2
fi

export_dir="$(cd "$1" && pwd)"
out_dir="$2"
version="$(sed -n 's:.*<Version>\(.*\)</Version>.*:\1:p' "$repo/Directory.Build.props" | head -n 1)"
name="OdysseyLauncher-$version-linux-x86_64.AppImage"
data=("$export_dir"/data_OdysseyLauncher_*_x86_64)
for needed in "$export_dir/OdysseyLauncher.x86_64" "$export_dir/OdysseyLauncher.pck" "${data[0]}" "$export_dir/themes/memory-card/theme.toml"; do
    if [[ ! -e $needed ]]; then
        echo "error: the export in $export_dir has no ${needed#"$export_dir/"}" >&2
        exit 1
    fi
done

ffmpeg_libs=("${FFMPEG_LIBS[@]/#/$FFMPEG_DIR/lib/}")
for needed in "${ffmpeg_libs[@]}" "$FFMPEG_DIR/COPYING.LGPLv2.1" "$FFMPEG_DIR/recipe.txt" "$PDFIUM_DIR/lib/libpdfium.so" "$PDFIUM_DIR/licenses/pdfium.txt"; do
    if [[ ! -f $needed ]]; then
        echo "error: there's no $needed: run tools/linux/setup.sh" >&2
        exit 1
    fi
done

app_dir="$ODYSSEY_LINUX_CACHE/AppDir"
echo "==> The AppDir, in $app_dir"
rm -rf "$app_dir"
mkdir -p "$app_dir/usr/bin"
cp -r "$export_dir/OdysseyLauncher.x86_64" "$export_dir/OdysseyLauncher.pck" "${data[0]}" "$export_dir/themes" "$app_dir/usr/bin/"
cp "$here/AppRun" "$here/$APP_ID.desktop" "$here/odyssey-launcher.png" "$app_dir/"
ln -s odyssey-launcher.png "$app_dir/.DirIcon"
# Where AppStream looks: the metadata, and the desktop entry its launchable names.
mkdir -p "$app_dir/usr/share/metainfo" "$app_dir/usr/share/applications"
cp "$here/$APP_ID.appdata.xml" "$app_dir/usr/share/metainfo/"
cp "$here/$APP_ID.desktop" "$app_dir/usr/share/applications/"

# FFmpeg, and what its LGPL asks for: the licence, and where its exact source is and how it was built.
licences="$app_dir/usr/share/licenses/ffmpeg"
mkdir -p "$app_dir/usr/lib" "$licences"
cp "${ffmpeg_libs[@]}" "$app_dir/usr/lib/"
cp "$FFMPEG_DIR/COPYING.LGPLv2.1" "$licences/"
cat > "$licences/SOURCE.txt" << EOF
The libraries in usr/lib named libav*.so.* and libsw*.so.* are FFmpeg $FFMPEG_VERSION (https://ffmpeg.org), unmodified,
built as shared libraries under the GNU Lesser General Public License 2.1 or later (COPYING.LGPLv2.1 here) by
tools/linux/setup.sh in Odyssey Launcher's repository (https://github.com/GeekRhapsody/OdysseyLauncher). The launcher
uses FFmpeg's public API only, and loads these files by their names, so they can be replaced by your own build of the
same version.

Source:          https://ffmpeg.org/releases/ffmpeg-$FFMPEG_VERSION.tar.xz
Its SHA-256:     $FFMPEG_SHA256
Configured with: ${FFMPEG_CONFIGURE[*]} --extra-cflags="-include glibc-floor.h"

glibc-floor.h holds one line, which binds an older glibc symbol so the libraries run on glibc $GLIBC_FLOOR:
$(grep '^__asm__' "$here/glibc-floor.h")
EOF

# PDFium, with the licences of PDFium and of what it's built from, and pdfium-binaries' own (its build scripts).
mkdir -p "$app_dir/usr/share/licenses/pdfium"
cp "$PDFIUM_DIR/lib/libpdfium.so" "$app_dir/usr/lib/"
cp "$PDFIUM_DIR"/licenses/* "$app_dir/usr/share/licenses/pdfium/"
cp "$PDFIUM_DIR/LICENSE" "$app_dir/usr/share/licenses/pdfium/pdfium-binaries.txt"
cat > "$app_dir/usr/share/licenses/pdfium/README.txt" << EOF
usr/lib/libpdfium.so is PDFium (https://pdfium.googlesource.com/pdfium/), as built by pdfium-binaries
(https://github.com/bblanchon/pdfium-binaries), release chromium/$PDFIUM_BUILD, unmodified. pdfium.txt is PDFium's
licence (BSD 3-clause); each other file here is the licence of a library built into it, and pdfium-binaries.txt that
of pdfium-binaries' build scripts.
EOF

# Folders and programs (every ELF file, the .NET runtime's included) 755, everything else 644.
find "$app_dir" -type d -exec chmod 755 {} +
find "$app_dir" -type f -exec chmod 644 {} +
chmod 755 "$app_dir/AppRun"
elf_files=()
while IFS= read -r -d '' file; do
    if [[ $(head -c 4 "$file" | od -An -c | tr -d ' \n') == '177ELF' ]]; then
        chmod 755 "$file"
        elf_files+=("$file")
    fi
done < <(find "$app_dir/usr" -type f -print0)

echo "==> glibc $GLIBC_FLOOR or later is enough for its ${#elf_files[@]} ELF files"
check_glibc_floor "${elf_files[@]}"

echo "==> AppStream metadata"
# Without the network, so the check doesn't depend on the screenshots' URLs; appimagetool checks the tree again.
appstreamcli validate-tree --no-net "$app_dir"

# zsync's update information (decisions log, 2026-11-05): GitHub's latest release for a release, and the newest
# release or pre-release for a pre-release (a version with a '-'), as "Check for updates" offers them.
channel=latest
[[ $version == *-* ]] && channel=latest-all
update_info="gh-releases-zsync|GeekRhapsody|OdysseyLauncher|$channel|OdysseyLauncher-*-linux-x86_64.AppImage.zsync"

echo "==> $name ($update_info)"
staged="$ODYSSEY_LINUX_CACHE/$name"
rm -f "$staged" "$staged.zsync"
(cd "$ODYSSEY_LINUX_CACHE" && ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" --updateinformation "$update_info"     --runtime-file "$APPIMAGE_RUNTIME" "$app_dir" "$staged")
if [[ ! -f $staged.zsync ]]; then
    echo "error: appimagetool wrote no $name.zsync: is zsyncmake installed (tools/linux/setup.sh)?" >&2
    exit 1
fi

mkdir -p "$out_dir"
cp "$staged" "$out_dir/$name"
cp "$staged.zsync" "$out_dir/$name.zsync"
chmod 755 "$out_dir/$name"
(cd "$out_dir" && printf '%s  %s' "$(sha256sum "$name" | cut -d ' ' -f 1)" "$name" > "$name.sha256")
echo "$out_dir/$name ($(du -h "$out_dir/$name" | cut -f 1))"
