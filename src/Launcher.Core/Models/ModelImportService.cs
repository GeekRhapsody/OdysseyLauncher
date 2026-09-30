using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Platform;

namespace Launcher.Core.Models;

public enum ModelImportStatus
{
    /// <summary>The model is the game's now (<see cref="ModelImportResult.ModelPath"/>).</summary>
    Imported,

    /// <summary>The file is broken or more than 2× over budget (<see cref="ModelImportResult.Report"/>): nothing changed.</summary>
    Rejected,

    /// <summary>The file isn't a model the launcher can import (not a .glb, an OBJ zip or an .obj), or couldn't be converted.</summary>
    Unsupported,

    /// <summary>The game isn't in the library.</summary>
    NotInLibrary,
}

/// <summary>What importing a model for a game did.</summary>
/// <param name="ModelPath">Where the model is now, relative to ConfigDir and '/'-separated (<c>models/games/ps2/Game.iso.glb</c>).</param>
/// <param name="Converted">True when it was converted from an OBJ model.</param>
/// <param name="Report">The inspector's report, once the file was a <c>.glb</c>; null before that.</param>
/// <param name="Messages">Problems before the report existed (conversion), for the user.</param>
public sealed record ModelImportResult(ModelImportStatus Status, string? ModelPath, bool Converted, ModelReport? Report, IReadOnlyList<string> Messages);

/// <summary>What removing a game's model did.</summary>
public enum ModelRemoveStatus
{
    Removed,

    /// <summary>The game had no model of its own.</summary>
    None,

    /// <summary>
    /// Its model is a file every game with its name uses (<c>Game.glb</c> for <c>Game.cue</c> and <c>Game.chd</c>), so
    /// it was left alone; <see cref="ModelRemoveResult.SharedPath"/> says which.
    /// </summary>
    Shared,
}

public sealed record ModelRemoveResult(ModelRemoveStatus Status, string? SharedPath);

/// <summary>
/// The user's own models for games (A7), as a service the game options panel (M7) and <c>odyssey-scrape
/// import-model</c> call. Importing takes a <c>.glb</c>, a zip of an OBJ model (<c>.obj</c>, <c>.mtl</c> and
/// textures) or a bare <c>.obj</c>; converts OBJ to glTF (<see cref="ObjConverter"/>); fits it to the per-game
/// budget (<see cref="ModelProcessor"/>: textures scaled down, counts checked, a broken or more-than-2×-over file
/// rejected with nothing changed); writes it to the game's model slot,
/// <c>ConfigDir/models/games/&lt;system&gt;/&lt;rel path&gt;.glb</c>, atomically; primes the processed-model cache so
/// the app doesn't process it again; indexes it (<see cref="LibraryService.RefreshUserMediaAsync"/>, which raises
/// <c>MediaChanged</c>, so a running grid swaps the game's model in place); and logs the outcome to the model log.
/// Clearing a game's metadata (<c>ScrapeService.ClearGameAsync</c>) removes its model too.
/// </summary>
public sealed class ModelImportService
{
    private readonly LibraryService _library;
    private readonly IPlatformPaths _paths;
    private readonly IImageDecoder? _decoder;
    private readonly ModelLog _log;
    private readonly ModelCache _cache;

    /// <param name="decoder">For scaling textures down and converting OBJ textures; null where there's none (Linux).</param>
    public ModelImportService(LibraryService library, IPlatformPaths paths, IImageDecoder? decoder, ModelLog? log = null)
    {
        _library = library ?? throw new ArgumentNullException(nameof(library));
        _paths = paths ?? throw new ArgumentNullException(nameof(paths));
        _decoder = decoder;
        _log = log ?? new ModelLog(paths.DataDir);
        _cache = new ModelCache(paths.CacheDir, decoder, null);
    }

    /// <summary>The files <see cref="ImportGameModelAsync"/> takes.</summary>
    public static IReadOnlyList<string> Extensions { get; } = [".glb", ".zip", ".obj"];

