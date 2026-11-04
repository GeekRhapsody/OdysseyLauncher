# Sourced by the other tools/linux scripts: where the Linux tools live, their pinned versions, and the shared helpers
# (docs/ARCHITECTURE.md decisions log, 2026-11-02, "A Linux AppImage, built locally").

ODYSSEY_LINUX_CACHE="${ODYSSEY_LINUX_CACHE:-$HOME/.cache/odyssey-linux}"
TOOLS_DIR="$ODYSSEY_LINUX_CACHE/tools"

# Each pinned by version and by the SHA-256 GitHub gives for the asset.
POWERSHELL_VERSION=7.6.9
POWERSHELL_SHA256=1da6d6d6035d651f20e70ddee7c4c15ac6ab8b9fb40ee92240d91263f28a884b
APPIMAGETOOL_VERSION=1.9.1
APPIMAGETOOL_SHA256=ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0
RUNTIME_VERSION=20251108
RUNTIME_SHA256=2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d

# FFmpeg's release tarball; its SHA-256 was taken from a copy whose signature checked out against FFmpeg's release
# signing key (FCF9 86EA 15E6 E293 A564 4F10 B432 2F04 D676 58D8).
FFMPEG_VERSION=9.0.2
FFMPEG_SHA256=8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e

# The AppImage's floor (decisions log, 2026-11-02): every ELF file it carries must run on glibc 2.34.
GLIBC_FLOOR=2.34

# FFmpeg for videos (L4): an LGPL build (no --enable-gpl, --enable-version3 or --enable-nonfree) with only the
# decoders the media folders need, as shared libraries. FFMPEG_LIBS are its sonames, each after the ones it needs, as
# Launcher.Core loads them (Platform/Linux/BundledLibraries.cs).
FFMPEG_CONFIGURE=(
    --disable-everything --disable-programs --disable-doc --disable-network --disable-autodetect
    --enable-shared --disable-static --disable-avdevice --disable-avfilter
    --enable-decoder=h264,hevc,vp9,aac,mp3float,opus --enable-demuxer=mov
    --enable-parser=h264,hevc,vp9,aac,mpegaudio,opus --enable-protocol=file
    --enable-swscale --enable-swresample
)
FFMPEG_LIBS=(libavutil.so.61 libswresample.so.7 libavcodec.so.63 libavformat.so.63 libswscale.so.10)
FFMPEG_DIR="$ODYSSEY_LINUX_CACHE/native/ffmpeg-$FFMPEG_VERSION"

# PDFium for manuals (L4): bblanchon/pdfium-binaries' build, by its release (chromium/<build>) and the SHA-256 GitHub
# gives for its pdfium-linux-x64.tgz.
PDFIUM_BUILD=8138
PDFIUM_SHA256=d6b1e28950a0392590d79bbdbb7eb19686872b688f8a36f170acb19e41473113
PDFIUM_DIR="$ODYSSEY_LINUX_CACHE/native/pdfium-$PDFIUM_BUILD"

PWSH="$TOOLS_DIR/powershell-$POWERSHELL_VERSION/pwsh"
APPIMAGETOOL="$TOOLS_DIR/appimagetool-$APPIMAGETOOL_VERSION-x86_64.AppImage"
APPIMAGE_RUNTIME="$TOOLS_DIR/runtime-$RUNTIME_VERSION-x86_64"

export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
# As release.yml: no build servers left holding the console after a build.
export MSBUILDDISABLENODEREUSE=1 DOTNET_CLI_USE_MSBUILD_SERVER=0 UseSharedCompilation=false

# Downloads <url> to <file> unless it's there already with the right SHA-256; a file that doesn't match is refused.
fetch() {
    local url=$1 sha256=$2 file=$3
    if [[ -f $file ]] && echo "$sha256  $file" | sha256sum --check --status; then
        return
    fi

    mkdir -p "$(dirname "$file")"
    curl --fail --location --silent --show-error --output "$file.part" "$url"
    if ! echo "$sha256  $file.part" | sha256sum --check --status; then
        rm -f "$file.part"
        echo "error: $url doesn't have the SHA-256 pinned in tools/linux/common.sh" >&2
        exit 1
    fi

    mv "$file.part" "$file"
}

# Fails, naming them, if any of the ELF files given needs a glibc symbol newer than GLIBC_FLOOR.
check_glibc_floor() {
    local file newest failed=0
    for file in "$@"; do
        newest="$(objdump -T "$file" | grep -o 'GLIBC_[0-9.]*' | sed 's/^GLIBC_//' | sort -Vu | tail -n 1)"
        if [[ -n $newest && $(printf '%s\n%s\n' "$GLIBC_FLOOR" "$newest" | sort -V | tail -n 1) != "$GLIBC_FLOOR" ]]; then
            echo "error: $file needs glibc $newest, above the AppImage's floor of $GLIBC_FLOOR" >&2
            failed=1
        fi
    done

    return $failed
}

# Copies the working tree at <from> to <to>, leaving out Windows' build outputs (bin/, obj/), Godot's import cache,
# artifacts/ and .git/, and keeping <to>'s own bin/ and obj/, so builds there stay incremental.
sync_tree() {
    local from=$1 to=$2
    mkdir -p "$to"
    if command -v rsync > /dev/null; then
        rsync -a --delete --exclude=/.git/ --exclude=/.vs/ --exclude=/.claude/ --exclude=/artifacts/ \
            --exclude=/godot/.godot/ --exclude=bin/ --exclude=obj/ "$from/" "$to/"
    else
        rm -rf "$to"
        mkdir -p "$to"
        tar -C "$from" --exclude=./.git --exclude=./.vs --exclude=./.claude --exclude=./artifacts \
            --exclude=./godot/.godot --exclude=bin --exclude=obj -cf - . | tar -C "$to" -xf -
    fi
}
