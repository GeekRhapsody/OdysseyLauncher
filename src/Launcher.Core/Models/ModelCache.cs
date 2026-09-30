using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Launcher.Core.Media;

namespace Launcher.Core.Models;

/// <summary>A model ready to load: the processed file (null when it's rejected) and its report.</summary>
/// <param name="FromCache">True when nothing was processed this time.</param>
public sealed record CachedModel(string? Path, ModelReport Report, bool FromCache);

/// <summary>
/// Processed user models (A7): <c>CacheDir/models/&lt;source&gt;-&lt;version&gt;.glb</c>, each with its report in a
/// <c>.json</c> beside it. A model is inspected and fitted to its budget (<see cref="ModelProcessor"/>) the first
/// time it's used; after that it loads from here, until its source file changes size or time (or processing
/// changes), when it's processed again and the old entry is deleted. A rejected model is remembered too, so a bad
/// file isn't parsed on every boot. Everything here can be deleted at any time (A4). Does file I/O, so never on the
/// main thread; safe from several threads for different sources.
/// </summary>
public sealed class ModelCache
{
    public const string FolderName = "models";

    private readonly IImageDecoder? _decoder;
    private readonly ModelLog? _log;

    public ModelCache(string cacheDir, IImageDecoder? decoder, ModelLog? log)
    {
        ArgumentNullException.ThrowIfNull(cacheDir);
        Folder = System.IO.Path.Combine(cacheDir, FolderName);
        _decoder = decoder;
        _log = log;
    }

    public string Folder { get; }

    /// <summary>The processed model for a source file, processing it now if the cache has no current entry.</summary>
    /// <param name="description">How the log names the model: "your models/games/ps2/Game.glb".</param>
    public CachedModel Get(string sourcePath, ModelKind kind, string? description = null)
    {
        ArgumentNullException.ThrowIfNull(sourcePath);
        var name = description ?? sourcePath;
        FileInfo info;
        try
        {
            info = new FileInfo(sourcePath);
            if (!info.Exists)
            {
                return new CachedModel(null, ModelReport.Rejected(kind, "doesn't exist"), false);
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or ArgumentException)
        {
            return new CachedModel(null, ModelReport.Rejected(kind, $"couldn't be read: {e.Message}"), false);
        }

        var key = Key(sourcePath, info.Length, info.LastWriteTimeUtc.Ticks, kind);
        if (TryRead(key, out var cached))
        {
            return cached;
        }

        ProcessedModel processed;
        try
        {
            processed = info.Length > GlbFile.MaxBytes
                ? new ProcessedModel(null, ModelReport.Rejected(kind, string.Create(CultureInfo.InvariantCulture, $"is {info.Length / (1024 * 1024)} MB, more than a model may be")))
                : ModelProcessor.Process(File.ReadAllBytes(sourcePath), kind, _decoder, System.IO.Path.Combine(Folder, "scratch"));
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return new CachedModel(null, ModelReport.Rejected(kind, $"couldn't be read: {e.Message}"), false);
        }

        _log?.Report(name, processed.Report, processed.Report.Accepted ? null : "The next model in line is used instead");
        var path = Store(key, processed);
        return new CachedModel(path, processed.Report, false);
    }

    /// <summary>
    /// Puts an already processed model in the cache for its source (the import service writes the source itself), so
    /// the app loads it without processing it again.
    /// </summary>
    public void Put(string sourcePath, ModelKind kind, ProcessedModel processed)
    {
        ArgumentNullException.ThrowIfNull(sourcePath);
        ArgumentNullException.ThrowIfNull(processed);
        var info = new FileInfo(sourcePath);
        if (info.Exists)
        {
            Store(Key(sourcePath, info.Length, info.LastWriteTimeUtc.Ticks, kind), processed);
        }
    }

    /// <summary>Deletes every cached entry for a source (its model was removed or cleared).</summary>
    public void Forget(string sourcePath)
    {
        ArgumentNullException.ThrowIfNull(sourcePath);
        DeleteEntries(SourcePrefix(sourcePath), keep: null);
    }

    private static string SourcePrefix(string sourcePath)
    {
        // Paths are compared ignoring case on Windows, where the file system does.
        var full = System.IO.Path.GetFullPath(sourcePath);
        if (OperatingSystem.IsWindows())
        {
            full = full.ToUpperInvariant();
        }

        return Hex(full)[..16];
    }

    private static string Key(string sourcePath, long size, long ticks, ModelKind kind) =>
        SourcePrefix(sourcePath) + "-" + Hex(string.Create(CultureInfo.InvariantCulture, $"{ModelProcessor.Version}|{size}|{ticks}|{kind}"))[..16];

    private static string Hex(string text) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(text))).ToLowerInvariant();

    private bool TryRead(string key, out CachedModel model)
    {
        model = null!;
        var json = System.IO.Path.Combine(Folder, key + ".json");
        var glb = System.IO.Path.Combine(Folder, key + ".glb");
        try
        {
            if (!File.Exists(json) || JsonSerializer.Deserialize(File.ReadAllText(json), ModelJsonContext.Default.ModelReport) is not { } report)
            {
                return false;
            }

            if (report.Accepted && !File.Exists(glb))
            {
                return false;
            }

            model = new CachedModel(report.Accepted ? glb : null, report, true);
            return true;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or JsonException or NotSupportedException)
        {
            // A broken entry is processed again.
            return false;
        }
    }

    /// <summary>Writes the entry (the model, then its report, each atomically) and deletes the source's older ones.</summary>
    private string? Store(string key, ProcessedModel processed)
    {
        var glb = System.IO.Path.Combine(Folder, key + ".glb");
        try
        {
            Directory.CreateDirectory(Folder);
            DeleteEntries(key[..16], keep: key);
            if (processed.Glb is { } bytes)
            {
                WriteAtomically(glb, bytes);
            }

            WriteAtomically(System.IO.Path.Combine(Folder, key + ".json"),
                Encoding.UTF8.GetBytes(JsonSerializer.Serialize(processed.Report, ModelJsonContext.Default.ModelReport)));
            return processed.Glb is null ? null : glb;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            // Uncached: the model is processed again next time. Without the file there's nothing to load now either.
            return processed.Glb is null || !File.Exists(glb) ? null : glb;
        }
    }

    private void DeleteEntries(string prefix, string? keep)
    {
        if (!Directory.Exists(Folder))
        {
            return;
        }

        try
        {
            foreach (var file in Directory.EnumerateFiles(Folder, prefix + "-*"))
            {
                if (keep is null || !System.IO.Path.GetFileNameWithoutExtension(file).Equals(keep, StringComparison.Ordinal))
                {
                    File.Delete(file);
                }
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            // In use or read-only: stale entries are harmless and go next time.
        }
    }

    private static void WriteAtomically(string path, byte[] bytes)
    {
        var temporary = path + "." + Guid.NewGuid().ToString("N")[..8] + ".tmp";
        File.WriteAllBytes(temporary, bytes);
        File.Move(temporary, path, overwrite: true);
    }
}

[JsonSourceGenerationOptions(WriteIndented = true, PropertyNamingPolicy = JsonKnownNamingPolicy.SnakeCaseLower, UseStringEnumConverter = true)]
[JsonSerializable(typeof(ModelReport))]
internal sealed partial class ModelJsonContext : JsonSerializerContext
{
}