    /// <summary>The game's model slot, relative to ConfigDir: <c>models/games/&lt;system&gt;/&lt;rel path&gt;.glb</c>.</summary>
    public static string ModelPathFor(GameKey game, string relPath)
    {
        ArgumentNullException.ThrowIfNull(relPath);
        return $"{UserMedia.ModelsFolderName}/{game.SystemId}/{relPath}.glb";
    }

    public async Task<ModelImportResult> ImportGameModelAsync(GameKey game, string sourceFile, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(sourceFile);
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return new ModelImportResult(ModelImportStatus.NotInLibrary, null, false, null,
                [$"{game.SystemId}/{game.PathKey} isn't in the library: rescan its system first"]);
        }

        var relative = ModelPathFor(game, details.RelPath);
        var name = $"{Path.GetFileName(sourceFile)} for {game.SystemId}/{details.RelPath}";
        var result = await Task.Run(() =>
        {
            var prepared = Prepare(sourceFile, ModelKind.PerGame, _decoder, ScratchDir);
            if (prepared.Processed is not { } processed)
            {
                foreach (var message in prepared.Messages)
                {
                    _log.Write(Diagnostics.LogLevel.Error, $"{name}: {message}");
                }

                return new ModelImportResult(ModelImportStatus.Unsupported, null, prepared.Converted, null, prepared.Messages);
            }

            if (processed.Glb is not { } glb)
            {
                _log.Report(name, processed.Report, "Nothing was imported");
                return new ModelImportResult(ModelImportStatus.Rejected, null, prepared.Converted, processed.Report, prepared.Messages);
            }

            var target = Path.Combine(_paths.ConfigDir, relative.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            var temporary = target + ".import.tmp";
            File.WriteAllBytes(temporary, glb);
            File.Move(temporary, target, overwrite: true);
            _cache.Put(target, ModelKind.PerGame, processed);
            _log.Report(name, processed.Report, $"Imported{(prepared.Converted ? " (converted from OBJ)" : string.Empty)} as {relative}");
            return new ModelImportResult(ModelImportStatus.Imported, relative, prepared.Converted, processed.Report, prepared.Messages);
        }, cancellationToken).ConfigureAwait(false);

        if (result.Status == ModelImportStatus.Imported)
        {
            await _library.RefreshUserMediaAsync(game.SystemId, cancellationToken).ConfigureAwait(false);
        }

        return result;
    }

    /// <summary>
    /// Removes the game's own model (its file in the model slot) and re-indexes, so it shows its system's template again.
    /// A model file every game of that name shares is left alone (<see cref="ModelRemoveStatus.Shared"/>).
    /// </summary>
    public async Task<ModelRemoveResult> RemoveGameModelAsync(GameKey game, CancellationToken cancellationToken)
    {
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return new ModelRemoveResult(ModelRemoveStatus.None, null);
        }

        var rows = await _library.GetGameMediaAsync([details.GameId], [MediaKinds.Model], cancellationToken).ConfigureAwait(false);
        var own = ModelPathFor(game, details.RelPath);
        var removed = await Task.Run(() =>
        {
            var target = Path.Combine(_paths.ConfigDir, own.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(target))
            {
                return false;
            }

            File.Delete(target);
            _cache.Forget(target);
            _log.Write(Diagnostics.LogLevel.Info, $"{own}: removed for {game.SystemId}/{details.RelPath}");
            return true;
        }, cancellationToken).ConfigureAwait(false);

        if (removed)
        {
            await _library.RefreshUserMediaAsync(game.SystemId, cancellationToken).ConfigureAwait(false);
            return new ModelRemoveResult(ModelRemoveStatus.Removed, null);
        }

