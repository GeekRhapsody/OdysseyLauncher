using Launcher.Core.Library;

namespace Launcher.Core.Media;

/// <summary>What <see cref="ThemeLogos.BakeMissingAsync"/> did.</summary>
public sealed record LogoBakeSummary(int Logos, int Baked, int Failed, int Pruned, TimeSpan Elapsed);

/// <summary>One card's logo: its image file, and how the grid requests its derivative.</summary>
/// <param name="Source">The image, an absolute path.</param>
/// <param name="Media">
/// <see cref="MediaRef.Path"/> is the logo's key, <c>&lt;theme id&gt;/&lt;path in the theme&gt;</c>, not where the theme
/// is, so an editor run and an exported build (whose themes are copied beside it, times kept) share one derivative.
/// </param>
public readonly record struct ThemeLogo(string Source, MediaRef Media);

/// <summary>
/// System cards' logos (A6 <c>logos/</c>): images in a theme's folder, not the library's, so their derivatives live
/// apart from the library's, in <c>CacheDir/theme-logos/textures/</c>, where the library's bake never prunes them. The
/// grid requests a logo by its <see cref="ThemeLogo.Media"/>, with <see cref="CacheRoot"/> as its streamer's cache folder.
/// </summary>
public static class ThemeLogos
{
    public const string FolderName = "theme-logos";

    /// <summary>The cache folder logos' derivatives are named under, as <see cref="TextureDerivatives.PathFor(string, string, long, long)"/> takes it.</summary>
    public static string CacheRoot(string cacheDir) => Path.Combine(cacheDir, FolderName);

    /// <summary>The logo's derivative.</summary>
    public static string DerivativePath(string cacheDir, in MediaRef logo) =>
        TextureDerivatives.PathFor(CacheRoot(cacheDir), logo.Path, logo.SizeBytes, logo.MtimeMs);

    /// <summary>
    /// A logo file as the grid requests it: its key, its aspect from its header, its size and its time. Does file I/O:
    /// never on the main thread. Null if it can't be read.
    /// </summary>
    /// <param name="key">The theme's id and the file's path in it ('/'-separated).</param>
    public static ThemeLogo? Describe(string absolutePath, string key)
    {
        ArgumentNullException.ThrowIfNull(absolutePath);
        ArgumentNullException.ThrowIfNull(key);
        try
        {
            var file = new FileInfo(absolutePath);
            if (!file.Exists || !ImageHeaders.TryReadSize(absolutePath, out var width, out var height))
            {
                return null;
            }

            return new ThemeLogo(absolutePath, new MediaRef(key, (float)width / height, file.Length,
                new DateTimeOffset(file.LastWriteTimeUtc).ToUnixTimeMilliseconds()));
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    /// <summary>
    /// Bakes each logo that has no derivative, in order (the caller puts the ones on screen first), on the derivative
    /// service's logo threads, ahead of any library bake, then deletes the logo derivatives none of them names. The app
    /// calls it for a theme with logos only, so they're kept for the last theme that had some.
    /// </summary>
    /// <param name="baked">Called on a worker after each logo is baked, so the cards can show it at once.</param>
    public static async Task<LogoBakeSummary> BakeMissingAsync(
        DerivativeService derivatives, string cacheDir, IReadOnlyList<ThemeLogo> logos, Action? baked, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(derivatives);
        ArgumentNullException.ThrowIfNull(cacheDir);
        ArgumentNullException.ThrowIfNull(logos);
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var wanted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        int done = 0, failed = 0;
        var bakes = new List<Task>();
        foreach (var logo in logos)
        {
            var destination = DerivativePath(cacheDir, logo.Media);
            if (!wanted.Add(Path.GetFileName(destination)) || File.Exists(destination))
            {
                continue;
            }

            // Queued all at once, in order: the service's logo threads take them first come, first served.
            bakes.Add(Bake(logo.Source, destination));
        }

        await Task.WhenAll(bakes).ConfigureAwait(false);

        var pruned = 0;
        var folder = Path.Combine(CacheRoot(cacheDir), TextureDerivatives.FolderName);
        if (Directory.Exists(folder))
        {
            foreach (var file in Directory.EnumerateFiles(folder, "*" + TextureDerivatives.Extension))
            {
                if (!wanted.Contains(Path.GetFileName(file)))
                {
                    try
                    {
                        File.Delete(file);
                        pruned++;
                    }
                    catch (IOException)
                    {
                        // In use (the grid is reading it): the next run prunes it.
                    }
                }
            }
        }

        return new LogoBakeSummary(logos.Count, done, failed, pruned, stopwatch.Elapsed);

        async Task Bake(string source, string destination)
        {
            if (await derivatives.BakeFileAsync(source, destination, cancellationToken).ConfigureAwait(false))
            {
                Interlocked.Increment(ref done);
                baked?.Invoke();
            }
            else
            {
                Interlocked.Increment(ref failed);
            }
        }
    }
}
