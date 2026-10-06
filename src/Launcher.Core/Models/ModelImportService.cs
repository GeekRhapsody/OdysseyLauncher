using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Theming;

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
/// <param name="ModelPath">
/// Where the model is now, '/'-separated: a game's as stored (<c>media/ps2/models/Game.glb</c>), a
/// system's relative to ConfigDir (<c>models/systems/ps2.glb</c>).
/// </param>
/// <param name="Converted">True when it was converted from an OBJ model.</param>
/// <param name="Report">The inspector's report, once the file was a <c>.glb</c>; null before that.</param>
/// <param name="Messages">Problems before the report existed (conversion), for the user.</param>
public sealed record ModelImportResult(ModelImportStatus Status, string? ModelPath, bool Converted, ModelReport? Report, IReadOnlyList<string> Messages);

/// <summary>Which of a system's own models (A7 level 2).</summary>
public enum SystemModelSlot
{
    /// <summary>Its card in the systems grid: <c>ConfigDir/models/systems/&lt;system&gt;.glb</c>.</summary>
    Card,

    /// <summary>The template its games use: <c>ConfigDir/models/templates/&lt;system&gt;.glb</c>.</summary>
    GameTemplate,
}

/// <summary>What removing a game's model did.</summary>
public enum ModelRemoveStatus
{
    Removed,

    /// <summary>The game had no model of its own.</summary>
    None,
}

public sealed record ModelRemoveResult(ModelRemoveStatus Status);