        return rows.Count > 0 && !string.Equals(rows[0].Media.Path, own, StringComparison.Ordinal)
            ? new ModelRemoveResult(ModelRemoveStatus.Shared, rows[0].Media.Path)
            : new ModelRemoveResult(ModelRemoveStatus.None, null);
    }

    /// <summary>The report for the game's current model (processing it if the cache has none), or null if it has none.</summary>
    public async Task<(string Path, ModelReport Report)?> GetGameModelAsync(GameKey game, CancellationToken cancellationToken)
    {
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return null;
        }

        var rows = await _library.GetGameMediaAsync([details.GameId], [MediaKinds.Model], cancellationToken).ConfigureAwait(false);
        if (rows.Count == 0)
        {
            return null;
        }

        var path = rows[0].Media.Path;
        var full = Path.Combine(_paths.ConfigDir, path.Replace('/', Path.DirectorySeparatorChar));
        var cached = await Task.Run(() => _cache.Get(full, ModelKind.PerGame), cancellationToken).ConfigureAwait(false);
        return (path, cached.Report);
    }

    private string ScratchDir => Path.Combine(_paths.CacheDir, ModelCache.FolderName, "scratch");

    /// <summary>A file read, converted if it's OBJ, and processed: what import and <c>inspect-model</c> both do.</summary>
    /// <param name="Processed">Null when there was no <c>.glb</c> to process (see <see cref="Messages"/>).</param>
    public sealed record PreparedModel(ProcessedModel? Processed, bool Converted, IReadOnlyList<string> Messages);

    /// <summary>Reads, converts and processes a model file without writing it anywhere. Does file I/O.</summary>
    public static PreparedModel Prepare(string sourceFile, ModelKind kind, IImageDecoder? decoder, string scratchDir)
    {
        ArgumentNullException.ThrowIfNull(sourceFile);
        byte[] bytes;
        var converted = false;
        var messages = new List<string>();
        try
        {
            var info = new FileInfo(sourceFile);
            if (!info.Exists)
            {
                return new PreparedModel(null, false, [$"'{sourceFile}' doesn't exist"]);
            }

            var extension = info.Extension.ToLowerInvariant();
            if (extension == ".zip" || extension == ".obj")
            {
                ConvertedModelFile conversion;
                if (extension == ".zip")
                {
                    if (info.Length > ObjConverter.MaxZipBytes)
                    {
                        return new PreparedModel(null, false, ["the zip is too large to be a model"]);
                    }

                    using var zip = File.OpenRead(sourceFile);
                    conversion = ObjConverter.FromZip(zip, decoder, scratchDir);
                }
                else
                {
                    conversion = ObjConverter.FromFile(sourceFile, decoder, scratchDir);
                }

                messages.AddRange(conversion.Errors);
                messages.AddRange(conversion.Warnings);
                if (conversion.Glb is null)
                {
                    return new PreparedModel(null, true, messages);
                }

                bytes = conversion.Glb;
                converted = extension == ".obj" || !IsPassThrough(sourceFile);
            }
            else if (extension == ".glb")
            {
                if (info.Length > GlbFile.MaxBytes)
                {
                    return new PreparedModel(null, false, ["the file is too large to be a model"]);
                }

                bytes = File.ReadAllBytes(sourceFile);
            }
            else
            {
                return new PreparedModel(null, false,
                    [$"'{info.Name}' isn't a model the launcher can import: use a .glb (glTF 2.0 binary), or a zip of a Wavefront OBJ model (.obj, .mtl and textures)"]);
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return new PreparedModel(null, converted, [$"'{sourceFile}' couldn't be read: {e.Message}"]);
        }

        return new PreparedModel(ModelProcessor.Process(bytes, kind, decoder, scratchDir), converted, messages);
    }

    /// <summary>Whether a zip held a <c>.glb</c> rather than an OBJ model (then nothing was converted).</summary>
    private static bool IsPassThrough(string zipPath)
    {
        try
        {
            using var zip = System.IO.Compression.ZipFile.OpenRead(zipPath);
            return !zip.Entries.Any(e => e.FullName.EndsWith(".obj", StringComparison.OrdinalIgnoreCase));
        }
        catch (Exception e) when (e is IOException or InvalidDataException or UnauthorizedAccessException)
        {
            return false;
        }
    }
}
