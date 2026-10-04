using Launcher.Core.Library;

namespace Launcher.Core.Media;

public enum UserArtStatus
{
    /// <summary>The image is the game's now (<see cref="UserArtResult.Path"/>).</summary>
    Set,

    /// <summary>The game's image went (scraped or the user's own); the slot is empty until a scrape fills it.</summary>
    Removed,

    /// <summary>The game had no image of that kind.</summary>
    None,

    /// <summary>
    /// Its image is a file every game with its name uses (<c>Game.png</c> for <c>Game.cue</c> and <c>Game.chd</c>), so it
    /// was left alone; <see cref="UserArtResult.Path"/> says which.
    /// </summary>
    Shared,

    /// <summary>The file isn't a PNG, JPEG or WebP image the launcher can read: nothing changed.</summary>
    NotAnImage,

    /// <summary>The game isn't in the library.</summary>
    NotInLibrary,
}

/// <summary>What setting or removing one of a game's images did.</summary>
/// <param name="Path">The image's file as stored, '/'-separated (<c>media/ps2/cover/Game.iso.png</c>).</param>
/// <param name="Message">Why it was refused, for the user.</param>
public sealed record UserArtResult(UserArtStatus Status, string? Path, string? Message = null);

/// <summary>
/// The user's own images for a game (M7's game options panel): one per media kind, chosen with the image picker.
/// <para>
/// Setting one copies the file to the game's own name in the media folder,
/// <c>&lt;media folder&gt;/&lt;system&gt;/&lt;kind&gt;/&lt;rel path&gt;.&lt;ext&gt;</c> (the ROM's whole name, so no other game
/// takes it; A4), replacing the game's file of that kind (a scraped one too: there's one file per kind), bakes its
/// derivative, and indexes it without a ROM scan (<see cref="LibraryService.RefreshMediaAsync"/>, which raises
/// <c>MediaChanged</c>, so the grid shows it at once). Scraping never replaces it.
/// </para>
/// <para>
/// Removing deletes the game's own file of that kind, whoever put it there; the slot stays empty until a scrape
/// fills it. A file every game of that name shares isn't removed for one game.
/// </para>
/// It's just files in the folder the scanner indexes, so a rebuild keeps them. Clearing a game's metadata removes them.
/// </summary>
public sealed class UserArtService(LibraryService library, DerivativeService? derivatives)
{
    private readonly LibraryService _library = library ?? throw new ArgumentNullException(nameof(library));

    /// <summary>The game's own file for a kind, as stored: <c>media/&lt;system&gt;/&lt;kind&gt;/&lt;rel path&gt;&lt;ext&gt;</c>.</summary>
    public static string PathFor(GameKey game, string relPath, string kind, string extension)
    {
        ArgumentNullException.ThrowIfNull(extension);
        return MediaStore.RelativePathFor(game.SystemId, relPath, kind, extension.ToLowerInvariant());
    }

    public async Task<UserArtResult> SetAsync(GameKey game, string kind, string sourceFile, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(sourceFile);
        CheckKind(kind);
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return new UserArtResult(UserArtStatus.NotInLibrary, null, Message: $"{game.SystemId}/{game.PathKey} isn't in the library: rescan its system first.");
        }

        var written = await Task.Run(() =>
        {
            var extension = Path.GetExtension(sourceFile).ToLowerInvariant();
            if (!MediaKinds.ImageExtensions.Contains(extension))
            {
                return new UserArtResult(UserArtStatus.NotAnImage, null, Message: $"'{Path.GetFileName(sourceFile)}' isn't a PNG, JPEG or WebP image.");
            }

            try
            {
                if (!ImageHeaders.TryReadSize(sourceFile, out var width, out var height) || width <= 0 || height <= 0)
                {
                    return new UserArtResult(UserArtStatus.NotAnImage, null, Message: $"'{Path.GetFileName(sourceFile)}' isn't an image the launcher can read.");
                }

                var relative = PathFor(game, details.RelPath, kind, extension);
                var target = Full(relative);

                // Choosing the file that's already there (from the art folder itself) changes nothing.
                if (!string.Equals(Path.GetFullPath(sourceFile), Path.GetFullPath(target), StringComparison.OrdinalIgnoreCase))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                    var temporary = target + ".import.tmp";
                    File.Copy(sourceFile, temporary, overwrite: true);
                    File.Move(temporary, target, overwrite: true);
                }

                // One image per kind: the game's own file in another format would be a second one.
                foreach (var other in OwnFiles(game, details.RelPath, kind))
                {
                    if (!string.Equals(other, relative, StringComparison.Ordinal))
                    {
                        File.Delete(Full(other));
                    }
                }

                return new UserArtResult(UserArtStatus.Set, relative);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                return new UserArtResult(UserArtStatus.NotAnImage, null, Message: $"'{Path.GetFileName(sourceFile)}' couldn't be copied: {e.Message}");
            }
        }, cancellationToken).ConfigureAwait(false);

        if (written.Status != UserArtStatus.Set)
        {
            return written;
        }

        // The derivative first, so the grid can show the image as soon as the index says it's there.
        var info = new FileInfo(Full(written.Path!));
        if (derivatives is not null)
        {
            await derivatives.BakeAsync(written.Path!, info.Length, new DateTimeOffset(info.LastWriteTimeUtc).ToUnixTimeMilliseconds(), cancellationToken).ConfigureAwait(false);
        }

        await _library.RefreshMediaAsync(game.SystemId, cancellationToken).ConfigureAwait(false);
        return written;
    }

    /// <summary>Removes the game's own image of <paramref name="kind"/>, scraped or the user's.</summary>
    public async Task<UserArtResult> RemoveAsync(GameKey game, string kind, CancellationToken cancellationToken)
    {
        CheckKind(kind);
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return new UserArtResult(UserArtStatus.NotInLibrary, null);
        }

        var removed = await Task.Run(() =>
        {
            var files = OwnFiles(game, details.RelPath, kind);
            foreach (var file in files)
            {
                File.Delete(Full(file));
            }

            return files.Count > 0 ? files[0] : null;
        }, cancellationToken).ConfigureAwait(false);

        if (removed is null)
        {
            var rows = await _library.GetGameMediaInfoAsync(details.GameId, cancellationToken).ConfigureAwait(false);
            return rows.FirstOrDefault(r => r.Kind == kind) is { } shared
                ? new UserArtResult(UserArtStatus.Shared, shared.Media.Path)
                : new UserArtResult(UserArtStatus.None, null);
        }

        await _library.RefreshMediaAsync(game.SystemId, cancellationToken).ConfigureAwait(false);
        return new UserArtResult(UserArtStatus.Removed, removed);
    }

    /// <summary>The game's own files of a kind (its whole ROM name, any image extension), as stored.</summary>
    private List<string> OwnFiles(GameKey game, string relPath, string kind)
    {
        var files = new List<string>();
        foreach (var extension in MediaKinds.ImageExtensions)
        {
            var relative = PathFor(game, relPath, kind, extension);
            if (File.Exists(Full(relative)))
            {
                files.Add(relative);
            }
        }

        return files;
    }

    private string Full(string relative) => _library.MediaPath(relative);

    private static void CheckKind(string kind)
    {
        if (!MediaKinds.Images.Contains(kind))
        {
            throw new ArgumentException($"'{kind}' isn't an image kind.", nameof(kind));
        }
    }
}