/// <summary>
/// The user's own models for games (A7), as a service the game options panel (M7) and <c>odyssey-scrape
/// import-model</c> call. Importing takes a <c>.glb</c>, a zip of an OBJ model (<c>.obj</c>, <c>.mtl</c> and
/// textures) or a bare <c>.obj</c>; converts OBJ to glTF (<see cref="ObjConverter"/>); fits it to the per-game
/// budget (<see cref="ModelProcessor"/>: textures scaled down, counts checked, a broken or more-than-2×-over file
/// rejected with nothing changed); writes it to the game's model slot in the media folder,
/// <c>&lt;media folder&gt;/&lt;system&gt;/models/&lt;name&gt;.glb</c> (the ROM's name without its extension, so every ROM of
/// that name shares it, as the rest of its media), atomically, removing the game's other model file (named after its
/// whole ROM name), which would win over it; primes the processed-model cache so
/// the app doesn't process it again; indexes it (<see cref="LibraryService.RefreshMediaAsync"/>, which raises
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

    /// <summary>The game's model slot, as stored: <c>media/&lt;system&gt;/models/&lt;name&gt;.glb</c> (<see cref="MediaStore.PathFor"/>).</summary>
    public static string ModelPathFor(GameKey game, string relPath) =>
        MediaStore.PathFor(game.SystemId, relPath, MediaKinds.Model, ".glb");

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
        var result = await ImportAsync(sourceFile, _library.MediaPath(relative), relative, ModelKind.PerGame, $"{Path.GetFileName(sourceFile)} for {game.SystemId}/{details.RelPath}", cancellationToken).ConfigureAwait(false);
        if (result.Status == ModelImportStatus.Imported)
        {
            // One model a game: one named after its whole ROM name would be used instead.
            await Task.Run(() =>
            {
                foreach (var other in new MediaStore(_library.MediaDir).FilesOf(game.SystemId, details.RelPath, MediaKinds.Model))
                {
                    if (!string.Equals(other, relative, StringComparison.Ordinal))
                    {
                        Forget(other, game, details.RelPath);
                    }
                }
            }, cancellationToken).ConfigureAwait(false);
            await _library.RefreshMediaAsync(game.SystemId, cancellationToken).ConfigureAwait(false);
        }

        return result;
    }

    /// <summary>
    /// Removes the game's model (its files in the model slot, named with or without the ROM's extension, so every ROM
    /// of that name loses it) and re-indexes, so it shows its system's template again.
    /// </summary>
    public async Task<ModelRemoveResult> RemoveGameModelAsync(GameKey game, CancellationToken cancellationToken)
    {
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return new ModelRemoveResult(ModelRemoveStatus.None);
        }

        var removed = await Task.Run(() =>
        {
            var files = new MediaStore(_library.MediaDir).FilesOf(game.SystemId, details.RelPath, MediaKinds.Model);
            foreach (var file in files)
            {
                Forget(file, game, details.RelPath);
            }

            return files.Count > 0;
        }, cancellationToken).ConfigureAwait(false);

        if (!removed)
        {
            return new ModelRemoveResult(ModelRemoveStatus.None);
        }

        await _library.RefreshMediaAsync(game.SystemId, cancellationToken).ConfigureAwait(false);
        return new ModelRemoveResult(ModelRemoveStatus.Removed);
    }

    /// <summary>Deletes a game's model file (as stored) and its processed copy, and logs it.</summary>
    private void Forget(string stored, GameKey game, string relPath)
    {
        var target = _library.MediaPath(stored);
        File.Delete(target);
        _cache.Forget(target);
        _log.Write(Diagnostics.LogLevel.Info, $"{stored}: removed for {game.SystemId}/{relPath}");
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
        var full = _library.MediaPath(path);
        var cached = await Task.Run(() => _cache.Get(full, ModelKind.PerGame), cancellationToken).ConfigureAwait(false);
        return (path, cached.Report);
    }

    /// <summary>A system's own model, relative to ConfigDir: <c>models/systems/&lt;system&gt;.glb</c> or <c>models/templates/&lt;system&gt;.glb</c> (A7 level 2).</summary>
    public static string SystemModelPathFor(string systemId, SystemModelSlot slot)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        return $"{UserModels.FolderName}/{(slot == SystemModelSlot.Card ? "systems" : "templates")}/{systemId}.glb";
    }

    /// <summary>
    /// Imports the user's model for a system (M7's system options panel): its card in the systems grid, or the template
    /// every one of its games uses unless a game has its own. Checked, fitted to the budget of its kind and written as
    /// <see cref="ImportGameModelAsync"/> does; nothing is indexed, since these are found when a theme is resolved, so
    /// the app resolves its theme again to show it.
    /// </summary>
    public async Task<ModelImportResult> ImportSystemModelAsync(string systemId, SystemModelSlot slot, string sourceFile, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(sourceFile);
        if (_library.Config.FindSystem(systemId) is null)
        {
            return new ModelImportResult(ModelImportStatus.NotInLibrary, null, false, null, [$"'{systemId}' isn't an enabled system"]);
        }

        var relative = SystemModelPathFor(systemId, slot);
        var what = slot == SystemModelSlot.Card ? "the system model" : "the game template";
        return await ImportAsync(sourceFile, Path.Combine(_paths.ConfigDir, relative.Replace('/', Path.DirectorySeparatorChar)), relative, KindOf(slot), $"{Path.GetFileName(sourceFile)} as {what} for {systemId}", cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Removes the user's model for a system, so the theme's shows again. False when there wasn't one.</summary>
    public Task<bool> RemoveSystemModelAsync(string systemId, SystemModelSlot slot, CancellationToken cancellationToken)
    {
        var relative = SystemModelPathFor(systemId, slot);
        return Task.Run(() =>
        {
            var target = Path.Combine(_paths.ConfigDir, relative.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(target))
            {
                return false;
            }

            File.Delete(target);
            _cache.Forget(target);
            _log.Write(Diagnostics.LogLevel.Info, $"{relative}: removed");
            return true;
        }, cancellationToken);
    }

    /// <summary>The report for the system's own model (processing it if the cache has none), or null if it has none.</summary>
    public Task<ModelReport?> GetSystemModelAsync(string systemId, SystemModelSlot slot, CancellationToken cancellationToken)
    {
        var target = Path.Combine(_paths.ConfigDir, SystemModelPathFor(systemId, slot).Replace('/', Path.DirectorySeparatorChar));
        return Task.Run(() => File.Exists(target) ? _cache.Get(target, KindOf(slot)).Report : null, cancellationToken);
    }

    private static ModelKind KindOf(SystemModelSlot slot) => slot == SystemModelSlot.Card ? ModelKind.SystemModel : ModelKind.GameTemplate;

    /// <summary>Prepares <paramref name="sourceFile"/> as <paramref name="kind"/> and, if it passes, writes it to <paramref name="target"/> (<paramref name="relative"/>, as reported).</summary>
    private Task<ModelImportResult> ImportAsync(string sourceFile, string target, string relative, ModelKind kind, string name, CancellationToken cancellationToken) =>
        Task.Run(() =>
        {
            var prepared = Prepare(sourceFile, kind, _decoder, ScratchDir);
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

            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            var temporary = target + ".import.tmp";
            File.WriteAllBytes(temporary, glb);
            File.Move(temporary, target, overwrite: true);
            _cache.Put(target, kind, processed);
            _log.Report(name, processed.Report, $"Imported{(prepared.Converted ? " (converted from OBJ)" : string.Empty)} as {relative}");
            return new ModelImportResult(ModelImportStatus.Imported, relative, prepared.Converted, processed.Report, prepared.Messages);
        }, cancellationToken);

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
