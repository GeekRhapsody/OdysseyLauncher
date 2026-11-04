using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// Loads the native libraries the AppImage carries (L4: FFmpeg for videos, PDFium for manuals) from its own folders,
/// never the system's (docs/ARCHITECTURE.md A1 <c>Platform</c>). A binding names its library <c>odyssey-&lt;file&gt;</c>
/// (<see cref="Prefix"/>), a name no system has, which this resolves to the file already loaded from beside the
/// executable, from its <c>../lib</c> (the AppImage's <c>usr/lib</c>) or from beside Launcher.Core (the tests). A
/// library's group is loaded together by full paths, each file after those it needs: the dynamic loader then finds
/// each one's dependencies among those already loaded (by their sonames) instead of searching for them, which could
/// find a system's copy of the same version.
/// </summary>
[SupportedOSPlatform("linux")]
internal static class BundledLibraries
{
    public const string Prefix = "odyssey-";

    /// <summary>FFmpeg 9.0's sonames (tools/linux/common.sh, <c>FFMPEG_LIBS</c>), each after the ones it needs.</summary>
    internal static readonly string[] Ffmpeg =
        ["libavutil.so.61", "libswresample.so.7", "libavcodec.so.63", "libavformat.so.63", "libswscale.so.10"];

    /// <summary>pdfium-binaries' PDFium (tools/linux/common.sh, <c>PDFIUM_BUILD</c>), which needs nothing but libc's.</summary>
    internal static readonly string[] Pdfium = ["libpdfium.so"];

    private static readonly object Gate = new();
    private static readonly Dictionary<string, nint> Loaded = new(StringComparer.Ordinal);
    private static readonly Dictionary<string[], string> Failed = [];
    private static bool _registered;

    /// <summary>Loads a group of libraries once; null, or why it can't be. Does file I/O: never on Godot's main thread.</summary>
    public static string? Load(string[] files)
    {
        lock (Gate)
        {
            if (Failed.TryGetValue(files, out var failed))
            {
                return failed;
            }

            if (files.All(Loaded.ContainsKey))
            {
                return null;
            }

            if (!_registered)
            {
                NativeLibrary.SetDllImportResolver(typeof(BundledLibraries).Assembly, Resolve);
                _registered = true;
            }

            var error = LoadFiles(files);
            if (error is not null)
            {
                Failed[files] = error;
            }

            return error;
        }
    }

    /// <summary>The folders the libraries are looked for in, in order.</summary>
    internal static IEnumerable<string> Folders()
    {
        if (Path.GetDirectoryName(Environment.ProcessPath) is { Length: > 0 } executable)
        {
            yield return executable;
            yield return Path.GetFullPath(Path.Combine(executable, "..", "lib"));
        }

        yield return AppContext.BaseDirectory;
    }

    private static string? LoadFiles(string[] files)
    {
        var folder = Folders().FirstOrDefault(f => files.All(file => File.Exists(Path.Combine(f, file))));
        if (folder is null)
        {
            return $"{files[^1]} and the libraries it needs aren't beside the launcher (the AppImage carries them)";
        }

        foreach (var file in files)
        {
            var path = Path.Combine(folder, file);
            if (!NativeLibrary.TryLoad(path, out var handle))
            {
                return $"couldn't load {path}";
            }

            Loaded[file] = handle;
        }

        return null;
    }

    private static nint Resolve(string name, Assembly assembly, DllImportSearchPath? searchPath)
    {
        if (!name.StartsWith(Prefix, StringComparison.Ordinal))
        {
            return 0;
        }

        lock (Gate)
        {
            return Loaded.GetValueOrDefault(name[Prefix.Length..]);
        }
    }
}
